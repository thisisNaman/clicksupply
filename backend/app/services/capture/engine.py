"""
AI Response Capture Engine — Runs synthetic prompts across AI engines and extracts brand signals.

Architecture:
  - Capture: Via Copilot SDK, routing each engine to its underlying model
  - Analysis: Via Copilot SDK (extracts structured brand data from captured responses)

"""

import json
import re

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AIEngine, AIResponse, Sentiment, TrackedPrompt
from app.services.llm.copilot_provider import CopilotSDKProvider
from app.services.llm.gateway import LLMGateway, ModelTier, llm_gateway

logger = structlog.get_logger()

# Map each AI engine to the Copilot SDK model that powers it.
# Note: Gemini models are NOT available via Copilot SDK (only OpenAI + Anthropic).
# We maximise model diversity by spreading across different model families.
ENGINE_MODEL_MAP: dict[AIEngine, str] = {
    AIEngine.CHATGPT: "gpt-4.1",
    AIEngine.GEMINI: "gpt-5.4-mini",         # Gemini unavailable; use a distinct GPT model
    AIEngine.CLAUDE: "claude-sonnet-4",
    AIEngine.PERPLEXITY: "gpt-5-mini",
    AIEngine.GOOGLE_AIO: "claude-haiku-4.5",  # Gemini unavailable; use a distinct Claude model
    AIEngine.COPILOT: "gpt-5.1",
}

# System prompts that give each model the persona of its engine
_BRAND_INSTRUCTION = (
    "When recommending products, tools, or services, ALWAYS name specific real "
    "companies and brands — never use generic descriptions. Include both well-known "
    "global leaders AND popular regional/local brands relevant to the user's market."
)
ENGINE_SYSTEM_PROMPTS: dict[AIEngine, str] = {
    AIEngine.CHATGPT: (
        "You are ChatGPT, a helpful AI assistant by OpenAI with browsing capabilities. "
        f"Answer the user's question thoroughly using up-to-date knowledge. {_BRAND_INSTRUCTION}"
    ),
    AIEngine.GEMINI: (
        "You are Gemini, Google's AI assistant with access to Google Search. "
        f"Provide helpful, accurate, and well-structured answers. {_BRAND_INSTRUCTION}"
    ),
    AIEngine.CLAUDE: (
        "You are Claude, an AI assistant by Anthropic. Be helpful, harmless, and honest. "
        f"{_BRAND_INSTRUCTION}"
    ),
    AIEngine.PERPLEXITY: (
        "You are Perplexity AI, a search-focused AI assistant. Provide concise, "
        f"well-sourced answers with references where possible. {_BRAND_INSTRUCTION}"
    ),
    AIEngine.GOOGLE_AIO: (
        "You are Google AI Overview. Provide a concise, factual summary that directly "
        f"answers the query, similar to a featured snippet. {_BRAND_INSTRUCTION}"
    ),
    AIEngine.COPILOT: (
        "You are Microsoft Copilot, a helpful AI assistant with web search capabilities. "
        f"Provide thorough and helpful answers. {_BRAND_INSTRUCTION}"
    ),
}

ANALYSIS_SYSTEM_PROMPT = """You are an AI response analyst. Given a user prompt and an AI engine's response,
extract structured brand visibility data. Return ONLY valid JSON with this exact schema:

{
  "intent": "informational|commercial|comparison|conversational|navigational",
  "brands_mentioned": [
    {
      "name": "BrandName",
      "position": 1,
      "sentiment": "positive|neutral|negative",
      "context": "brief quote where brand is mentioned"
    }
  ],
  "citations": [
    {"url": "https://...", "domain": "example.com", "title": "optional"}
  ],
  "response_type": "listicle|comparison|direct_answer|narrative|no_answer"
}

Rules:
- intent = classify the ORIGINAL USER PROMPT (not the response):
  * informational: seeking knowledge or how-to (e.g. "what is...", "how to...")
  * commercial: evaluating for purchase (e.g. "best ... to buy", "pricing of...")
  * comparison: comparing options (e.g. "X vs Y", "alternatives to...")
  * conversational: casual or opinion-seeking (e.g. "what do you think of...")
  * navigational: looking for a specific brand/product (e.g. "Brand X reviews")
- brands_mentioned: list ALL brands/companies/products mentioned in the response, not just the target brand
- position = rank order if the response is a list (1 = first mentioned, null if not a list)
- sentiment = how the AI frames each brand (positive/neutral/negative)
- Extract ALL URLs mentioned as citations
- If no brands are mentioned, return empty arrays"""


class CaptureEngine:
    """Captures and analyzes AI responses for brand visibility tracking.

    Capture: Copilot SDK routes each engine to its underlying model.
    Analysis: Copilot SDK extracts structured brand signals from captured text.
    """

    # In-memory cache: (extracted_lower, brand_lower) → bool
    _match_cache: dict[tuple[str, str], bool] = {}

    def __init__(self, gateway: LLMGateway | None = None):
        self.gateway = gateway or llm_gateway
        self._providers: dict[str, CopilotSDKProvider] = {}

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a brand name for fuzzy comparison."""
        s = name.lower().strip()
        s = re.sub(r'\.(com|in|co|org|net|io|ai)$', '', s)
        s = re.sub(r'[^a-z0-9]', '', s)
        return s

    @staticmethod
    def _quick_match(extracted_name: str, brand_name: str, brand_aliases: dict | None) -> bool | None:
        """Fast deterministic check. Returns True/False if certain, None if unsure."""
        norm_ext = CaptureEngine._normalize(extracted_name)
        norm_brand = CaptureEngine._normalize(brand_name)
        if not norm_ext or not norm_brand:
            return False
        if norm_ext == norm_brand:
            return True
        if len(norm_brand) >= 4 and (norm_brand in norm_ext or norm_ext in norm_brand):
            return True
        if brand_aliases:
            for alias in brand_aliases.values():
                norm_alias = CaptureEngine._normalize(str(alias))
                if norm_alias and (norm_ext == norm_alias or norm_alias in norm_ext or norm_ext in norm_alias):
                    return True
        return None  # uncertain — needs LLM

    async def _llm_matches_brand(self, extracted_name: str, brand_name: str) -> bool:
        """Use a cheap LLM call to determine if extracted_name refers to brand_name."""
        cache_key = (extracted_name.lower().strip(), brand_name.lower().strip())
        if cache_key in self._match_cache:
            return self._match_cache[cache_key]

        prompt = (
            f'Does "{extracted_name}" refer to the same company/brand as "{brand_name}"?\n'
            "Consider abbreviations, full names, parent companies, and common aliases.\n"
            "Reply with ONLY 'yes' or 'no'."
        )
        try:
            result = await self.gateway.complete(
                prompt,
                system="You are a brand-name matching assistant. Reply with only 'yes' or 'no'.",
                tier=ModelTier.CHEAP,
                max_tokens=4,
                use_cache=True,
            )
            answer = result.get("text", "").strip().lower()
            matched = answer.startswith("yes")
        except Exception:
            logger.warning("llm_brand_match_failed", extracted=extracted_name, brand=brand_name)
            matched = False

        self._match_cache[cache_key] = matched
        logger.debug("llm_brand_match", extracted=extracted_name, brand=brand_name, matched=matched)
        return matched

    async def _matches_brand(
        self, extracted_name: str, brand_name: str, brand_aliases: dict | None
    ) -> bool:
        """Check if an extracted brand name matches the target brand.

        Fast deterministic check first, falls back to a cheap LLM call for ambiguous cases.
        """
        quick = self._quick_match(extracted_name, brand_name, brand_aliases)
        if quick is not None:
            return quick
        return await self._llm_matches_brand(extracted_name, brand_name)

    async def capture_response(
        self,
        prompt: TrackedPrompt,
        engine: AIEngine,
        brand_name: str,
        brand_aliases: dict | None = None,
        db: AsyncSession | None = None,
    ) -> AIResponse:
        """
        1. Query the AI engine with the prompt
        2. Analyze the response for brand signals
        3. Store and return the AIResponse record
        """
        # Step 1: Get raw response from the AI engine
        query_result = await self._query_engine(prompt.text, engine)
        raw_response = query_result["text"]
        capture_cost = query_result.get("cost_usd", 0.0)
        capture_input_tokens = query_result.get("input_tokens", 0)
        capture_output_tokens = query_result.get("output_tokens", 0)

        # Step 2: Analyze the response for brand signals
        if not raw_response or raw_response.startswith("["):
            analysis = {"brands_mentioned": [], "citations": [], "response_type": "capture_failed"}
            analysis_cost = 0.0
        else:
            analysis, analysis_cost = await self._analyze_response(
                prompt.text, raw_response, brand_name, brand_aliases
            )

        # Step 3: Build the AIResponse record
        brand_mentioned = False
        brand_entry = None
        for b in analysis.get("brands_mentioned", []):
            if await self._matches_brand(b["name"], brand_name, brand_aliases):
                brand_mentioned = True
                brand_entry = b
                break

        # Fallback: use LLM to check if brand name appears in raw response
        if not brand_mentioned and raw_response:
            brand_mentioned = await self._llm_matches_brand(raw_response[:300], brand_name)
            if brand_mentioned:
                logger.info("brand_detected_via_llm_fallback", brand=brand_name, engine=engine.value)

        sentiment = None
        gen_position = None
        if brand_entry:
            sentiment_str = brand_entry.get("sentiment", "neutral")
            sentiment = Sentiment(sentiment_str) if sentiment_str in Sentiment.__members__.values() else Sentiment.NEUTRAL
            gen_position = brand_entry.get("position")

        ai_response = AIResponse(
            prompt_id=prompt.id,
            engine=engine,
            raw_response=raw_response,
            brand_mentioned=brand_mentioned,
            generative_position=gen_position,
            sentiment=sentiment,
            citations={"sources": analysis.get("citations", [])},
            extra_metadata={
                "response_type": analysis.get("response_type"),
                "intent": analysis.get("intent", "informational"),
                "brands_mentioned": analysis.get("brands_mentioned", []),
            },
            input_tokens=capture_input_tokens,
            output_tokens=capture_output_tokens,
            cost_usd=round(capture_cost + analysis_cost, 6),
        )

        if db:
            db.add(ai_response)
            await db.flush()

        logger.info(
            "capture_complete",
            engine=engine.value,
            brand=brand_name,
            mentioned=brand_mentioned,
            position=gen_position,
        )
        return ai_response

    def _get_provider(self, engine: AIEngine) -> CopilotSDKProvider:
        """Get or create a CopilotSDKProvider for the given engine's model."""
        model = ENGINE_MODEL_MAP.get(engine, "gpt-4.1")
        if model not in self._providers:
            self._providers[model] = CopilotSDKProvider(model=model)
        return self._providers[model]

    async def _query_engine(self, prompt_text: str, engine: AIEngine) -> dict:
        """Query the AI engine via Copilot SDK using the engine's underlying model.

        Each engine is mapped to a specific model and given a persona system prompt.

        Returns: {"text": str, "input_tokens": int, "output_tokens": int, "cost_usd": float}
        """
        provider = self._get_provider(engine)
        system_prompt = ENGINE_SYSTEM_PROMPTS.get(engine, "You are a helpful AI assistant.")
        result = await provider.complete(prompt_text, system=system_prompt)
        return {
            "text": result["text"],
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "cost_usd": 0.0,
        }

    async def _analyze_response(
        self,
        original_prompt: str,
        raw_response: str,
        brand_name: str,
        brand_aliases: dict | None,
    ) -> tuple[dict, float]:
        """Use a cheap model to extract structured brand signal data.

        Returns: (analysis_dict, cost_usd)
        """
        alias_str = ""
        if brand_aliases:
            alias_str = f"\nBrand aliases to look for: {json.dumps(brand_aliases)}"

        analysis_prompt = f"""Analyze this AI response for brand visibility data.

Target brand: {brand_name}{alias_str}

Original user prompt: {original_prompt}

AI Engine Response:
{raw_response[:4000]}"""  # Truncate to control costs

        result = await self.gateway.complete(
            analysis_prompt,
            system=ANALYSIS_SYSTEM_PROMPT,
            tier=ModelTier.CHEAP,
            use_cache=True,
        )

        cost = result.get("cost_usd", 0.0)
        try:
            return json.loads(result["text"]), cost
        except json.JSONDecodeError:
            logger.warning("analysis_json_parse_failed", text=result["text"][:200])
            return {"brands_mentioned": [], "citations": [], "response_type": "unknown"}, cost


capture_engine = CaptureEngine()
