# src/utils.py

"""
Utility functions for the RSS News AI application.

Provides LLM calling functionality through the provider abstraction layer,
with backward compatibility for existing code. Includes automatic usage
tracking to SQLite database (Sprint 12).
"""

import os
import logging
from typing import Optional

from providers import get_provider, parse_model_config, LLMUsageMetadata
from pricing import calculate_cost
from history_db import save_llm_usage, init_database


def call_llm(
    model_config: str,
    prompt: str,
    api_keys: dict,
    instructions: str = "",
    max_tokens: int = 500,
    temperature: float = 1.0,
    task_type: str = "unknown",
) -> str:
    """
    Call an LLM using the provider abstraction layer.

    This is the preferred way to call LLMs as it supports multiple providers.
    Automatically logs usage metrics to the database.

    Args:
        model_config: Model configuration string
            - Old format: "gpt-4o-mini" (defaults to OpenAI)
            - New format: "provider:model-name" (e.g., "anthropic:claude-sonnet-4-20250514")
        prompt: The input prompt/text
        api_keys: Dictionary of API keys, e.g.:
            {
                "openai": "sk-...",
                "anthropic": "sk-ant-...",
                "google": "AIza...",
                "xai": "xai-..."
            }
        instructions: System instructions or context
        max_tokens: Maximum tokens in the response
        temperature: Sampling temperature (0.0 to 2.0)
        task_type: Type of task for usage tracking ('filter', 'group', 'summarize', 'query')

    Returns:
        The generated text response

    Raises:
        ValueError: If provider is unknown or API key is missing
        requests.HTTPError: If the API request fails
    """
    provider = get_provider(
        model_config,
        openai_api_key=api_keys.get("openai"),
        anthropic_api_key=api_keys.get("anthropic"),
        google_api_key=api_keys.get("google"),
        xai_api_key=api_keys.get("xai"),
    )

    # Call provider and get response with usage metadata
    response_text, usage = provider.complete(
        prompt=prompt,
        instructions=instructions,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Log usage to database (non-fatal if it fails)
    _log_usage(provider, usage, task_type)

    return response_text


def _log_usage(provider, usage: LLMUsageMetadata, task_type: str) -> None:
    """
    Log LLM usage to the database.

    This is non-fatal - errors are logged but don't break the pipeline.
    """
    try:
        provider_name = provider.get_provider_name()
        model_name = provider.get_model_name()

        # Calculate cost estimate
        cost_usd = calculate_cost(
            provider=provider_name,
            model=model_name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )

        # Save to database
        save_llm_usage(
            provider=provider_name,
            model=model_name,
            task_type=task_type,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=cost_usd,
            response_time_ms=usage.response_time_ms,
        )

    except Exception as e:
        # Non-fatal: log warning but don't break the pipeline
        logging.warning(f"Failed to log LLM usage: {e}")


def call_responses_api(
    model: str,
    prompt: str,
    openai_api_key: str,
    instructions: str = "",
    max_output_tokens: int = 500,
    temperature: float = 1.0,
) -> str:
    """
    Call OpenAI's Responses API (backward-compatible wrapper).

    DEPRECATED: Use call_llm() instead for multi-provider support.

    This function is maintained for backward compatibility with existing code.
    It delegates to the OpenAI provider through the new abstraction layer.

    Args:
        model: The OpenAI model name (e.g., 'gpt-4o-mini', 'gpt-5-mini')
        prompt: The input prompt/text
        openai_api_key: OpenAI API key
        instructions: System instructions or context
        max_output_tokens: Maximum tokens in the response
        temperature: Sampling temperature (0.0 to 2.0)

    Returns:
        The generated text response
    """
    return call_llm(
        model_config=model,  # Will default to OpenAI provider
        prompt=prompt,
        api_keys={"openai": openai_api_key},
        instructions=instructions,
        max_tokens=max_output_tokens,
        temperature=temperature,
    )


def setup_logger():
    """
    Sets up a logger to log to both the console and a file in the logs directory.

    Returns:
        logger (logging.Logger): Configured logger instance.
    """
    logger = logging.getLogger("RSSFeedMonitor")
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # File handler for logging to a file
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(logging.INFO)

    # Console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter to include timestamp, module, level, and message
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
