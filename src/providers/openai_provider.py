# src/providers/openai_provider.py

"""
OpenAI provider implementation using the Responses API.

Supports both gpt-4 and gpt-5 model families with appropriate
handling for each (temperature, reasoning effort, response parsing).
"""

import logging
import requests
from typing import Optional

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI provider using the Responses API."""

    API_URL = "https://api.openai.com/v1/responses"

    def get_provider_name(self) -> str:
        return "openai"

    def _is_gpt5_model(self) -> bool:
        """Check if this is a gpt-5 family model."""
        return self.model.startswith("gpt-5")

    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate a completion using OpenAI's Responses API.

        Handles gpt-5 models differently:
        - No temperature parameter (not supported)
        - Uses low reasoning effort for speed
        - Higher max_tokens to accommodate reasoning tokens
        - Different response structure (reasoning block + message block)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # gpt-5 models use reasoning tokens that count against max_output_tokens
        # Need higher limit to leave room for actual output after reasoning
        effective_max_tokens = max_tokens
        if self._is_gpt5_model():
            effective_max_tokens = max(max_tokens * 4, 4096)

        data = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": effective_max_tokens,
        }

        # gpt-5 models: no temperature, use low reasoning effort for speed
        if self._is_gpt5_model():
            data["reasoning"] = {"effort": "low"}
        else:
            data["temperature"] = temperature

        if instructions:
            data["instructions"] = instructions

        resp = requests.post(self.API_URL, headers=headers, json=data)
        if not resp.ok:
            logging.error(
                f"OpenAI Responses API error. Status: {resp.status_code}, Body: {resp.text}"
            )
            resp.raise_for_status()

        resp_json = resp.json()

        # Check for errors in the response object
        if resp_json.get("error"):
            raise ValueError(f"OpenAI error: {resp_json['error']}")

        return self._parse_response(resp_json)

    def _parse_response(self, resp_json: dict) -> str:
        """
        Parse the OpenAI response to extract text.

        Handles multiple response formats:
        - gpt-5 models: [reasoning block, message block]
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
