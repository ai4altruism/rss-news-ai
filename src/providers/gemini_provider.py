# src/providers/gemini_provider.py

"""
Google Gemini provider implementation.

Uses the Google Generative Language API which has a unique request/response format.
Supports Gemini Pro, Gemini Flash, and other Gemini models.

API Documentation: https://ai.google.dev/api/rest
"""

import logging
import requests
from typing import Optional

from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini provider using the Generative Language API."""

    API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def get_provider_name(self) -> str:
        return "google"

    def _get_api_url(self) -> str:
        """Build the API URL for the model."""
        # Handle both "gemini-2.0-flash" and "models/gemini-2.0-flash" formats
        model_name = self.model
        if model_name.startswith("models/"):
            model_name = model_name[7:]  # Remove "models/" prefix
        return f"{self.API_BASE_URL}/{model_name}:generateContent"

    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate a completion using Google's Generative Language API.

        Args:
            prompt: The input prompt/text to complete
            instructions: System instructions (sent as systemInstruction)
            max_tokens: Maximum tokens in the response
            temperature: Sampling temperature (0.0 to 2.0 for Gemini)

        Returns:
            The generated text response

        Raises:
            ValueError: If the response cannot be parsed
            requests.HTTPError: If the API request fails
        """
        # Gemini uses API key as query parameter
        url = f"{self._get_api_url()}?key={self.api_key}"

        headers = {
            "Content-Type": "application/json",
        }

        # Build contents array (Gemini format)
        contents = [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]

        data = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }

        # Gemini uses systemInstruction for system prompts
        if instructions:
            data["systemInstruction"] = {
                "parts": [{"text": instructions}]
            }

        resp = requests.post(url, headers=headers, json=data)

        if not resp.ok:
            self._handle_error(resp)

        resp_json = resp.json()

        # Check for error in response body
        if "error" in resp_json:
            error_msg = resp_json["error"].get("message", "Unknown error")
            raise ValueError(f"Gemini error: {error_msg}")

        return self._parse_response(resp_json)

    def _handle_error(self, resp: requests.Response) -> None:
        """
        Handle Gemini API errors with specific error messages.

        Gemini error codes:
        - 400: Invalid request (bad parameter, safety block)
        - 401/403: Authentication/permission error
        - 404: Model not found
        - 429: Rate limit exceeded
        - 500: Internal server error
        """
        error_messages = {
            400: "Invalid request - check parameters or content may have been blocked by safety filters",
            401: "Invalid API key",
            403: "Permission denied - API key may not have access to this model",
            404: "Model not found - check model name",
            429: "Rate limit exceeded - please retry after a delay",
            500: "Google internal server error",
        }

        status = resp.status_code
        default_msg = f"Gemini API error (status {status})"
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

        logging.error(f"Gemini API error. Status: {status}, Body: {resp.text}")
        resp.raise_for_status()

    def _parse_response(self, resp_json: dict) -> str:
        """
        Parse the Gemini response to extract text.

        Gemini API response format:
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "response text here"}
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    ...
                }
            ],
            ...
        }
        """
        candidates = resp_json.get("candidates", [])
        if not candidates:
            # Check if blocked by safety filters
            if "promptFeedback" in resp_json:
                feedback = resp_json["promptFeedback"]
                block_reason = feedback.get("blockReason", "UNKNOWN")
                raise ValueError(f"Content blocked by safety filters: {block_reason}")

            logging.error(f"No candidates in Gemini response: {resp_json}")
            raise ValueError("No candidates in Gemini response")

        # Get the first candidate
        candidate = candidates[0]

        # Check for blocked content in candidate
        finish_reason = candidate.get("finishReason", "")
        if finish_reason == "SAFETY":
            safety_ratings = candidate.get("safetyRatings", [])
            raise ValueError(f"Response blocked by safety filters: {safety_ratings}")

        content = candidate.get("content", {})
        parts = content.get("parts", [])

        if not parts:
            logging.error(f"No parts in Gemini response: {resp_json}")
            raise ValueError("No content parts in Gemini response")

        # Extract text from parts
        text_parts = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])

        if not text_parts:
            logging.error(f"No text in Gemini response parts: {resp_json}")
            raise ValueError("No text content in Gemini response")

        return "".join(text_parts).strip()
