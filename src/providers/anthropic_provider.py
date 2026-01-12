# src/providers/anthropic_provider.py

"""
Anthropic Claude provider implementation.

Uses the Anthropic Messages API which has a different request/response format
from OpenAI. Supports Claude Sonnet, Haiku, and Opus models.

API Documentation: https://docs.anthropic.com/en/api/messages
"""

import logging
import time
import requests
from typing import Optional, Tuple

from .base import BaseProvider, LLMUsageMetadata


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider using the Messages API."""

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def get_provider_name(self) -> str:
        return "anthropic"

    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> Tuple[str, LLMUsageMetadata]:
        """
        Generate a completion using Anthropic's Messages API.

        Args:
            prompt: The input prompt/text to complete
            instructions: System instructions (sent as system parameter)
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0.0 to 1.0 for Anthropic)

        Returns:
            Tuple of (response_text, usage_metadata)

        Raises:
            ValueError: If the response cannot be parsed
            requests.HTTPError: If the API request fails
        """
        start_time = time.time()

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

        # Build messages array (Anthropic format)
        messages = [{"role": "user", "content": prompt}]

        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        # Anthropic uses separate system parameter (not in messages)
        if instructions:
            data["system"] = instructions

        # Anthropic temperature range is 0.0 to 1.0
        # Clamp temperature to valid range
        clamped_temp = max(0.0, min(1.0, temperature))
        data["temperature"] = clamped_temp

        resp = requests.post(self.API_URL, headers=headers, json=data)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        if not resp.ok:
            self._handle_error(resp)

        resp_json = resp.json()

        # Check for error in response body
        if resp_json.get("type") == "error":
            error_msg = resp_json.get("error", {}).get("message", "Unknown error")
            raise ValueError(f"Anthropic error: {error_msg}")

        # Extract usage metadata
        usage = self._extract_usage(resp_json, response_time_ms)

        return self._parse_response(resp_json), usage

    def _extract_usage(self, resp_json: dict, response_time_ms: int) -> LLMUsageMetadata:
        """Extract token usage from Anthropic response."""
        usage_data = resp_json.get("usage", {})

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens

        return LLMUsageMetadata(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
        )

    def _handle_error(self, resp: requests.Response) -> None:
        """
        Handle Anthropic API errors with specific error messages.

        Anthropic error codes:
        - 400: Invalid request
        - 401: Authentication error
        - 403: Permission denied
        - 404: Not found
        - 429: Rate limit exceeded
        - 500: Internal server error
        - 529: API overloaded
        """
        error_messages = {
            400: "Invalid request - check your parameters",
            401: "Invalid API key",
            403: "Permission denied for this resource",
            404: "Model or resource not found",
            429: "Rate limit exceeded - please retry after a delay",
            500: "Anthropic internal server error",
            529: "Anthropic API is overloaded - please retry later",
        }

        status = resp.status_code
        default_msg = f"Anthropic API error (status {status})"
        error_msg = error_messages.get(status, default_msg)

        # Try to extract more detail from response body
        try:
            error_body = resp.json()
            if "error" in error_body:
                detail = error_body["error"].get("message", "")
                if detail:
                    error_msg = f"{error_msg}: {detail}"
        except Exception:
            pass

        logging.error(f"Anthropic API error. Status: {status}, Body: {resp.text}")
        resp.raise_for_status()

    def _parse_response(self, resp_json: dict) -> str:
        """
        Parse the Anthropic response to extract text.

        Anthropic Messages API response format:
        {
            "id": "msg_...",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "response text here"
                }
            ],
            "stop_reason": "end_turn",
            ...
        }
        """
        content = resp_json.get("content", [])
        if not content:
            logging.error(f"No content in Anthropic response: {resp_json}")
            raise ValueError("No content in Anthropic response")

        # Extract text from content blocks
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        if not text_parts:
            logging.error(f"No text blocks in Anthropic response: {resp_json}")
            raise ValueError("No text content in Anthropic response")

        return "".join(text_parts).strip()
