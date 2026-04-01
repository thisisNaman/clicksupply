# ClickSupply: AI Pipeline & Backend Architecture

## 1. Tech Stack
*   **Backend Framework:** Python (FastAPI/Django) or Node.js.
*   **Database:** PostgreSQL (Relational) and Pinecone/Weaviate (Vector Database for semantic matching).
*   **Data Extraction:** API-first extraction of AI responses to prevent breakages caused by traditional HTML web scraping.

## 2. LLM Integration Gateway (The Probing Engine)
The backend must run "Synthetic Prompts" across multiple models to reverse-engineer their Retrieval-Augmented Generation (RAG) pipelines and calculate visibility.

### 2.1. Supported Global Models
*   OpenAI (ChatGPT Search, GPT-4o, GPT-o3)
*   Anthropic (Claude 3.5 Sonnet, Haiku, Opus)
*   Google (Gemini 3.1 Pro, Gemini 3 Flash, AI Overviews)
*   Perplexity AI & Microsoft Copilot

### 2.2. Sovereign Indic Models (Critical Differentiator)
ClickSupply must natively support Indian LLMs that are trained on culturally grounded data and Indian-language tokens.
*   **Sarvam AI:** Integration with Sarvam-105B (for complex reasoning in 11+ Indic languages) and Sarvam-30B.
*   **Krutrim:** Tracking visibility in Ola's consumer-facing AI.
*   **BharatGen & Hanooman:** For healthcare, education, and regional nuances.

## 3. Indic NLP & Code-Switching Layer
To accurately track brand mentions in India, the system must process 22 official languages, code-switched text (e.g., Hinglish, Tanglish), and multiple scripts.
*   **Linguistic Mapping:** Normalize phonetic spelling variations of brand names across Devanagari, Latin, and regional scripts.
*   **Code-Switching Support:** Utilize models fine-tuned on code-switched datasets (e.g., HingBERT or MuRIL) to accurately detect sentiment in mixed-language prompts.