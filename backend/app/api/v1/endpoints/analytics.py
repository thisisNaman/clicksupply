import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    AIResponse,
    Brand,
    CrawlerLog,
    CrawlerType,
    TrackedPrompt,
    User,
    VisibilityScore,
)
from app.schemas.schemas import AIResponseOut, CrawlerStats, VisibilityScoreOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/visibility/{brand_id}", response_model=list[VisibilityScoreOut])
async def get_visibility(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_brand_access(brand_id, user.organization_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(VisibilityScore).where(
        VisibilityScore.brand_id == brand_id, VisibilityScore.date >= since
    )
    if engine:
        query = query.where(VisibilityScore.engine == engine)
    query = query.order_by(VisibilityScore.date.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/responses/{brand_id}", response_model=list[AIResponseOut])
async def get_responses(
    brand_id: uuid.UUID,
    prompt_id: uuid.UUID | None = None,
    engine: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_brand_access(brand_id, user.organization_id, db)

    query = (
        select(AIResponse)
        .join(TrackedPrompt)
        .where(TrackedPrompt.brand_id == brand_id)
    )
    if prompt_id:
        query = query.where(AIResponse.prompt_id == prompt_id)
    if engine:
        query = query.where(AIResponse.engine == engine)
    query = query.order_by(AIResponse.captured_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/crawlers/{brand_id}", response_model=list[CrawlerStats])
async def get_crawler_stats(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_brand_access(brand_id, user.organization_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            CrawlerLog.crawler_type,
            func.count(CrawlerLog.id).label("total_visits"),
            func.count(func.distinct(CrawlerLog.request_path)).label("unique_paths"),
            func.avg(CrawlerLog.response_size_bytes).label("avg_response_size"),
            func.max(CrawlerLog.timestamp).label("latest_visit"),
        )
        .where(
            and_(CrawlerLog.brand_id == brand_id, CrawlerLog.timestamp >= since)
        )
        .group_by(CrawlerLog.crawler_type)
    )

    return [
        CrawlerStats(
            crawler_type=row.crawler_type.value if isinstance(row.crawler_type, CrawlerType) else row.crawler_type,
            total_visits=row.total_visits,
            unique_paths=row.unique_paths,
            avg_response_size=float(row.avg_response_size or 0),
            latest_visit=row.latest_visit,
        )
        for row in result.all()
    ]


@router.get("/share-of-model/{brand_id}")
async def get_share_of_model(
    brand_id: uuid.UUID,
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Real-time SoM calculation from recent responses."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total responses for this brand's prompts
    total_q = (
        select(func.count(AIResponse.id))
        .join(TrackedPrompt)
        .where(TrackedPrompt.brand_id == brand_id, AIResponse.captured_at >= since)
    )
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    # Mentioned count
    mentioned_q = (
        select(func.count(AIResponse.id))
        .join(TrackedPrompt)
        .where(
            TrackedPrompt.brand_id == brand_id,
            AIResponse.captured_at >= since,
            AIResponse.brand_mentioned.is_(True),
        )
    )
    mentioned_result = await db.execute(mentioned_q)
    mentioned = mentioned_result.scalar() or 0

    som = (mentioned / total * 100) if total > 0 else 0.0

    return {
        "brand_id": str(brand_id),
        "period_days": days,
        "total_responses": total,
        "brand_mentioned": mentioned,
        "share_of_model": round(som, 2),
    }


async def _verify_brand_access(
    brand_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.organization_id == org_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
