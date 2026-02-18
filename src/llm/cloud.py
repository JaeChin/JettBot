"""
Claude API streaming wrapper.

Thin wrapper around the Anthropic Python SDK that yields tokens one at a time,
matching the same generator interface as Ollama streaming.
"""

import os
from typing import Generator, Optional


class CloudLLM:
    """
    Streams responses from Claude API.

    Uses the Anthropic SDK's streaming API to yield tokens incrementally,
    compatible with the pipeline's speak_streaming() method.
    """

    SYSTEM_PROMPT = (
        "You are Jett, a helpful voice assistant. "
        "Keep responses concise — 1 to 3 sentences max. "
        "Be direct and conversational."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 150,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

        # Resolve API key: explicit > env var
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    @property
    def available(self) -> bool:
        """Check if cloud LLM is configured (has an API key)."""
        return self._api_key is not None

    def _ensure_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "No API key. Set ANTHROPIC_API_KEY env var or pass api_key."
                )
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)

    def stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Stream a response from Claude API.

        Yields:
            Text chunks as they arrive from the API.
        """
        try:
            self._ensure_client()
        except RuntimeError as e:
            yield f"[Cloud LLM unavailable: {e}]"
            return

        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        yield text
        except Exception as e:
            yield f"[Cloud error: {e}]"
