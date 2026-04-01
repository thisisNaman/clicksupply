"""
AI Response Capture Engine — Runs synthetic prompts across AI engines and extracts brand signals.

Architecture:
  - Capture: Via Copilot SDK, routing each engine to its underlying model
  - Analysis: Via Copilot SDK (extracts structured brand data from captured responses)

"""

import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AIEngine, AIResponse, Sentiment, TrackedPrompt
from app.services.llm.copilot_provider import CopilotSDKProvider
from app.services.llm.gateway import LLMGateway, ModelTier, llm_gateway

logger = structlog.get_logger()

# Map each AI engine to the Copilot SDK model that powers it
ENGINE_MODEL_MAP: dict[AIEngine, str] = {
    AIEngine.CHATGPT: "gpt-4.1",
    AIEngine.GEMINI: "gemini-2.0-flash",
    AIEngine.CLAUDE: "claude-sonnet-4",
    AIEngine.PERPLEXITY: "gpt-4.1",
    AIEngine.GOOGLE_AIO: "gemini-2.0-flash",
    AIEngine.COPILOT: "gpt-4.1",
}

# System prompts that give each model the persona of its engine
ENGINE_SYSTEM_PROMPTS: dict[AIEngine, str] = {
    AIEngine.CHATGPT: "You are ChatGPT, a helpful AI assistant by OpenAI. Answer the user's question thoroughly.",
    AIEngine.GEMINI: "You are Gemini, Google's AI assistant. Provide helpful, accurate, and well-structured answers.",
    AIEngine.CLAUDE: "You are Claude, an AI assistant by Anthropic. Be helpful, harmless, and honest.",
    AIEngine.PERPLEXITY: "You are Perplexity AI, a search-focused AI assistant. Provide concise, well-sourced answers with references where possible.",
    AIEngine.GOOGLE_AIO: "You are Google AI Overview. Provide a concise, factual summary that directly answers the query, similar to a featured snippet.",
    AIEngine.COPILOT: "You are Microsoft Copilot, a helpful AI assistant. Provide thorough and helpful answers.",
}

ANALYSIS_SYSTEM_PROMPT = """You are an AI response analyst. Given a user prompt and an AI engine's response,
extract structured brand visibility data. Return ONLY valid JSON with this exact schema:

{
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
- position = rank order if the response is a list (1 = first mentioned, null if not a list)
- sentiment = how the AI frames the brand (positive/neutral/negative)
- Extract ALL URLs mentioned as citations
- If no brands are mentioned, return empty arrays"""


class CaptureEngine:
    """Captures and analyzes AI responses for brand visibility tracking.

    Capture: Copilot SDK routes each engine to its underlying model.
    Analysis: Copilot SDK extracts structured brand signals from captured text.
    """

    def __init__(self, gateway: LLMGateway | None = None):
        self.gateway = gateway or llm_gateway
        self._providers: dict[str, CopilotSDKProvider] = {}

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
        brand_mentioned = any(
            b["name"].lower() == brand_name.lower()
            or (brand_aliases and b["name"].lower() in [a.lower() for a in brand_aliases.values()])
            for b in analysis.get("brands_mentioned", [])
        )

        brand_entry = next(
            (b for b in analysis.get("brands_mentioned", [])
             if b["name"].lower() == brand_name.lower()
             or (brand_aliases and b["name"].lower() in [a.lower() for a in brand_aliases.values()])),
            None,
        )

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
