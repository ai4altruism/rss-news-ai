# tests/test_history_db.py
"""
Unit tests for history_db module.
"""

import os
import json
import pytest
import sqlite3
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from history_db import (
    init_database,
    save_summary_to_db,
    get_db_connection,
    normalize_topic_name,
    get_canonical_topic_name,
    get_summary_count,
    get_topic_count,
    get_article_count,
    get_recent_summaries,
    get_summary_by_id,
    import_json_file,
)


class TestInitDatabase:
    """Tests for database initialization."""

    def test_init_database_creates_tables(self, temp_db_path):
        """Verify that init_database creates all required tables."""
        result = init_database(temp_db_path)
        assert result is True

        # Verify tables exist
        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row["name"] for row in cursor.fetchall()]

        assert "summaries" in tables
        assert "topics" in tables
        assert "articles" in tables
        assert "topic_aliases" in tables

    def test_init_database_creates_indexes(self, temp_db_path):
        """Verify that init_database creates indexes."""
        init_database(temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            indexes = [row["name"] for row in cursor.fetchall()]

        assert "idx_summaries_generated_at" in indexes
        assert "idx_topics_summary_id" in indexes
        assert "idx_topics_normalized_name" in indexes
        assert "idx_articles_topic_id" in indexes

    def test_init_database_idempotent(self, temp_db_path):
        """Verify that init_database can be called multiple times safely."""
        result1 = init_database(temp_db_path)
        result2 = init_database(temp_db_path)

        assert result1 is True
        assert result2 is True


class TestSaveSummary:
    """Tests for saving summaries to database."""

    def test_save_summary_creates_records(self, temp_db_path, sample_summary):
        """Verify that save_summary_to_db creates summary, topics, and articles."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(sample_summary, temp_db_path)
        assert summary_id is not None
        assert summary_id > 0

        # Verify summary record
        assert get_summary_count(temp_db_path) == 1

        # Verify topics (sample_summary has 2 topics)
        assert get_topic_count(temp_db_path) == 2

        # Verify articles (3 total in sample_summary)
        assert get_article_count(temp_db_path) == 3

    def test_save_summary_normalizes_topics(self, temp_db_path):
        """Verify that topic names are normalized correctly."""
        init_database(temp_db_path)

        summary = {
            "topics": [
                {
                    "topic": "  OpenAI NEWS  ",
                    "summary": "Test summary",
                    "articles": []
                }
            ],
            "generated_at": datetime.now().isoformat()
        }

        save_summary_to_db(summary, temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute("SELECT name, normalized_name FROM topics")
            row = cursor.fetchone()

        assert row["name"] == "  OpenAI NEWS  "  # Original preserved
        assert row["normalized_name"] == "openai news"  # Normalized

    def test_save_summary_preserves_article_urls(self, temp_db_path, sample_summary):
        """Verify that article URLs are stored correctly."""
        init_database(temp_db_path)

        save_summary_to_db(sample_summary, temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute("SELECT title, link FROM articles ORDER BY title")
            articles = [dict(row) for row in cursor.fetchall()]

        # Check URLs are preserved
        links = [a["link"] for a in articles]
        assert "https://example.com/google-gemini-update" in links
        assert "https://example.com/openai-gpt4-turbo" in links
        assert "https://example.com/openai-api-features" in links

    def test_save_summary_handles_empty_topics(self, temp_db_path, sample_summary_empty):
        """Verify that empty summaries are handled gracefully."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(sample_summary_empty, temp_db_path)
        assert summary_id is not None

        assert get_summary_count(temp_db_path) == 1
        assert get_topic_count(temp_db_path) == 0
        assert get_article_count(temp_db_path) == 0

    def test_save_summary_handles_none(self, temp_db_path):
        """Verify that None summary returns None."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(None, temp_db_path)
        assert summary_id is None

    def test_save_summary_handles_empty_dict(self, temp_db_path):
        """Verify that empty dict summary returns None."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db({}, temp_db_path)
        assert summary_id is None

    def test_save_summary_stores_raw_json(self, temp_db_path, sample_summary):
        """Verify that raw JSON is stored for later retrieval."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(sample_summary, temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT raw_json FROM summaries WHERE id = ?", (summary_id,)
            )
            row = cursor.fetchone()

        stored_json = json.loads(row["raw_json"])
        assert stored_json["topics"] == sample_summary["topics"]


class TestTopicNormalization:
    """Tests for topic name normalization."""

    def test_normalize_topic_name(self):
        """Verify basic normalization."""
        assert normalize_topic_name("OpenAI") == "openai"
        assert normalize_topic_name("  OpenAI  ") == "openai"
        assert normalize_topic_name("GOOGLE AI") == "google ai"

    def test_get_canonical_topic_name_no_alias(self, temp_db_path):
        """Verify canonical name lookup when no alias exists."""
        init_database(temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            result = get_canonical_topic_name("OpenAI", conn)

        assert result == "openai"

    def test_get_canonical_topic_name_with_alias(self, temp_db_path):
        """Verify canonical name lookup when alias exists."""
        init_database(temp_db_path)

        # Insert an alias
        with get_db_connection(temp_db_path) as conn:
            conn.execute(
                "INSERT INTO topic_aliases (canonical_name, alias) VALUES (?, ?)",
                ("openai", "openai news")
            )
            conn.commit()

            result = get_canonical_topic_name("OpenAI News", conn)

        assert result == "openai"


class TestQueryFunctions:
    """Tests for database query functions."""

    def test_get_recent_summaries(self, temp_db_path, sample_summaries_multi_day):
        """Verify recent summaries retrieval."""
        init_database(temp_db_path)

        # Save multiple summaries
        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        recent = get_recent_summaries(3, temp_db_path)

        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0]["generated_at"] > recent[1]["generated_at"]

    def test_get_summary_by_id(self, temp_db_path, sample_summary):
        """Verify summary retrieval by ID."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(sample_summary, temp_db_path)
        retrieved = get_summary_by_id(summary_id, temp_db_path)

        assert retrieved is not None
        assert retrieved["topics"] == sample_summary["topics"]

    def test_get_summary_by_id_not_found(self, temp_db_path):
        """Verify None returned for non-existent ID."""
        init_database(temp_db_path)

        retrieved = get_summary_by_id(9999, temp_db_path)
        assert retrieved is None


class TestImportJson:
    """Tests for JSON file import."""

    def test_import_json_file(self, temp_db_path, tmp_path, sample_summary):
        """Verify JSON file import."""
        init_database(temp_db_path)

        # Write sample summary to file
        json_file = tmp_path / "test_summary.json"
        with open(json_file, "w") as f:
            json.dump(sample_summary, f)

        summary_id = import_json_file(str(json_file), temp_db_path)

        assert summary_id is not None
        assert get_summary_count(temp_db_path) == 1

    def test_import_json_file_adds_timestamp(self, temp_db_path, tmp_path):
        """Verify timestamp is added from file mtime when missing."""
        init_database(temp_db_path)

        # Write summary without generated_at
        summary = {"topics": []}
        json_file = tmp_path / "no_timestamp.json"
        with open(json_file, "w") as f:
            json.dump(summary, f)

        summary_id = import_json_file(str(json_file), temp_db_path)
        assert summary_id is not None

        # Verify timestamp was added
        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT generated_at FROM summaries WHERE id = ?", (summary_id,)
            )
            row = cursor.fetchone()

        assert row["generated_at"] is not None

    def test_import_json_file_not_found(self, temp_db_path):
        """Verify graceful handling of missing file."""
        init_database(temp_db_path)

        summary_id = import_json_file("/nonexistent/file.json", temp_db_path)
        assert summary_id is None

    def test_import_json_file_invalid_json(self, temp_db_path, tmp_path):
        """Verify graceful handling of invalid JSON."""
        init_database(temp_db_path)

        # Write invalid JSON
        json_file = tmp_path / "invalid.json"
        with open(json_file, "w") as f:
            f.write("not valid json {{{")

        summary_id = import_json_file(str(json_file), temp_db_path)
        assert summary_id is None


class TestDatabaseIntegrity:
    """Tests for database integrity and error handling."""

    def test_foreign_key_cascade(self, temp_db_path, sample_summary):
        """Verify foreign key cascades on delete."""
        init_database(temp_db_path)

        summary_id = save_summary_to_db(sample_summary, temp_db_path)

        # Delete the summary
        with get_db_connection(temp_db_path) as conn:
            conn.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
            conn.commit()

        # Topics and articles should be deleted too
        assert get_topic_count(temp_db_path) == 0
        assert get_article_count(temp_db_path) == 0

    def test_multiple_summaries_independent(self, temp_db_path, sample_summary):
        """Verify multiple summaries are stored independently."""
        init_database(temp_db_path)

        id1 = save_summary_to_db(sample_summary, temp_db_path)
        id2 = save_summary_to_db(sample_summary, temp_db_path)

        assert id1 != id2
        assert get_summary_count(temp_db_path) == 2
        # Each summary has 2 topics, so 4 total
        assert get_topic_count(temp_db_path) == 4
