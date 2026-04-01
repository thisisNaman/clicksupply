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
Given a brand name, its industry, and optionally its domain, generate a list of
search-style prompts that real users would type into AI engines like ChatGPT,
Gemini, Perplexity, or Copilot to discover products/services in that category.

Return ONLY a JSON array of strings. Each string should be a natural user query.

Rules:
- Generate exactly 10 prompts
- Mix different query types: comparisons, "best of" lists, review-style, recommendation requests, alternative searches
- Include the brand name in 3-4 of the prompts (not all)
- The rest should be generic industry queries where the brand might appear
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
    user_prompt = f"Brand: {brand_name}"
    if industry:
        user_prompt += f"\nIndustry: {industry}"
    if domain:
        user_prompt += f"\nDomain: {domain}"

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
            return prompts[:15]  # Cap at 15

    except Exception as exc:
        logger.warning("prompt_generation_failed", brand=brand_name, error=str(exc))

    # Fallback: template-based prompts
    return _fallback_prompts(brand_name, industry)


def _fallback_prompts(brand_name: str, industry: str | None) -> list[str]:
    """Generate basic template prompts when LLM is unavailable."""
    ind = industry or "this category"
    return [
        f"What is {brand_name} and is it good?",
        f"Best {ind} companies in India",
        f"{brand_name} vs competitors comparison",
        f"Top {ind} tools and platforms 2025",
        f"Is {brand_name} worth it? Reviews and opinions",
        f"Best alternatives to {brand_name}",
        f"Recommend a good {ind} platform",
        f"{ind} recommendations for beginners",
        f"Which {ind} brands do experts recommend?",
        f"How does {brand_name} compare to others in {ind}?",
    ]
