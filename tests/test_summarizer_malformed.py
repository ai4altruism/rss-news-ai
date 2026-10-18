# tests/test_summarizer_malformed.py
"""
Malformed grouping output must never crash group_and_summarize.

unify_topics runs outside the per-chunk try/except, so a topic that is a
bare string, a null name, a null article list, or a dict where a list was
expected raises AttributeError/TypeError and aborts the whole run, losing
every accepted article.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from summarizer import group_and_summarize, unify_topics
from tests.fakes import known_bug

ARTICLES = [
    {"title": "Alpha", "link": "https://example.com/a", "summary": "alpha"},
    {"title": "Beta", "link": "https://example.com/b", "summary": "beta"},
]
GOOD_TOPIC = {"topic": "Models", "articles": [
    {"title": "Alpha", "link": "https://example.com/a"}]}

MALFORMED = {
    "string_topic": {"topics": ["Models"]},
    "null_topic_name": {"topics": [{"topic": None, "articles": [
        {"title": "Alpha", "link": "https://example.com/a"}]}]},
    "topics_is_dict": {"topics": {"topic": "Models", "articles": []}},
    "null_articles": {"topics": [{"topic": "Models", "articles": None}]},
}


def _run(group_payload):
    def fake(**kwargs):
        if kwargs["task_type"] == "group":
            return json.dumps(group_payload)
        return "A summary."
    with patch("summarizer.call_llm", side_effect=fake):
        return group_and_summarize(ARTICLES, "gpt-4o-mini", "gpt-4o-mini", "key")


def _all_links(result):
    return sorted(a["link"] for t in result["topics"] for a in t["articles"])


class TestUnifyTopics:

    def test_merges_same_name_and_dedupes_articles(self):
        a1 = {"title": "A", "link": "l1"}
        a2 = {"title": "B", "link": "l2"}
        result = unify_topics([
            {"topic": "X ", "articles": [a1]},
            {"topic": "X", "articles": [a1, a2]},
        ])
        assert len(result) == 1
        assert result[0]["articles"] == [a1, a2]

    def test_missing_topic_key_becomes_untitled(self):
        result = unify_topics([{"articles": []}])
        assert result[0]["topic"] == "Untitled"

    def test_empty_input(self):
        assert unify_topics([]) == []

    @known_bug("a non-dict topic entry raises AttributeError in unify_topics")
    def test_string_topic_does_not_raise(self):
        unify_topics(["Models"])

    @known_bug('"topic": null raises AttributeError (None.strip()) in unify_topics')
    def test_null_topic_name_does_not_raise(self):
        unify_topics([{"topic": None, "articles": []}])

    @known_bug('"articles": null raises TypeError in unify_topics')
    def test_null_articles_does_not_raise(self):
        unify_topics([{"topic": "X", "articles": None}])


class TestGroupAndSummarizeWellFormed:

    def test_well_formed_grouping_covers_every_article(self):
        result = _run({"topics": [GOOD_TOPIC, {"topic": "Funding", "articles": [
            {"title": "Beta", "link": "https://example.com/b"}]}]})
        assert _all_links(result) == ["https://example.com/a", "https://example.com/b"]
        assert all(t["summary"] for t in result["topics"])

    def test_empty_input_returns_empty_topics(self):
        assert group_and_summarize([], "m", "m", "k") == {"topics": []}

    def test_omitted_articles_go_to_catch_all_topic(self):
        result = _run({"topics": [GOOD_TOPIC]})
        names = [t["topic"] for t in result["topics"]]
        assert "Additional stories" in names
        assert _all_links(result) == ["https://example.com/a", "https://example.com/b"]

    def test_hallucinated_article_is_dropped_and_real_one_kept(self):
        result = _run({"topics": [{"topic": "T", "articles": [
            {"title": "Made up", "link": "https://evil.example/x"},
            {"title": "Alpha", "link": "https://example.com/a"}]}]})
        assert "https://evil.example/x" not in _all_links(result)

    def test_llm_exception_falls_back_to_group_topic(self):
        with patch("summarizer.call_llm", side_effect=RuntimeError("down")):
            result = group_and_summarize(ARTICLES, "m", "m", "k")
        assert _all_links(result) == ["https://example.com/a", "https://example.com/b"]
        assert "collection of 2 articles" in result["topics"][0]["summary"]


class TestGroupAndSummarizeMalformed:

    @known_bug("malformed grouping JSON (string topic, null topic name, dict topics, null articles) aborts the run")
    @pytest.mark.parametrize("case", sorted(MALFORMED))
    def test_malformed_grouping_does_not_raise_and_keeps_articles(self, case):
        result = _run(MALFORMED[case])

        assert _all_links(result) == ["https://example.com/a", "https://example.com/b"]
