# src/providers/base.py

"""
Abstract base class for LLM providers.

All provider implementations must inherit from BaseProvider and implement
the required abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class LLMUsageMetadata:
    """
    Metadata about LLM API usage for a single call.

    Attributes:
        input_tokens: Number of tokens in the input/prompt
        output_tokens: Number of tokens in the generated response
        total_tokens: Total tokens (input + output)
        response_time_ms: Response time in milliseconds (optional)
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    response_time_ms: Optional[int] = None

    def __post_init__(self):
        """Calculate total_tokens if not provided."""
        if self.total_tokens == 0 and (self.input_tokens or self.output_tokens):
            self.total_tokens = self.input_tokens + self.output_tokens


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
    ) -> Tuple[str, LLMUsageMetadata]:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: The input prompt/text to complete
            instructions: System instructions or context
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            Tuple of (response_text, usage_metadata):
                - response_text: The generated text response
                - usage_metadata: LLMUsageMetadata with token counts and timing

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
