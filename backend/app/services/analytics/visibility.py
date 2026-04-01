"""
Analytics Service — Computes Share of Model, aggregates visibility scores, and
provides competitive benchmarking, sentiment analysis, citation authority,
trend analysis, and platform comparisons.
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    AIEngine,
    AIResponse,
    Brand,
    Competitor,
    Sentiment,
    TrackedPrompt,
    VisibilityScore,
)

logger = structlog.get_logger()

# Stopwords for keyword extraction (basic English set)
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could and but or nor for yet so at by from in into "
    "of on to with as it its i me my we our you your he she they them their this "
    "that these those what which who whom how when where why all any each every no "
    "not very also just about above after again between both during few more most "
    "other some such than too up down out off over under same own here there then".split()
)


class AnalyticsService:
    """Computes brand visibility analytics from captured AI responses."""

    async def compute_daily_visibility(
        self, brand_id, engine: AIEngine, date: datetime, db: AsyncSession
    ) -> VisibilityScore:
        """Aggregate all responses for a brand+engine on a given date into a VisibilityScore."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        # Get all responses for this brand + engine + date
        result = await db.execute(
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.engine == engine,
                AIResponse.captured_at >= start,
                AIResponse.captured_at < end,
            )
        )
        responses = result.scalars().all()

        if not responses:
            return None

        total = len(responses)
        mentioned = sum(1 for r in responses if r.brand_mentioned)
        som = (mentioned / total * 100) if total > 0 else 0.0

        positions = [r.generative_position for r in responses if r.generative_position is not None]
        avg_position = sum(positions) / len(positions) if positions else None

        positive = sum(1 for r in responses if r.sentiment == Sentiment.POSITIVE)
        negative = sum(1 for r in responses if r.sentiment == Sentiment.NEGATIVE)
        neutral = sum(1 for r in responses if r.sentiment == Sentiment.NEUTRAL)
        total_with_sentiment = positive + negative + neutral or 1

        # Aggregate citations
        all_citations = {}
        for r in responses:
            if r.citations and "sources" in r.citations:
                for c in r.citations["sources"]:
                    domain = c.get("domain", "unknown")
                    all_citations[domain] = all_citations.get(domain, 0) + 1

        top_citations = dict(sorted(all_citations.items(), key=lambda x: x[1], reverse=True)[:10])

        # Upsert visibility score
        existing = await db.execute(
            select(VisibilityScore).where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.engine == engine,
                VisibilityScore.date == start,
            )
        )
        score = existing.scalar_one_or_none()

        if score:
            score.share_of_model = som
            score.avg_generative_position = avg_position
            score.mention_count = mentioned
            score.total_prompts_run = total
            score.positive_sentiment_pct = round(positive / total_with_sentiment * 100, 1)
            score.negative_sentiment_pct = round(negative / total_with_sentiment * 100, 1)
            score.neutral_sentiment_pct = round(neutral / total_with_sentiment * 100, 1)
            score.top_citations = top_citations
        else:
            score = VisibilityScore(
                brand_id=brand_id,
                engine=engine,
                date=start,
                share_of_model=som,
                avg_generative_position=avg_position,
                mention_count=mentioned,
                total_prompts_run=total,
                positive_sentiment_pct=round(positive / total_with_sentiment * 100, 1),
                negative_sentiment_pct=round(negative / total_with_sentiment * 100, 1),
                neutral_sentiment_pct=round(neutral / total_with_sentiment * 100, 1),
                top_citations=top_citations,
            )
            db.add(score)

        await db.flush()
        logger.info(
            "visibility_computed",
            brand_id=str(brand_id),
            engine=engine.value,
            som=som,
            mentions=mentioned,
            total=total,
        )
        return score

    async def get_competitive_benchmark(
        self, brand_id, days: int, db: AsyncSession
    ) -> dict:
        """Compare brand's SoM against its registered competitors."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get brand info
        brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            return {}

        # Get brand's average SoM
        brand_scores = await db.execute(
            select(func.avg(VisibilityScore.share_of_model))
            .where(VisibilityScore.brand_id == brand_id, VisibilityScore.date >= since)
        )
        brand_avg_som = brand_scores.scalar() or 0

        # Get competitors
        comp_result = await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )
        competitors = comp_result.scalars().all()

        return {
            "brand": {"name": brand.name, "avg_som": round(brand_avg_som, 2)},
            "competitors": [
                {"name": c.name, "domain": c.domain}
                for c in competitors
            ],
            "period_days": days,
        }

    # ──────────────────── Sentiment & Keywords ────────────────────

    async def get_sentiment_breakdown(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Aggregate sentiment per engine + extract top keywords from raw responses."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        responses = result.scalars().all()

        # Per-engine sentiment
        engine_groups: dict[str, list] = defaultdict(list)
        for r in responses:
            engine_groups[r.engine.value if hasattr(r.engine, "value") else str(r.engine)].append(r)

        per_engine = []
        for eng, resps in engine_groups.items():
            total = len(resps)
            pos = sum(1 for r in resps if r.sentiment == Sentiment.POSITIVE)
            neg = sum(1 for r in resps if r.sentiment == Sentiment.NEGATIVE)
            neu = sum(1 for r in resps if r.sentiment == Sentiment.NEUTRAL)
            denom = pos + neg + neu or 1
            per_engine.append({
                "engine": eng,
                "positive_pct": round(pos / denom * 100, 1),
                "neutral_pct": round(neu / denom * 100, 1),
                "negative_pct": round(neg / denom * 100, 1),
                "total_responses": total,
            })

        # Top keywords from raw_response
        word_counter: Counter = Counter()
        word_sentiment: dict[str, Counter] = defaultdict(Counter)
        for r in responses:
            if not r.raw_response:
                continue
            words = re.findall(r"[a-zA-Z]{3,}", r.raw_response.lower())
            for w in words:
                if w not in _STOPWORDS:
                    word_counter[w] += 1
                    sent = r.sentiment.value if r.sentiment and hasattr(r.sentiment, "value") else "neutral"
                    word_sentiment[w][sent] += 1

        top_keywords = []
        for word, count in word_counter.most_common(20):
            bias = word_sentiment[word].most_common(1)[0][0] if word_sentiment[word] else "neutral"
            top_keywords.append({"word": word, "count": count, "sentiment_bias": bias})

        # Trend by day
        day_groups: dict[str, dict] = defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0})
        for r in responses:
            day_key = r.captured_at.strftime("%Y-%m-%d")
            if r.sentiment == Sentiment.POSITIVE:
                day_groups[day_key]["pos"] += 1
            elif r.sentiment == Sentiment.NEGATIVE:
                day_groups[day_key]["neg"] += 1
            else:
                day_groups[day_key]["neu"] += 1

        trend = []
        for day_key in sorted(day_groups.keys()):
            d = day_groups[day_key]
            total = d["pos"] + d["neg"] + d["neu"] or 1
            trend.append({
                "date": day_key,
                "positive_pct": round(d["pos"] / total * 100, 1),
                "neutral_pct": round(d["neu"] / total * 100, 1),
                "negative_pct": round(d["neg"] / total * 100, 1),
            })

        return {"per_engine": per_engine, "top_keywords": top_keywords, "trend": trend}

    # ──────────────────── Citation Authority ────────────────────

    async def get_citation_authority(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Aggregate citation URLs from AI responses, group by domain."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
                AIResponse.citations.isnot(None),
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        responses = result.scalars().all()

        domain_counts: Counter = Counter()
        domain_engines: dict[str, set] = defaultdict(set)
        total_citations = 0

        for r in responses:
            sources = []
            if isinstance(r.citations, dict):
                sources = r.citations.get("sources", [])
            eng_name = r.engine.value if hasattr(r.engine, "value") else str(r.engine)
            for cite in sources:
                url = cite.get("url", "")
                domain = cite.get("domain", "")
                if not domain and url:
                    try:
                        domain = urlparse(url).netloc.lower()
                    except Exception:
                        domain = "unknown"
                domain = domain.removeprefix("www.")
                if domain:
                    domain_counts[domain] += 1
                    domain_engines[domain].add(eng_name)
                    total_citations += 1

        top_domains = [
            {"domain": d, "count": c, "engines": sorted(domain_engines[d])}
            for d, c in domain_counts.most_common(25)
        ]

        return {
            "top_domains": top_domains,
            "total_citations": total_citations,
            "unique_domains": len(domain_counts),
        }

    # ──────────────────── Trends Over Time ────────────────────

    async def get_trends(
        self,
        brand_id,
        days: int,
        db: AsyncSession,
        engine_filter: str | None = None,
        granularity: str = "daily",
    ) -> dict:
        """Time-series of visibility score, mention count, avg position."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(VisibilityScore).where(
            VisibilityScore.brand_id == brand_id,
            VisibilityScore.date >= since,
        )
        if engine_filter:
            query = query.where(VisibilityScore.engine == engine_filter)
        query = query.order_by(VisibilityScore.date.asc())

        result = await db.execute(query)
        scores = result.scalars().all()

        # Group by date (or week)
        groups: dict[str, list] = defaultdict(list)
        for s in scores:
            if granularity == "weekly":
                key = s.date.strftime("%Y-W%W")
            else:
                key = s.date.strftime("%Y-%m-%d")
            groups[key].append(s)

        series = []
        for date_key in sorted(groups.keys()):
            items = groups[date_key]
            avg_som = sum(s.share_of_model for s in items) / len(items) if items else 0
            total_mentions = sum(s.mention_count for s in items)
            positions = [s.avg_generative_position for s in items if s.avg_generative_position is not None]
            avg_pos = sum(positions) / len(positions) if positions else None
            avg_pos_pct = sum(s.positive_sentiment_pct for s in items) / len(items) if items else 0

            series.append({
                "date": date_key,
                "visibility_score": round(avg_som, 2),
                "mention_count": total_mentions,
                "avg_position": round(avg_pos, 1) if avg_pos is not None else None,
                "sentiment_positive_pct": round(avg_pos_pct, 1),
            })

        return {"series": series}

    # ──────────────────── Platform Comparison ────────────────────

    async def get_platform_comparison(
        self, brand_id, days: int, db: AsyncSession
    ) -> dict:
        """Side-by-side comparison of all engines for a brand."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(VisibilityScore).where(
                VisibilityScore.brand_id == brand_id,
                VisibilityScore.date >= since,
            )
        )
        scores = result.scalars().all()

        engine_groups: dict[str, list] = defaultdict(list)
        for s in scores:
            key = s.engine.value if hasattr(s.engine, "value") else str(s.engine)
            engine_groups[key].append(s)

        # Count citations per engine
        cite_result = await db.execute(
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
                AIResponse.citations.isnot(None),
            )
        )
        cite_responses = cite_result.scalars().all()
        engine_cite_count: Counter = Counter()
        for r in cite_responses:
            eng = r.engine.value if hasattr(r.engine, "value") else str(r.engine)
            sources = r.citations.get("sources", []) if isinstance(r.citations, dict) else []
            engine_cite_count[eng] += len(sources)

        platforms = []
        for eng, items in engine_groups.items():
            avg_som = sum(s.share_of_model for s in items) / len(items) if items else 0
            positions = [s.avg_generative_position for s in items if s.avg_generative_position is not None]
            avg_pos = sum(positions) / len(positions) if positions else None
            total_mentioned = sum(s.mention_count for s in items)
            total_run = sum(s.total_prompts_run for s in items)
            mention_rate = (total_mentioned / total_run * 100) if total_run else 0
            avg_pos_pct = sum(s.positive_sentiment_pct for s in items) / len(items) if items else 0

            platforms.append({
                "engine": eng,
                "visibility_score": round(avg_som, 2),
                "avg_position": round(avg_pos, 1) if avg_pos is not None else None,
                "mention_rate": round(mention_rate, 1),
                "sentiment_positive_pct": round(avg_pos_pct, 1),
                "citation_count": engine_cite_count.get(eng, 0),
            })

        platforms.sort(key=lambda p: p["visibility_score"], reverse=True)
        return {"platforms": platforms}

    # ──────────────── Enhanced Competitive Benchmarking ────────────────

    async def get_enhanced_benchmark(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Full competitive benchmark: SoM, position, sentiment, rankings."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get brand
        brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            return {}

        async def _get_metrics(bid, name, domain=None):
            query = select(VisibilityScore).where(
                VisibilityScore.brand_id == bid,
                VisibilityScore.date >= since,
            )
            if engine_filter:
                query = query.where(VisibilityScore.engine == engine_filter)

            res = await db.execute(query)
            scores = res.scalars().all()
            if not scores:
                return {
                    "name": name,
                    "domain": domain,
                    "avg_som": 0.0,
                    "avg_position": None,
                    "mention_count": 0,
                    "sentiment_positive_pct": 0.0,
                }

            avg_som = sum(s.share_of_model for s in scores) / len(scores)
            positions = [s.avg_generative_position for s in scores if s.avg_generative_position is not None]
            avg_pos = sum(positions) / len(positions) if positions else None
            mentions = sum(s.mention_count for s in scores)
            avg_pospct = sum(s.positive_sentiment_pct for s in scores) / len(scores)

            return {
                "name": name,
                "domain": domain,
                "avg_som": round(avg_som, 2),
                "avg_position": round(avg_pos, 1) if avg_pos is not None else None,
                "mention_count": mentions,
                "sentiment_positive_pct": round(avg_pospct, 1),
            }

        brand_metrics = await _get_metrics(brand_id, brand.name, brand.domain)

        # Get competitors and compute their metrics from actual AI responses
        comp_result = await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )
        competitors = comp_result.scalars().all()

        # Load all AI responses for this brand's prompts to scan for competitor mentions
        resp_result = await db.execute(
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
            )
        )
        all_responses = resp_result.scalars().all()

        comp_metrics = []
        for c in competitors:
            # Search for competitor mentions in raw AI responses
            search_terms = [c.name.lower()]
            if c.domain:
                search_terms.append(c.domain.lower())
            mentioned_count = 0
            positive_count = 0
            total_with_sentiment = 0
            positions: list[int] = []

            for r in all_responses:
                raw_lower = (r.raw_response or "").lower()
                is_mentioned = any(term in raw_lower for term in search_terms)
                if is_mentioned:
                    mentioned_count += 1
                    # Check if competitor appears in extracted brands_mentioned
                    if r.citations and isinstance(r.citations, dict):
                        for b in r.extra_metadata.get("brands_mentioned", []) if r.extra_metadata else []:
                            if b.get("name", "").lower() in search_terms:
                                if b.get("position"):
                                    positions.append(b["position"])
                                if b.get("sentiment") == "positive":
                                    positive_count += 1
                                total_with_sentiment += 1

            total = len(all_responses) or 1
            comp_som = round(mentioned_count / total * 100, 2)
            avg_pos = round(sum(positions) / len(positions), 1) if positions else None
            pos_pct = round(positive_count / total_with_sentiment * 100, 1) if total_with_sentiment else 0.0

            comp_metrics.append({
                "name": c.name,
                "domain": c.domain,
                "avg_som": comp_som,
                "avg_position": avg_pos,
                "mention_count": mentioned_count,
                "sentiment_positive_pct": pos_pct,
            })

        # Rankings (brand vs competitors by SoM)
        all_entities = [brand_metrics] + comp_metrics
        sorted_by_som = sorted(all_entities, key=lambda x: x["avg_som"], reverse=True)
        som_rank = next(
            (i + 1 for i, e in enumerate(sorted_by_som) if e["name"] == brand.name), 1
        )

        return {
            "brand": brand_metrics,
            "competitors": comp_metrics,
            "rankings": {"som_rank": som_rank, "total_entities": len(all_entities)},
        }


analytics_service = AnalyticsService()
