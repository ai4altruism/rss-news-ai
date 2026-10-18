# tests/test_filter_decisions.py
"""
Index handling in llm_filter.filter_stories.

The prompt asks for 1-based indices, but models sometimes answer 0-based.
Index 0 is dropped and every later decision lands on the previous article,
silently flipping accept/reject. Duplicate indices resolve last-wins, so a
conflicting pair is decided by arrival order rather than flagged.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_filter import filter_stories
from tests.fakes import known_bug

A, B, C = (
    {"title": name, "link": f"https://example.com/{name}", "summary": "s"}
    for name in ("A", "B", "C")
)


def _run(decisions, articles=(A, B, C), batch_size=5):
    with patch("llm_filter.call_llm") as mock_llm:
        mock_llm.return_value = json.dumps({"decisions": decisions})
        return filter_stories(list(articles), "p", "gpt-4o-mini", "key",
                              batch_size=batch_size)


def _titles(items):
    return [a["title"] for a in items]


class TestIndexHandlingThatWorks:

    def test_one_based_indices_map_in_order(self):
        accepted, rejected, errored = _run([
            {"index": 1, "decision": "Yes"},
            {"index": 2, "decision": "No"},
            {"index": 3, "decision": "Yes"},
        ])
        assert _titles(accepted) == ["A", "C"]
        assert _titles(rejected) == ["B"]
        assert errored == []

    def test_out_of_range_index_is_ignored(self):
        accepted, _rejected, errored = _run([
            {"index": 1, "decision": "Yes"},
            {"index": 99, "decision": "Yes"},
        ], articles=(A,))
        assert _titles(accepted) == ["A"]
        assert errored == []

    def test_agreeing_duplicate_indices_are_harmless(self):
        accepted, _rejected, errored = _run([
            {"index": 1, "decision": "Yes"},
            {"index": 1, "decision": "Yes"},
        ], articles=(A,))
        assert _titles(accepted) == ["A"]
        assert errored == []

    def test_every_article_lands_in_exactly_one_list(self):
        accepted, rejected, errored = _run([{"index": 2, "decision": "No"}])
        assert sorted(_titles(accepted + rejected + errored)) == ["A", "B", "C"]

    def test_batches_are_independent(self):
        with patch("llm_filter.call_llm") as mock_llm:
            mock_llm.side_effect = [
                json.dumps({"decisions": [{"index": 1, "decision": "Yes"},
                                          {"index": 2, "decision": "Yes"}]}),
                RuntimeError("down"),
            ]
            accepted, _rejected, errored = filter_stories(
                [A, B, C], "p", "gpt-4o-mini", "key", batch_size=2)
        assert _titles(accepted) == ["A", "B"]
        assert _titles(errored) == ["C"]


class TestIndexHandlingBugs:

    @known_bug("0-based indices shift every decision onto the previous article without erroring")
    def test_zero_based_indices_do_not_silently_shift(self):
        # Model meant: A=Yes, B=No, C=Yes, but answered 0-based.
        accepted, rejected, errored = _run([
            {"index": 0, "decision": "Yes"},
            {"index": 1, "decision": "No"},
            {"index": 2, "decision": "Yes"},
        ])

        batch_errored = len(errored) == 3
        index_zero_handled = _titles(accepted) == ["A", "C"] and _titles(rejected) == ["B"]
        assert batch_errored or index_zero_handled

    @known_bug("duplicate indices resolve last-wins instead of erroring the article")
    def test_conflicting_duplicate_indices_error_the_article(self):
        accepted, rejected, errored = _run([
            {"index": 1, "decision": "Yes"},
            {"index": 1, "decision": "No"},
        ], articles=(A,))

        assert _titles(errored) == ["A"]
        assert accepted == [] and rejected == []
