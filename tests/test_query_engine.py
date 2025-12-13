# tests/test_query_engine.py
"""
Tests for the LLM query engine.
"""

import os
import sys
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from query_engine import (
    validate_sql,
    execute_safe_sql,
    QueryEngine,
    query,
    FORBIDDEN_SQL_KEYWORDS,
)
from history_db import init_database, save_summary_to_db


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_query.db")
    init_database(db_path)
    return db_path


@pytest.fixture
def populated_db(temp_db):
    """Create a database with test data."""
    # Add some test summaries
    summaries = [
        {
            "generated_at": "2024-01-15T10:00:00",
            "topics": [
                {
                    "topic": "OpenAI Developments",
                    "summary": "OpenAI released GPT-5 with improved capabilities.",
                    "articles": [
                        {"title": "GPT-5 Announced", "link": "https://example.com/gpt5"},
                        {"title": "OpenAI Funding Round", "link": "https://example.com/funding"},
                    ]
                },
                {
                    "topic": "Google AI",
                    "summary": "Google announced Gemini 2.",
                    "articles": [
                        {"title": "Gemini 2 Launch", "link": "https://example.com/gemini2"},
                    ]
                }
            ]
        },
        {
            "generated_at": "2024-02-20T10:00:00",
            "topics": [
                {
                    "topic": "OpenAI Developments",
                    "summary": "OpenAI partnership with Microsoft expands.",
                    "articles": [
                        {"title": "Microsoft Partnership", "link": "https://example.com/msft"},
                    ]
                },
                {
                    "topic": "Anthropic News",
                    "summary": "Anthropic released Claude 3.",
                    "articles": [
                        {"title": "Claude 3 Released", "link": "https://example.com/claude3"},
                        {"title": "Anthropic Raises $2B", "link": "https://example.com/anthropic-funding"},
                    ]
                }
            ]
        }
    ]

    for summary in summaries:
        save_summary_to_db(summary, temp_db)

    return temp_db


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "sk-test-mock-key-12345"


# =============================================================================
# SQL Guardrails Tests
# =============================================================================

class TestSqlGuardrails:
    """Tests for SQL validation and guardrails."""

    def test_sql_guardrails_allows_select(self):
        """Valid SELECT queries should pass validation."""
        valid_queries = [
            "SELECT * FROM topics",
            "SELECT name, summary_text FROM topics WHERE id = 1",
            "SELECT COUNT(*) FROM articles",
            "SELECT t.name, COUNT(a.id) FROM topics t JOIN articles a ON t.id = a.topic_id GROUP BY t.name",
            "SELECT * FROM topics WHERE normalized_name LIKE '%openai%'",
            "SELECT (SELECT COUNT(*) FROM topics) as topic_count",
        ]

        for sql in valid_queries:
            is_valid, error = validate_sql(sql)
            assert is_valid, f"Should allow: {sql}, got error: {error}"
            assert error == "", f"Should have no error for: {sql}"

    def test_sql_guardrails_blocks_delete(self):
        """DELETE statements should be blocked."""
        is_valid, error = validate_sql("DELETE FROM topics WHERE id = 1")
        assert not is_valid
        assert "Forbidden keyword: DELETE" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_drop(self):
        """DROP statements should be blocked."""
        is_valid, error = validate_sql("DROP TABLE topics")
        assert not is_valid
        assert "Forbidden keyword: DROP" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_update(self):
        """UPDATE statements should be blocked."""
        is_valid, error = validate_sql("UPDATE topics SET name = 'hacked'")
        assert not is_valid
        assert "Forbidden keyword: UPDATE" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_insert(self):
        """INSERT statements should be blocked."""
        is_valid, error = validate_sql("INSERT INTO topics (name) VALUES ('test')")
        assert not is_valid
        assert "Forbidden keyword: INSERT" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_truncate(self):
        """TRUNCATE statements should be blocked."""
        is_valid, error = validate_sql("TRUNCATE TABLE topics")
        assert not is_valid
        assert "Forbidden keyword: TRUNCATE" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_alter(self):
        """ALTER statements should be blocked."""
        is_valid, error = validate_sql("ALTER TABLE topics ADD COLUMN evil TEXT")
        assert not is_valid
        assert "Forbidden keyword: ALTER" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_create(self):
        """CREATE statements should be blocked."""
        is_valid, error = validate_sql("CREATE TABLE evil (id INTEGER)")
        assert not is_valid
        assert "Forbidden keyword: CREATE" in error or "Only SELECT queries" in error

    def test_sql_guardrails_blocks_multiple_statements(self):
        """Multiple SQL statements should be blocked."""
        is_valid, error = validate_sql("SELECT * FROM topics; DROP TABLE topics")
        assert not is_valid
        assert "Forbidden" in error

    def test_sql_guardrails_blocks_comment_injection(self):
        """SQL comments that might hide malicious code should be blocked."""
        is_valid, error = validate_sql("SELECT * FROM topics -- DROP TABLE topics")
        assert not is_valid
        assert "Forbidden" in error

    def test_sql_guardrails_blocks_block_comments(self):
        """Block comments should be blocked."""
        is_valid, error = validate_sql("SELECT * FROM topics /* DROP TABLE topics */")
        assert not is_valid
        assert "Forbidden" in error

    def test_sql_guardrails_blocks_empty_query(self):
        """Empty queries should be rejected."""
        is_valid, error = validate_sql("")
        assert not is_valid
        assert "Empty" in error

        is_valid, error = validate_sql("   ")
        assert not is_valid
        assert "Empty" in error

    def test_sql_guardrails_blocks_non_select_start(self):
        """Queries not starting with SELECT should be blocked."""
        is_valid, error = validate_sql("WITH cte AS (SELECT 1) DELETE FROM topics")
        assert not is_valid
        assert "Only SELECT" in error

    def test_sql_guardrails_all_forbidden_keywords(self):
        """Test that all forbidden keywords are blocked."""
        for keyword in FORBIDDEN_SQL_KEYWORDS:
            sql = f"{keyword} something"
            is_valid, error = validate_sql(sql)
            assert not is_valid, f"Should block keyword: {keyword}"


class TestExecuteSafeSql:
    """Tests for safe SQL execution."""

    def test_execute_safe_sql_valid_query(self, populated_db):
        """Valid queries should execute and return results."""
        success, result = execute_safe_sql(
            "SELECT name FROM topics",
            populated_db
        )
        assert success
        assert isinstance(result, list)
        assert len(result) > 0
        assert "name" in result[0]

    def test_execute_safe_sql_rejects_invalid(self, populated_db):
        """Invalid queries should be rejected before execution."""
        success, result = execute_safe_sql(
            "DELETE FROM topics",
            populated_db
        )
        assert not success
        assert "Forbidden" in result or "Only SELECT" in result

    def test_execute_safe_sql_handles_sql_error(self, populated_db):
        """SQL errors should be caught and reported."""
        success, result = execute_safe_sql(
            "SELECT * FROM nonexistent_table",
            populated_db
        )
        assert not success
        assert "error" in result.lower()

    def test_execute_safe_sql_returns_correct_columns(self, populated_db):
        """Query results should include correct column names."""
        success, result = execute_safe_sql(
            "SELECT name, summary_text, article_count FROM topics LIMIT 1",
            populated_db
        )
        assert success
        assert len(result) > 0
        row = result[0]
        assert "name" in row
        assert "summary_text" in row
        assert "article_count" in row


# =============================================================================
# Query Classification Tests (with mocking)
# =============================================================================

class TestQueryClassification:
    """Tests for query classification with mocked LLM responses."""

    @patch('query_engine.call_responses_api')
    def test_classify_trends_query(self, mock_api, populated_db, mock_api_key):
        """Trends queries should be classified correctly."""
        # Mock LLM response
        mock_api.return_value = json.dumps({
            "function": "get_trends",
            "parameters": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "period": "week"
            },
            "reasoning": "User asked about trends in January"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("What were the trending topics in January 2024?")

        assert result["success"]
        assert result["query_type"] == "trends"
        assert mock_api.called

    @patch('query_engine.call_responses_api')
    def test_classify_comparison_query(self, mock_api, populated_db, mock_api_key):
        """Comparison queries should be classified correctly."""
        mock_api.return_value = json.dumps({
            "function": "compare_periods",
            "parameters": {
                "period1_start": "2024-01-01",
                "period1_end": "2024-01-31",
                "period2_start": "2024-02-01",
                "period2_end": "2024-02-29",
                "limit": 10
            },
            "reasoning": "User wants to compare January vs February"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Compare January vs February 2024")

        assert result["success"]
        assert result["query_type"] == "comparison"
        assert "period1" in result["data"]
        assert "period2" in result["data"]

    @patch('query_engine.call_responses_api')
    def test_classify_search_query(self, mock_api, populated_db, mock_api_key):
        """Search queries should be classified correctly."""
        mock_api.return_value = json.dumps({
            "function": "search_topics",
            "parameters": {
                "query": "OpenAI",
                "limit": 20
            },
            "reasoning": "User searching for OpenAI articles"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Find articles about OpenAI")

        assert result["success"]
        assert result["query_type"] == "search"
        assert isinstance(result["data"], list)
        # Should find our test OpenAI data
        assert len(result["data"]) > 0

    @patch('query_engine.call_responses_api')
    def test_classify_complex_query(self, mock_api, populated_db, mock_api_key):
        """Complex queries should use custom SQL."""
        mock_api.return_value = json.dumps({
            "function": "execute_sql",
            "parameters": {
                "sql": "SELECT normalized_name, COUNT(*) as count FROM topics GROUP BY normalized_name ORDER BY count DESC",
                "explanation": "Counting topics by name"
            },
            "reasoning": "Complex aggregation query"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Which topic appears most frequently?")

        assert result["success"]
        assert result["query_type"] == "custom"
        assert isinstance(result["data"], list)

    @patch('query_engine.call_responses_api')
    def test_classification_handles_malformed_response(self, mock_api, populated_db, mock_api_key):
        """Should handle malformed LLM responses gracefully."""
        mock_api.return_value = "This is not valid JSON"

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Some query")

        # Should fail gracefully
        assert not result["success"]
        assert "couldn't understand" in result["response"].lower() or "error" in result["response"].lower()

    @patch('query_engine.call_responses_api')
    def test_classification_handles_api_error(self, mock_api, populated_db, mock_api_key):
        """Should handle API errors gracefully."""
        mock_api.side_effect = Exception("API rate limit exceeded")

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Some query")

        assert not result["success"]
        assert "error" in result["response"].lower()


# =============================================================================
# Response Formatting Tests
# =============================================================================

class TestResponseFormatting:
    """Tests for response formatting."""

    @patch('query_engine.call_responses_api')
    def test_response_includes_article_urls(self, mock_api, populated_db, mock_api_key):
        """Search responses should include article URLs."""
        mock_api.return_value = json.dumps({
            "function": "search_topics",
            "parameters": {
                "query": "OpenAI"
            },
            "reasoning": "Searching for OpenAI"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Find OpenAI articles")

        assert result["success"]
        assert result["data"]

        # Check that articles have URLs
        for topic in result["data"]:
            if topic.get("articles"):
                for article in topic["articles"]:
                    assert "link" in article
                    assert article["link"].startswith("http")

        # Also check the response text includes URLs
        response_text = result["response"]
        assert "https://" in response_text

    @patch('query_engine.call_responses_api')
    def test_trends_response_includes_article_urls(self, mock_api, populated_db, mock_api_key):
        """Trends responses should include article URLs."""
        mock_api.return_value = json.dumps({
            "function": "get_trends",
            "parameters": {
                "start_date": "2024-01-01",
                "end_date": "2024-02-28",
                "period": "month"
            },
            "reasoning": "Getting trends"
        })

        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        result = engine.classify_and_execute("Show trends for Jan-Feb 2024")

        assert result["success"]

        # Check data includes URLs
        for item in result["data"]:
            if item.get("articles"):
                for article in item["articles"]:
                    assert "link" in article


# =============================================================================
# Query Engine Initialization Tests
# =============================================================================

class TestQueryEngineInit:
    """Tests for QueryEngine initialization."""

    def test_init_requires_api_key(self, populated_db):
        """Should raise error if no API key available."""
        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            with patch('query_engine.dotenv_values', return_value={}):
                with pytest.raises(ValueError) as exc_info:
                    QueryEngine(db_path=populated_db)
                assert "API key required" in str(exc_info.value)

    def test_init_accepts_api_key_parameter(self, populated_db, mock_api_key):
        """Should accept API key as parameter."""
        engine = QueryEngine(openai_api_key=mock_api_key, db_path=populated_db)
        assert engine.api_key == mock_api_key

    def test_init_reads_api_key_from_env(self, populated_db, mock_api_key):
        """Should read API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": mock_api_key}):
            engine = QueryEngine(db_path=populated_db)
            assert engine.api_key == mock_api_key


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestQueryFunction:
    """Tests for the query() convenience function."""

    @patch('query_engine.call_responses_api')
    def test_query_function_works(self, mock_api, populated_db, mock_api_key):
        """The query() convenience function should work."""
        mock_api.return_value = json.dumps({
            "function": "search_topics",
            "parameters": {"query": "AI"},
            "reasoning": "Search"
        })

        result = query(
            "Find AI articles",
            db_path=populated_db,
            openai_api_key=mock_api_key
        )

        assert isinstance(result, dict)
        assert "success" in result
        assert "query_type" in result
        assert "data" in result
        assert "response" in result
