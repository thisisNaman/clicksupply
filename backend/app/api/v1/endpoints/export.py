"""
Export endpoints — CSV/JSON streaming export for visibility data, responses, and citations.
"""

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.endpoints.analytics import _verify_brand_access
from app.core.database import get_db
from app.models.models import AIResponse, TrackedPrompt, User, VisibilityScore

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{brand_id}/visibility")
async def export_visibility(
    brand_id: uuid.UUID,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export visibility scores as CSV or JSON."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(VisibilityScore)
        .where(VisibilityScore.brand_id == brand_id, VisibilityScore.date >= since)
        .order_by(VisibilityScore.date.asc())
    )
    scores = result.scalars().all()

    if format == "json":
        data = [
            {
                "date": s.date.isoformat(),
                "engine": s.engine.value if hasattr(s.engine, "value") else str(s.engine),
                "share_of_model": s.share_of_model,
                "avg_generative_position": s.avg_generative_position,
                "mention_count": s.mention_count,
                "total_prompts_run": s.total_prompts_run,
                "positive_sentiment_pct": s.positive_sentiment_pct,
                "negative_sentiment_pct": s.negative_sentiment_pct,
                "neutral_sentiment_pct": s.neutral_sentiment_pct,
            }
            for s in scores
        ]
        return Response(
            content=__import__("json").dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=visibility_{brand_id}.json"},
        )

    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "engine", "share_of_model", "avg_generative_position",
        "mention_count", "total_prompts_run",
        "positive_sentiment_pct", "negative_sentiment_pct", "neutral_sentiment_pct",
    ])
    for s in scores:
        writer.writerow([
            s.date.isoformat(),
            s.engine.value if hasattr(s.engine, "value") else str(s.engine),
            s.share_of_model,
            s.avg_generative_position,
            s.mention_count,
            s.total_prompts_run,
            s.positive_sentiment_pct,
            s.negative_sentiment_pct,
            s.neutral_sentiment_pct,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=visibility_{brand_id}.csv"},
    )


@router.get("/{brand_id}/responses")
async def export_responses(
    brand_id: uuid.UUID,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export AI responses as CSV or JSON."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(AIResponse)
        .join(TrackedPrompt)
        .where(TrackedPrompt.brand_id == brand_id, AIResponse.captured_at >= since)
        .order_by(AIResponse.captured_at.desc())
    )
    responses = result.scalars().all()

    if format == "json":
        data = [
            {
                "id": str(r.id),
                "engine": r.engine.value if hasattr(r.engine, "value") else str(r.engine),
                "brand_mentioned": r.brand_mentioned,
                "generative_position": r.generative_position,
                "sentiment": r.sentiment.value if r.sentiment and hasattr(r.sentiment, "value") else str(r.sentiment),
                "captured_at": r.captured_at.isoformat(),
                "cost_usd": float(r.cost_usd) if r.cost_usd else 0,
            }
            for r in responses
        ]
        return Response(
            content=__import__("json").dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=responses_{brand_id}.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "engine", "brand_mentioned", "generative_position",
        "sentiment", "captured_at", "cost_usd",
    ])
    for r in responses:
        writer.writerow([
            str(r.id),
            r.engine.value if hasattr(r.engine, "value") else str(r.engine),
            r.brand_mentioned,
            r.generative_position,
            r.sentiment.value if r.sentiment and hasattr(r.sentiment, "value") else str(r.sentiment),
            r.captured_at.isoformat(),
            float(r.cost_usd) if r.cost_usd else 0,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=responses_{brand_id}.csv"},
    )
