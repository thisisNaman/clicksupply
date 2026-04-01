import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────── Auth ────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)
    consent_given: bool = Field(
        description="DPDPA: User must consent to data processing"
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ──────────────────────────── Users ────────────────────────────


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    organization_id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────── Brands ────────────────────────────


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str | None = None
    aliases: dict[str, str] | None = None
    industry: str | None = None


class BrandOut(BaseModel):
    id: uuid.UUID
    name: str
    domain: str | None
    aliases: dict | None
    industry: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    aliases: dict[str, str] | None = None
    industry: str | None = None


# ──────────────────────────── Prompts ────────────────────────────


class PromptCreate(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    language: str = "en"
    region: str = "IN"


class PromptOut(BaseModel):
    id: uuid.UUID
    text: str
    language: str
    region: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────── Visibility ────────────────────────────


class VisibilityScoreOut(BaseModel):
    engine: str
    date: datetime
    share_of_model: float
    avg_generative_position: float | None
    mention_count: int
    total_prompts_run: int
    positive_sentiment_pct: float
    negative_sentiment_pct: float
    neutral_sentiment_pct: float
    top_citations: dict | None

    model_config = {"from_attributes": True}


# ──────────────────────────── Crawler Logs ────────────────────────────


class CrawlerLogCreate(BaseModel):
    crawler_type: str
    ip_address: str
    user_agent: str
    request_path: str
    status_code: int
    response_size_bytes: int = 0
    timestamp: datetime


class CrawlerLogOut(BaseModel):
    id: uuid.UUID
    crawler_type: str
    request_path: str
    status_code: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class CrawlerStats(BaseModel):
    crawler_type: str
    total_visits: int
    unique_paths: int
    avg_response_size: float
    latest_visit: datetime | None


# ──────────────────────────── Competitors ────────────────────────────


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str | None = None


class CompetitorOut(BaseModel):
    id: uuid.UUID
    name: str
    domain: str | None

    model_config = {"from_attributes": True}


# ──────────────────────────── AI Response ────────────────────────────


class AIResponseOut(BaseModel):
    id: uuid.UUID
    engine: str
    brand_mentioned: bool
    generative_position: int | None
    sentiment: str | None
    citations: dict | None
    captured_at: datetime
    cost_usd: float

    model_config = {"from_attributes": True}


# ──────────────────────────── AEO Recommendations ────────────────────────────


class AEOAuditRequest(BaseModel):
    url: str = Field(description="Page URL to audit for AEO readiness")


class AEORecommendation(BaseModel):
    category: str  # "content_structure", "schema_markup", "technical", "trust"
    severity: str  # "critical", "warning", "info"
    title: str
    description: str
    action: str


class AEOAuditResult(BaseModel):
    url: str
    score: float  # 0-100
    recommendations: list[AEORecommendation]
    schema_suggestions: dict | None
    llms_txt_content: str | None


# ──────────────────────────── Insights ────────────────────────────


class SentimentByEngine(BaseModel):
    engine: str
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    total_responses: int


class KeywordItem(BaseModel):
    word: str
    count: int
    sentiment_bias: str  # "positive", "neutral", "negative"


class SentimentTrend(BaseModel):
    date: str
    positive_pct: float
    neutral_pct: float
    negative_pct: float


class SentimentResponse(BaseModel):
    per_engine: list[SentimentByEngine]
    top_keywords: list[KeywordItem]
    trend: list[SentimentTrend]


class CitationDomain(BaseModel):
    domain: str
    count: int
    engines: list[str]


class CitationResponse(BaseModel):
    top_domains: list[CitationDomain]
    total_citations: int
    unique_domains: int


class TrendPoint(BaseModel):
    date: str
    visibility_score: float
    mention_count: int
    avg_position: float | None
    sentiment_positive_pct: float


class TrendsResponse(BaseModel):
    series: list[TrendPoint]


class PlatformStat(BaseModel):
    engine: str
    visibility_score: float
    avg_position: float | None
    mention_rate: float
    sentiment_positive_pct: float
    citation_count: int


class PlatformsResponse(BaseModel):
    platforms: list[PlatformStat]


class BenchmarkMetrics(BaseModel):
    name: str
    domain: str | None = None
    avg_som: float
    avg_position: float | None
    mention_count: int
    sentiment_positive_pct: float


class BenchmarkResponse(BaseModel):
    brand: BenchmarkMetrics
    competitors: list[BenchmarkMetrics]
    rankings: dict[str, int]  # {"som_rank": 1, "position_rank": 2}
