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

    # ──────────────── Intent Distribution ────────────────

    async def get_intent_distribution(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Aggregate intent classification across prompts and their responses."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(AIResponse, TrackedPrompt)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        rows = result.all()

        # Count intents from extra_metadata (per response)
        intent_counter: Counter = Counter()
        intent_prompts: dict[str, dict[str, dict]] = defaultdict(dict)  # intent -> prompt_id -> {text, mentions, total}

        for resp, prompt in rows:
            intent = "informational"
            if resp.extra_metadata and resp.extra_metadata.get("intent"):
                intent = resp.extra_metadata["intent"]
            elif prompt.intent:
                intent = prompt.intent
            intent_counter[intent] += 1

            pid = str(prompt.id)
            if pid not in intent_prompts[intent]:
                intent_prompts[intent][pid] = {"text": prompt.text, "mentions": 0, "total": 0}
            intent_prompts[intent][pid]["total"] += 1
            if resp.brand_mentioned:
                intent_prompts[intent][pid]["mentions"] += 1

        total = sum(intent_counter.values()) or 1
        distribution = [
            {"intent": intent, "count": count, "pct": round(count / total * 100, 1)}
            for intent, count in intent_counter.most_common()
        ]

        # Top prompts per intent (by visibility %)
        top_prompts_by_intent = {}
        for intent, prompts_map in intent_prompts.items():
            sorted_prompts = sorted(
                prompts_map.values(),
                key=lambda p: (p["mentions"] / p["total"] * 100) if p["total"] else 0,
                reverse=True,
            )[:5]
            top_prompts_by_intent[intent] = [
                {
                    "text": p["text"],
                    "visibility_pct": round(p["mentions"] / p["total"] * 100, 1) if p["total"] else 0,
                }
                for p in sorted_prompts
            ]

        return {"distribution": distribution, "top_prompts_by_intent": top_prompts_by_intent}

    # ──────────────── Co-Citation Mapping ────────────────

    async def get_co_citation_map(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Find brands that appear alongside the target brand in AI responses."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            return {"co_cited_brands": [], "total_responses_with_brand": 0}

        query = (
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
                AIResponse.brand_mentioned.is_(True),
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        responses = result.scalars().all()

        brand_lower = brand.name.lower()
        alias_lowers = set()
        if brand.aliases:
            alias_lowers = {v.lower() for v in brand.aliases.values()}

        co_brand_data: dict[str, dict] = {}  # name -> {count, platforms, sentiments}

        for r in responses:
            if not r.extra_metadata:
                continue
            brands_in_response = r.extra_metadata.get("brands_mentioned", [])
            eng = r.engine.value if hasattr(r.engine, "value") else str(r.engine)

            for b in brands_in_response:
                name = b.get("name", "")
                name_lower = name.lower()
                # Skip the target brand itself
                if name_lower == brand_lower or name_lower in alias_lowers:
                    continue
                if name_lower not in co_brand_data:
                    co_brand_data[name_lower] = {
                        "name": name,
                        "count": 0,
                        "platforms": set(),
                        "sentiments": Counter(),
                    }
                co_brand_data[name_lower]["count"] += 1
                co_brand_data[name_lower]["platforms"].add(eng)
                co_brand_data[name_lower]["sentiments"][b.get("sentiment", "neutral")] += 1

        co_cited_brands = sorted(
            [
                {
                    "name": d["name"],
                    "co_occurrence_count": d["count"],
                    "platforms": sorted(d["platforms"]),
                    "avg_sentiment": d["sentiments"].most_common(1)[0][0] if d["sentiments"] else "neutral",
                }
                for d in co_brand_data.values()
            ],
            key=lambda x: x["co_occurrence_count"],
            reverse=True,
        )[:25]

        return {
            "co_cited_brands": co_cited_brands,
            "total_responses_with_brand": len(responses),
        }

    # ──────────────── Prompt-wise Brand Distribution ────────────────

    async def get_prompt_brand_matrix(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """For each tracked prompt, show which brands were mentioned across which engines."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        brand_result = await db.execute(select(Brand).where(Brand.id == brand_id))
        brand = brand_result.scalar_one_or_none()
        if not brand:
            return {"prompts": [], "total_prompts": 0, "brands_found": []}

        brand_lower = brand.name.lower()

        query = (
            select(AIResponse, TrackedPrompt)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        rows = result.all()

        # prompt_id -> { text, intent, brands -> { name -> { engines, positions, sentiments } } }
        prompt_data: dict[str, dict] = {}
        all_brand_names: set[str] = set()

        for resp, prompt in rows:
            pid = str(prompt.id)
            if pid not in prompt_data:
                prompt_data[pid] = {
                    "prompt_text": prompt.text,
                    "prompt_id": pid,
                    "intent": prompt.intent,
                    "brands": {},
                }

            eng = resp.engine.value if hasattr(resp.engine, "value") else str(resp.engine)

            # Track target brand from brand_mentioned flag
            target_key = brand.name
            if target_key not in prompt_data[pid]["brands"]:
                prompt_data[pid]["brands"][target_key] = {
                    "engines": set(),
                    "positions": [],
                    "sentiments": Counter(),
                    "is_target": True,
                }
            if resp.brand_mentioned:
                prompt_data[pid]["brands"][target_key]["engines"].add(eng)
                if resp.generative_position:
                    prompt_data[pid]["brands"][target_key]["positions"].append(resp.generative_position)
                if resp.sentiment:
                    s = resp.sentiment.value if hasattr(resp.sentiment, "value") else str(resp.sentiment)
                    prompt_data[pid]["brands"][target_key]["sentiments"][s] += 1
                all_brand_names.add(target_key)

            # Track all other brands from extra_metadata
            if not resp.extra_metadata:
                continue
            for b in resp.extra_metadata.get("brands_mentioned", []):
                name = b.get("name", "")
                if not name or name.lower() == brand_lower:
                    continue
                if name not in prompt_data[pid]["brands"]:
                    prompt_data[pid]["brands"][name] = {
                        "engines": set(),
                        "positions": [],
                        "sentiments": Counter(),
                        "is_target": False,
                    }
                prompt_data[pid]["brands"][name]["engines"].add(eng)
                pos = b.get("position")
                if pos is not None:
                    prompt_data[pid]["brands"][name]["positions"].append(pos)
                prompt_data[pid]["brands"][name]["sentiments"][b.get("sentiment", "neutral")] += 1
                all_brand_names.add(name)

        # Build response
        prompts_out = []
        for pd in prompt_data.values():
            brand_mentions = []
            for bname, binfo in pd["brands"].items():
                if not binfo["engines"]:
                    continue
                avg_pos = round(sum(binfo["positions"]) / len(binfo["positions"]), 1) if binfo["positions"] else None
                dom_sent = binfo["sentiments"].most_common(1)[0][0] if binfo["sentiments"] else "neutral"
                brand_mentions.append({
                    "name": bname,
                    "engines": sorted(binfo["engines"]),
                    "mention_count": len(binfo["engines"]),
                    "avg_position": avg_pos,
                    "dominant_sentiment": dom_sent,
                    "is_target": binfo["is_target"],
                })
            brand_mentions.sort(key=lambda x: (-int(x["is_target"]), -x["mention_count"]))
            prompts_out.append({
                "prompt_text": pd["prompt_text"],
                "prompt_id": pd["prompt_id"],
                "intent": pd["intent"],
                "brand_mentions": brand_mentions,
            })

        # Sort: prompts with most non-target brands + missing target first
        def sort_key(p):
            has_target = any(b["is_target"] for b in p["brand_mentions"])
            competitor_count = sum(1 for b in p["brand_mentions"] if not b["is_target"])
            return (has_target, -competitor_count)

        prompts_out.sort(key=sort_key)

        return {
            "prompts": prompts_out,
            "total_prompts": len(prompts_out),
            "brands_found": sorted(all_brand_names),
        }

    # ──────────────── Uncited Prompt Detection ────────────────

    async def get_uncited_prompts(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Find prompts where competitors are mentioned but the target brand is NOT."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Load competitors
        comp_result = await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )
        competitors = comp_result.scalars().all()
        if not competitors:
            return {"gaps": [], "total_prompts_analyzed": 0}

        comp_names = {c.name.lower(): c.name for c in competitors}

        query = (
            select(AIResponse, TrackedPrompt)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
                AIResponse.brand_mentioned.is_(False),
            )
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)

        result = await db.execute(query)
        rows = result.all()

        # Group by prompt
        prompt_gaps: dict[str, dict] = {}  # prompt_id -> {text, competitors: {name: {engines, sentiment}}}

        for resp, prompt in rows:
            if not resp.extra_metadata:
                continue
            brands_in_response = resp.extra_metadata.get("brands_mentioned", [])
            eng = resp.engine.value if hasattr(resp.engine, "value") else str(resp.engine)

            for b in brands_in_response:
                b_lower = b.get("name", "").lower()
                if b_lower in comp_names:
                    pid = str(prompt.id)
                    if pid not in prompt_gaps:
                        prompt_gaps[pid] = {"prompt_text": prompt.text, "prompt_id": pid, "competitors": {}}
                    comp_display = comp_names[b_lower]
                    if comp_display not in prompt_gaps[pid]["competitors"]:
                        prompt_gaps[pid]["competitors"][comp_display] = {
                            "engines": set(),
                            "sentiment": b.get("sentiment", "neutral"),
                        }
                    prompt_gaps[pid]["competitors"][comp_display]["engines"].add(eng)

        gaps = []
        for gap_data in prompt_gaps.values():
            for comp_name, comp_info in gap_data["competitors"].items():
                gaps.append({
                    "prompt_text": gap_data["prompt_text"],
                    "prompt_id": gap_data["prompt_id"],
                    "competitor_name": comp_name,
                    "competitor_sentiment": comp_info["sentiment"],
                    "engines": sorted(comp_info["engines"]),
                })

        # Sort by number of engines (more engines = bigger gap)
        gaps.sort(key=lambda g: len(g["engines"]), reverse=True)

        # Count total unique prompts analyzed
        total_prompts = len({str(prompt.id) for _, prompt in rows})

        return {"gaps": gaps[:50], "total_prompts_analyzed": total_prompts}

    # ──────────────── Topic Clustering ────────────────

    async def get_topic_clusters(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None,
        language: str | None = None, region: str | None = None,
    ) -> dict:
        """Cluster prompts into topics based on shared keywords and return per-topic analytics."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(AIResponse, TrackedPrompt)
            .join(TrackedPrompt)
            .where(TrackedPrompt.brand_id == brand_id, AIResponse.captured_at >= since)
        )
        if engine_filter:
            query = query.where(AIResponse.engine == engine_filter)
        if language:
            query = query.where(TrackedPrompt.language == language)
        if region:
            query = query.where(TrackedPrompt.region == region)

        result = await db.execute(query)
        rows = result.all()
        if not rows:
            return {"clusters": [], "total_prompts": 0, "total_topics": 0}

        # Build per-prompt stats
        prompt_stats: dict[str, dict] = {}
        for resp, prompt in rows:
            pid = str(prompt.id)
            if pid not in prompt_stats:
                prompt_stats[pid] = {
                    "text": prompt.text,
                    "intent": prompt.intent,
                    "total": 0,
                    "mentioned": 0,
                    "positions": [],
                }
            prompt_stats[pid]["total"] += 1
            if resp.brand_mentioned:
                prompt_stats[pid]["mentioned"] += 1
            if resp.generative_position:
                prompt_stats[pid]["positions"].append(resp.generative_position)

        # Extract topic keywords from prompt text (top 2-3 meaningful words)
        def extract_topic(text: str) -> str:
            words = re.findall(r"[a-z]+", text.lower())
            meaningful = [w for w in words if w not in _STOPWORDS and len(w) > 2]
            return " ".join(meaningful[:3]) if meaningful else "general"

        topic_prompts: dict[str, list] = defaultdict(list)
        for pid, stats in prompt_stats.items():
            topic = extract_topic(stats["text"])
            vis = (stats["mentioned"] / stats["total"] * 100) if stats["total"] else 0
            avg_pos = (sum(stats["positions"]) / len(stats["positions"])) if stats["positions"] else None
            topic_prompts[topic].append({
                "prompt_id": pid,
                "text": stats["text"],
                "intent": stats["intent"],
                "visibility_pct": round(vis, 1),
                "mention_count": stats["mentioned"],
                "avg_position": avg_pos,
            })

        clusters = []
        for topic, prompts in topic_prompts.items():
            avg_vis = sum(p["visibility_pct"] for p in prompts) / len(prompts)
            positions = [p["avg_position"] for p in prompts if p["avg_position"] is not None]
            avg_pos = round(sum(positions) / len(positions), 1) if positions else None
            intents = Counter(p["intent"] for p in prompts if p["intent"])
            dom_intent = intents.most_common(1)[0][0] if intents else None
            clusters.append({
                "topic": topic,
                "prompt_count": len(prompts),
                "avg_visibility": round(avg_vis, 1),
                "avg_position": avg_pos,
                "dominant_intent": dom_intent,
                "prompts": sorted(prompts, key=lambda p: -p["visibility_pct"]),
            })

        clusters.sort(key=lambda c: -c["avg_visibility"])

        return {
            "clusters": clusters,
            "total_prompts": len(prompt_stats),
            "total_topics": len(clusters),
        }

    # ──────────────── Competitive Citations ────────────────

    async def get_competitive_citations(
        self, brand_id, days: int, db: AsyncSession, engine_filter: str | None = None
    ) -> dict:
        """Compare which domains/sources power your brand's citations vs competitors'."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Your brand's citations
        your_query = (
            select(AIResponse)
            .join(TrackedPrompt)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
                AIResponse.brand_mentioned.is_(True),
            )
        )
        if engine_filter:
            your_query = your_query.where(AIResponse.engine == engine_filter)

        your_result = await db.execute(your_query)
        your_responses = your_result.scalars().all()

        def extract_domains(responses):
            domain_data: dict[str, dict] = {}
            for r in responses:
                if not r.citations:
                    continue
                eng = r.engine.value if hasattr(r.engine, "value") else str(r.engine)
                sent = r.sentiment.value if hasattr(r.sentiment, "value") and r.sentiment else "neutral"
                cites = r.citations if isinstance(r.citations, list) else r.citations.get("urls", [])
                for c in cites:
                    domain = c.get("domain", "") if isinstance(c, dict) else ""
                    if not domain:
                        continue
                    if domain not in domain_data:
                        domain_data[domain] = {"count": 0, "engines": set(), "sentiments": Counter()}
                    domain_data[domain]["count"] += 1
                    domain_data[domain]["engines"].add(eng)
                    domain_data[domain]["sentiments"][sent] += 1
            return sorted(
                [
                    {
                        "domain": d,
                        "count": info["count"],
                        "engines": sorted(info["engines"]),
                        "avg_sentiment": info["sentiments"].most_common(1)[0][0] if info["sentiments"] else "neutral",
                    }
                    for d, info in domain_data.items()
                ],
                key=lambda x: -x["count"],
            )[:20]

        your_top = extract_domains(your_responses)
        your_domain_set = {d["domain"] for d in your_top}

        # Load competitors
        comp_result = await db.execute(
            select(Competitor).where(Competitor.brand_id == brand_id)
        )
        competitors = comp_result.scalars().all()

        comp_citations = []
        all_comp_domains: set[str] = set()

        for comp in competitors:
            # Find responses where this competitor is mentioned in extra_metadata
            all_query = (
                select(AIResponse)
                .join(TrackedPrompt)
                .where(
                    TrackedPrompt.brand_id == brand_id,
                    AIResponse.captured_at >= since,
                )
            )
            if engine_filter:
                all_query = all_query.where(AIResponse.engine == engine_filter)

            all_result = await db.execute(all_query)
            all_responses = all_result.scalars().all()

            # Filter to responses that mention this competitor
            comp_lower = comp.name.lower()
            comp_responses = []
            for r in all_responses:
                if not r.extra_metadata:
                    continue
                brands = r.extra_metadata.get("brands_mentioned", [])
                if any(b.get("name", "").lower() == comp_lower for b in brands):
                    comp_responses.append(r)

            top_domains = extract_domains(comp_responses)
            for d in top_domains:
                all_comp_domains.add(d["domain"])

            comp_citations.append({
                "competitor_name": comp.name,
                "total_citations": sum(d["count"] for d in top_domains),
                "top_domains": top_domains,
            })

        overlap = sorted(your_domain_set & all_comp_domains)

        return {
            "competitors": comp_citations,
            "your_top_domains": your_top,
            "overlap_domains": overlap,
        }


analytics_service = AnalyticsService()
