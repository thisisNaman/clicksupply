"""
Background task definitions for the capture pipeline.

Tasks:
  - run_capture_for_brand: Run all tracked prompts against all engines for a brand
  - compute_daily_scores: Compute daily visibility scores after capture
"""

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.models import AIEngine, Brand, TrackedPrompt
from app.services.analytics.visibility import analytics_service
from app.services.capture.engine import ENGINE_MODEL_MAP, capture_engine
from app.services.llm.gateway import llm_gateway

logger = structlog.get_logger()


class _PromptStub:
    """Lightweight stand-in for TrackedPrompt, used to avoid ORM lazy-loading
    during background capture where the DB session is closed."""
    __slots__ = ("id", "text")

    def __init__(self, id, text):
        self.id = id
        self.text = text


def _get_available_engines(requested: list[AIEngine] | None = None) -> list[AIEngine]:
    """Return the list of engines to capture.

    All engines in ENGINE_MODEL_MAP are available via Copilot SDK.
    """
    all_engines = list(ENGINE_MODEL_MAP.keys())
    if requested:
        return [e for e in requested if e in all_engines]
    return all_engines


async def run_capture_for_brand(
    brand_id: str,
    engines: list[AIEngine] | None = None,
    progress_store: dict | None = None,
) -> dict:
    """Run capture for all active prompts of a brand across specified engines.

    Returns summary stats: {prompts_run, responses_captured, errors}.
    If progress_store is provided, it is updated in-place for live polling.

    The DB session is separated from the Copilot SDK calls to avoid greenlet
    context conflicts between asyncpg and the SDK's subprocess transport.
    """
    target_engines = _get_available_engines(engines)
    stats = {"prompts_run": 0, "responses_captured": 0, "errors": 0}

    if not target_engines:
        logger.error("capture_no_engines_available", brand_id=brand_id,
                     hint="No engines configured for capture")
        return stats

    # Phase 1: Load data into plain Python objects, then close the session
    async with async_session() as db:
        brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            logger.error("capture_brand_not_found", brand_id=brand_id)
            return stats

        prompt_result = await db.execute(
            select(TrackedPrompt).where(
                TrackedPrompt.brand_id == brand_id,
                TrackedPrompt.is_active.is_(True),
            )
        )
        prompts = prompt_result.scalars().all()

        if not prompts:
            logger.info("capture_no_prompts", brand_id=brand_id)
            return stats

        # Extract plain values so we don't touch ORM objects during SDK calls
        brand_name = brand.name
        brand_aliases = brand.aliases
        prompt_data = [(p.id, p.text) for p in prompts]

    # Phase 2: Run capture loop with Copilot SDK (no open DB session)
    _MAX_STEPS = 20
    if len(prompt_data) * len(target_engines) > _MAX_STEPS:
        max_prompts = max(1, _MAX_STEPS // len(target_engines))
        prompt_data = prompt_data[:max_prompts]

    total_steps = len(prompt_data) * len(target_engines)

    if progress_store is not None:
        progress_store.update({
            "total_prompts": len(prompt_data),
            "total_engines": len(target_engines),
            "total_steps": total_steps,
            "completed_steps": 0,
        })

    logger.info(
        "capture_started",
        brand=brand_name,
        prompts=len(prompt_data),
        engines=[e.value for e in target_engines],
    )

    completed_steps = 0
    for prompt_id, prompt_text in prompt_data:
        stats["prompts_run"] += 1
        for engine in target_engines:
            if progress_store is not None:
                progress_store.update({
                    "current_prompt": prompt_text[:80],
                    "current_engine": engine.value,
                    "prompts_run": stats["prompts_run"],
                    "responses_captured": stats["responses_captured"],
                    "errors": stats["errors"],
                })

            try:
                # Build a minimal prompt-like object for the capture engine
                prompt_obj = _PromptStub(id=prompt_id, text=prompt_text)

                # Run Copilot SDK capture (no DB session involved here)
                ai_response = await capture_engine.capture_response(
                    prompt=prompt_obj,
                    engine=engine,
                    brand_name=brand_name,
                    brand_aliases=brand_aliases,
                    db=None,  # Don't pass DB — we save separately below
                )

                # Phase 3: Save with a fresh short-lived session
                async with async_session() as db:
                    db.add(ai_response)
                    # Backfill intent on the TrackedPrompt from the first response
                    if ai_response.extra_metadata and ai_response.extra_metadata.get("intent"):
                        prompt_row = await db.get(TrackedPrompt, prompt_id)
                        if prompt_row and not prompt_row.intent:
                            prompt_row.intent = ai_response.extra_metadata["intent"]
                    await db.commit()

                stats["responses_captured"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.error(
                    "capture_error",
                    prompt_id=str(prompt_id),
                    engine=engine.value,
                    error=str(exc),
                )

            completed_steps += 1
            if progress_store is not None:
                progress_store["completed_steps"] = completed_steps

    logger.info("capture_completed", brand=brand_name, **stats)
    return stats


async def compute_daily_scores(brand_id: str) -> int:
    """Compute visibility scores for today across all engines for a brand."""
    today = datetime.now(timezone.utc)
    scores_computed = 0

    async with async_session() as db:
        for engine in AIEngine:
            try:
                score = await analytics_service.compute_daily_visibility(
                    brand_id=brand_id,
                    engine=engine,
                    date=today,
                    db=db,
                )
                if score:
                    scores_computed += 1
            except Exception as exc:
                logger.error(
                    "score_compute_error",
                    brand_id=brand_id,
                    engine=engine.value,
                    error=str(exc),
                )

        await db.commit()

    logger.info("scores_computed", brand_id=brand_id, count=scores_computed)
    return scores_computed


async def run_daily_capture_all() -> None:
    """Run capture + scoring for all brands. Called by the scheduler."""
    async with async_session() as db:
        result = await db.execute(select(Brand))
        brands = result.scalars().all()

    logger.info("daily_capture_starting", brand_count=len(brands))

    for brand in brands:
        try:
            await run_capture_for_brand(str(brand.id))
            await compute_daily_scores(str(brand.id))
        except Exception as exc:
            logger.error(
                "daily_capture_brand_error",
                brand_id=str(brand.id),
                error=str(exc),
            )

    logger.info("daily_capture_complete")
