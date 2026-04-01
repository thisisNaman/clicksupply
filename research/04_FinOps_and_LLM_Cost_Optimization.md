# ClickSupply: FinOps & LLM Cost Architecture

To maintain healthy margins while running thousands of synthetic visibility prompts daily, the architecture must aggressively optimize LLM API costs.

## 1. API Pricing Baselines (Per 1 Million Tokens)
*   **Grok-4.1 Fast (xAI):** $0.20 Input / $0.50 Output (Lowest cost, good for high-volume baseline tracking).
*   **Gemini 3 Flash:** $0.50 Input / $3.00 Output.
*   **Claude Haiku 4.5:** $1.00 Input / $5.00 Output.
*   **GPT-5.2:** $1.75 Input / $14.00 Output.
*   **Claude Opus 4.6:** $5.00 Input / $25.00 Output (Reserve for complex reasoning).

## 2. Cost Reduction Strategies (Up to 90% Savings)
*   **Aggressive Prompt Caching:** Cache exact-match prompts, system instructions, and RAG retrieval contexts. Cache hits on models like Claude can discount input tokens by up to 90%.
*   **Asynchronous Batch API Processing:** Use Batch APIs for non-urgent tasks like weekly visibility tracking, competitor audits, and sentiment analysis. This guarantees a 50% discount on both input and output tokens across major providers (OpenAI, Anthropic).
*   **Hierarchical Model Routing:** Route simple binary classification tasks (e.g., "Is the brand mentioned? Yes/No") to ultra-cheap models like Grok-4.1 Fast or Gemini 3 Flash. Route complex sentiment/narrative analysis to GPT-5.2 or Claude Opus.

## 3. Output Control
*   Strictly limit `max_tokens` on responses.
*   Force `JSON` structured outputs to prevent expensive, verbose, conversational filler from the models.