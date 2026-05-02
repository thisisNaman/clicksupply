"""
Brand Health Score — Composite 0-100 score with 5 pillar breakdown.

Pillars:
  1. Visibility (SoM across engines)          — weight 30
  2. Sentiment (positive vs negative ratio)    — weight 20
  3. Citation Quality (own domain %, diversity)— weight 20
  4. Prompt Coverage (% of prompts with brand) — weight 15
  5. Competitive Position (rank vs competitors)— weight 15
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    AIResponse,
    Brand,
    Competitor,
    TrackedPrompt,
    VisibilityScore,
)

logger = structlog.get_logger()

PILLAR_WEIGHTS = {
    "visibility": 30,
    "sentiment": 20,
    "citation_quality": 20,
    "prompt_coverage": 15,
    "competitive_position": 15,
}


class HealthScoreEngine:
    """Calculates composite brand health score with per-pillar breakdown."""

    async def calculate(
        self,
        brand_id: uuid.UUID,
        db: AsyncSession,
        days: int = 7,
    ) -> dict:
        brand = await db.get(Brand, brand_id)
        if not brand:
            return self._empty_result()

        since = datetime.now(timezone.utc) - timedelta(days=days)

        pillars = {}
        pillars["visibility"] = await self._visibility_score(brand_id, since, db)
        pillars["sentiment"] = await self._sentiment_score(brand_id, since, db)
        pillars["citation_quality"] = await self._citation_score(brand_id, brand.domain, since, db)
        pillars["prompt_coverage"] = await self._coverage_score(brand_id, since, db)
        pillars["competitive_position"] = await self._competitive_score(brand_id, since, db)

        # Weighted composite
        composite = sum(
            pillars[p]["score"] * PILLAR_WEIGHTS[p] / 100
            for p in pillars
        )

        # Determine grade
        grade = self._grade(composite)

        # Trend comparison (previous period)
        prev_since = since - timedelta(days=days)
        prev_pillars = {}
        prev_pillars["visibility"] = await self._visibility_score(brand_id, prev_since, since, db)
        prev_pillars["sentiment"] = await self._sentiment_score(brand_id, prev_since, since, db)
        prev_pillars["citation_quality"] = await self._citation_score(brand_id, brand.domain, prev_since, since, db)
        prev_pillars["prompt_coverage"] = await self._coverage_score(brand_id, prev_since, since, db)
        prev_pillars["competitive_position"] = await self._competitive_score(brand_id, prev_since, since, db)
        prev_composite = sum(
            prev_pillars[p]["score"] * PILLAR_WEIGHTS[p] / 100
            for p in prev_pillars
        )

        return {
            "score": round(composite, 1),
            "grade": grade,
            "trend": round(composite - prev_composite, 1),
            "period_days": days,
            "pillars": {
                name: {
                    "score": round(data["score"], 1),
                    "weight": PILLAR_WEIGHTS[name],
                    "detail": data.get("detail", ""),
                    "trend": round(data["score"] - prev_pillars[name]["score"], 1),
                }
                for name, data in pillars.items()
            },
        }

    def _empty_result(self) -> dict:
        return {
            "score": 0,
            "grade": "F",
            "trend": 0,
            "period_days": 7,
            "pillars": {
                name: {"score": 0, "weight": w, "detail": "No data", "trend": 0}
                for name, w in PILLAR_WEIGHTS.items()
            },
        }

    def _grade(self, score: float) -> str:
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"

    # ──── Pillar calculators ────

    async def _visibility_score(
        self, brand_id: uuid.UUID, start: datetime, end_or_db=None, db: AsyncSession | None = None,
    ) -> dict:
        # Support both (brand_id, since, db) and (brand_id, start, end, db) signatures
        if isinstance(end_or_db, AsyncSession):
            db = end_or_db
            end = datetime.now(timezone.utc)
        else:
            end = end_or_db

        result = await db.execute(
            select(func.avg(VisibilityScore.share_of_model))
            .where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.date >= start,
                VisibilityScore.date <= end,
            )
        )
        avg_som = result.scalar() or 0

        # SoM of 50%+ = perfect score; 0% = 0
        score = min(100, avg_som * 2)
        return {"score": score, "detail": f"{avg_som:.1f}% avg SoM"}

    async def _sentiment_score(
        self, brand_id: uuid.UUID, start: datetime, end_or_db=None, db: AsyncSession | None = None,
    ) -> dict:
        if isinstance(end_or_db, AsyncSession):
            db = end_or_db
            end = datetime.now(timezone.utc)
        else:
            end = end_or_db

        result = await db.execute(
            select(
                func.avg(VisibilityScore.positive_sentiment_pct),
                func.avg(VisibilityScore.negative_sentiment_pct),
            )
            .where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.date >= start,
                VisibilityScore.date <= end,
            )
        )
        row = result.one()
        pos_avg = row[0] or 0
        neg_avg = row[1] or 0

        # Score: high positive + low negative = good
        # 80%+ positive & <10% negative = perfect
        pos_component = min(100, pos_avg * 1.25)  # 80% → 100
        neg_penalty = min(50, neg_avg * 2.5)  # 20% negative → 50 penalty
        score = max(0, pos_component - neg_penalty)

        return {"score": score, "detail": f"{pos_avg:.0f}% positive, {neg_avg:.0f}% negative"}

    async def _citation_score(
        self, brand_id: uuid.UUID, brand_domain: str | None, start: datetime, end_or_db=None, db: AsyncSession | None = None,
    ) -> dict:
        if isinstance(end_or_db, AsyncSession):
            db = end_or_db
            end = datetime.now(timezone.utc)
        else:
            end = end_or_db

        result = await db.execute(
            select(AIResponse.citations)
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= start,
                AIResponse.captured_at <= end,
                AIResponse.brand_mentioned == True,
                AIResponse.citations.isnot(None),
            )
            .limit(200)
        )

        domain_counts: dict[str, int] = {}
        for (citations,) in result:
            if not citations:
                continue
            urls = citations if isinstance(citations, list) else citations.get("urls", [])
            for c in urls:
                domain = c.get("domain", "") if isinstance(c, dict) else ""
                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

        total = sum(domain_counts.values())
        if total == 0:
            return {"score": 0, "detail": "No citations found"}

        unique_domains = len(domain_counts)
        own_pct = 0
        if brand_domain:
            own_count = domain_counts.get(brand_domain, 0)
            own_pct = own_count / total * 100 if total else 0

        # Score: own domain cited (40pts max) + diversity bonus (30pts) + volume (30pts)
        own_score = min(40, own_pct * 2)  # 20%+ own domain = max
        diversity_score = min(30, unique_domains * 5)  # 6+ unique domains = max
        volume_score = min(30, total * 3)  # 10+ citations = max
        score = own_score + diversity_score + volume_score

        return {"score": score, "detail": f"{total} citations from {unique_domains} domains, {own_pct:.0f}% own"}

    async def _coverage_score(
        self, brand_id: uuid.UUID, start: datetime, end_or_db=None, db: AsyncSession | None = None,
    ) -> dict:
        if isinstance(end_or_db, AsyncSession):
            db = end_or_db
            end = datetime.now(timezone.utc)
        else:
            end = end_or_db

        result = await db.execute(
            select(
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= start,
                AIResponse.captured_at <= end,
            )
        )
        row = result.one()
        total = row[0] or 0
        mentioned = row[1] or 0
        rate = (mentioned / total * 100) if total else 0

        # 80%+ mention rate = perfect score
        score = min(100, rate * 1.25)
        return {"score": score, "detail": f"{mentioned}/{total} responses ({rate:.0f}%)"}

    async def _competitive_score(
        self, brand_id: uuid.UUID, start: datetime, end_or_db=None, db: AsyncSession | None = None,
    ) -> dict:
        if isinstance(end_or_db, AsyncSession):
            db = end_or_db
            end = datetime.now(timezone.utc)
        else:
            end = end_or_db

        # Get brand SoM
        brand_result = await db.execute(
            select(func.avg(VisibilityScore.share_of_model))
            .where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.date >= start,
                VisibilityScore.date <= end,
            )
        )
        brand_som = brand_result.scalar() or 0

        # Get competitors
        competitors = (await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )).scalars().all()

        if not competitors:
            # No competitors = max competitive score by default
            return {"score": 75, "detail": "No competitors configured"}

        # Count how many competitors have lower SoM (from responses)
        comp_names = [c.name for c in competitors]
        # For now, use brand SoM as a proxy — if brand > 50%, it's doing well vs competitors
        # In practice, this would compare actual competitor SoM data
        if brand_som >= 50:
            score = 90
        elif brand_som >= 30:
            score = 70
        elif brand_som >= 15:
            score = 50
        elif brand_som > 0:
            score = 30
        else:
            score = 0

        return {"score": score, "detail": f"{brand_som:.1f}% SoM vs {len(competitors)} competitors"}


# Singleton
health_score_engine = HealthScoreEngine()
