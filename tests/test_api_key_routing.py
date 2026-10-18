# tests/test_api_key_routing.py
"""
Every call site passes ``api_keys={"openai": key}`` to call_llm, whatever
provider the configured model names. With FILTER_MODEL="xai:grok-3-mini" or
an "anthropic:" model the provider factory then raises "API key required"
and every batch errors.

The contract: the key for the configured provider reaches call_llm (OpenAI
models use the caller's key, other providers read theirs from the
environment, and an OpenAI key is never sent to another provider).
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_filter import filter_stories
from summarizer import group_and_summarize
from query_engine import QueryEngine
from providers import XAIProvider, AnthropicProvider

PROVIDER_ENV = {"xai": "XAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


@pytest.fixture(autouse=True)
def provider_keys(monkeypatch):
    """Non-OpenAI providers take their key from the environment."""
    for name in PROVIDER_ENV.values():
        monkeypatch.setenv(name, "sk-from-env")

ARTICLES = [{"title": "Alpha", "link": "https://example.com/a", "summary": "s"}]
NON_OPENAI_MODELS = [
    ("xai:grok-3-mini", "xai"),
    ("anthropic:claude-sonnet-4-20250514", "anthropic"),
]


def _group_and_summary_llm(**kwargs):
    if kwargs["task_type"] == "group":
        return json.dumps({"topics": [{"topic": "T", "articles": [
            {"title": "Alpha", "link": "https://example.com/a"}]}]})
    return "Summary."


class TestOpenAIKeyPassesToday:

    @patch("llm_filter.call_llm")
    def test_filter_passes_openai_key_for_openai_model(self, mock_llm):
        mock_llm.return_value = json.dumps({"decisions": []})

        filter_stories(ARTICLES, "p", "gpt-4o-mini", "sk-openai")

        assert mock_llm.call_args.kwargs["api_keys"] == {"openai": "sk-openai"}

    @patch("summarizer.call_llm", side_effect=_group_and_summary_llm)
    def test_summarizer_passes_openai_key_for_both_calls(self, mock_llm):
        group_and_summarize(ARTICLES, "gpt-4o-mini", "gpt-4o-mini", "sk-openai")

        assert len(mock_llm.call_args_list) == 2
        for call in mock_llm.call_args_list:
            assert call.kwargs["api_keys"] == {"openai": "sk-openai"}


class TestConfiguredProviderKey:

    @pytest.mark.parametrize("model,provider", NON_OPENAI_MODELS)
    @patch("llm_filter.call_llm")
    def test_filter_passes_key_of_configured_provider(self, mock_llm, model, provider):
        mock_llm.return_value = json.dumps({"decisions": []})

        filter_stories(ARTICLES, "p", model, "sk-key")

        assert mock_llm.call_args.kwargs["api_keys"].get(provider)

    @pytest.mark.parametrize("model,provider", NON_OPENAI_MODELS)
    @patch("summarizer.call_llm", side_effect=_group_and_summary_llm)
    def test_group_call_passes_key_of_configured_provider(self, mock_llm, model, provider):
        group_and_summarize(ARTICLES, model, "gpt-4o-mini", "sk-key")

        group_call = next(c for c in mock_llm.call_args_list
                          if c.kwargs["task_type"] == "group")
        assert group_call.kwargs["api_keys"].get(provider)

    @pytest.mark.parametrize("model,provider", NON_OPENAI_MODELS)
    @patch("summarizer.call_llm", side_effect=_group_and_summary_llm)
    def test_summarize_call_passes_key_of_configured_provider(self, mock_llm, model, provider):
        group_and_summarize(ARTICLES, "gpt-4o-mini", model, "sk-key")

        summarize_call = next(c for c in mock_llm.call_args_list
                              if c.kwargs["task_type"] == "summarize")
        assert summarize_call.kwargs["api_keys"].get(provider)

    @pytest.mark.parametrize("model,provider", NON_OPENAI_MODELS)
    @patch("query_engine.call_llm", return_value="not json")
    def test_query_engine_passes_key_of_configured_provider(
            self, mock_llm, model, provider, tmp_path):
        engine = QueryEngine(openai_api_key="sk-key", model=model,
                             db_path=str(tmp_path / "q.db"))

        engine.classify_and_execute("anything")

        assert mock_llm.call_args.kwargs["api_keys"].get(provider)


class TestEndToEndThroughRealFactory:
    """Same bug, observed through the real call_llm -> get_provider path
    with the provider's HTTP layer stubbed out."""

    @patch("utils.save_llm_usage")
    @patch.object(XAIProvider, "complete")
    def test_filter_with_xai_model_reaches_provider(self, mock_complete, _save):
        from providers import LLMUsageMetadata
        mock_complete.return_value = (
            json.dumps({"decisions": [{"index": 1, "decision": "Yes"}]}),
            LLMUsageMetadata(1, 1, 2, 5),
        )

        accepted, _rejected, errored = filter_stories(
            ARTICLES, "p", "xai:grok-3-mini", "sk-key")

        assert len(accepted) == 1 and errored == []

    def test_openai_key_is_never_sent_to_another_provider(self, monkeypatch):
        monkeypatch.delenv("XAI_API_KEY")

        from utils import build_api_keys
        assert build_api_keys("xai:grok-3-mini", "sk-openai") == {}
