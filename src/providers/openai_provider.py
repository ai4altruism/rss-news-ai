# src/providers/openai_provider.py

"""
OpenAI provider implementation using the Responses API.

Supports the non-reasoning gpt-4 family and the reasoning families
(gpt-5, gpt-6, o-series) with appropriate handling for each
(temperature, reasoning effort, response parsing).
"""

import logging
import time
import requests
from typing import Optional, Tuple

from .base import BaseProvider, LLMUsageMetadata


class OpenAIProvider(BaseProvider):
    """OpenAI provider using the Responses API."""

    API_URL = "https://api.openai.com/v1/responses"

    def get_provider_name(self) -> str:
        return "openai"

    # Families that answer without hidden reasoning tokens. Every newer
    # family reasons first, rejects `temperature`, and spends reasoning
    # tokens against max_output_tokens. Listing the old families, rather
    # than the new ones, keeps the next family from failing every call.
    NON_REASONING_PREFIXES = ("gpt-4", "gpt-3.5")

    def _is_reasoning_model(self) -> bool:
        """True unless the model belongs to a known non-reasoning family."""
        return not self.model.startswith(self.NON_REASONING_PREFIXES)

    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> Tuple[str, LLMUsageMetadata]:
        """
        Generate a completion using OpenAI's Responses API.

        Handles reasoning models (see _is_reasoning_model) differently:
        - No temperature parameter (not supported)
        - Uses low reasoning effort for speed
        - Higher max_tokens to accommodate reasoning tokens
        - Different response structure (reasoning block + message block)

        Returns:
            Tuple of (response_text, usage_metadata)
        """
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Reasoning models spend reasoning tokens against max_output_tokens.
        # Billing is per token used, so a generous cap costs nothing extra.
        # Need higher limit to leave room for actual output after reasoning
        effective_max_tokens = max_tokens
        if self._is_reasoning_model():
            effective_max_tokens = max(max_tokens * 8, 16384)

        data = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": effective_max_tokens,
        }

        # Reasoning models: no temperature, use low reasoning effort for speed
        if self._is_reasoning_model():
            data["reasoning"] = {"effort": "low"}
        else:
            data["temperature"] = temperature

        if instructions:
            data["instructions"] = instructions

        resp = requests.post(self.API_URL, headers=headers, json=data, timeout=self.REQUEST_TIMEOUT)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        if not resp.ok:
            logging.error(
                f"OpenAI Responses API error. Status: {resp.status_code}, Body: {resp.text}"
            )
            resp.raise_for_status()

        resp_json = resp.json()

        # Check for errors in the response object
        if resp_json.get("error"):
            raise ValueError(f"OpenAI error: {resp_json['error']}")

        # Extract usage metadata
        usage = self._extract_usage(resp_json, response_time_ms)

        # The tokens are spent once the response arrives, so a failure from
        # here on carries the usage on the exception for call_llm to log.
        try:
            if resp_json.get("status") == "incomplete":
                reason = (resp_json.get("incomplete_details") or {}).get("reason")
                raise ValueError(f"OpenAI response incomplete: {reason or 'unknown reason'}")
            return self._parse_response(resp_json), usage
        except Exception as e:
            e.usage = usage
            raise

    def _extract_usage(self, resp_json: dict, response_time_ms: int) -> LLMUsageMetadata:
        """Extract token usage from OpenAI response."""
        usage_data = resp_json.get("usage", {})

        input_tokens = usage_data.get("input_tokens", 0) or usage_data.get("prompt_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0) or usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", input_tokens + output_tokens)

        return LLMUsageMetadata(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
        )

    def _parse_response(self, resp_json: dict) -> str:
        """
        Parse the OpenAI response to extract text.

        Handles multiple response formats:
        - reasoning models: [reasoning block, message block]
        - gpt-4 models: [message block]
        """
        output_list = resp_json.get("output", [])
        if not output_list:
            raise ValueError("No output in the OpenAI response")

        # Find the message block (skip reasoning blocks)
        message_output = None
        for output_item in output_list:
            if output_item.get("type") == "message":
                message_output = output_item
                break

        # Fall back to first output if no message type found
        if not message_output:
            message_output = output_list[0]

        # Extract text from content array
        content_list = message_output.get("content", [])
        if content_list:
            extracted_text = []
            for content_piece in content_list:
                if content_piece.get("type") == "output_text":
                    extracted_text.append(content_piece.get("text", ""))
                elif content_piece.get("type") == "text":
                    extracted_text.append(content_piece.get("text", ""))
                elif isinstance(content_piece, str):
                    extracted_text.append(content_piece)
            if extracted_text:
                return "".join(extracted_text).strip()

        # Format 2: output[].text (simpler format)
        if message_output.get("text"):
            return message_output.get("text").strip()

        # If nothing worked, log the structure for debugging
        logging.error(f"Unknown response structure: {resp_json}")
        raise ValueError("No content in the message output block")
