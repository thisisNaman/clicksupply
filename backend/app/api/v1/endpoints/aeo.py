import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import AuditResult, Brand, User
from app.schemas.schemas import AEOAuditRequest, AEOAuditResult
from app.services.recommendations.aeo_engine import aeo_engine

router = APIRouter(prefix="/aeo", tags=["aeo"])

_CACHE_MINUTES = 60  # serve cached result if audited within this window


@router.post("/audit", response_model=AEOAuditResult)
async def audit_page(
    req: AEOAuditRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run an AEO readiness audit on a web page.

    Returns cached result if the same URL was audited within the last hour.
    Persists every audit for historical tracking.
    """
    # Check cache — reuse recent result for same URL
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_CACHE_MINUTES)
    cached = await db.execute(
        select(AuditResult)
        .where(AuditResult.url == req.url, AuditResult.created_at >= cutoff)
        .order_by(AuditResult.created_at.desc())
        .limit(1)
    )
    existing = cached.scalar_one_or_none()
    if existing:
        return AEOAuditResult(
            url=existing.url,
            score=existing.score,
            recommendations=existing.recommendations,
            schema_suggestions=existing.schema_suggestions,
            llms_txt_content=existing.llms_txt_content,
        )

    # Fresh audit
    result = await aeo_engine.audit_page(req.url)

    # Resolve brand_id if user has a brand with matching domain
    brand_id = None
    from urllib.parse import urlparse
    domain = urlparse(req.url).netloc.replace("www.", "")
    brand_row = await db.execute(
        select(Brand.id).where(
            Brand.organization_id == user.organization_id,
            Brand.domain.ilike(f"%{domain}%"),
        ).limit(1)
    )
    brand_match = brand_row.scalar_one_or_none()
    if brand_match:
        brand_id = brand_match

    # Persist
    audit = AuditResult(
        brand_id=brand_id,
        url=req.url,
        score=result.score,
        recommendations=[r.model_dump() for r in result.recommendations],
        schema_suggestions=result.schema_suggestions,
        llms_txt_content=result.llms_txt_content,
    )
    db.add(audit)
    await db.flush()

    return result


@router.get("/audit/history")
async def get_audit_history(
    url: str | None = Query(default=None),
    brand_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical audit results. Filter by URL or brand_id."""
    q = select(AuditResult).order_by(AuditResult.created_at.desc()).limit(limit)
    if url:
        q = q.where(AuditResult.url == url)
    if brand_id:
        q = q.where(AuditResult.brand_id == brand_id)
    rows = await db.execute(q)
    results = rows.scalars().all()
    return [
        {
            "id": str(r.id),
            "url": r.url,
            "score": r.score,
            "recommendations_count": len(r.recommendations) if r.recommendations else 0,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]
