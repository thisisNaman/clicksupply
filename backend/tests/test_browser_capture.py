"""Tests for Playwright browser capture configuration."""

from app.models.models import AIEngine
from app.services.capture.browser import ENGINE_CONFIG, PlaywrightCapture


class TestEngineConfig:
    def test_chatgpt_config_exists(self):
        assert AIEngine.CHATGPT in ENGINE_CONFIG
        assert "url" in ENGINE_CONFIG[AIEngine.CHATGPT]

    def test_perplexity_config_exists(self):
        assert AIEngine.PERPLEXITY in ENGINE_CONFIG
        assert ENGINE_CONFIG[AIEngine.PERPLEXITY]["needs_auth"] is False

    def test_google_aio_config_has_no_input(self):
        """Google AIO uses URL query, not input selector."""
        config = ENGINE_CONFIG[AIEngine.GOOGLE_AIO]
        assert config["input_selector"] is None
        assert config["submit_selector"] is None

    def test_copilot_config_exists(self):
        assert AIEngine.COPILOT in ENGINE_CONFIG

    def test_gemini_config_needs_auth(self):
        assert ENGINE_CONFIG[AIEngine.GEMINI]["needs_auth"] is True

    def test_all_configs_have_required_fields(self):
        required = {"url", "response_selector", "wait_for", "wait_timeout", "needs_auth"}
        for engine, config in ENGINE_CONFIG.items():
            for field in required:
                assert field in config, f"{engine.value} missing {field}"


class TestPlaywrightCaptureInit:
    def test_capture_creates(self):
        capture = PlaywrightCapture()
        assert capture._browser is None  # Lazy-init
        assert capture._playwright is None

    def test_unconfigured_engines_fallback(self):
        """Engines not in ENGINE_CONFIG should be handled gracefully."""
        # DEEPSEEK, META_AI, SARVAM, KRUTRIM are not in ENGINE_CONFIG
        unconfigured = [AIEngine.DEEPSEEK, AIEngine.META_AI, AIEngine.SARVAM, AIEngine.KRUTRIM]
        for engine in unconfigured:
            assert engine not in ENGINE_CONFIG


class TestCaptureEngineMode:
    def test_provider_lazy_inits(self):
        """Copilot SDK providers should lazy-init on first access."""
        from app.services.capture.engine import CaptureEngine
        engine = CaptureEngine()
        assert engine._providers == {}
        provider = engine._get_provider(AIEngine.CHATGPT)
        assert provider is not None
        assert "gpt-4.1" in engine._providers

    def test_provider_reuses_instance(self):
        """Engines sharing the same model should reuse the same provider."""
        from app.services.capture.engine import CaptureEngine
        engine = CaptureEngine()
        p1 = engine._get_provider(AIEngine.CHATGPT)
        p2 = engine._get_provider(AIEngine.COPILOT)
        assert p1 is p2  # Both use gpt-4.1
