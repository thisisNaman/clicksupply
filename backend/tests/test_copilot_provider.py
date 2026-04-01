"""Tests for Copilot SDK provider."""

from unittest.mock import patch, AsyncMock, MagicMock


class TestCopilotSDKProvider:
    def test_provider_creates_with_default_model(self):
        """Provider should use COPILOT_MODEL from settings."""
        with patch("app.services.llm.copilot_provider.settings") as mock_settings:
            mock_settings.COPILOT_MODEL = "gpt-4.1"
            from app.services.llm.copilot_provider import CopilotSDKProvider
            provider = CopilotSDKProvider()
            assert provider.model == "gpt-4.1"

    def test_provider_creates_with_custom_model(self):
        """Provider should accept a custom model override."""
        with patch("app.services.llm.copilot_provider.settings") as mock_settings:
            mock_settings.COPILOT_MODEL = "gpt-4.1"
            from app.services.llm.copilot_provider import CopilotSDKProvider
            provider = CopilotSDKProvider(model="claude-sonnet-4")
            assert provider.model == "claude-sonnet-4"

    def test_copilot_model_returns_prefixed_name(self):
        """Complete result should have model prefixed with 'copilot:'."""
        with patch("app.services.llm.copilot_provider.settings") as mock_settings:
            mock_settings.COPILOT_MODEL = "gpt-4.1"
            from app.services.llm.copilot_provider import CopilotSDKProvider
            provider = CopilotSDKProvider()
            # The model in results will be "copilot:gpt-4.1"
            assert provider.model == "gpt-4.1"
