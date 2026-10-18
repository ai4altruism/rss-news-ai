# tests/test_prompt_snapshots.py
"""
Golden snapshots of the four LLM prompts (filter, group, summarize, query).

These pin the exact prompt text so a later rewrite shows up as a reviewable
diff in tests/snapshots/. Notably the filter prompt currently asks the model
to compare each article with "previous similar reports" that it is never
shown; the snapshot records that wording as-is.
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
from tests.fakes import assert_matches_snapshot

ARTICLES = [
    {"title": "Alpha model released", "link": "https://example.com/a",
     "summary": "Alpha is a new generative model."},
    {"title": "Beta funding round", "link": "https://example.com/b",
     "summary": "Beta raised money.\nSecond line."},
]


def _capture_prompts(mock_llm):
    return [call.kwargs["prompt"] for call in mock_llm.call_args_list]


class TestPromptSnapshots:

    @patch("llm_filter.call_llm")
    def test_filter_prompt_matches_snapshot(self, mock_llm):
        mock_llm.return_value = json.dumps({"decisions": []})

        filter_stories(ARTICLES, "Keep generative AI news.", "gpt-4o-mini", "key")

        (prompt,) = _capture_prompts(mock_llm)
        assert_matches_snapshot("filter_prompt", prompt)

    @patch("llm_filter.call_llm")
    def test_filter_prompt_truncates_long_summaries_in_snapshot(self, mock_llm):
        mock_llm.return_value = json.dumps({"decisions": []})
        long_article = {"title": "Long", "link": "https://example.com/l",
                        "summary": "x" * 400}

        filter_stories([long_article], "Keep it.", "gpt-4o-mini", "key")

        (prompt,) = _capture_prompts(mock_llm)
        assert "x" * 300 + "..." in prompt
        assert "x" * 301 not in prompt

    @patch("summarizer.call_llm")
    def test_group_and_summarize_prompts_match_snapshots(self, mock_llm):
        def fake(**kwargs):
            if kwargs["task_type"] == "group":
                return json.dumps({"topics": [
                    {"topic": "Models", "articles": [
                        {"title": a["title"], "link": a["link"]} for a in ARTICLES]}
                ]})
            return "A short summary."
        mock_llm.side_effect = fake

        group_and_summarize(ARTICLES, "gpt-4o-mini", "gpt-4o-mini", "key")

        by_task = {c.kwargs["task_type"]: c.kwargs["prompt"]
                   for c in mock_llm.call_args_list}
        assert_matches_snapshot("group_prompt", by_task["group"])
        assert_matches_snapshot("summarize_prompt", by_task["summarize"])

    @patch("query_engine.call_llm")
    @patch.object(QueryEngine, "_get_date_context",
                  return_value="Today's date: 2026-01-01\nDatabase is empty (no data yet)")
    def test_query_prompt_matches_snapshot(self, _ctx, mock_llm, tmp_path):
        mock_llm.return_value = "not json"
        engine = QueryEngine(openai_api_key="key", model="gpt-4o-mini",
                             db_path=str(tmp_path / "q.db"))

        engine.classify_and_execute("Which topic has the most articles?")

        (prompt,) = _capture_prompts(mock_llm)
        assert_matches_snapshot("query_prompt", prompt)
