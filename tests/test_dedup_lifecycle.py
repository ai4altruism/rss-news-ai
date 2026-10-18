# tests/test_dedup_lifecycle.py
"""
Semantic-dedup behavior across days, against a real temporary SQLite DB.

Only the OpenAI embedding call is stubbed (generate_embeddings_batch);
storage, lookback windows and similarity run for real. Time is moved by
back-dating created_at rows rather than by sleeping.
"""

import os
import sqlite3
import sys
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from embeddings import filter_semantic_duplicates
from history_db import init_database, get_recent_embeddings
from tests.fakes import known_bug

VEC_X = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
VEC_X_NEAR = np.array([0.99, 0.05, 0.0, 0.0], dtype=np.float32)
VEC_Y = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)


def art(name):
    return {"title": name, "link": f"https://example.com/{name}", "summary": f"{name} body."}


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "dedup.db")
    init_database(path)
    return path


def run(db, articles, vectors, **kwargs):
    with patch("embeddings.generate_embeddings_batch",
               return_value=(list(vectors), 10)):
        return filter_semantic_duplicates(
            articles, api_key="k", db_path=db, similarity_threshold=0.85,
            lookback_days=7, **kwargs)


def age_all_rows(db, days):
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE article_embeddings SET created_at = datetime('now', ?)",
                     (f"-{days} days",))


class TestDedupWithinWindow:

    def test_near_duplicate_of_stored_article_is_dropped(self, db):
        run(db, [art("A")], [VEC_X])

        unique, stats = run(db, [art("B")], [VEC_X_NEAR])

        assert unique == []
        assert stats["duplicates"] == 1

    def test_unrelated_article_passes_and_is_recorded(self, db):
        run(db, [art("A")], [VEC_X])

        unique, _ = run(db, [art("C")], [VEC_Y])

        assert [a["title"] for a in unique] == ["C"]
        assert len(get_recent_embeddings(days=7, db_path=db)) == 2

    def test_duplicate_within_one_batch_is_dropped(self, db):
        unique, stats = run(db, [art("A"), art("B")], [VEC_X, VEC_X_NEAR])

        assert [a["title"] for a in unique] == ["A"]
        assert stats["duplicates"] == 1

    def test_dropped_duplicate_is_not_itself_recorded(self, db):
        run(db, [art("A"), art("B")], [VEC_X, VEC_X_NEAR])

        urls = {r["url"] for r in get_recent_embeddings(days=7, db_path=db)}
        assert urls == {"https://example.com/A"}

    def test_article_never_matches_its_own_stored_embedding(self, db):
        run(db, [art("A")], [VEC_X])

        unique, _ = run(db, [art("A")], [VEC_X])

        assert [a["title"] for a in unique] == ["A"]

    def test_defer_saves_persists_nothing(self, db):
        _, stats = run(db, [art("A")], [VEC_X], defer_saves=True)

        assert get_recent_embeddings(days=7, db_path=db) == []
        assert len(stats["pending_embeddings"]) == 1

    def test_failed_embedding_keeps_article(self, db):
        unique, _ = run(db, [art("A")], [None])
        assert [a["title"] for a in unique] == ["A"]


class TestDedupLifecycleBugs:

    @known_bug("a duplicate dropped on day 0 is never recorded, so it returns once its original leaves the 7-day window")
    def test_duplicate_dropped_on_day_zero_is_still_suppressed_on_day_eight(self, db):
        run(db, [art("A"), art("B")], [VEC_X, VEC_X_NEAR])   # day 0: B dropped as dup of A
        age_all_rows(db, 8)                                   # day 8: A is outside lookback

        unique, _ = run(db, [art("B")], [VEC_X_NEAR])         # B still in the feed

        assert unique == []

    @known_bug("a stored embedding of a different dimension makes np.dot raise instead of being skipped")
    def test_stored_embedding_with_other_dimension_is_skipped(self, db):
        old_model_vec = np.array([1.0, 0.0], dtype=np.float32)
        run(db, [art("OLD")], [old_model_vec])

        unique, _ = run(db, [art("NEW")], [VEC_X])

        assert [a["title"] for a in unique] == ["NEW"]
