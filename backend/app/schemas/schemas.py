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


class PromptUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=5, max_length=2000)
    language: str | None = None
    region: str | None = None
    is_active: bool | None = None


class PromptOut(BaseModel):
    id: uuid.UUID
    text: str
    language: str
    region: str
    intent: str | None = None
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


class AIResponseDetail(BaseModel):
    id: uuid.UUID
    engine: str
    raw_response: str
    brand_mentioned: bool
    generative_position: int | None
    sentiment: str | None
    citations: dict | None
    extra_metadata: dict | None
    captured_at: datetime
    cost_usd: float
    prompt_text: str | None = None
    prompt_language: str | None = None
    prompt_region: str | None = None


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


# ──────────────────────────── Intent Distribution ────────────────────────────


class IntentDistribution(BaseModel):
    intent: str
    count: int
    pct: float


class IntentPrompt(BaseModel):
    text: str
    visibility_pct: float


class IntentResponse(BaseModel):
    distribution: list[IntentDistribution]
    top_prompts_by_intent: dict[str, list[IntentPrompt]]


# ──────────────────────────── Co-Citations ────────────────────────────


class CoCitedBrand(BaseModel):
    name: str
    co_occurrence_count: int
    platforms: list[str]
    avg_sentiment: str


class UncitedGap(BaseModel):
    prompt_text: str
    prompt_id: str
    competitor_name: str
    competitor_sentiment: str
    engines: list[str]


class CoCitationResponse(BaseModel):
    co_cited_brands: list[CoCitedBrand]
    total_responses_with_brand: int
    uncited_gaps: list[UncitedGap]
    total_prompts_analyzed: int


# ──────────────────────── Prompt-Brand Matrix ────────────────────────


class BrandMention(BaseModel):
    name: str
    engines: list[str]
    mention_count: int
    avg_position: float | None = None
    dominant_sentiment: str
    is_target: bool


class PromptBrandEntry(BaseModel):
    prompt_text: str
    prompt_id: str
    intent: str | None = None
    brand_mentions: list[BrandMention]


class PromptBrandMatrix(BaseModel):
    prompts: list[PromptBrandEntry]
    total_prompts: int
    brands_found: list[str]


# ──────────────── Topic Clustering ────────────────────


class TopicPrompt(BaseModel):
    prompt_id: str
    text: str
    intent: str | None = None
    visibility_pct: float
    mention_count: int


class TopicCluster(BaseModel):
    topic: str
    prompt_count: int
    avg_visibility: float
    avg_position: float | None = None
    dominant_intent: str | None = None
    prompts: list[TopicPrompt]


class TopicClusterResponse(BaseModel):
    clusters: list[TopicCluster]
    total_prompts: int
    total_topics: int


# ──────────────── Competitive Citations ────────────────────


class CompetitorCitationDomain(BaseModel):
    domain: str
    count: int
    engines: list[str]
    avg_sentiment: str


class CompetitorCitations(BaseModel):
    competitor_name: str
    total_citations: int
    top_domains: list[CompetitorCitationDomain]


class CompetitorCitationsResponse(BaseModel):
    competitors: list[CompetitorCitations]
    your_top_domains: list[CompetitorCitationDomain]
    overlap_domains: list[str]


# ──────────────── Smart Insights ────────────────────


class InsightItem(BaseModel):
    type: str
    severity: str
    title: str
    description: str
    action: str | None = None
    engine: str | None = None
    metric_before: float | None = None
    metric_after: float | None = None
    change_pct: float | None = None
    examples: list[dict] | None = None
    prompts: list[dict] | None = None
    top_sources: list[dict] | None = None
    engine_breakdown: list[dict] | None = None


class InsightsResponse(BaseModel):
    insights: list[InsightItem]
    generated_at: str


# ──────────────── Brand Health Score ────────────────────


class HealthPillar(BaseModel):
    score: float
    weight: int
    detail: str
    trend: float


class HealthScoreResponse(BaseModel):
    score: float
    grade: str
    trend: float
    period_days: int
    pillars: dict[str, HealthPillar]


# ──────────────── Action Center ────────────────────


class ActionItem(BaseModel):
    id: str
    brand_id: str
    category: str
    title: str
    description: str
    impact: str
    effort: str
    action_type: str
    status: str
    priority_rank: int
    created_at: str
    prompt_text: str | None = None
    prompt_id: str | None = None
    current_mention_rate: float | None = None
    suggested_content: str | None = None
    suggested_schema: str | None = None
    engine: str | None = None
    current_rate: float | None = None
    updated_at: str | None = None
    # Verification fields
    verification_type: str | None = None  # aeo_audit, re_capture, crawler_check, manual
    baseline_value: float | None = None
    verified_at: str | None = None
    verified_value: float | None = None
    verification_status: str | None = None  # improved, no_change, regressed, error
    # Crawler-specific
    crawler_type: str | None = None
    # Website audit metadata
    audit_category: str | None = None
    audit_severity: str | None = None
    engines_missing: list[str] | None = None
    engines_citing: list[str] | None = None


class ActionsResponse(BaseModel):
    actions: list[ActionItem]
    total: int
    pending: int
    completed: int


class ActionStatusUpdate(BaseModel):
    status: str = Field(description="New status: pending, in_progress, completed, dismissed")
