"""
AEO Action Center — Data-driven optimization actions with verification.

Actions are generated from three real data sources:
1. AI capture data — prompts where brand visibility is weak
2. AEO page audit — actual website analysis (schema, structure, crawlability)
3. Crawler log analysis — which AI bots visit (or don't) and what errors they hit

Each action includes a verification_type so users can re-run the check after fixing.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Action,
    AIResponse,
    Brand,
    CrawlerLog,
    CrawlerType,
    TrackedPrompt,
    VisibilityScore,
)
from app.services.llm.gateway import ModelTier, llm_gateway
from app.services.recommendations.aeo_engine import AEORecommendationEngine

logger = structlog.get_logger()

# Generation progress tracking per brand (in-memory, ephemeral)
_generation_progress: dict[str, dict] = {}

_aeo_engine = AEORecommendationEngine()

# Map crawler types to the AI engines they power
_CRAWLER_ENGINE_MAP: dict[str, str] = {
    "GPTBot": "ChatGPT / OpenAI",
    "ClaudeBot": "Claude / Anthropic",
    "Googlebot": "Gemini / Google AIO",
    "Bingbot": "Copilot / Microsoft",
    "PerplexityBot": "Perplexity",
    "meta-externalagent": "Meta AI",
    "Bytespider": "Doubao / ByteDance",
}

# Clean display names for AI engine enum values
_ENGINE_DISPLAY: dict[str, str] = {
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
    "google_aio": "Google AIO",
    "claude": "Claude",
    "copilot": "Copilot",
    "grok": "Grok",
    "deepseek": "DeepSeek",
    "meta_ai": "Meta AI",
    "sarvam": "Sarvam",
    "krutrim": "Krutrim",
}


def _engine_name(val: str) -> str:
    """Human-readable engine name from enum value."""
    return _ENGINE_DISPLAY.get(val, val.replace("_", " ").title())


class ActionCenterEngine:
    """Generates and manages data-driven AEO optimization actions."""

    # Fields to persist from generated action dicts to Action model
    _ACTION_FIELDS = [
        "category", "title", "description", "impact", "effort", "action_type",
        "engine", "prompt_text", "prompt_id", "current_mention_rate", "current_rate",
        "suggested_content", "suggested_schema", "verification_type", "baseline_value",
        "crawler_type", "audit_category", "audit_severity", "engines_missing", "engines_citing",
    ]

    @staticmethod
    def _action_to_dict(a: Action) -> dict:
        """Convert an Action ORM object to a plain dict for API response."""
        return {
            "id": str(a.id),
            "brand_id": str(a.brand_id),
            "category": a.category,
            "title": a.title,
            "description": a.description,
            "impact": a.impact,
            "effort": a.effort,
            "status": a.status,
            "priority_rank": a.priority_rank,
            "action_type": a.action_type,
            "engine": a.engine,
            "prompt_text": a.prompt_text,
            "prompt_id": a.prompt_id,
            "current_mention_rate": a.current_mention_rate,
            "current_rate": a.current_rate,
            "suggested_content": a.suggested_content,
            "suggested_schema": a.suggested_schema,
            "verification_type": a.verification_type,
            "baseline_value": a.baseline_value,
            "verified_at": a.verified_at.isoformat() if a.verified_at else None,
            "verified_value": a.verified_value,
            "verification_status": a.verification_status,
            "crawler_type": a.crawler_type,
            "audit_category": a.audit_category,
            "audit_severity": a.audit_severity,
            "engines_missing": a.engines_missing,
            "engines_citing": a.engines_citing,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }

    async def generate_actions(
        self,
        brand_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Generate a fresh set of prioritized AEO actions for a brand."""
        bid = str(brand_id)
        brand = await db.get(Brand, brand_id)
        if not brand:
            _generation_progress.pop(bid, None)
            return []

        actions: list[dict] = []
        since = datetime.now(timezone.utc) - timedelta(days=14)

        def _set_progress(step: int, stage: str, detail: str = ""):
            _generation_progress[bid] = {
                "status": "running",
                "step": step,
                "total_steps": 6,
                "stage": stage,
                "detail": detail,
                "actions_so_far": len(actions),
            }

        # 1. Website audit — real page analysis
        _set_progress(1, "Auditing website", f"Scanning {brand.domain or 'no domain'}…")
        actions.extend(await self._website_audit_actions(brand.domain, brand.name))

        # 2. Crawler coverage — analysis of actual AI bot visits
        _set_progress(2, "Analyzing crawler logs", "Checking which AI bots visit your site…")
        actions.extend(await self._crawler_coverage_actions(brand_id, brand.domain, db))

        # 3. Content gap actions — prompts where brand is rarely mentioned
        _set_progress(3, "Finding content gaps", "Comparing brand mentions across engines…")
        actions.extend(await self._content_gap_actions(brand_id, brand.name, since, db))

        # 4. Answer-first rewrite suggestions (LLM-powered)
        _set_progress(4, "Generating content rewrites", "Using AI to write optimized content…")
        actions.extend(await self._rewrite_suggestions(brand_id, brand.name, since, db))

        # 5. Engine-specific optimization based on capture data
        _set_progress(5, "Analyzing engine performance", "Finding your weakest AI engines…")
        actions.extend(await self._engine_optimization_actions(brand_id, brand.name, since, db))

        # 6. Best-practice quick wins (always generate)
        _set_progress(6, "Adding best practices", "Compiling quick wins…")
        actions.extend(await self._best_practice_actions(brand.domain, brand.name, actions))

        # Delete old actions for this brand
        await db.execute(
            select(Action).where(Action.brand_id == brand_id)
        )
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(Action).where(Action.brand_id == brand_id))

        # Persist new actions to DB
        now = datetime.now(timezone.utc)
        db_actions: list[Action] = []
        for i, action_data in enumerate(actions):
            kwargs = {k: action_data.get(k) for k in self._ACTION_FIELDS}
            db_action = Action(
                brand_id=brand_id,
                status="pending",
                priority_rank=i + 1,
                created_at=now,
                **kwargs,
            )
            db.add(db_action)
            db_actions.append(db_action)

        await db.flush()  # Assign IDs

        result = [self._action_to_dict(a) for a in db_actions]

        # Mark complete
        _generation_progress[bid] = {
            "status": "completed",
            "step": 6,
            "total_steps": 6,
            "stage": "Done",
            "detail": f"Generated {len(result)} actions",
            "actions_so_far": len(result),
        }

        return result

    def get_generation_progress(self, brand_id: uuid.UUID) -> dict | None:
        """Get current generation progress for a brand."""
        return _generation_progress.get(str(brand_id))

    async def get_actions(self, brand_id: uuid.UUID, db: AsyncSession) -> list[dict]:
        """Get current action list for a brand from DB."""
        result = await db.execute(
            select(Action)
            .where(Action.brand_id == brand_id)
            .order_by(Action.priority_rank)
        )
        return [self._action_to_dict(a) for a in result.scalars().all()]

    async def update_action_status(
        self, brand_id: uuid.UUID, action_id: str, status: str, db: AsyncSession,
    ) -> dict | None:
        """Mark an action as completed, dismissed, or in-progress."""
        action = await db.get(Action, uuid.UUID(action_id))
        if not action or action.brand_id != brand_id:
            return None
        action.status = status
        action.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return self._action_to_dict(action)

    async def verify_action(
        self, brand_id: uuid.UUID, action_id: str, db: AsyncSession,
    ) -> dict | None:
        """Re-run the relevant check for an action and compare to baseline."""
        action = await db.get(Action, uuid.UUID(action_id))
        if not action or action.brand_id != brand_id:
            return None

        brand = await db.get(Brand, brand_id)
        if not brand:
            return None

        v_type = action.verification_type or "manual"
        baseline = action.baseline_value
        now_val = None
        v_status = "no_change"

        try:
            if v_type == "aeo_audit" and brand.domain:
                url = f"https://{brand.domain}"
                result = await _aeo_engine.audit_page(url)
                now_val = result.score
            elif v_type == "re_capture":
                prompt_id = action.prompt_id
                if prompt_id:
                    since = datetime.now(timezone.utc) - timedelta(days=7)
                    row = await db.execute(
                        select(
                            func.count(AIResponse.id).label("total"),
                            func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
                        )
                        .where(
                            AIResponse.prompt_id == uuid.UUID(prompt_id),
                            AIResponse.captured_at >= since,
                        )
                    )
                    r = row.one_or_none()
                    if r and r.total:
                        now_val = round((r.mentioned or 0) / r.total * 100, 1)
            elif v_type == "crawler_check":
                crawler_type_str = action.crawler_type
                if crawler_type_str:
                    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                    row = await db.execute(
                        select(func.count(CrawlerLog.id))
                        .where(
                            CrawlerLog.brand_id == brand_id,
                            CrawlerLog.crawler_type == CrawlerType(crawler_type_str),
                            CrawlerLog.timestamp >= week_ago,
                        )
                    )
                    now_val = row.scalar() or 0
            else:
                # manual — just mark verified
                v_status = "improved"

            # Compare
            if now_val is not None and baseline is not None:
                if now_val > baseline + 0.5:
                    v_status = "improved"
                elif now_val < baseline - 0.5:
                    v_status = "regressed"
                else:
                    v_status = "no_change"
            elif now_val is not None:
                v_status = "improved" if now_val > 0 else "no_change"

        except Exception as e:
            logger.warning("action_verify_failed", action_id=action_id, error=str(e))
            v_status = "error"

        action.verified_at = datetime.now(timezone.utc)
        action.verified_value = now_val
        action.verification_status = v_status
        await db.flush()

        return self._action_to_dict(action)

    # ──── Action generators ────

    async def _website_audit_actions(
        self, brand_domain: str | None, brand_name: str,
    ) -> list[dict]:
        """Audit the brand's actual website and convert findings into actions."""
        if not brand_domain:
            return [{
                "category": "website_audit",
                "title": "Add your website domain",
                "description": "We need your domain to audit your site for AI engine readiness. Go to Brand Setup and add your domain.",
                "impact": "high",
                "effort": "low",
                "action_type": "setup",
                "verification_type": "manual",
                "baseline_value": None,
            }]

        actions = []
        url = f"https://{brand_domain}"

        try:
            result = await _aeo_engine.audit_page(url)
        except Exception as e:
            logger.warning("website_audit_failed", domain=brand_domain, error=str(e))
            return [{
                "category": "website_audit",
                "title": f"[{brand_domain}] Website audit failed — site may be blocking our scanner",
                "description": f"We tried to fetch {url} but got an error. This often means the site blocks automated requests. Check that your robots.txt allows crawling and that there's no WAF/CDN rule blocking bots — if AI crawlers can't access your site, they can't cite you.",
                "impact": "high",
                "effort": "medium",
                "action_type": "fix_access",
                "verification_type": "aeo_audit",
                "baseline_value": 0,
            }]

        audit_score = result.score

        # Convert each recommendation to an action
        severity_to_impact = {"critical": "high", "warning": "medium", "info": "low"}
        category_to_effort = {
            "content_structure": "medium",
            "schema_markup": "low",
            "technical": "medium",
            "trust": "medium",
        }

        for rec in result.recommendations:
            actions.append({
                "category": "website_audit",
                "title": f"[{brand_domain}] {rec.title}",
                "description": rec.description,
                "impact": severity_to_impact.get(rec.severity, "medium"),
                "effort": category_to_effort.get(rec.category, "medium"),
                "action_type": rec.category,
                "suggested_content": rec.action,
                "verification_type": "aeo_audit",
                "baseline_value": audit_score,
                "audit_category": rec.category,
                "audit_severity": rec.severity,
            })

        # Add schema suggestion action if we have suggestions
        if result.schema_suggestions:
            schema_json = json.dumps(result.schema_suggestions, indent=2)
            actions.append({
                "category": "website_audit",
                "title": f"[{brand_domain}] Add recommended schema markup",
                "description": f"We scanned {brand_domain} and found missing schema types. Add these JSON-LD blocks to your pages to improve AI citation rates.",
                "impact": "high",
                "effort": "low",
                "action_type": "add_schema",
                "suggested_schema": schema_json,
                "verification_type": "aeo_audit",
                "baseline_value": audit_score,
            })

        # Add llms.txt action if generated
        if result.llms_txt_content:
            actions.append({
                "category": "website_audit",
                "title": f"[{brand_domain}] Create llms.txt",
                "description": "We generated an llms.txt file for your site. This helps AI crawlers understand your content structure — like robots.txt but for LLM agents.",
                "impact": "medium",
                "effort": "low",
                "action_type": "create_file",
                "suggested_content": result.llms_txt_content,
                "verification_type": "aeo_audit",
                "baseline_value": audit_score,
            })

        # Add overall score context to first action
        if actions:
            score_note = f" (AEO Score: {audit_score}/100)"
            actions[0]["title"] = actions[0]["title"] + score_note

        return actions

    async def _crawler_coverage_actions(
        self, brand_id: uuid.UUID, brand_domain: str | None, db: AsyncSession,
    ) -> list[dict]:
        """Analyze AI crawler logs and generate actions for gaps."""
        actions = []
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # Check if we have any crawler data at all
        total_count = await db.execute(
            select(func.count(CrawlerLog.id))
            .where(CrawlerLog.brand_id == brand_id)
        )
        total = total_count.scalar() or 0

        if total == 0:
            domain = brand_domain or "your site"
            actions.extend([
                {
                    "category": "crawler_analysis",
                    "title": f"Check if robots.txt blocks AI crawlers on {domain}",
                    "description": f"Visit https://{domain}/robots.txt and verify that GPTBot, ClaudeBot, Googlebot, Bingbot, and PerplexityBot are NOT in any Disallow rules. Many sites accidentally block AI crawlers, which prevents citation.",
                    "impact": "high",
                    "effort": "low",
                    "action_type": "check_robots",
                    "suggested_content": f"# Recommended robots.txt additions for {domain}\n\nUser-agent: GPTBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /\n\nUser-agent: PerplexityBot\nAllow: /\n\nUser-agent: Googlebot\nAllow: /\n\nUser-agent: Bingbot\nAllow: /",
                    "verification_type": "manual",
                    "baseline_value": None,
                },
                {
                    "category": "crawler_analysis",
                    "title": "Upload server logs to track AI bot visits",
                    "description": "Upload your Apache, Nginx, or CloudFront access logs to see which AI engines actually crawl your site, how often, and whether they hit errors. This turns the Crawler Analysis from guesswork into data.",
                    "impact": "high",
                    "effort": "low",
                    "action_type": "upload_logs",
                    "verification_type": "manual",
                    "baseline_value": None,
                },
                {
                    "category": "crawler_analysis",
                    "title": f"Submit {domain} sitemap to AI search engines",
                    "description": f"Ensure https://{domain}/sitemap.xml exists and is submitted to Google Search Console and Bing Webmaster Tools. AI engines like Google AIO and Copilot use search indexes — a fresh sitemap helps them discover your content.",
                    "impact": "medium",
                    "effort": "low",
                    "action_type": "submit_sitemap",
                    "verification_type": "manual",
                    "baseline_value": None,
                },
            ])
            return actions

        # Get crawler visits grouped by type (last 30 days)
        result = await db.execute(
            select(
                CrawlerLog.crawler_type,
                func.count(CrawlerLog.id).label("visit_count"),
                func.max(CrawlerLog.timestamp).label("last_seen"),
                func.sum(
                    func.cast(CrawlerLog.status_code >= 400, Integer)
                ).label("error_count"),
            )
            .where(
                CrawlerLog.brand_id == brand_id,
                CrawlerLog.timestamp >= thirty_days_ago,
            )
            .group_by(CrawlerLog.crawler_type)
        )

        crawlers_seen: dict[str, dict] = {}
        for row in result:
            ct = row.crawler_type.value if hasattr(row.crawler_type, "value") else row.crawler_type
            crawlers_seen[ct] = {
                "visits": row.visit_count,
                "last_seen": row.last_seen,
                "error_count": row.error_count or 0,
                "error_rate": (row.error_count or 0) / row.visit_count * 100 if row.visit_count else 0,
            }

        # Check for missing important crawlers
        important_crawlers = ["GPTBot", "ClaudeBot", "Googlebot", "Bingbot", "PerplexityBot"]
        for crawler_name in important_crawlers:
            if crawler_name not in crawlers_seen:
                engine_name = _CRAWLER_ENGINE_MAP.get(crawler_name, crawler_name)
                actions.append({
                    "category": "crawler_analysis",
                    "title": f"{crawler_name} has never visited your site",
                    "description": f"{crawler_name} powers {engine_name}. If it can't crawl your content, that engine won't have evidence to cite {brand_domain or 'your brand'}. Check your robots.txt isn't blocking it, and ensure your content is discoverable via sitemaps.",
                    "impact": "high",
                    "effort": "low",
                    "action_type": "fix_crawl_access",
                    "crawler_type": crawler_name,
                    "verification_type": "crawler_check",
                    "baseline_value": 0,
                })

        # Check for high error rates
        for crawler_name, data in crawlers_seen.items():
            if crawler_name == "unknown":
                continue

            error_rate = data["error_rate"]
            if error_rate > 10 and data["error_count"] >= 3:
                engine_name = _CRAWLER_ENGINE_MAP.get(crawler_name, crawler_name)
                actions.append({
                    "category": "crawler_analysis",
                    "title": f"{crawler_name} is hitting errors ({error_rate:.0f}% error rate)",
                    "description": f"{data['error_count']} of {data['visits']} visits from {crawler_name} returned 4xx/5xx errors. This means {engine_name} can't access some of your content. Check server logs for the failing paths and fix access issues.",
                    "impact": "high",
                    "effort": "medium",
                    "action_type": "fix_errors",
                    "crawler_type": crawler_name,
                    "verification_type": "crawler_check",
                    "baseline_value": data["error_count"],
                })

            # Check for low crawl frequency
            if data["visits"] < 5 and crawler_name in important_crawlers:
                engine_name = _CRAWLER_ENGINE_MAP.get(crawler_name, crawler_name)
                actions.append({
                    "category": "crawler_analysis",
                    "title": f"Low crawl frequency from {crawler_name} ({data['visits']} visits in 30d)",
                    "description": f"{crawler_name} ({engine_name}) is barely crawling your site. This suggests your content may not be fresh enough or well-linked. Ensure your sitemap is submitted, content is updated regularly, and internal linking is strong.",
                    "impact": "medium",
                    "effort": "medium",
                    "action_type": "improve_crawlability",
                    "crawler_type": crawler_name,
                    "verification_type": "crawler_check",
                    "baseline_value": data["visits"],
                })

        return actions

    async def _content_gap_actions(
        self, brand_id: uuid.UUID, brand_name: str, since: datetime, db: AsyncSession,
    ) -> list[dict]:
        """Generate actions for prompts with low brand visibility, with per-engine evidence."""
        actions = []

        result = await db.execute(
            select(
                TrackedPrompt.id,
                TrackedPrompt.text,
                TrackedPrompt.intent,
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(AIResponse, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                TrackedPrompt.is_active == True,
                AIResponse.captured_at >= since,
            )
            .group_by(TrackedPrompt.id, TrackedPrompt.text, TrackedPrompt.intent)
        )

        gap_prompts = []
        for row in result:
            mention_rate = (row.mentioned or 0) / row.total * 100 if row.total else 0
            if mention_rate < 30:
                gap_prompts.append(row)

        if not gap_prompts:
            return actions

        # For each gap prompt, find which specific engines miss the brand
        for row in sorted(gap_prompts, key=lambda r: (r.mentioned or 0) / r.total if r.total else 0)[:8]:
            mention_rate = (row.mentioned or 0) / row.total * 100 if row.total else 0

            engine_result = await db.execute(
                select(
                    AIResponse.engine,
                    AIResponse.brand_mentioned,
                )
                .where(
                    AIResponse.prompt_id == row.id,
                    AIResponse.captured_at >= since,
                )
            )
            engines_missing = []
            engines_citing = []
            for er in engine_result:
                engine_val = er.engine.value if hasattr(er.engine, "value") else er.engine
                display = _engine_name(engine_val)
                if er.brand_mentioned:
                    engines_citing.append(display)
                else:
                    engines_missing.append(display)

            intent = row.intent or "general"
            impact = "high" if mention_rate < 10 else "medium"
            effort = "medium" if intent in ("comparison", "commercial") else "low"

            missing_str = ", ".join(_engine_name(e) for e in engines_missing[:4]) if engines_missing else "none"
            citing_str = ", ".join(_engine_name(e) for e in engines_citing[:4]) if engines_citing else "none"

            actions.append({
                "category": "content_gap",
                "title": f"Low visibility: \"{row.text[:55]}\"",
                "description": f"Only {mention_rate:.0f}% mention rate across AI engines. Missing on: {missing_str}. Cited by: {citing_str}. This {intent} query needs better content coverage for {brand_name}.",
                "impact": impact,
                "effort": effort,
                "prompt_text": row.text,
                "prompt_id": str(row.id),
                "current_mention_rate": round(mention_rate, 1),
                "engines_missing": engines_missing,
                "engines_citing": engines_citing,
                "action_type": "create_content",
                "verification_type": "re_capture",
                "baseline_value": round(mention_rate, 1),
            })

        return actions

    async def _rewrite_suggestions(
        self, brand_id: uuid.UUID, brand_name: str, since: datetime, db: AsyncSession,
    ) -> list[dict]:
        """Use LLM to generate answer-first content rewrites for low-performing prompts."""
        actions = []

        result = await db.execute(
            select(
                TrackedPrompt.id,
                TrackedPrompt.text,
                TrackedPrompt.intent,
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(AIResponse, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                TrackedPrompt.is_active == True,
                AIResponse.captured_at >= since,
            )
            .group_by(TrackedPrompt.id, TrackedPrompt.text, TrackedPrompt.intent)
            .having(func.count(AIResponse.id) >= 2)
            .order_by(
                (func.sum(func.cast(AIResponse.brand_mentioned, Integer)) * 100.0 / func.count(AIResponse.id)).asc()
            )
            .limit(3)
        )

        for row in result:
            mention_rate = ((row.mentioned or 0) / row.total * 100) if row.total else 0
            try:
                prompt = f"""You are an AEO (Answer Engine Optimization) expert. A user asks AI engines: "{row.text}"

The brand "{brand_name}" currently appears in only {mention_rate:.0f}% of AI responses.

Generate a short "answer-first" content paragraph (80-120 words) that {brand_name} should publish on their website to maximize the chance of being cited by AI engines. The paragraph should:
1. Start with a direct answer to the query
2. Mention {brand_name} naturally in the first sentence
3. Include specific facts, numbers, or differentiators
4. Be structured for easy AI extraction (clear, factual, no fluff)

Write ONLY the paragraph, nothing else."""

                llm_result = await llm_gateway.complete(
                    prompt=prompt,
                    tier=ModelTier.STANDARD,
                    max_tokens=250,
                    use_cache=True,
                )

                content = llm_result.get("content", "").strip()
                if content:
                    actions.append({
                        "category": "content_rewrite",
                        "title": f"Publish answer-first content: \"{row.text[:45]}\"",
                        "description": f"AI-generated content optimized for this query ({mention_rate:.0f}% current mention rate). Add this to your website or FAQ page to improve AI engine citations.",
                        "impact": "high",
                        "effort": "low",
                        "suggested_content": content,
                        "prompt_text": row.text,
                        "prompt_id": str(row.id),
                        "current_mention_rate": round(mention_rate, 1),
                        "action_type": "publish_content",
                        "verification_type": "re_capture",
                        "baseline_value": round(mention_rate, 1),
                    })
            except Exception as e:
                logger.warning("rewrite_generation_failed", prompt=row.text, error=str(e))

        return actions

    async def _engine_optimization_actions(
        self, brand_id: uuid.UUID, brand_name: str, since: datetime, db: AsyncSession,
    ) -> list[dict]:
        """Generate engine-specific optimization actions with real per-engine stats."""
        actions = []

        result = await db.execute(
            select(
                AIResponse.engine,
                func.count(AIResponse.id).label("total"),
                func.sum(func.cast(AIResponse.brand_mentioned, Integer)).label("mentioned"),
            )
            .join(TrackedPrompt, AIResponse.prompt_id == TrackedPrompt.id)
            .where(
                TrackedPrompt.brand_id == brand_id,
                AIResponse.captured_at >= since,
            )
            .group_by(AIResponse.engine)
        )

        engine_data = []
        for row in result:
            rate = (row.mentioned or 0) / row.total * 100 if row.total else 0
            engine_val = row.engine.value if hasattr(row.engine, "value") else row.engine
            engine_data.append({
                "engine": engine_val,
                "rate": rate,
                "total": row.total,
                "mentioned": row.mentioned or 0,
            })

        if not engine_data:
            return actions

        engine_data.sort(key=lambda x: x["rate"])
        best_engine = max(engine_data, key=lambda x: x["rate"])

        for eng in engine_data:
            if eng["rate"] >= 50:
                continue

            # Find worst prompts for this engine
            worst_prompts_result = await db.execute(
                select(TrackedPrompt.text)
                .join(AIResponse, AIResponse.prompt_id == TrackedPrompt.id)
                .where(
                    TrackedPrompt.brand_id == brand_id,
                    AIResponse.engine == eng["engine"],
                    AIResponse.brand_mentioned == False,
                    AIResponse.captured_at >= since,
                )
                .limit(3)
            )
            worst_prompts = [r.text[:50] for r in worst_prompts_result]
            worst_str = "; ".join(f'"{p}"' for p in worst_prompts) if worst_prompts else "various prompts"

            gap_vs_best = best_engine["rate"] - eng["rate"]
            desc = (
                f"{_engine_name(eng['engine'])} mentions {brand_name} in {eng['mentioned']}/{eng['total']} responses "
                f"({eng['rate']:.0f}% rate). "
            )
            if gap_vs_best > 10:
                desc += f"That's {gap_vs_best:.0f}pp behind your best engine ({_engine_name(best_engine['engine'])} at {best_engine['rate']:.0f}%). "
            desc += f"Failing on: {worst_str}."

            actions.append({
                "category": "engine_optimization",
                "title": f"Boost {_engine_name(eng['engine'])} visibility ({eng['rate']:.0f}% → target 50%+)",
                "description": desc,
                "impact": "high" if eng["rate"] < 20 else "medium",
                "effort": "medium",
                "engine": _engine_name(eng["engine"]),
                "current_rate": round(eng["rate"], 1),
                "action_type": "optimize_content",
                "verification_type": "re_capture",
                "baseline_value": round(eng["rate"], 1),
            })

        return actions

    async def _best_practice_actions(
        self, brand_domain: str | None, brand_name: str, existing_actions: list[dict],
    ) -> list[dict]:
        """Always-available best practice actions — useful even without data."""
        actions = []
        existing_types = {a.get("action_type") for a in existing_actions}
        domain = brand_domain or "yourdomain.com"

        # Only add if not already covered by audit results
        if "create_file" not in existing_types:
            actions.append({
                "category": "best_practice",
                "title": f"Create an llms.txt file at {domain}/llms.txt",
                "description": "llms.txt is like robots.txt but for AI engines. It tells LLMs what your brand is, what you offer, and how to describe you. Major AI providers are starting to check for it.",
                "impact": "medium",
                "effort": "low",
                "action_type": "create_llms_txt",
                "suggested_content": f"# {brand_name}\n\n> Brief description of {brand_name} and its core offerings.\n\n## What We Do\n- Key product/service 1\n- Key product/service 2\n\n## How to Cite Us\n- Official name: {brand_name}\n- Website: https://{domain}\n- Industry: [your industry]\n\n## Key Facts\n- Founded: [year]\n- Headquarters: [location]\n- Key differentiators: [what makes you unique]",
                "verification_type": "manual",
                "baseline_value": None,
            })

        if "add_schema" not in existing_types:
            actions.append({
                "category": "best_practice",
                "title": "Add Organization + FAQ schema to your homepage",
                "description": "JSON-LD structured data helps AI engines extract accurate facts about your brand. Organization schema ensures correct name/logo/description. FAQ schema lets AI engines directly quote your answers.",
                "impact": "high",
                "effort": "low",
                "action_type": "add_schema",
                "suggested_content": f'{{"@context":"https://schema.org","@type":"Organization","name":"{brand_name}","url":"https://{domain}","description":"[Your brand description]","logo":"https://{domain}/logo.png"}}',
                "verification_type": "aeo_audit",
                "baseline_value": None,
            })

        # Check if captures have been run
        has_capture_data = any(a.get("category") in ("content_gap", "content_rewrite", "engine_optimization") for a in existing_actions)
        if not has_capture_data:
            actions.append({
                "category": "best_practice",
                "title": "Run your first AI capture to unlock deeper insights",
                "description": f"We haven't captured how AI engines respond to your tracked prompts yet. Run a capture from the dashboard to see which engines mention {brand_name}, find content gaps, and get AI-powered rewrite suggestions.",
                "impact": "high",
                "effort": "low",
                "action_type": "run_capture",
                "verification_type": "manual",
                "baseline_value": None,
            })

        actions.append({
            "category": "best_practice",
            "title": "Add 'About' and 'FAQ' pages optimized for AI citation",
            "description": f"AI engines heavily rely on dedicated About and FAQ pages when deciding what to say about a brand. Ensure {brand_name} has clear, factual, answer-first content on these pages with structured headings.",
            "impact": "medium",
            "effort": "medium",
            "action_type": "create_content",
            "verification_type": "manual",
            "baseline_value": None,
        })

        return actions


# Singleton
action_center = ActionCenterEngine()
