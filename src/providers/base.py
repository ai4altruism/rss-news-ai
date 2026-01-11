# src/providers/base.py

"""
Abstract base class for LLM providers.

All provider implementations must inherit from BaseProvider and implement
the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: str):
        """
        Initialize the provider.

        Args:
            model: The model identifier (e.g., 'gpt-4o-mini', 'claude-sonnet-4-20250514')
            api_key: The API key for authentication
        """
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The input prompt/text to complete
            instructions: System instructions or context
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            The generated text response

        Raises:
            ValueError: If the response cannot be parsed
            requests.HTTPError: If the API request fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider identifier (e.g., 'openai', 'anthropic')."""
        pass

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return self.model

    def validate_config(self) -> bool:
        """
        Validate provider configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        return bool(self.api_key and self.model)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model='{self.model}')"
