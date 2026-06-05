"""
Agent Factory

Factory for creating AI agents based on provider type.
Supports cloud providers and local model servers.
"""

from typing import Optional
from src.agents.base_agent import BaseAIAgent


def create_agent(
    provider: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> BaseAIAgent:
    """
    Create an AI agent based on the provider.

    Args:
        provider: AI provider type ("openai", "anthropic", or custom)
        model: Model identifier
        api_key: API key (optional, reads from environment if not provided)
        api_base_url: Custom API endpoint for local / self-hosted models.
                      When set, requests are routed to this URL instead of
                      the default cloud endpoint.

    Returns:
        An instance of BaseAIAgent

    Example:
        # Cloud providers
        agent = create_agent("openai", model="gpt-4")
        agent = create_agent("anthropic", model="claude-3-opus-20240229")

        # Local models (Ollama)
        agent = create_agent(
            "openai",
            model="llama3",
            api_base_url="http://localhost:11434/v1",
        )

        # Local models (LM Studio)
        agent = create_agent(
            "openai",
            model="mistral",
            api_base_url="http://localhost:1234/v1",
        )
    """
    provider_lower = provider.lower()

    if provider_lower == "openai":
        from src.agents.openai_agent import OpenAIAgent
        return OpenAIAgent(
            model=model or "gpt-4",
            api_key=api_key,
            api_base_url=api_base_url,
        )

    elif provider_lower == "anthropic":
        from src.agents.anthropic_agent import AnthropicAgent
        return AnthropicAgent(
            model=model or "claude-3-opus-20240229",
            api_key=api_key,
            api_base_url=api_base_url,
        )

    elif provider_lower == "gemini":
        from src.agents.gemini_agent import GeminiAgent
        return GeminiAgent(
            model=model or "gemini-2.0-flash",
            api_key=api_key,
            api_base_url=api_base_url,
        )

    else:
        raise ValueError(
            f"Unsupported AI provider: '{provider}'. "
            "Supported providers are 'openai', 'anthropic', and 'gemini'."
        )
