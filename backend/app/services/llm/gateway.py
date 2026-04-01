"""
LLM Gateway — Unified interface for AI response analysis via GitHub Copilot SDK.

All LLM analysis (brand signal extraction) flows through the Copilot SDK.
No API keys required — uses the user's GitHub Copilot subscription.
Capture itself always happens via Playwright browsers.

The gateway provides tier-based routing as a conceptual abstraction,
but all requests go through the single Copilot SDK provider.
"""

import hashlib
from enum import Enum

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ModelTier(str, Enum):
    CHEAP = "cheap"      # Binary classification, mention detection
    STANDARD = "standard"  # Sentiment analysis, citation extraction
    PREMIUM = "premium"    # Complex reasoning, content generation


# Token costs per 1M tokens (input/output) — kept for cost tracking if API keys are ever re-added
MODEL_COSTS = {
    "gemini-2.0-flash": {"input": 0.50, "output": 3.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "sonar": {"input": 1.00, "output": 1.00},
}

TIER_MODEL_MAP = {
    ModelTier.CHEAP: ["gemini-2.0-flash", "gpt-4o-mini"],
    ModelTier.STANDARD: ["claude-3-5-haiku-20241022", "gpt-4o"],
    ModelTier.PREMIUM: ["claude-3-5-sonnet-20241022"],
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model.startswith("copilot:"):
        return 0.0  # Copilot SDK usage billed via GitHub subscription
    costs = MODEL_COSTS.get(model, {"input": 1.0, "output": 5.0})
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000


# ──── Prompt Cache ────

_prompt_cache: dict[str, dict] = {}


def _cache_key(prompt: str, system: str | None, model: str) -> str:
    raw = f"{model}:{system or ''}:{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


class LLMGateway:
    """Unified LLM gateway using GitHub Copilot SDK for all analysis.

    Zero API keys needed. The Copilot SDK uses the user's GitHub Copilot
    subscription to power all LLM calls (brand signal extraction, etc.).
    """

    def __init__(self):
        self._copilot_provider = None
        self._init_provider()

    def _init_provider(self) -> None:
        from app.services.llm.copilot_provider import CopilotSDKProvider
        self._copilot_provider = CopilotSDKProvider(model=settings.COPILOT_MODEL)
        logger.info("llm_gateway_ready", mode="copilot_sdk", model=settings.COPILOT_MODEL)

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        tier: ModelTier = ModelTier.CHEAP,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> dict:
        """Complete a prompt via Copilot SDK. Tier is logged but all requests use the same model."""
        max_tok = max_tokens or settings.DEFAULT_MAX_TOKENS
        model = f"copilot:{settings.COPILOT_MODEL}"

        if use_cache:
            key = _cache_key(prompt, system, model)
            if key in _prompt_cache:
                logger.info("llm_cache_hit", model=model)
                cached = _prompt_cache[key].copy()
                cached["cached"] = True
                cached["cost_usd"] = 0.0
                return cached

        result = await self._copilot_provider.complete(prompt, system, max_tok)
        result["cost_usd"] = 0.0  # Copilot SDK is subscription-based
        result["cached"] = False

        if use_cache:
            key = _cache_key(prompt, system, model)
            _prompt_cache[key] = result

        logger.info(
            "llm_complete",
            mode="copilot_sdk",
            model=model,
            tier=tier.value,
        )
        return result

    async def complete_for_engine(
        self,
        prompt: str,
        engine_value: str,
        system: str | None = None,
        max_tokens: int | None = None,
        use_cache: bool = False,
    ) -> dict:
        """Route analysis through Copilot SDK (engine value is logged for context)."""
        max_tok = max_tokens or settings.DEFAULT_MAX_TOKENS
        model = f"copilot:{settings.COPILOT_MODEL}"

        if use_cache:
            key = _cache_key(prompt, system, model)
            if key in _prompt_cache:
                cached = _prompt_cache[key].copy()
                cached["cached"] = True
                cached["cost_usd"] = 0.0
                return cached

        result = await self._copilot_provider.complete(prompt, system, max_tok)
        result["cost_usd"] = 0.0
        result["cached"] = False

        if use_cache:
            key = _cache_key(prompt, system, model)
            _prompt_cache[key] = result

        logger.info("llm_complete_for_engine", engine=engine_value, model=model)
        return result

    async def shutdown(self):
        """Shut down the Copilot SDK client."""
        from app.services.llm.copilot_provider import shutdown_copilot
        await shutdown_copilot()


# Singleton
llm_gateway = LLMGateway()
