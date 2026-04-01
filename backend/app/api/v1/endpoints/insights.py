"""
Deep analytics endpoints — Sentiment, Citations, Trends, Platforms, Benchmark.

"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.endpoints.analytics import _verify_brand_access
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    BenchmarkResponse,
    CitationResponse,
    PlatformsResponse,
    SentimentResponse,
    TrendsResponse,
)
from app.services.analytics.visibility import analytics_service

router = APIRouter(prefix="/analytics", tags=["insights"])


@router.get("/sentiment/{brand_id}", response_model=SentimentResponse)
async def get_sentiment(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sentiment breakdown per engine with top keywords and daily trend."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_sentiment_breakdown(
        brand_id, days, db, engine_filter=engine
    )
    return data


@router.get("/citations/{brand_id}", response_model=CitationResponse)
async def get_citations(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Citation authority — top domains cited by AI engines."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_citation_authority(
        brand_id, days, db, engine_filter=engine
    )
    return data


@router.get("/trends/{brand_id}", response_model=TrendsResponse)
async def get_trends(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    granularity: str = Query(default="daily", pattern="^(daily|weekly)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Time-series trends of visibility score, mentions, position."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_trends(
        brand_id, days, db, engine_filter=engine, granularity=granularity
    )
    return data


@router.get("/platforms/{brand_id}", response_model=PlatformsResponse)
async def get_platforms(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Side-by-side platform comparison across all AI engines."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_platform_comparison(brand_id, days, db)
    return data


@router.get("/benchmark/{brand_id}", response_model=BenchmarkResponse)
async def get_benchmark(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enhanced competitive benchmarking — brand vs competitors."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_enhanced_benchmark(
        brand_id, days, db, engine_filter=engine
    )
    return data
