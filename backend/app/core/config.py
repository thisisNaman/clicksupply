from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "ClickSupply"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://clicksupply:clicksupply@localhost:5432/clicksupply"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # ── Copilot SDK (for response analysis) ──
    # All LLM analysis uses GitHub Copilot SDK.
    COPILOT_MODEL: str = "gpt-4.1"
    GITHUB_TOKEN: str = ""  # GitHub PAT with copilot scope  # Model to use via Copilot SDK

    # LLM Cost Controls
    DEFAULT_MAX_TOKENS: int = 1024
    MONTHLY_TOKEN_BUDGET: int = 100_000_000  # 100M tokens default

    # Capture Engine
    CAPTURE_CONCURRENCY: int = 5
    CAPTURE_INTERVAL_HOURS: int = 24
    CAPTURE_SCHEDULE_HOUR: int = 2  # Hour (UTC) for daily capture job
    PLAYWRIGHT_HEADLESS: bool = True  # Run browser in headless mode

    # DPDPA Compliance
    DATA_REGION: str = "ap-south-1"  # AWS Mumbai
    AUDIT_LOG_RETENTION_DAYS: int = 365
    BREACH_NOTIFICATION_HOURS: int = 72

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = Settings()
