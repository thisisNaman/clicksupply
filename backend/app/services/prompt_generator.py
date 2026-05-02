"""
Auto-generate tracked prompts for a brand using LLM.

Called during brand creation to seed an initial set of prompts
that reflect real queries users ask AI engines about the brand's industry.
"""

import json

import structlog

from app.services.llm.gateway import ModelTier, llm_gateway

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are an AEO (AI Engine Optimization) specialist.
Given a brand's industry and optionally its domain, generate a list of
search-style prompts that real users would type into AI engines like ChatGPT,
Gemini, Perplexity, or Copilot to discover products/services in that category.

Return ONLY a JSON array of strings. Each string should be a natural user query.

Rules:
- Generate exactly 20 prompts
- Mix different query types: comparisons, "best of" lists, review-style, recommendation requests, alternative searches
- Do NOT include the brand name in any prompt — all prompts must be fully generic industry queries
- Keep prompts natural — how a real person would ask an AI chatbot
- Do NOT wrap in markdown fences, return raw JSON array only"""


async def generate_prompts_for_brand(
    brand_name: str,
    industry: str | None = None,
    domain: str | None = None,
) -> list[str]:
    """Query LLM to generate relevant tracked prompts for a brand.

    Returns a list of prompt strings (typically 10).
    Falls back to template-based prompts if LLM fails.
    """
    user_prompt = ""
    if industry:
        user_prompt += f"Industry: {industry}"
    if domain:
        user_prompt += f"\nDomain: {domain}"
    if not user_prompt:
        user_prompt = f"Industry: {brand_name}"

    try:
        result = await llm_gateway.complete(
            user_prompt,
            system=SYSTEM_PROMPT,
            tier=ModelTier.CHEAP,
            use_cache=False,
        )
        text = result["text"].strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        prompts = json.loads(text)
        if isinstance(prompts, list) and all(isinstance(p, str) for p in prompts):
            logger.info(
                "prompts_generated",
                brand=brand_name,
                count=len(prompts),
                cost_usd=result.get("cost_usd", 0),
            )
            return prompts[:20]  # Cap at 20

    except Exception as exc:
        logger.warning("prompt_generation_failed", brand=brand_name, error=str(exc))

    # Fallback: template-based prompts
    return _fallback_prompts(brand_name, industry)


def _fallback_prompts(brand_name: str, industry: str | None) -> list[str]:
    """Generate basic template prompts when LLM is unavailable."""
    ind = industry or "this category"
    return [
        f"Best {ind} companies in India",
        f"Top {ind} tools and platforms 2025",
        f"Recommend a good {ind} platform",
        f"{ind} recommendations for beginners",
        f"Which {ind} brands do experts recommend?",
        f"Top rated {ind} services",
        f"Most popular {ind} platforms",
        f"{ind} comparison guide",
        f"Best {ind} for small businesses",
        f"How to choose a {ind} tool",
        f"Affordable {ind} solutions",
        f"{ind} tools with best reviews",
        f"Enterprise {ind} platforms ranked",
        f"Free vs paid {ind} options",
        f"What to look for in a {ind} product",
        f"{ind} industry leaders",
        f"Trending {ind} tools in 2026",
        f"Best {ind} software for startups",
        f"Community recommended {ind} platforms",
        f"{ind} tools used by professionals",
    ]
