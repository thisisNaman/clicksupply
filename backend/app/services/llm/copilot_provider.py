"""
Copilot SDK Provider — Uses GitHub Copilot SDK for LLM completions.

Zero API keys required. Uses the user's GitHub Copilot subscription.
All LLM analysis (brand signal extraction) flows through this provider.
"""

import asyncio

import structlog

from copilot import (
    CopilotClient,
    CopilotSession,
    PermissionHandler,
    SubprocessConfig,
    SystemMessageReplaceConfig,
)
from copilot.generated.session_events import SessionEventType

from app.core.config import settings

logger = structlog.get_logger()

# Singleton client — shared across the process
_client: CopilotClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> CopilotClient:
    """Lazily initialise and return the shared CopilotClient."""
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        config = SubprocessConfig(github_token=settings.GITHUB_TOKEN) if settings.GITHUB_TOKEN else None
        _client = CopilotClient(config=config, auto_start=True)
        await _client.start()
        logger.info("copilot_client_started")
        return _client


class CopilotSDKProvider:
    """LLM provider backed by GitHub Copilot SDK.

    Each `complete()` call creates a short-lived session, sends the prompt,
    waits for the assistant's response, and tears down the session.
    """

    def __init__(self, model: str | None = None):
        self.model = model or settings.COPILOT_MODEL

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Send a prompt through Copilot SDK and return structured result.

        Returns: {"text": str, "input_tokens": int, "output_tokens": int, "model": str}
        """
        client = await _get_client()

        system_message = None
        if system:
            system_message = SystemMessageReplaceConfig(mode="replace", content=system)

        session: CopilotSession = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model=self.model,
            system_message=system_message,
            tools=[],  # No tools needed for analysis
        )

        try:
            event = await session.send_and_wait(prompt, timeout=120.0)

            # Extract the assistant message text
            text = ""
            if event and event.data and event.data.content:
                text = event.data.content
            elif event and event.type == SessionEventType.ASSISTANT_MESSAGE:
                text = event.data.content or ""

            # If we got a turn_end event, pull the last message from the session
            if not text and event and event.type == SessionEventType.ASSISTANT_TURN_END:
                messages = await session.get_messages()
                for msg in reversed(messages):
                    if hasattr(msg, "role") and msg.role == "assistant" and hasattr(msg, "content"):
                        text = msg.content
                        break

            return {
                "text": text,
                "input_tokens": 0,  # Copilot SDK doesn't expose token counts
                "output_tokens": 0,
                "model": f"copilot:{self.model}",
            }
        finally:
            await session.disconnect()

    async def list_available_models(self) -> list[str]:
        """List models available through the Copilot SDK."""
        client = await _get_client()
        models = await client.list_models()
        return [m.id for m in models if hasattr(m, "id")]


async def shutdown_copilot():
    """Gracefully shut down the Copilot client."""
    global _client
    if _client is not None:
        await _client.stop()
        _client = None
        logger.info("copilot_client_stopped")
