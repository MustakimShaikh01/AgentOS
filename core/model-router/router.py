"""
core/model-router/router.py

LiteLLM wrapper that provides model-agnostic LLM access.

Design:
    All LLM calls in the entire application go through this module.
    Never import openai, anthropic, or google.generativeai directly.
    This ensures models are swappable via config, not code changes.

Stage 1: Basic LiteLLM wrapper
Stage 5: Add cost routing, fallback chains, circuit breaker
"""

import litellm
from app.config import get_settings

settings = get_settings()

# Configure LiteLLM to use our proxy
litellm.api_base = settings.litellm_base_url


class LLMClient:
    """
    Thin wrapper around LiteLLM for a specific model.
    Provides a consistent interface regardless of provider.
    """

    def __init__(self, model: str):
        self.model = model

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        """
        Send a chat completion request.
        Returns: {"content": str, "tokens": int, "model": str}
        """
        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": response.usage.total_tokens if response.usage else 0,
            "model": response.model,
        }

    async def stream(self, messages: list[dict], **kwargs):
        """
        Stream a chat completion request.
        Yields: content chunks (strings)
        """
        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


def get_llm_client(model: str | None = None) -> LLMClient:
    """
    Factory function. Returns an LLMClient for the given model.
    Falls back to the configured default model.
    """
    return LLMClient(model=model or settings.default_model)
