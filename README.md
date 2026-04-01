# ClickSupply — AEO/GEO Platform

Enterprise **Answer Engine Optimization (AEO)** and **Generative Engine Optimization (GEO)** platform for the Indian market. Track how AI engines mention your brand, audit AI-readiness, and optimize for visibility across ChatGPT, Perplexity, Gemini, Claude, and more.

## Project Structure

```
clicksupply/
├── backend/            # Python FastAPI application
│   ├── app/
│   │   ├── api/        # REST endpoints (auth, brands, analytics, aeo, capture)
│   │   ├── core/       # Config, database, security, logging
│   │   ├── models/     # SQLAlchemy ORM models
│   │   ├── schemas/    # Pydantic request/response schemas
│   │   ├── services/   # Business logic
│   │   │   ├── analytics/      # Crawler parser, keyword extraction, visibility
│   │   │   ├── capture/        # Playwright browser automation engine
│   │   │   ├── llm/            # LLM gateway + GitHub Copilot SDK provider
│   │   │   └── recommendations/ # AEO audit engine
│   │   └── workers/    # APScheduler background tasks
│   ├── alembic/        # Database migrations
│   ├── tests/          # pytest test suite
│   ├── .env.example    # Environment variable template
│   └── Dockerfile
├── frontend/           # Next.js 15 application
│   ├── src/
│   │   ├── app/        # App Router pages (dashboard, login, signup)
│   │   ├── components/ # Shared UI components
│   │   └── lib/        # API client, hooks, context
│   └── Dockerfile
├── research/           # Product research and architecture docs
│   ├── 01_Product_Overview_and_Features.md
│   ├── 02_AI_and_Backend_Architecture.md
│   ├── 03_AEO_Recommendation_Engine.md
│   ├── 04_FinOps_and_LLM_Cost_Optimization.md
│   ├── 05_Data_Privacy_and_DPDPA_Compliance.md
│   └── 06_Implementation_Phases.md
└── docker-compose.yml
```

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│   Next.js       │────▶│  FastAPI Backend                             │
│   Frontend      │     │                                              │
│   (port 3000)   │     │  ┌───────────┐  ┌──────────────────┐       │
└─────────────────┘     │  │ Auth/RBAC │  │ LLM Gateway      │       │
                        │  └───────────┘  │ ├─ GitHub Copilot│       │
                        │                  │ ├─ OpenAI        │       │
                        │  ┌───────────┐  │ ├─ Anthropic     │       │
                        │  │ Analytics │  │ ├─ Gemini        │       │
                        │  │ Engine    │  │ └─ Sarvam AI     │       │
                        │  └───────────┘  └──────────────────┘       │
                        │                  ┌──────────────────┐       │
                        │  ┌───────────┐  │ Capture Engine   │       │
                        │  │ AEO Audit │  │ (Playwright +    │       │
                        │  │ Engine    │  │  Synthetic       │       │
                        │  └───────────┘  │  Prompts)        │       │
                        │                  └──────────────────┘       │
                        │  ┌───────────┐  ┌──────────────────┐       │
                        │  │ Crawler   │  │ Agent Analytics  │       │
                        │  │ Parser    │  │ (Log Ingestion)  │       │
                        │  └───────────┘  └──────────────────┘       │
                        └──────────────────────────────────────────────┘
                                      │
                        ┌─────────────┼──────────────┐
                        │             │              │
                   PostgreSQL     Redis         APScheduler
                   (data)         (cache/queue)  (background jobs)
```

## Prerequisites

- **Docker & Docker Compose** — for running PostgreSQL and Redis
- **Python 3.11+** — for the backend
- **Node.js 20+** — for the frontend
- **GitHub Personal Access Token** — used by the LLM Gateway via GitHub Copilot SDK (`GITHUB_TOKEN`)

## Quick Start

### 1. Start infrastructure

```bash
docker compose up db redis -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env        # Fill in SECRET_KEY and GITHUB_TOKEN
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Visit

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Full stack via Docker Compose

```bash
docker compose up --build
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the required values:

| Variable              | Required | Description                                             |
| --------------------- | -------- | ------------------------------------------------------- |
| `SECRET_KEY`          | Yes      | JWT signing key — generate with `openssl rand -hex 32`  |
| `GITHUB_TOKEN`        | Yes      | GitHub PAT for Copilot SDK LLM access                   |
| `DATABASE_URL`        | Yes      | PostgreSQL connection string                            |
| `REDIS_URL`           | Yes      | Redis connection string                                 |
| `COPILOT_MODEL`       | No       | LLM model name (default: `gpt-4.1`)                     |
| `PLAYWRIGHT_HEADLESS` | No       | Run browsers headlessly (default: `true`)               |
| `DATA_REGION`         | No       | AWS region for DPDPA compliance (default: `ap-south-1`) |

> **Security**: Never commit `backend/.env` to version control. It is listed in `.gitignore`.

## API Endpoints

| Method | Path                                       | Description                             |
| ------ | ------------------------------------------ | --------------------------------------- |
| POST   | `/api/v1/auth/signup`                      | Create account (DPDPA consent required) |
| POST   | `/api/v1/auth/login`                       | Login                                   |
| GET    | `/api/v1/auth/me`                          | Current user                            |
| POST   | `/api/v1/brands`                           | Create brand to track                   |
| GET    | `/api/v1/brands`                           | List brands                             |
| POST   | `/api/v1/brands/{id}/prompts`              | Add tracked prompt                      |
| POST   | `/api/v1/brands/{id}/competitors`          | Add competitor                          |
| GET    | `/api/v1/analytics/visibility/{id}`        | Visibility scores over time             |
| GET    | `/api/v1/analytics/share-of-model/{id}`    | Real-time SoM calculation               |
| GET    | `/api/v1/analytics/crawlers/{id}`          | AI crawler statistics                   |
| GET    | `/api/v1/analytics/responses/{id}`         | Raw AI responses                        |
| POST   | `/api/v1/aeo/audit`                        | AEO page audit with recommendations     |
| POST   | `/api/v1/agent-analytics/{id}/ingest-logs` | Upload server logs                      |

Full interactive docs available at http://localhost:8000/docs when running locally.

## Core Modules

### 1. Answer Engine Insights

Track brand visibility across 11 AI engines: ChatGPT, Perplexity, Gemini, Google AI Overviews, Claude, Copilot, Grok, DeepSeek, Meta AI, Sarvam AI, Krutrim.

### 2. Share of Model (SoM)

`(Brand Citations / Total Citations) × 100` — the AI-era equivalent of Share of Voice.

### 3. Agent Analytics

Ingest AWS/Cloudflare server logs to track GPTBot, ClaudeBot, PerplexityBot, and other AI crawlers. Identifies 7+ bot signatures including Googlebot, Bingbot, MetaBot, and Bytespider.

### 4. AEO Audit Engine

Audit any URL for AI readiness:

- Content structure (answer-first, semantic chunking)
- Schema markup (FAQPage, Organization, Article JSON-LD)
- Technical GEO (JS complexity, robots directives)
- Trust signals (E-E-A-T, author attribution, external references)
- Auto-generates `llms.txt`

### 5. LLM Gateway

Hierarchical model routing with cost controls (100M token/month budget):

- **Cheap tier**: Gemini Flash, GPT-4o-mini (mention detection)
- **Standard tier**: Claude Haiku, GPT-4o (sentiment analysis)
- **Premium tier**: Claude Sonnet (content generation)
- Primary provider: **GitHub Copilot SDK** (no per-token billing, uses GitHub subscription)

### 6. Capture Engine

Playwright-based headless browser automation that submits synthetic prompts to AI engines and captures responses for brand mention analysis. Supports 5 concurrent captures.

## Indian Market Differentiators

- 22 Indic language support (Hinglish, Tanglish code-switching via MuRIL)
- Sovereign Indian LLMs (Sarvam AI, Krutrim, BharatGen)
- DPDPA compliance (consent management, data localization in AWS Mumbai `ap-south-1`)
- Indian verification anchors (NSE/BSE, Wikidata entity graphs)

## Tech Stack

| Layer          | Technology                                                                |
| -------------- | ------------------------------------------------------------------------- |
| Frontend       | Next.js 15.2, React 19, Tailwind CSS 4, Recharts                          |
| Backend        | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Alembic                       |
| Database       | PostgreSQL 16, Redis 7                                                    |
| LLM            | GitHub Copilot SDK (primary), OpenAI, Anthropic, Google Gemini, Sarvam AI |
| Browser        | Playwright (headless Chromium)                                            |
| Auth           | JWT (python-jose + bcrypt)                                                |
| Scheduler      | APScheduler 3.10 + Celery 5.4                                             |
| Logging        | structlog                                                                 |
| Infrastructure | Docker Compose, AWS Mumbai region                                         |

## Tests

All tests are in `backend/tests/`. Run with:

```bash
cd backend && source .venv/bin/activate
pytest tests/ -v
```

| Test file                  | Coverage                                                                           |
| -------------------------- | ---------------------------------------------------------------------------------- |
| `test_aeo_engine.py`       | AEO audit: content structure, FAQPage schema, trust signals, `llms.txt` generation |
| `test_browser_capture.py`  | Playwright capture config per AI engine, lazy init, provider reuse                 |
| `test_copilot_provider.py` | GitHub Copilot SDK provider: model defaults, name prefixing                        |
| `test_crawler_parser.py`   | Bot identification (GPTBot, ClaudeBot, PerplexityBot, etc.), log line parsing      |
| `test_insights.py`         | Pydantic schema validation for all analytics response types                        |
| `test_keywords.py`         | Keyword extraction, stopword filtering, sentiment-aware n-grams                    |
| `test_llm_gateway.py`      | Cost calculation per tier, gateway init, `COPILOT_MODEL` config                    |
| `test_scheduler.py`        | APScheduler start/stop, background task imports                                    |
