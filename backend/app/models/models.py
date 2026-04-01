import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────── Enums ────────────────────────────


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class AIEngine(str, enum.Enum):
    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"
    GOOGLE_AIO = "google_aio"
    CLAUDE = "claude"
    COPILOT = "copilot"
    GROK = "grok"
    DEEPSEEK = "deepseek"
    META_AI = "meta_ai"
    SARVAM = "sarvam"
    KRUTRIM = "krutrim"


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class CrawlerType(str, enum.Enum):
    GPTBOT = "GPTBot"
    CLAUDEBOT = "ClaudeBot"
    GOOGLEBOT = "Googlebot"
    BINGBOT = "Bingbot"
    PERPLEXITYBOT = "PerplexityBot"
    METABOT = "meta-externalagent"
    BYTESPIDER = "Bytespider"
    UNKNOWN = "unknown"


# ──────────────────────────── Users & Orgs ────────────────────────────


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    monthly_prompt_limit: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    brands: Mapped[list["Brand"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)  # DPDPA
    consent_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="users")


# ──────────────────────────── Brands & Tracking ────────────────────────────


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=True)
    aliases: Mapped[dict | None] = mapped_column(JSONB, default=dict)  # {"hindi": "ब्रांड", ...}
    industry: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="brands")
    prompts: Mapped[list["TrackedPrompt"]] = relationship(back_populates="brand")
    visibility_scores: Mapped[list["VisibilityScore"]] = relationship(back_populates="brand")
    crawler_logs: Mapped[list["CrawlerLog"]] = relationship(back_populates="brand")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="brand")

    __table_args__ = (Index("ix_brands_org_name", "organization_id", "name"),)


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))

    brand: Mapped["Brand"] = relationship(back_populates="competitors")


# ──────────────────────────── Prompts & AI Responses ────────────────────────────


class TrackedPrompt(Base):
    __tablename__ = "tracked_prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    region: Mapped[str] = mapped_column(String(10), default="IN")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="prompts")
    responses: Mapped[list["AIResponse"]] = relationship(back_populates="prompt")

    __table_args__ = (Index("ix_prompts_brand_active", "brand_id", "is_active"),)


class AIResponse(Base):
    __tablename__ = "ai_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracked_prompts.id"), nullable=False
    )
    engine: Mapped[AIEngine] = mapped_column(Enum(AIEngine), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    generative_position: Mapped[int | None] = mapped_column(Integer)  # rank in listicle
    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment))
    citations: Mapped[dict | None] = mapped_column(JSONB)  # [{"url": "...", "domain": "..."}]
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB)  # model version, tokens used, etc.
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    prompt: Mapped["TrackedPrompt"] = relationship(back_populates="responses")

    __table_args__ = (
        Index("ix_responses_prompt_engine", "prompt_id", "engine"),
        Index("ix_responses_captured_at", "captured_at"),
    )


# ──────────────────────────── Visibility Scores ────────────────────────────


class VisibilityScore(Base):
    """Daily aggregated visibility score per brand per engine."""

    __tablename__ = "visibility_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    engine: Mapped[AIEngine] = mapped_column(Enum(AIEngine), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    share_of_model: Mapped[float] = mapped_column(Float, default=0.0)  # percentage
    avg_generative_position: Mapped[float | None] = mapped_column(Float)
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    total_prompts_run: Mapped[int] = mapped_column(Integer, default=0)
    positive_sentiment_pct: Mapped[float] = mapped_column(Float, default=0.0)
    negative_sentiment_pct: Mapped[float] = mapped_column(Float, default=0.0)
    neutral_sentiment_pct: Mapped[float] = mapped_column(Float, default=0.0)
    top_citations: Mapped[dict | None] = mapped_column(JSONB)

    brand: Mapped["Brand"] = relationship(back_populates="visibility_scores")

    __table_args__ = (
        Index("ix_visibility_brand_engine_date", "brand_id", "engine", "date", unique=True),
    )


# ──────────────────────────── Crawler / Agent Analytics ────────────────────────────


class CrawlerLog(Base):
    __tablename__ = "crawler_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    crawler_type: Mapped[CrawlerType] = mapped_column(Enum(CrawlerType), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    request_path: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    brand: Mapped["Brand"] = relationship(back_populates="crawler_logs")

    __table_args__ = (
        Index("ix_crawler_brand_type_ts", "brand_id", "crawler_type", "timestamp"),
    )


# ──────────────────────────── Audit Log (DPDPA) ────────────────────────────


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_audit_ts", "timestamp"),)
