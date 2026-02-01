"""
Unified LLM client supporting Anthropic and OpenRouter.
"""

import os
from openai import OpenAI


def get_llm_client():
    """Get configured LLM client (OpenRouter or Anthropic)."""

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if openrouter_key:
        return OpenRouterClient(openrouter_key)
    elif anthropic_key:
        # Use Anthropic via OpenRouter format for consistency
        import anthropic
        return AnthropicClient(anthropic_key)
    else:
        raise ValueError("Set OPENROUTER_API_KEY or ANTHROPIC_API_KEY")


class OpenRouterClient:
    """OpenRouter LLM client."""

    def __init__(self, api_key: str):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        # Use Claude Sonnet via OpenRouter
        self.model = "anthropic/claude-sonnet-4"

    def complete(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
        """Generate completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


class AnthropicClient:
    """Anthropic direct client."""

    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def complete(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
        """Generate completion."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
