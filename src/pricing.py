# src/pricing.py

"""
LLM pricing configuration and cost estimation.

Provides pricing data for all supported LLM providers and models,
and utilities for calculating estimated costs based on token usage.
"""

import logging
from typing import Optional, Dict, Any


# Pricing per 1 million tokens (as of January 2026)
# Format: {provider: {model_pattern: {"input": price, "output": price}}}
PRICING = {
    "openai": {
        # GPT-4o models
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        # GPT-5 models
        "gpt-5": {"input": 5.00, "output": 20.00},
        "gpt-5-mini": {"input": 1.00, "output": 4.00},
        # GPT-4 models (legacy)
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        # GPT-3.5 models (legacy)
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
    "xai": {
        # Grok models
        "grok-3": {"input": 3.00, "output": 15.00},
        "grok-3-mini": {"input": 0.20, "output": 0.80},
        "grok-2": {"input": 2.00, "output": 10.00},
    },
    "anthropic": {
        # Claude 4 models
        "claude-sonnet-4": {"input": 3.00, "output": 15.00},
        "claude-opus-4": {"input": 15.00, "output": 75.00},
        # Claude 3.5 models
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
        # Claude 3 models
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        # Haiku shorthand
        "claude-haiku": {"input": 0.25, "output": 1.25},
    },
    "google": {
        # Gemini 2.0 models
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
        # Gemini 1.5 models
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        # Gemini Pro (legacy)
        "gemini-pro": {"input": 0.50, "output": 1.50},
    },
}


def get_model_pricing(provider: str, model: str) -> Optional[Dict[str, float]]:
    """
    Get pricing for a specific provider and model.

    Args:
        provider: Provider name ('openai', 'xai', 'anthropic', 'google')
        model: Model name (e.g., 'gpt-4o-mini', 'claude-sonnet-4-20250514')

    Returns:
        Dict with 'input' and 'output' prices per 1M tokens, or None if not found.
    """
    provider_lower = provider.lower()
    if provider_lower not in PRICING:
        logging.warning(f"Unknown provider for pricing: {provider}")
        return None

    provider_pricing = PRICING[provider_lower]

    # Try exact match first
    if model in provider_pricing:
        return provider_pricing[model]

    # Try prefix matching for versioned models (e.g., 'claude-sonnet-4-20250514' -> 'claude-sonnet-4')
    for pattern, prices in provider_pricing.items():
        if model.startswith(pattern):
            return prices

    # Try matching model family (e.g., 'gpt-4o-2024-08-06' -> 'gpt-4o')
    model_parts = model.split("-")
    for i in range(len(model_parts), 0, -1):
        partial = "-".join(model_parts[:i])
        if partial in provider_pricing:
            return provider_pricing[partial]

    logging.warning(f"Pricing not found for {provider}:{model}")
    return None


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int
) -> Optional[float]:
    """
    Calculate estimated cost for an LLM call.

    Args:
        provider: Provider name
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD, or None if pricing not available.
    """
    pricing = get_model_pricing(provider, model)
    if not pricing:
        return None

    # Convert from per-million to actual cost
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)


def get_all_pricing() -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Get all pricing data.

    Returns:
        Complete pricing dictionary.
    """
    return PRICING


def format_cost(cost_usd: Optional[float]) -> str:
    """
    Format cost for display.

    Args:
        cost_usd: Cost in USD (can be None)

    Returns:
        Formatted string (e.g., '$0.0012', 'N/A')
    """
    if cost_usd is None:
        return "N/A"
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def get_provider_models(provider: str) -> list:
    """
    Get list of models with pricing for a provider.

    Args:
        provider: Provider name

    Returns:
        List of model names.
    """
    provider_lower = provider.lower()
    if provider_lower not in PRICING:
        return []
    return list(PRICING[provider_lower].keys())
