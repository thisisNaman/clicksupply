"""Tests for LLM Gateway cost calculation, tier routing, and Copilot SDK init."""

from unittest.mock import patch, MagicMock

from app.services.llm.gateway import (
    LLMGateway,
    ModelTier,
    TIER_MODEL_MAP,
    calculate_cost,
)


class TestCostCalculation:
    def test_gemini_flash_cost(self):
        cost = calculate_cost("gemini-2.0-flash", 1_000_000, 1_000_000)
        assert cost == 0.50 + 3.00  # $3.50 per 1M in + 1M out

    def test_haiku_cost(self):
        cost = calculate_cost("claude-3-5-haiku-20241022", 500_000, 100_000)
        expected = (500_000 * 1.00 + 100_000 * 5.00) / 1_000_000
        assert abs(cost - expected) < 0.001

    def test_small_request(self):
        cost = calculate_cost("gpt-4o-mini", 1000, 500)
        expected = (1000 * 0.15 + 500 * 0.60) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_unknown_model_defaults(self):
        cost = calculate_cost("unknown-model", 1_000_000, 1_000_000)
        assert cost == 1.0 + 5.0  # default costs

    def test_copilot_model_zero_cost(self):
        """Copilot SDK models should report zero cost (billed via subscription)."""
        cost = calculate_cost("copilot:gpt-4.1", 1_000_000, 1_000_000)
        assert cost == 0.0


class TestTierModelMap:
    def test_cheap_tier_has_models(self):
        assert len(TIER_MODEL_MAP[ModelTier.CHEAP]) >= 1

    def test_standard_tier_has_models(self):
        assert len(TIER_MODEL_MAP[ModelTier.STANDARD]) >= 1

    def test_premium_tier_has_models(self):
        assert len(TIER_MODEL_MAP[ModelTier.PREMIUM]) >= 1


class TestGatewayInit:
    def test_gateway_creates_with_copilot_sdk(self):
        """Gateway should initialize with Copilot SDK provider."""
        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.COPILOT_MODEL = "gpt-4.1"
            mock_settings.DEFAULT_MAX_TOKENS = 1024
            gateway = LLMGateway()
            assert gateway._copilot_provider is not None

    def test_gateway_uses_configured_model(self):
        """Gateway should use the COPILOT_MODEL from settings."""
        with patch("app.services.llm.gateway.settings") as mock_settings:
            mock_settings.COPILOT_MODEL = "claude-sonnet-4"
            mock_settings.DEFAULT_MAX_TOKENS = 1024
            gateway = LLMGateway()
            assert gateway._copilot_provider.model == "claude-sonnet-4"
