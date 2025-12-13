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
    topic_counts_by_period,
    top_topics_comparison,
    topic_search,
    get_date_range,
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


# =============================================================================
# Sprint 2: Query Function Tests
# =============================================================================

class TestTopicCountsByPeriod:
    """Tests for topic_counts_by_period function."""

    def test_topic_counts_by_period_daily(self, temp_db_path, sample_summaries_multi_day):
        """Verify daily aggregation works."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = topic_counts_by_period(
            "2024-11-01", "2024-11-30", "day", temp_db_path
        )

        assert len(results) > 0
        # Each result should have required fields
        for item in results:
            assert "period" in item
            assert "topic" in item
            assert "story_count" in item
            assert "articles" in item

    def test_topic_counts_by_period_weekly(self, temp_db_path, sample_summaries_multi_day):
        """Verify weekly aggregation works."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = topic_counts_by_period(
            "2024-11-01", "2024-11-30", "week", temp_db_path
        )

        assert len(results) > 0
        # Weekly periods should have format YYYY-Www
        for item in results:
            assert "-W" in item["period"]

    def test_topic_counts_by_period_monthly(self, temp_db_path, sample_summaries_multi_day):
        """Verify monthly aggregation works."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = topic_counts_by_period(
            "2024-11-01", "2024-11-30", "month", temp_db_path
        )

        assert len(results) > 0
        # Monthly periods should have format YYYY-MM
        for item in results:
            assert item["period"].startswith("2024-")
            assert len(item["period"]) == 7  # YYYY-MM

    def test_topic_counts_returns_articles(self, temp_db_path, sample_summaries_multi_day):
        """Verify article URLs are included in results."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = topic_counts_by_period(
            "2024-11-01", "2024-11-30", "week", temp_db_path
        )

        # Find a result with articles
        has_articles = any(len(r["articles"]) > 0 for r in results)
        assert has_articles

        # Articles should have title and link
        for item in results:
            for article in item["articles"]:
                assert "title" in article
                assert "link" in article

    def test_topic_counts_invalid_period(self, temp_db_path):
        """Verify invalid period returns empty list."""
        init_database(temp_db_path)

        results = topic_counts_by_period(
            "2024-11-01", "2024-11-30", "invalid", temp_db_path
        )

        assert results == []

    def test_topic_counts_empty_date_range(self, temp_db_path, sample_summary):
        """Verify empty date range returns no results."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        # Query for dates with no data
        results = topic_counts_by_period(
            "2020-01-01", "2020-01-31", "week", temp_db_path
        )

        assert results == []


class TestTopTopicsComparison:
    """Tests for top_topics_comparison function."""

    def test_top_topics_comparison(self, temp_db_path, sample_summaries_multi_day):
        """Verify period comparison works."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = top_topics_comparison(
            "2024-11-01", "2024-11-15",
            "2024-11-16", "2024-11-30",
            10, temp_db_path
        )

        assert "period1" in results
        assert "period2" in results
        assert "comparison" in results
        assert "topics" in results["period1"]
        assert "topics" in results["period2"]

    def test_comparison_includes_common_topics(self, temp_db_path, sample_summaries_multi_day):
        """Verify comparison identifies common topics."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = top_topics_comparison(
            "2024-11-01", "2024-11-15",
            "2024-11-08", "2024-11-30",
            10, temp_db_path
        )

        comp = results["comparison"]
        assert "common_topics" in comp
        assert "new_in_period2" in comp
        assert "dropped_from_period1" in comp

    def test_comparison_returns_articles(self, temp_db_path, sample_summaries_multi_day):
        """Verify article URLs are included in comparison results."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        results = top_topics_comparison(
            "2024-11-01", "2024-11-30",
            "2024-11-01", "2024-11-30",
            10, temp_db_path
        )

        # Check period1 topics have articles
        for topic in results["period1"]["topics"]:
            assert "articles" in topic
            for article in topic["articles"]:
                assert "title" in article
                assert "link" in article


class TestTopicSearch:
    """Tests for topic_search function."""

    def test_topic_search_returns_urls(self, temp_db_path, sample_summary):
        """Verify search results include article URLs."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        results = topic_search("openai", db_path=temp_db_path)

        assert len(results) > 0
        for item in results:
            assert "articles" in item
            for article in item["articles"]:
                assert "link" in article
                assert article["link"].startswith("http")

    def test_topic_search_case_insensitive(self, temp_db_path, sample_summary):
        """Verify search is case-insensitive."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        results_lower = topic_search("openai", db_path=temp_db_path)
        results_upper = topic_search("OPENAI", db_path=temp_db_path)
        results_mixed = topic_search("OpenAI", db_path=temp_db_path)

        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_topic_search_partial_match(self, temp_db_path, sample_summary):
        """Verify partial matching works."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        results = topic_search("google", db_path=temp_db_path)

        assert len(results) > 0
        # Should match "Google AI Updates"
        topics = [r["normalized_name"] for r in results]
        assert any("google" in t for t in topics)

    def test_topic_search_date_filtering(self, temp_db_path, sample_summaries_multi_day):
        """Verify date range filtering works."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        # Search with date filter
        all_results = topic_search("ai", db_path=temp_db_path)
        filtered_results = topic_search(
            "ai",
            start_date="2024-11-01",
            end_date="2024-11-07",
            db_path=temp_db_path
        )

        # Filtered should be subset
        assert len(filtered_results) <= len(all_results)

    def test_topic_search_no_results(self, temp_db_path, sample_summary):
        """Verify empty results for non-matching query."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        results = topic_search("nonexistent_topic_xyz", db_path=temp_db_path)

        assert results == []

    def test_topic_search_includes_summary_text(self, temp_db_path, sample_summary):
        """Verify search results include summary text."""
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        results = topic_search("openai", db_path=temp_db_path)

        assert len(results) > 0
        for item in results:
            assert "summary_text" in item
            assert "topic_name" in item
            assert "generated_at" in item


class TestGetDateRange:
    """Tests for get_date_range function."""

    def test_get_date_range(self, temp_db_path, sample_summaries_multi_day):
        """Verify date range retrieval."""
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        date_range = get_date_range(temp_db_path)

        assert date_range["earliest"] is not None
        assert date_range["latest"] is not None
        assert date_range["earliest"] <= date_range["latest"]

    def test_get_date_range_empty_db(self, temp_db_path):
        """Verify date range for empty database."""
        init_database(temp_db_path)

        date_range = get_date_range(temp_db_path)

        assert date_range["earliest"] is None
        assert date_range["latest"] is None


# =============================================================================
# Sprint 5: Topic Alias Tests
# =============================================================================

class TestTopicAliases:
    """Tests for topic alias management."""

    def test_add_topic_alias(self, temp_db_path):
        """Verify alias creation."""
        from history_db import add_topic_alias, list_topic_aliases
        init_database(temp_db_path)

        result = add_topic_alias("gpt-4", "openai", temp_db_path)

        assert result is True
        aliases = list_topic_aliases(temp_db_path)
        assert len(aliases) == 1
        assert aliases[0]["alias"] == "gpt-4"
        assert aliases[0]["canonical_name"] == "openai"

    def test_add_topic_alias_normalizes(self, temp_db_path):
        """Verify alias names are normalized."""
        from history_db import add_topic_alias, list_topic_aliases
        init_database(temp_db_path)

        result = add_topic_alias("  GPT-4  ", "  OpenAI  ", temp_db_path)

        assert result is True
        aliases = list_topic_aliases(temp_db_path)
        assert aliases[0]["alias"] == "gpt-4"
        assert aliases[0]["canonical_name"] == "openai"

    def test_add_topic_alias_same_name_fails(self, temp_db_path):
        """Verify alias cannot equal canonical name."""
        from history_db import add_topic_alias
        init_database(temp_db_path)

        result = add_topic_alias("openai", "OpenAI", temp_db_path)

        assert result is False

    def test_remove_topic_alias(self, temp_db_path):
        """Verify alias removal."""
        from history_db import add_topic_alias, remove_topic_alias, list_topic_aliases
        init_database(temp_db_path)

        add_topic_alias("gpt", "openai", temp_db_path)
        assert len(list_topic_aliases(temp_db_path)) == 1

        result = remove_topic_alias("gpt", temp_db_path)

        assert result is True
        assert len(list_topic_aliases(temp_db_path)) == 0

    def test_remove_nonexistent_alias(self, temp_db_path):
        """Verify removing nonexistent alias returns False."""
        from history_db import remove_topic_alias
        init_database(temp_db_path)

        result = remove_topic_alias("nonexistent", temp_db_path)

        assert result is False

    def test_topic_alias_applied_on_save(self, temp_db_path, sample_summary):
        """Verify alias is applied when saving summary."""
        from history_db import add_topic_alias
        init_database(temp_db_path)

        # Add alias before saving
        add_topic_alias("openai developments", "openai", temp_db_path)

        # Save summary (topic should be normalized to alias canonical)
        save_summary_to_db(sample_summary, temp_db_path)

        # Search should find it under canonical name
        results = topic_search("openai", db_path=temp_db_path)
        assert len(results) > 0

    def test_get_unique_topics(self, temp_db_path, sample_summaries_multi_day):
        """Verify unique topics list."""
        from history_db import get_unique_topics
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        topics = get_unique_topics(temp_db_path)

        assert len(topics) > 0
        for topic in topics:
            assert "normalized_name" in topic
            assert "count" in topic
            assert topic["count"] > 0


# =============================================================================
# Sprint 5: Export Tests
# =============================================================================

class TestExportFunctions:
    """Tests for data export functions."""

    def test_export_topics_csv(self, temp_db_path, sample_summary):
        """Verify topics CSV export."""
        from history_db import export_topics_csv
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        csv_data = export_topics_csv(db_path=temp_db_path)

        assert csv_data  # Not empty
        assert "date,topic,normalized_name" in csv_data  # Header
        assert "openai" in csv_data.lower()  # Content

    def test_export_topics_csv_date_filter(self, temp_db_path, sample_summaries_multi_day):
        """Verify CSV export with date filtering."""
        from history_db import export_topics_csv
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        all_csv = export_topics_csv(db_path=temp_db_path)
        filtered_csv = export_topics_csv(
            start_date="2024-11-01",
            end_date="2024-11-07",
            db_path=temp_db_path
        )

        # Filtered should have fewer rows
        all_lines = all_csv.strip().split('\n')
        filtered_lines = filtered_csv.strip().split('\n')
        assert len(filtered_lines) <= len(all_lines)

    def test_export_articles_csv(self, temp_db_path, sample_summary):
        """Verify articles CSV export."""
        from history_db import export_articles_csv
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        csv_data = export_articles_csv(db_path=temp_db_path)

        assert csv_data  # Not empty
        assert "date,topic,title,link" in csv_data  # Header
        assert "http" in csv_data  # Should have URLs

    def test_export_json(self, temp_db_path, sample_summary):
        """Verify JSON export."""
        from history_db import export_data_json
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        json_data = export_data_json(db_path=temp_db_path)

        assert "metadata" in json_data
        assert "summaries" in json_data
        assert "topics" in json_data
        assert json_data["metadata"]["summary_count"] == 1
        assert json_data["metadata"]["topic_count"] > 0

    def test_export_json_includes_articles(self, temp_db_path, sample_summary):
        """Verify JSON export includes article data."""
        from history_db import export_data_json
        init_database(temp_db_path)
        save_summary_to_db(sample_summary, temp_db_path)

        json_data = export_data_json(db_path=temp_db_path)

        # Topics should include articles
        assert len(json_data["topics"]) > 0
        for topic in json_data["topics"]:
            assert "articles" in topic
            for article in topic["articles"]:
                assert "link" in article

    def test_export_json_date_filter(self, temp_db_path, sample_summaries_multi_day):
        """Verify JSON export with date filtering."""
        from history_db import export_data_json
        init_database(temp_db_path)

        for summary in sample_summaries_multi_day:
            save_summary_to_db(summary, temp_db_path)

        all_data = export_data_json(db_path=temp_db_path)
        filtered_data = export_data_json(
            start_date="2024-11-01",
            end_date="2024-11-07",
            db_path=temp_db_path
        )

        assert filtered_data["metadata"]["topic_count"] <= all_data["metadata"]["topic_count"]
