"""
Manual capture trigger endpoint.

POST /api/v1/capture/run — trigger capture for a brand (background task).
GET  /api/v1/capture/progress/{brand_id} — poll progress.
GET  /api/v1/capture/status — available engines.
"""

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Brand, User
from app.workers.tasks import compute_daily_scores, run_capture_for_brand

logger = structlog.get_logger()
router = APIRouter(prefix="/capture", tags=["capture"])

# Track in-flight captures per brand
_running_captures: set[str] = set()

# In-memory progress store: brand_id -> progress dict
_capture_progress: dict[str, dict[str, Any]] = {}

# Track asyncio tasks for cancellation
_capture_tasks: dict[str, asyncio.Task] = {}


class CaptureRequest(BaseModel):
    brand_id: uuid.UUID
    engines: list[str] | None = None  # Optional engine filter


class CaptureResponse(BaseModel):
    status: str
    brand_id: str


class CaptureProgress(BaseModel):
    status: str  # "running" | "completed" | "failed" | "idle"
    brand_id: str
    total_prompts: int
    total_engines: int
    completed_steps: int
    total_steps: int
    current_prompt: str | None = None
    current_engine: str | None = None
    prompts_run: int = 0
    responses_captured: int = 0
    errors: int = 0
    scores_computed: int = 0
    error_message: str | None = None


async def _run_capture_background(brand_id_str: str, engines: list | None):
    """Background coroutine that runs capture and updates progress."""
    try:
        stats = await run_capture_for_brand(
            brand_id_str,
            engines=engines,
            progress_store=_capture_progress.get(brand_id_str),
        )

        # Compute scores after capture
        scores = await compute_daily_scores(brand_id_str)

        if brand_id_str in _capture_progress:
            _capture_progress[brand_id_str].update({
                "status": "completed",
                "prompts_run": stats["prompts_run"],
                "responses_captured": stats["responses_captured"],
                "errors": stats["errors"],
                "scores_computed": scores,
            })
    except asyncio.CancelledError:
        logger.info("capture_cancelled", brand_id=brand_id_str)
        if brand_id_str in _capture_progress:
            _capture_progress[brand_id_str].update({
                "status": "cancelled",
                "error_message": "Capture cancelled by user",
            })
    except Exception as exc:
        logger.error("background_capture_failed", brand_id=brand_id_str, error=str(exc))
        if brand_id_str in _capture_progress:
            _capture_progress[brand_id_str].update({
                "status": "failed",
                "error_message": str(exc),
            })
    finally:
        _running_captures.discard(brand_id_str)
        _capture_tasks.pop(brand_id_str, None)


@router.post("/run", response_model=CaptureResponse)
async def trigger_capture(
    req: CaptureRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger capture for a brand. Returns immediately; poll /progress for updates."""
    # Verify brand access
    result = await db.execute(
        select(Brand).where(
            Brand.id == req.brand_id,
            Brand.organization_id == user.organization_id,
        )
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    brand_id_str = str(req.brand_id)

    # Rate limit: 1 concurrent capture per brand
    if brand_id_str in _running_captures:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Capture already in progress for this brand",
        )

    _running_captures.add(brand_id_str)

    # Parse engine filter
    from app.models.models import AIEngine
    parsed_engines = None
    if req.engines:
        parsed_engines = []
        for e in req.engines:
            try:
                parsed_engines.append(AIEngine(e))
            except ValueError:
                _running_captures.discard(brand_id_str)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown engine: {e}",
                )

    # Initialise progress
    _capture_progress[brand_id_str] = {
        "status": "running",
        "brand_id": brand_id_str,
        "total_prompts": 0,
        "total_engines": 0,
        "completed_steps": 0,
        "total_steps": 0,
        "current_prompt": None,
        "current_engine": None,
        "prompts_run": 0,
        "responses_captured": 0,
        "errors": 0,
        "scores_computed": 0,
        "error_message": None,
    }

    # Fire background task
    task = asyncio.create_task(_run_capture_background(brand_id_str, parsed_engines))
    _capture_tasks[brand_id_str] = task

    return CaptureResponse(status="started", brand_id=brand_id_str)


@router.get("/progress/{brand_id}", response_model=CaptureProgress)
async def capture_progress(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """Poll the progress of a capture job."""
    brand_id_str = str(brand_id)
    progress = _capture_progress.get(brand_id_str)
    if not progress:
        return CaptureProgress(
            status="idle",
            brand_id=brand_id_str,
            total_prompts=0,
            total_engines=0,
            completed_steps=0,
            total_steps=0,
        )
    return CaptureProgress(**progress)


@router.post("/cancel/{brand_id}")
async def cancel_capture(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """Cancel a running capture job."""
    brand_id_str = str(brand_id)
    task = _capture_tasks.get(brand_id_str)
    if not task or task.done():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No running capture found for this brand",
        )
    task.cancel()
    return {"status": "cancelling", "brand_id": brand_id_str}


@router.get("/status")
async def capture_status(user: User = Depends(get_current_user)):
    """Report capture engine status. Browser capture + Copilot SDK analysis."""
    engines_status = {
        "PERPLEXITY": "browser",
        "GOOGLE_AIO": "browser",
        "COPILOT": "browser",
        "CHATGPT": "needs_auth",
        "GEMINI": "needs_auth",
    }

    return {
        "capture_mode": "browser",
        "analysis_mode": "copilot_sdk",
        "engines": engines_status,
        "available_count": sum(1 for v in engines_status.values() if v == "browser"),
    }
