# src/providers/__init__.py

"""
LLM Provider Factory

Provides a unified interface for creating provider instances from configuration.
Supports both old format (model only) and new format (provider:model).

Usage:
    from providers import get_provider

    # Old format (backward compatible, defaults to OpenAI)
    provider = get_provider("gpt-4o-mini", openai_api_key="sk-...")

    # New format (explicit provider)
    provider = get_provider("openai:gpt-4o-mini", openai_api_key="sk-...")
    provider = get_provider("anthropic:claude-sonnet-4-20250514", anthropic_api_key="sk-ant-...")

    # Use the provider
    response = provider.complete(prompt="Hello", instructions="Be helpful")
"""

from typing import Optional

from .base import BaseProvider, LLMUsageMetadata
from .openai_provider import OpenAIProvider
from .xai_provider import XAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider


# Registry of available providers
_PROVIDERS = {
    "openai": OpenAIProvider,
    "xai": XAIProvider,
    "anthropic": AnthropicProvider,
    "google": GeminiProvider,
}


def parse_model_config(model_config: str) -> tuple[str, str]:
    """
    Parse model configuration string into provider and model name.

    Args:
        model_config: Either "model-name" (old format) or "provider:model-name" (new format)

    Returns:
        Tuple of (provider_name, model_name)

    Examples:
        >>> parse_model_config("gpt-4o-mini")
        ("openai", "gpt-4o-mini")
        >>> parse_model_config("openai:gpt-4o-mini")
        ("openai", "gpt-4o-mini")
        >>> parse_model_config("anthropic:claude-sonnet-4-20250514")
        ("anthropic", "claude-sonnet-4-20250514")
    """
    if ":" in model_config:
        provider_name, model_name = model_config.split(":", 1)
        return provider_name.lower(), model_name
    else:
        # Backward compatibility: assume OpenAI for old format
        return "openai", model_config


def get_provider(
    model_config: str,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    xai_api_key: Optional[str] = None,
) -> BaseProvider:
    """
    Factory function to get a provider instance.

    Args:
        model_config: Model configuration string
            - Old format: "gpt-4o-mini" (defaults to OpenAI)
            - New format: "provider:model-name" (e.g., "anthropic:claude-sonnet-4-20250514")
        openai_api_key: OpenAI API key (required for OpenAI provider)
        anthropic_api_key: Anthropic API key (required for Anthropic provider)
        google_api_key: Google API key (required for Google provider)
        xai_api_key: xAI API key (required for xAI provider)

    Returns:
        BaseProvider instance configured for the specified model

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    provider_name, model_name = parse_model_config(model_config)

    # Get the provider class
    provider_class = _PROVIDERS.get(provider_name)
    if not provider_class:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider: '{provider_name}'. Available providers: {available}"
        )

    # Get the appropriate API key
    api_keys = {
        "openai": openai_api_key,
        "anthropic": anthropic_api_key,
        "google": google_api_key,
        "xai": xai_api_key,
    }

    api_key = api_keys.get(provider_name)
    if not api_key:
        raise ValueError(
            f"API key required for provider '{provider_name}'. "
            f"Pass {provider_name}_api_key parameter."
        )

    return provider_class(model=model_name, api_key=api_key)


def list_providers() -> list[str]:
    """Return list of available provider names."""
    return list(_PROVIDERS.keys())


def register_provider(name: str, provider_class: type) -> None:
    """
    Register a new provider.

    Args:
        name: Provider identifier (e.g., 'anthropic')
        provider_class: Provider class that inherits from BaseProvider
    """
    if not issubclass(provider_class, BaseProvider):
        raise TypeError(f"Provider class must inherit from BaseProvider")
    _PROVIDERS[name.lower()] = provider_class


# Export public API
__all__ = [
    "BaseProvider",
    "LLMUsageMetadata",
    "OpenAIProvider",
    "XAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "get_provider",
    "parse_model_config",
    "list_providers",
    "register_provider",
]
