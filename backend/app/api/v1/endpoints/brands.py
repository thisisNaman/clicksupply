import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    AIResponse,
    Brand,
    Competitor,
    CrawlerLog,
    TrackedPrompt,
    User,
    VisibilityScore,
)
from app.schemas.schemas import (
    BrandCreate,
    BrandOut,
    BrandUpdate,
    CompetitorCreate,
    CompetitorOut,
    PromptCreate,
    PromptOut,
)
from app.services.prompt_generator import generate_prompts_for_brand

logger = structlog.get_logger()
router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
async def create_brand(
    req: BrandCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce one brand per organization
    existing = await db.execute(
        select(func.count(Brand.id)).where(Brand.organization_id == user.organization_id)
    )
    if (existing.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already has a brand. Delete the existing one first.",
        )

    brand = Brand(
        organization_id=user.organization_id,
        name=req.name,
        domain=req.domain,
        aliases=req.aliases,
        industry=req.industry,
    )
    db.add(brand)
    await db.flush()

    # Auto-generate tracked prompts via LLM
    try:
        prompt_texts = await generate_prompts_for_brand(
            brand_name=req.name,
            industry=req.industry,
            domain=req.domain,
        )
        for text in prompt_texts:
            db.add(TrackedPrompt(brand_id=brand.id, text=text, language="en", region="IN"))
        await db.flush()
        logger.info("brand_created_with_prompts", brand=req.name, prompts=len(prompt_texts))
    except Exception as exc:
        # Don't fail brand creation if prompt generation fails
        logger.warning("prompt_auto_generation_failed", brand=req.name, error=str(exc))

    return brand


@router.get("", response_model=list[BrandOut])
async def list_brands(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Brand).where(Brand.organization_id == user.organization_id)
    )
    return result.scalars().all()


@router.get("/{brand_id}", response_model=BrandOut)
async def get_brand(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Brand).where(
            Brand.id == brand_id, Brand.organization_id == user.organization_id
        )
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


@router.put("/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: uuid.UUID,
    req: BrandUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    brand = await _get_brand_or_404(brand_id, user.organization_id, db)
    if req.name is not None:
        brand.name = req.name
    if req.domain is not None:
        brand.domain = req.domain or None
    if req.industry is not None:
        brand.industry = req.industry or None
    if req.aliases is not None:
        brand.aliases = req.aliases
    await db.flush()
    return brand


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    brand = await _get_brand_or_404(brand_id, user.organization_id, db)

    # Delete all child records (no cascade on the model)
    prompt_ids = (
        await db.execute(select(TrackedPrompt.id).where(TrackedPrompt.brand_id == brand.id))
    ).scalars().all()
    if prompt_ids:
        await db.execute(delete(AIResponse).where(AIResponse.prompt_id.in_(prompt_ids)))
    await db.execute(delete(TrackedPrompt).where(TrackedPrompt.brand_id == brand.id))
    await db.execute(delete(VisibilityScore).where(VisibilityScore.brand_id == brand.id))
    await db.execute(delete(CrawlerLog).where(CrawlerLog.brand_id == brand.id))
    await db.execute(delete(Competitor).where(Competitor.brand_id == brand.id))
    await db.delete(brand)
    await db.flush()

    logger.info("brand_deleted", brand_id=str(brand_id), name=brand.name)


# ──── Competitors ────


@router.post("/{brand_id}/competitors", response_model=CompetitorOut, status_code=201)
async def add_competitor(
    brand_id: uuid.UUID,
    req: CompetitorCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    brand = await _get_brand_or_404(brand_id, user.organization_id, db)
    comp = Competitor(brand_id=brand.id, name=req.name, domain=req.domain)
    db.add(comp)
    await db.flush()
    return comp


@router.get("/{brand_id}/competitors", response_model=list[CompetitorOut])
async def list_competitors(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_brand_or_404(brand_id, user.organization_id, db)
    result = await db.execute(select(Competitor).where(Competitor.brand_id == brand_id))
    return result.scalars().all()


# ──── Prompts ────


@router.post("/{brand_id}/prompts", response_model=PromptOut, status_code=201)
async def create_prompt(
    brand_id: uuid.UUID,
    req: PromptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_brand_or_404(brand_id, user.organization_id, db)
    prompt = TrackedPrompt(
        brand_id=brand_id, text=req.text, language=req.language, region=req.region
    )
    db.add(prompt)
    await db.flush()
    return prompt


@router.get("/{brand_id}/prompts", response_model=list[PromptOut])
async def list_prompts(
    brand_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_brand_or_404(brand_id, user.organization_id, db)
    result = await db.execute(
        select(TrackedPrompt).where(
            TrackedPrompt.brand_id == brand_id, TrackedPrompt.is_active.is_(True)
        )
    )
    return result.scalars().all()


async def _get_brand_or_404(
    brand_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Brand:
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.organization_id == org_id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand
