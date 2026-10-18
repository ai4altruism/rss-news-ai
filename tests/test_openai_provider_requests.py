# tests/test_openai_provider_requests.py
"""
OpenAIProvider request construction and response-status handling.

All HTTP is stubbed by patching ``requests.post`` in the provider module.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from providers import OpenAIProvider
from utils import call_llm
from tests.fakes import fake_response

MESSAGE_OK = {
    "status": "completed",
    "output": [{"type": "message",
                "content": [{"type": "output_text", "text": "hello"}]}],
    "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
}
POST = "providers.openai_provider.requests.post"


def _flagged(usage):
    """True when the provider surfaced truncation on the usage object."""
    return bool(getattr(usage, "truncated", False) or getattr(usage, "incomplete", False))


class TestRequestConstruction:

    @pytest.mark.parametrize("model,reasoning", [
        ("gpt-4o-mini", False),
        ("gpt-5-mini", True),
        ("gpt-6-luna", True),
        ("o3-mini", True),
    ])
    def test_temperature_and_reasoning_follow_model_family(self, model, reasoning):
        with patch(POST, return_value=fake_response(MESSAGE_OK)) as post:
            OpenAIProvider(model=model, api_key="k").complete(
                "hi", instructions="sys", max_tokens=500, temperature=0.3)

        body = post.call_args.kwargs["json"]
        assert body["model"] == model
        assert body["input"] == "hi"
        assert body["instructions"] == "sys"
        if reasoning:
            assert "temperature" not in body
            assert body["reasoning"] == {"effort": "low"}
            assert body["max_output_tokens"] == 16384
        else:
            assert body["temperature"] == 0.3
            assert "reasoning" not in body
            assert body["max_output_tokens"] == 500

    @pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-6-luna", "o3-mini"])
    def test_reasoning_budget_scales_eightfold_above_floor(self, model):
        with patch(POST, return_value=fake_response(MESSAGE_OK)) as post:
            OpenAIProvider(model=model, api_key="k").complete("hi", max_tokens=4000)

        assert post.call_args.kwargs["json"]["max_output_tokens"] == 32000

    def test_instructions_omitted_when_empty(self):
        with patch(POST, return_value=fake_response(MESSAGE_OK)) as post:
            OpenAIProvider(model="gpt-4o-mini", api_key="k").complete("hi")

        assert "instructions" not in post.call_args.kwargs["json"]

    def test_auth_header_timeout_and_url(self):
        with patch(POST, return_value=fake_response(MESSAGE_OK)) as post:
            OpenAIProvider(model="gpt-4o-mini", api_key="sk-x").complete("hi")

        assert post.call_args.args[0] == OpenAIProvider.API_URL
        assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-x"
        assert post.call_args.kwargs["timeout"] == OpenAIProvider.REQUEST_TIMEOUT


class TestResponseHandling:

    def test_returns_text_and_usage(self):
        with patch(POST, return_value=fake_response(MESSAGE_OK)):
            text, usage = OpenAIProvider(model="gpt-4o-mini", api_key="k").complete("hi")

        assert text == "hello"
        assert (usage.input_tokens, usage.output_tokens, usage.total_tokens) == (11, 7, 18)

    def test_reasoning_item_before_message_is_skipped(self):
        payload = dict(MESSAGE_OK, output=[
            {"type": "reasoning", "summary": []}, MESSAGE_OK["output"][0]])
        with patch(POST, return_value=fake_response(payload)):
            text, _ = OpenAIProvider(model="gpt-5-mini", api_key="k").complete("hi")

        assert text == "hello"

    def test_http_error_raises(self):
        import requests
        resp = fake_response({"error": "x"}, status_code=500)
        resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch(POST, return_value=resp):
            with pytest.raises(requests.HTTPError):
                OpenAIProvider(model="gpt-4o-mini", api_key="k").complete("hi")

    def test_error_object_in_body_raises_value_error(self):
        with patch(POST, return_value=fake_response({"error": {"message": "bad"}})):
            with pytest.raises(ValueError, match="OpenAI error"):
                OpenAIProvider(model="gpt-4o-mini", api_key="k").complete("hi")

    def test_empty_output_raises(self):
        with patch(POST, return_value=fake_response({"output": []})):
            with pytest.raises(ValueError, match="No output"):
                OpenAIProvider(model="gpt-4o-mini", api_key="k").complete("hi")

    def test_reasoning_only_output_raises_value_error(self):
        payload = {"status": "completed",
                   "output": [{"type": "reasoning", "summary": []}],
                   "usage": {"input_tokens": 50, "output_tokens": 16384}}
        with patch(POST, return_value=fake_response(payload)):
            with pytest.raises(ValueError):
                OpenAIProvider(model="gpt-5-mini", api_key="k").complete("hi")

    def test_incomplete_status_is_not_accepted_as_complete(self):
        payload = dict(MESSAGE_OK, status="incomplete",
                       incomplete_details={"reason": "max_output_tokens"})
        with patch(POST, return_value=fake_response(payload)):
            try:
                _text, usage = OpenAIProvider(model="gpt-5-mini", api_key="k").complete("hi")
            except Exception:
                return  # raising is an acceptable fix
        assert _flagged(usage)  # so is flagging truncation on the usage object


class TestUsageLoggingThroughCallLlm:

    @patch("utils.save_llm_usage")
    def test_successful_call_logs_tokens(self, mock_save):
        with patch(POST, return_value=fake_response(MESSAGE_OK)):
            call_llm("gpt-4o-mini", "hi", {"openai": "k"}, task_type="filter")

        kwargs = mock_save.call_args.kwargs
        assert (kwargs["input_tokens"], kwargs["output_tokens"]) == (11, 7)
        assert kwargs["task_type"] == "filter"
        assert kwargs["provider"] == "openai"

    @patch("utils.save_llm_usage")
    def test_usage_logged_when_provider_raises_after_http_200(self, mock_save):
        payload = {"status": "completed",
                   "output": [{"type": "reasoning", "summary": []}],
                   "usage": {"input_tokens": 50, "output_tokens": 16384}}
        with patch(POST, return_value=fake_response(payload)):
            with pytest.raises(ValueError):
                call_llm("gpt-5-mini", "hi", {"openai": "k"}, task_type="filter")

        assert mock_save.called
        assert mock_save.call_args.kwargs["output_tokens"] == 16384
