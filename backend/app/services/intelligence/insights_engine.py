"""
Smart Insights Engine — Generates actionable AI-powered insights from brand analytics data.

Analyzes recent capture data to surface patterns, opportunities, and threats:
- SoM changes per engine
- Competitive displacement alerts
- Uncited prompt opportunities
- Sentiment shifts
- Citation source changes
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
from app.services.llm.gateway import ModelTier, llm_gateway

logger = structlog.get_logger()


# TTL cache: brand_id -> (timestamp, insights)
_insights_cache: dict[uuid.UUID, tuple[datetime, list[dict]]] = {}
_CACHE_TTL = timedelta(minutes=60)


class InsightsEngine:
    """Generates weekly/daily smart insights from brand data."""

    async def generate_insights(
        self,
        brand_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Generate all insight types and return sorted by priority."""
        brand = await db.get(Brand, brand_id)
        if not brand:
            return []

        # Return cached insights if still fresh
        now = datetime.now(timezone.utc)
        cached = _insights_cache.get(brand_id)
        if cached and (now - cached[0]) < _CACHE_TTL:
            return cached[1]

        insights: list[dict] = []

        # Gather data for insight generation
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        # Current & previous period visibility scores
        current_scores = await self._get_scores(brand_id, week_ago, now, db)
        previous_scores = await self._get_scores(brand_id, two_weeks_ago, week_ago, db)

        # Generate each insight type
        insights.extend(self._som_change_insights(brand.name, current_scores, previous_scores))
        insights.extend(self._sentiment_shift_insights(brand.name, current_scores, previous_scores))
        insights.extend(await self._competitive_displacement_insights(brand_id, brand.name, db))
        insights.extend(await self._uncited_opportunity_insights(brand_id, brand.name, db))
        insights.extend(await self._citation_quality_insights(brand_id, brand.name, db))
        insights.extend(await self._coverage_gap_insights(brand_id, brand.name, db))

        # If we have enough data, ask LLM for a narrative summary
        if len(insights) >= 2:
            summary = await self._generate_llm_summary(brand.name, insights)
            if summary:
                insights.insert(0, summary)

        # Sort by priority (critical > warning > opportunity > info)
        priority_order = {"critical": 0, "warning": 1, "opportunity": 2, "info": 3}
        insights.sort(key=lambda x: priority_order.get(x.get("severity", "info"), 4))

        # Cache results
        _insights_cache[brand_id] = (datetime.now(timezone.utc), insights)

        return insights

    async def _get_scores(
        self, brand_id: uuid.UUID, start: datetime, end: datetime, db: AsyncSession
    ) -> list[VisibilityScore]:
        result = await db.execute(
            select(VisibilityScore)
            .where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.date >= start,
                VisibilityScore.date <= end,
            )
        )
        return list(result.scalars().all())

    def _som_change_insights(
        self,
        brand_name: str,
        current: list[VisibilityScore],
        previous: list[VisibilityScore],
    ) -> list[dict]:
        """Detect significant SoM changes per engine."""
        insights = []

        # Aggregate SoM by engine for each period
        curr_by_engine: dict[str, list[float]] = {}
        prev_by_engine: dict[str, list[float]] = {}

        for s in current:
            curr_by_engine.setdefault(s.engine.value if hasattr(s.engine, 'value') else s.engine, []).append(s.share_of_model)
        for s in previous:
            prev_by_engine.setdefault(s.engine.value if hasattr(s.engine, 'value') else s.engine, []).append(s.share_of_model)

        for engine, curr_vals in curr_by_engine.items():
            curr_avg = sum(curr_vals) / len(curr_vals) if curr_vals else 0
            prev_vals = prev_by_engine.get(engine, [])
            prev_avg = sum(prev_vals) / len(prev_vals) if prev_vals else 0

            if prev_avg == 0:
                continue

            change_pct = ((curr_avg - prev_avg) / prev_avg) * 100

            if abs(change_pct) >= 10:
                direction = "increased" if change_pct > 0 else "dropped"
                severity = "critical" if change_pct < -15 else "warning" if change_pct < 0 else "opportunity"
                insights.append({
                    "type": "som_change",
                    "severity": severity,
                    "engine": engine,
                    "title": f"SoM {direction} {abs(change_pct):.0f}% on {engine.title()}",
                    "description": f"Your Share of Model on {engine.title()} {direction} from {prev_avg:.1f}% to {curr_avg:.1f}% this week.",
                    "metric_before": round(prev_avg, 1),
                    "metric_after": round(curr_avg, 1),
                    "change_pct": round(change_pct, 1),
                    "action": f"Review recent {engine.title()} responses to understand what changed. Check if competitor content was updated.",
                })

        return insights

    def _sentiment_shift_insights(
        self,
        brand_name: str,
        current: list[VisibilityScore],
        previous: list[VisibilityScore],
    ) -> list[dict]:
        """Detect significant sentiment shifts."""
        insights = []

        # Aggregate sentiment
        curr_pos = [s.positive_sentiment_pct for s in current if s.positive_sentiment_pct > 0]
        prev_pos = [s.positive_sentiment_pct for s in previous if s.positive_sentiment_pct > 0]
        curr_neg = [s.negative_sentiment_pct for s in current if s.negative_sentiment_pct > 0]
        prev_neg = [s.negative_sentiment_pct for s in previous if s.negative_sentiment_pct > 0]

        curr_pos_avg = sum(curr_pos) / len(curr_pos) if curr_pos else 0
        prev_pos_avg = sum(prev_pos) / len(prev_pos) if prev_pos else 0
        curr_neg_avg = sum(curr_neg) / len(curr_neg) if curr_neg else 0
        prev_neg_avg = sum(prev_neg) / len(prev_neg) if prev_neg else 0

        # Negative sentiment spike
        if curr_neg_avg > prev_neg_avg + 10:
            insights.append({
                "type": "sentiment_shift",
                "severity": "warning",
                "title": f"Negative sentiment up {curr_neg_avg - prev_neg_avg:.0f}pp",
                "description": f"Negative sentiment across engines increased from {prev_neg_avg:.0f}% to {curr_neg_avg:.0f}%. This may indicate recent negative coverage or product issues being picked up by AI models.",
                "metric_before": round(prev_neg_avg, 1),
                "metric_after": round(curr_neg_avg, 1),
                "action": "Check recent AI responses for negative mentions. Review your brand's recent news and social media for potential causes.",
            })

        # Positive sentiment improvement
        if curr_pos_avg > prev_pos_avg + 10:
            insights.append({
                "type": "sentiment_shift",
                "severity": "info",
                "title": f"Positive sentiment up {curr_pos_avg - prev_pos_avg:.0f}pp",
                "description": f"Positive sentiment improved from {prev_pos_avg:.0f}% to {curr_pos_avg:.0f}%. Your brand perception is trending well.",
                "metric_before": round(prev_pos_avg, 1),
                "metric_after": round(curr_pos_avg, 1),
                "action": "Keep building on this momentum. Ensure your positive content remains fresh and authoritative.",
            })

        return insights

    async def _competitive_displacement_insights(
        self, brand_id: uuid.UUID, brand_name: str, db: AsyncSession
    ) -> list[dict]:
        """Detect prompts where competitors gained and you lost."""
        insights = []
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # Find prompts where brand is NOT mentioned but competitors are
        competitors = (await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )).scalars().all()

        if not competitors:
            return insights

        comp_names = {c.name.lower(): c.name for c in competitors}

        # Get recent responses
        recent = (await db.execute(
            select(AIResponse, TrackedPrompt.text)
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= week_ago,
            )
            .order_by(AIResponse.captured_at.desc())
            .limit(500)
        )).all()

        # Group by prompt
        prompt_results: dict[str, dict] = {}
        for resp, prompt_text in recent:
            if prompt_text not in prompt_results:
                prompt_results[prompt_text] = {"brand_mentioned": False, "competitor_engines": set()}

            if resp.brand_mentioned:
                prompt_results[prompt_text]["brand_mentioned"] = True

            # Check for competitor mentions in metadata
            brands_mentioned = (resp.extra_metadata or {}).get("brands_mentioned", [])
            for bm in brands_mentioned:
                name = bm.get("name", "").lower() if isinstance(bm, dict) else str(bm).lower()
                if name in comp_names:
                    engine_val = resp.engine.value if hasattr(resp.engine, 'value') else resp.engine
                    prompt_results[prompt_text]["competitor_engines"].add(
                        f"{comp_names[name]} on {engine_val}"
                    )

        # Find displacement patterns
        displacement_count = 0
        displacement_examples = []
        for prompt_text, data in prompt_results.items():
            if not data["brand_mentioned"] and data["competitor_engines"]:
                displacement_count += 1
                if len(displacement_examples) < 3:
                    displacement_examples.append({
                        "prompt": prompt_text[:80],
                        "competitors": list(data["competitor_engines"])[:3],
                    })

        if displacement_count >= 2:
            insights.append({
                "type": "competitive_displacement",
                "severity": "critical",
                "title": f"Competitors cited in {displacement_count} prompts where you're absent",
                "description": f"Competitors appear in {displacement_count} prompts where {brand_name} is not mentioned. These are high-priority content gaps.",
                "examples": displacement_examples,
                "action": "Create targeted content for these prompts. Focus on answer-first format with structured data that AI engines can easily extract.",
            })

        return insights

    async def _uncited_opportunity_insights(
        self, brand_id: uuid.UUID, brand_name: str, db: AsyncSession
    ) -> list[dict]:
        """Find high-value prompts where brand coverage is low."""
        insights = []
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # Get prompts with low mention rate
        result = await db.execute(
            select(
                TrackedPrompt.text,
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(AIResponse, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                TrackedPrompt.is_active == True,
                AIResponse.captured_at >= week_ago,
            )
            .group_by(TrackedPrompt.text)
            .having(func.count(AIResponse.id) >= 3)
        )

        low_coverage = []
        for row in result:
            mention_rate = (row.mentioned or 0) / row.total * 100 if row.total else 0
            if mention_rate < 20 and row.total >= 3:
                low_coverage.append({
                    "prompt": row.text[:80],
                    "mention_rate": round(mention_rate, 1),
                    "total_responses": row.total,
                })

        if low_coverage:
            insights.append({
                "type": "uncited_opportunity",
                "severity": "opportunity",
                "title": f"{len(low_coverage)} prompts with <20% mention rate",
                "description": f"{brand_name} appears in less than 20% of AI responses for {len(low_coverage)} tracked prompts. These are high-priority AEO opportunities.",
                "prompts": low_coverage[:5],
                "action": "Create answer-first content targeting these prompts. Add FAQ schema markup and ensure your content directly answers the query.",
            })

        return insights

    async def _citation_quality_insights(
        self, brand_id: uuid.UUID, brand_name: str, db: AsyncSession
    ) -> list[dict]:
        """Analyze citation source quality."""
        insights = []
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        result = await db.execute(
            select(AIResponse.citations)
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= week_ago,
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
            return insights

        # Check if brand's own domain is cited
        brand = await db.get(Brand, brand_id)
        brand_domain = brand.domain if brand else None

        if brand_domain:
            own_citations = domain_counts.get(brand_domain, 0)
            own_pct = (own_citations / total * 100) if total else 0

            if own_pct < 10:
                insights.append({
                    "type": "citation_quality",
                    "severity": "warning",
                    "title": f"Your domain cited in only {own_pct:.0f}% of brand mentions",
                    "description": f"When AI engines mention {brand_name}, they cite {brand_domain} only {own_pct:.0f}% of the time. Third-party sources dominate your brand narrative.",
                    "top_sources": [
                        {"domain": d, "count": c}
                        for d, c in sorted(domain_counts.items(), key=lambda x: -x[1])[:5]
                    ],
                    "action": "Strengthen your domain authority. Ensure your site has comprehensive, well-structured content that AI engines prefer to cite directly.",
                })

        return insights

    async def _coverage_gap_insights(
        self, brand_id: uuid.UUID, brand_name: str, db: AsyncSession
    ) -> list[dict]:
        """Identify engine-specific coverage gaps."""
        insights = []
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        result = await db.execute(
            select(
                AIResponse.engine,
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= week_ago,
            )
            .group_by(AIResponse.engine)
        )

        engine_rates = []
        for row in result:
            rate = (row.mentioned or 0) / row.total * 100 if row.total else 0
            engine_val = row.engine.value if hasattr(row.engine, 'value') else row.engine
            engine_rates.append({"engine": engine_val, "rate": round(rate, 1), "total": row.total})

        if len(engine_rates) >= 2:
            best = max(engine_rates, key=lambda x: x["rate"])
            worst = min(engine_rates, key=lambda x: x["rate"])

            if best["rate"] - worst["rate"] > 20:
                insights.append({
                    "type": "coverage_gap",
                    "severity": "opportunity",
                    "title": f"{worst['engine'].title()} lags {best['engine'].title()} by {best['rate'] - worst['rate']:.0f}pp",
                    "description": f"Your mention rate on {worst['engine'].title()} ({worst['rate']}%) is significantly lower than {best['engine'].title()} ({best['rate']}%). Different engines weight different content signals.",
                    "engine_breakdown": engine_rates,
                    "action": f"Research what content formats {worst['engine'].title()} prefers. Update your content strategy to improve visibility on underperforming engines.",
                })

        return insights

    async def _generate_llm_summary(self, brand_name: str, insights: list[dict]) -> dict | None:
        """Generate a natural language executive summary of all insights."""
        try:
            bullet_points = "\n".join(
                f"- [{i['severity'].upper()}] {i['title']}: {i.get('description', '')}"
                for i in insights[:8]
            )

            prompt = f"""You are an AI visibility analyst for the brand "{brand_name}".
Based on these findings from the past week, write a 2-3 sentence executive summary.
Be specific with numbers. Be direct and actionable. No fluff.

Findings:
{bullet_points}

Write ONLY the summary paragraph, nothing else."""

            result = await llm_gateway.complete(
                prompt=prompt,
                tier=ModelTier.STANDARD,
                max_tokens=200,
                use_cache=False,
            )

            return {
                "type": "weekly_summary",
                "severity": "info",
                "title": "Weekly Intelligence Brief",
                "description": result.get("content", "").strip(),
                "action": "Review individual insights below for detailed recommendations.",
            }
        except Exception as e:
            logger.warning("insights_summary_failed", error=str(e))
            return None


# Singleton
insights_engine = InsightsEngine()
