# tests/test_provider_truncation.py
"""
Truncated generations from the Anthropic and Gemini providers.

stop_reason "max_tokens" / finishReason "MAX_TOKENS" means the text was cut
off. Callers feed this text to a JSON parser or publish it as a summary, so
a silent partial answer is worse than an error. Either raising or flagging
on the usage object is an acceptable fix.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from providers import AnthropicProvider, GeminiProvider
from tests.fakes import fake_response, known_bug


def _flagged(usage):
    return bool(getattr(usage, "truncated", False) or getattr(usage, "incomplete", False))


def anthropic_payload(stop_reason):
    return {"type": "message", "stop_reason": stop_reason,
            "content": [{"type": "text", "text": "partial text"}],
            "usage": {"input_tokens": 9, "output_tokens": 4}}


def gemini_payload(finish_reason):
    return {"candidates": [{"finishReason": finish_reason,
                            "content": {"parts": [{"text": "partial text"}]}}],
            "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 4,
                              "totalTokenCount": 13}}


A_POST = "providers.anthropic_provider.requests.post"
G_POST = "providers.gemini_provider.requests.post"


class TestNormalCompletion:

    def test_anthropic_end_turn_returns_text(self):
        with patch(A_POST, return_value=fake_response(anthropic_payload("end_turn"))):
            text, usage = AnthropicProvider("claude-sonnet-4", "k").complete("hi")
        assert text == "partial text"
        assert usage.total_tokens == 13

    def test_gemini_stop_returns_text(self):
        with patch(G_POST, return_value=fake_response(gemini_payload("STOP"))):
            text, usage = GeminiProvider("gemini-2.0-flash", "k").complete("hi")
        assert text == "partial text"
        assert usage.total_tokens == 13

    def test_gemini_safety_block_raises(self):
        with patch(G_POST, return_value=fake_response(gemini_payload("SAFETY"))):
            with pytest.raises(ValueError, match="safety"):
                GeminiProvider("gemini-2.0-flash", "k").complete("hi")

    def test_anthropic_temperature_is_clamped_to_one(self):
        with patch(A_POST, return_value=fake_response(anthropic_payload("end_turn"))) as post:
            AnthropicProvider("claude-sonnet-4", "k").complete("hi", temperature=1.8)
        assert post.call_args.kwargs["json"]["temperature"] == 1.0


class TestTruncationDetection:

    @known_bug('Anthropic stop_reason "max_tokens" is returned as a complete answer')
    def test_anthropic_max_tokens_is_not_accepted_as_complete(self):
        with patch(A_POST, return_value=fake_response(anthropic_payload("max_tokens"))):
            try:
                _text, usage = AnthropicProvider("claude-sonnet-4", "k").complete("hi")
            except Exception:
                return
        assert _flagged(usage)

    @known_bug('Gemini finishReason "MAX_TOKENS" is returned as a complete answer')
    def test_gemini_max_tokens_is_not_accepted_as_complete(self):
        with patch(G_POST, return_value=fake_response(gemini_payload("MAX_TOKENS"))):
            try:
                _text, usage = GeminiProvider("gemini-2.0-flash", "k").complete("hi")
            except Exception:
                return
        assert _flagged(usage)
