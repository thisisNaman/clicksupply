"""
Playwright Browser Capture — Queries real AI web UIs for authentic response capture.

Instead of using APIs, this opens headless browsers to query:
- ChatGPT (chat.openai.com)
- Perplexity (perplexity.ai)
- Google Gemini (gemini.google.com)
- Google AIO (google.com - AI Overview)
- Microsoft Copilot (copilot.microsoft.com)
- And more

This captures what real users see, including citations, source panels, and formatting.
"""

import asyncio
import re

import structlog

from app.core.config import settings
from app.models.models import AIEngine

logger = structlog.get_logger()

# Lazy import playwright to avoid hard dependency in api mode
_playwright_module = None


def _get_playwright():
    global _playwright_module
    if _playwright_module is None:
        try:
            from playwright.async_api import async_playwright
            _playwright_module = async_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. "
                "Install with: pip install playwright && playwright install chromium"
            )
    return _playwright_module


# ── Engine URL + Selector Config ──

ENGINE_CONFIG = {
    AIEngine.CHATGPT: {
        "url": "https://chatgpt.com",
        "input_selector": "#prompt-textarea",
        "submit_selector": 'button[data-testid="send-button"]',
        "response_selector": '[data-message-author-role="assistant"]',
        "wait_for": '[data-message-author-role="assistant"]',
        "wait_timeout": 60_000,
        "needs_auth": True,
    },
    AIEngine.PERPLEXITY: {
        "url": "https://www.perplexity.ai",
        "input_selector": 'textarea, [contenteditable="true"], input[type="text"]',
        "submit_selector": 'button[aria-label="Submit"], button[type="submit"], button svg',
        "response_selector": ".prose, .markdown, [class*=\"answer\"], [class*=\"response\"]",
        "wait_for": ".prose, .markdown, [class*=\"answer\"], [class*=\"response\"]",
        "wait_timeout": 30_000,
        "needs_auth": False,
    },
    AIEngine.GEMINI: {
        "url": "https://gemini.google.com",
        "input_selector": '.ql-editor, [contenteditable="true"]',
        "submit_selector": 'button[aria-label="Send message"]',
        "response_selector": ".response-container, .model-response",
        "wait_for": ".response-container, .model-response",
        "wait_timeout": 45_000,
        "needs_auth": True,
    },
    AIEngine.GOOGLE_AIO: {
        "url": "https://www.google.com/search?q=",
        "input_selector": None,  # Query is in URL
        "submit_selector": None,
        "response_selector": '[data-attrid="ai_overview"], .kp-blk, .xpdopen',
        "wait_for": '[data-attrid="ai_overview"]',
        "wait_timeout": 15_000,
        "needs_auth": False,
    },
    AIEngine.COPILOT: {
        "url": "https://copilot.microsoft.com",
        "input_selector": 'textarea, #searchbox, [contenteditable="true"]',
        "submit_selector": 'button[aria-label="Submit"], button[type="submit"]',
        "response_selector": '.ac-textBlock, [class*="response"], [class*="message"]',
        "wait_for": '.ac-textBlock, [class*="response"], [class*="message"]',
        "wait_timeout": 45_000,
        "needs_auth": False,
    },
}


class PlaywrightCapture:
    """Browser-based AI response capture engine.

    Queries real AI web UIs using Playwright headless browsers
    to get authentic, user-facing responses.
    """

    def __init__(self):
        self._browser = None
        self._playwright = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Lazy-initialize the browser."""
        if self._browser is not None:
            return
        async with self._lock:
            if self._browser is not None:
                return
            async_playwright = _get_playwright()
            self._playwright = await async_playwright().__aenter__()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
            )
            logger.info("playwright_browser_launched")

    async def capture(self, prompt_text: str, engine: AIEngine) -> str:
        """Query an AI engine via browser and return the response text.

        Falls back to a simple HTTP fetch for engines without interactive UIs.
        """
        config = ENGINE_CONFIG.get(engine)

        if config is None:
            # Engines without browser config — use simple HTTP search fallback
            return await self._fallback_capture(prompt_text, engine)

        if engine == AIEngine.GOOGLE_AIO:
            return await self._capture_google_aio(prompt_text, config)

        if config.get("needs_auth"):
            # Auth-required engines need stored cookies/sessions
            # For now, fall back with a clear log message
            logger.warning(
                "browser_capture_needs_auth",
                engine=engine.value,
                hint="Set up browser session cookies for authenticated engines",
            )
            return await self._fallback_capture(prompt_text, engine)

        return await self._capture_interactive(prompt_text, engine, config)

    async def _capture_interactive(
        self, prompt_text: str, engine: AIEngine, config: dict
    ) -> str:
        """Capture from an interactive chat-style AI UI."""
        await self._ensure_browser()
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            await page.goto(config["url"], wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2000)  # Let JS hydrate

            # Type the prompt
            input_el = await page.wait_for_selector(config["input_selector"], timeout=10_000)
            await input_el.fill(prompt_text)
            await page.wait_for_timeout(500)

            # Submit
            submit_btn = await page.wait_for_selector(config["submit_selector"], timeout=5_000)
            await submit_btn.click()

            # Wait for response
            await page.wait_for_selector(
                config["wait_for"],
                timeout=config["wait_timeout"],
            )
            # Give extra time for streaming to finish
            await page.wait_for_timeout(5000)

            # Extract response text
            elements = await page.query_selector_all(config["response_selector"])
            texts = []
            for el in elements:
                text = await el.inner_text()
                if text.strip():
                    texts.append(text.strip())

            response = "\n\n".join(texts) if texts else ""

            # Also extract any citation links
            links = await page.query_selector_all(f"{config['response_selector']} a[href]")
            citations = []
            for link in links[:20]:  # Cap at 20 citations
                href = await link.get_attribute("href")
                if href and href.startswith("http"):
                    citations.append(href)

            if citations:
                response += "\n\nSources:\n" + "\n".join(f"- {url}" for url in citations)

            logger.info(
                "browser_capture_success",
                engine=engine.value,
                response_len=len(response),
            )
            return response or f"[No response captured from {engine.value}]"

        except Exception as e:
            logger.error("browser_capture_failed", engine=engine.value, error=str(e))
            return f"[Browser capture failed for {engine.value}: {type(e).__name__}]"
        finally:
            await context.close()

    async def _capture_google_aio(self, prompt_text: str, config: dict) -> str:
        """Capture Google AI Overview from search results."""
        await self._ensure_browser()
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            # Navigate directly with query in URL
            import urllib.parse
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(prompt_text)}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)

            # Wait for AI Overview to potentially appear
            try:
                await page.wait_for_selector(
                    config["wait_for"], timeout=config["wait_timeout"]
                )
            except Exception:
                # AI Overview not present for this query
                return "[No Google AI Overview for this query]"

            # Extract AI Overview content
            elements = await page.query_selector_all(config["response_selector"])
            texts = []
            for el in elements:
                text = await el.inner_text()
                if text.strip():
                    texts.append(text.strip())

            response = "\n\n".join(texts) if texts else "[No AI Overview content]"

            logger.info("google_aio_capture_success", response_len=len(response))
            return response

        except Exception as e:
            logger.error("google_aio_capture_failed", error=str(e))
            return f"[Google AIO capture failed: {type(e).__name__}]"
        finally:
            await context.close()

    async def _fallback_capture(self, prompt_text: str, engine: AIEngine) -> str:
        """Simple HTTP-based fallback for engines without browser automation."""
        logger.info("browser_capture_fallback", engine=engine.value)
        return (
            f"[Browser capture not yet configured for {engine.value}. "
            f"Configure ENGINE_CONFIG or use LLM_MODE=api for this engine.]"
        )

    async def shutdown(self):
        """Close the browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.__aexit__(None, None, None)
            self._playwright = None
            logger.info("playwright_browser_closed")
