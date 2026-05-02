"""
Intelligence API — Smart Insights, Brand Health Score, and AEO Action Center.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.endpoints.analytics import _verify_brand_access
from app.core.database import get_db, async_session
from app.models.models import User
from app.schemas.schemas import (
    ActionItem,
    ActionsResponse,
    ActionStatusUpdate,
    HealthScoreResponse,
    InsightsResponse,
)
from app.services.intelligence.action_center import action_center
from app.services.intelligence.health_score import health_score_engine
from app.services.intelligence.insights_engine import insights_engine

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ──── Smart Insights ────


@router.get("/insights/{brand_id}", response_model=InsightsResponse)
async def get_smart_insights(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered actionable insights for a brand."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    insights = await insights_engine.generate_insights(brand_id, db)
    return {
        "insights": insights,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ──── Brand Health Score ────


@router.get("/health/{brand_id}", response_model=HealthScoreResponse)
async def get_health_score(
    brand_id: uuid.UUID,
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate composite brand health score with pillar breakdown."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    return await health_score_engine.calculate(brand_id, db, days)


# ──── Action Center ────

# Track running generation tasks to prevent duplicates
_running_generations: set[str] = set()


async def _run_generation(brand_id: uuid.UUID):
    """Background task: generate actions with a fresh DB session."""
    bid = str(brand_id)
    try:
        async with async_session() as db:
            await action_center.generate_actions(brand_id, db)
            await db.commit()
    except Exception as e:
        from app.services.intelligence.action_center import _generation_progress
        _generation_progress[bid] = {
            "status": "failed",
            "step": 0,
            "total_steps": 5,
            "stage": "Error",
            "detail": str(e)[:200],
            "actions_so_far": 0,
        }
    finally:
        _running_generations.discard(bid)


@router.post("/actions/{brand_id}/generate")
async def generate_actions(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kick off action generation as a background task. Poll /progress for status."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    bid = str(brand_id)

    if bid in _running_generations:
        return {"status": "already_running", "brand_id": bid}

    _running_generations.add(bid)
    # Launch as a concurrent task (not FastAPI BackgroundTasks which runs after response)
    asyncio.create_task(_run_generation(brand_id))

    return {"status": "started", "brand_id": bid}


@router.get("/actions/{brand_id}/progress")
async def get_generation_progress(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll action generation progress (legacy fallback)."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    progress = action_center.get_generation_progress(brand_id)
    if not progress:
        return {"status": "idle", "step": 0, "total_steps": 6, "stage": "", "detail": "", "actions_so_far": 0}
    return progress


@router.get("/actions/{brand_id}/progress/stream")
async def stream_generation_progress(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of action generation progress. Closes when done/failed/idle."""
    await _verify_brand_access(brand_id, user.organization_id, db)

    async def _event_generator():
        last_sent = None
        idle_ticks = 0
        while True:
            progress = action_center.get_generation_progress(brand_id)
            payload = progress or {"status": "idle", "step": 0, "total_steps": 6, "stage": "", "detail": "", "actions_so_far": 0}

            # Only send if changed
            if payload != last_sent:
                yield f"data: {json.dumps(payload)}\n\n"
                last_sent = payload
                idle_ticks = 0

                # Terminal states — send and close
                if payload.get("status") in ("completed", "failed"):
                    return
            else:
                idle_ticks += 1
                # If nothing's happening for 60s, close the stream
                if idle_ticks > 30:
                    yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
                    return

            await asyncio.sleep(2)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/actions/{brand_id}", response_model=ActionsResponse)
async def get_actions(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current action list for a brand."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    actions = await action_center.get_actions(brand_id, db)
    pending = sum(1 for a in actions if a["status"] == "pending")
    completed = sum(1 for a in actions if a["status"] == "completed")
    return {"actions": actions, "total": len(actions), "pending": pending, "completed": completed}


@router.patch("/actions/{brand_id}/{action_id}")
async def update_action_status(
    brand_id: uuid.UUID,
    action_id: str,
    body: ActionStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an action's status (pending, in_progress, completed, dismissed)."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    action = await action_center.update_action_status(brand_id, action_id, body.status, db)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/actions/{brand_id}/{action_id}/verify", response_model=ActionItem)
async def verify_action(
    brand_id: uuid.UUID,
    action_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run the relevant check for an action and compare to baseline."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    result = await action_center.verify_action(brand_id, action_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found")
    return result
