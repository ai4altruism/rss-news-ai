# src/providers/xai_provider.py

"""
xAI Grok provider implementation.

xAI uses an OpenAI-compatible Chat Completions API, making integration
straightforward. Supports grok-3, grok-3-mini, and other Grok models.

API Documentation: https://docs.x.ai/api
"""

import logging
import time
import requests
from typing import Optional, Tuple

from .base import BaseProvider, LLMUsageMetadata


class XAIProvider(BaseProvider):
    """xAI Grok provider using OpenAI-compatible Chat Completions API."""

    API_URL = "https://api.x.ai/v1/chat/completions"

    def get_provider_name(self) -> str:
        return "xai"

    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> Tuple[str, LLMUsageMetadata]:
        """
        Generate a completion using xAI's Chat Completions API.

        Args:
            prompt: The input prompt/text to complete
            instructions: System instructions or context
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            Tuple of (response_text, usage_metadata)

        Raises:
            ValueError: If the response cannot be parsed
            requests.HTTPError: If the API request fails
        """
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build messages array (OpenAI chat format)
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = requests.post(self.API_URL, headers=headers, json=data)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        if not resp.ok:
            logging.error(
                f"xAI API error. Status: {resp.status_code}, Body: {resp.text}"
            )
            resp.raise_for_status()

        resp_json = resp.json()

        # Check for errors in response
        if resp_json.get("error"):
            raise ValueError(f"xAI error: {resp_json['error']}")

        # Extract usage metadata
        usage = self._extract_usage(resp_json, response_time_ms)

        return self._parse_response(resp_json), usage

    def _extract_usage(self, resp_json: dict, response_time_ms: int) -> LLMUsageMetadata:
        """Extract token usage from xAI response (OpenAI-compatible format)."""
        usage_data = resp_json.get("usage", {})

        input_tokens = usage_data.get("prompt_tokens", 0)
        output_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", input_tokens + output_tokens)

        return LLMUsageMetadata(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
        )

    def _parse_response(self, resp_json: dict) -> str:
        """
        Parse the xAI response to extract text.

        xAI uses standard OpenAI chat completion format:
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "response text"
                    }
                }
            ]
        }
        """
        choices = resp_json.get("choices", [])
        if not choices:
            logging.error(f"No choices in xAI response: {resp_json}")
            raise ValueError("No choices in xAI response")

        message = choices[0].get("message", {})
        content = message.get("content")

        if content is None:
            logging.error(f"No content in xAI response: {resp_json}")
            raise ValueError("No content in xAI response message")

        return content.strip()
