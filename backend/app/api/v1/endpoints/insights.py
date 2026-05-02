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
    PromptBrandMatrix,
    BenchmarkResponse,
    CitationResponse,
    CoCitationResponse,
    CompetitorCitationsResponse,
    IntentResponse,
    PlatformsResponse,
    SentimentResponse,
    TopicClusterResponse,
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


@router.get("/intent/{brand_id}", response_model=IntentResponse)
async def get_intent(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Intent distribution across tracked prompts."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    data = await analytics_service.get_intent_distribution(
        brand_id, days, db, engine_filter=engine
    )
    return data


@router.get("/co-citations/{brand_id}", response_model=CoCitationResponse)
async def get_co_citations(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Co-citation mapping and uncited prompt detection."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    co_data = await analytics_service.get_co_citation_map(
        brand_id, days, db, engine_filter=engine
    )
    gap_data = await analytics_service.get_uncited_prompts(
        brand_id, days, db, engine_filter=engine
    )
    return {
        "co_cited_brands": co_data["co_cited_brands"],
        "total_responses_with_brand": co_data["total_responses_with_brand"],
        "uncited_gaps": gap_data["gaps"],
        "total_prompts_analyzed": gap_data["total_prompts_analyzed"],
    }


@router.get("/prompt-brands/{brand_id}", response_model=PromptBrandMatrix)
async def get_prompt_brands(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prompt-wise brand distribution — which brands appear in which prompts across engines."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    return await analytics_service.get_prompt_brand_matrix(
        brand_id, days, db, engine_filter=engine
    )


@router.get("/topics/{brand_id}", response_model=TopicClusterResponse)
async def get_topic_clusters(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    language: str | None = None,
    region: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Group prompts into topic clusters with per-topic visibility analytics."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    return await analytics_service.get_topic_clusters(
        brand_id, days, db, engine_filter=engine, language=language, region=region
    )


@router.get("/competitive-citations/{brand_id}", response_model=CompetitorCitationsResponse)
async def get_competitive_citations(
    brand_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    engine: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare which domains power your brand's citations vs competitors'."""
    await _verify_brand_access(brand_id, user.organization_id, db)
    return await analytics_service.get_competitive_citations(
        brand_id, days, db, engine_filter=engine
    )
