# tests/test_history_cli.py
"""
Integration tests for the history CLI.
"""

import os
import sys
import subprocess
import pytest
import json
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from history_db import init_database, save_summary_to_db


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_cli.db")
    init_database(db_path)
    return db_path


@pytest.fixture
def populated_db(temp_db):
    """Create a database with test data."""
    summaries = [
        {
            "generated_at": "2024-01-15T10:00:00",
            "topics": [
                {
                    "topic": "OpenAI News",
                    "summary": "OpenAI released new features.",
                    "articles": [
                        {"title": "GPT-5 Announced", "link": "https://example.com/gpt5"},
                    ]
                }
            ]
        },
        {
            "generated_at": "2024-02-20T10:00:00",
            "topics": [
                {
                    "topic": "Google AI",
                    "summary": "Google AI updates.",
                    "articles": [
                        {"title": "Gemini Update", "link": "https://example.com/gemini"},
                    ]
                }
            ]
        }
    ]

    for summary in summaries:
        save_summary_to_db(summary, temp_db)

    return temp_db


# =============================================================================
# CLI Basic Tests
# =============================================================================

class TestCliBasics:
    """Tests for basic CLI functionality."""

    def test_cli_help(self):
        """CLI should show help message."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert "Manage and query historical news data" in result.stdout

    def test_cli_no_command(self):
        """CLI should show help when no command given."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 1
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_cli_init_command(self, tmp_path):
        """Init command should create database."""
        db_path = str(tmp_path / "new_test.db")
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", db_path, "init"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert os.path.exists(db_path)

    def test_cli_stats_command(self, populated_db):
        """Stats command should show database statistics."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db, "stats"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert "Summaries:" in result.stdout
        assert "Topics:" in result.stdout


# =============================================================================
# CLI Query Commands Tests
# =============================================================================

class TestCliQueryCommands:
    """Tests for CLI query commands (trends, compare, search)."""

    def test_cli_search_command(self, populated_db):
        """Search command should find matching topics."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db, "search", "OpenAI"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert "OpenAI" in result.stdout

    def test_cli_search_json_format(self, populated_db):
        """Search command should output valid JSON when requested."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "search", "OpenAI", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_cli_trends_command(self, populated_db):
        """Trends command should show topic trends."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "trends", "--start", "2024-01-01", "--end", "2024-12-31", "--period", "month"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0

    def test_cli_trends_json_format(self, populated_db):
        """Trends command should output valid JSON."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "trends", "--start", "2024-01-01", "--end", "2024-12-31",
             "--period", "month", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_cli_compare_command(self, populated_db):
        """Compare command should compare two periods."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "compare",
             "--period1", "2024-01-01", "2024-01-31",
             "--period2", "2024-02-01", "2024-02-28"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert "Period" in result.stdout

    def test_cli_compare_json_format(self, populated_db):
        """Compare command should output valid JSON."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "compare",
             "--period1", "2024-01-01", "2024-01-31",
             "--period2", "2024-02-01", "2024-02-28",
             "--format", "json"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "period1" in data
        assert "period2" in data
        assert "comparison" in data


# =============================================================================
# CLI Natural Language Query Tests
# =============================================================================

class TestCliNaturalLanguageQuery:
    """Tests for CLI natural language query command."""

    def test_cli_query_requires_api_key(self, populated_db, monkeypatch):
        """Query command should fail without API key."""
        # Clear any existing API key from environment
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "query", "What are the top topics?"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env={**os.environ, "OPENAI_API_KEY": ""}  # Clear API key
        )
        # Should fail due to missing API key
        assert result.returncode == 1 or "API key" in result.stdout

    def test_cli_query_command_exists(self, populated_db):
        """Query command should be available in CLI help."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert "query" in result.stdout


class TestCliQueryWithMockedApi:
    """Tests for CLI query command with mocked API."""

    @patch('query_engine.call_llm')
    def test_cli_query_natural_language(self, mock_api, populated_db):
        """Query command should work with mocked API."""
        # This test imports and uses the CLI module directly to allow mocking
        import history_cli
        from argparse import Namespace

        # Mock the API response
        mock_api.return_value = json.dumps({
            "function": "search_topics",
            "parameters": {"query": "AI"},
            "reasoning": "Search query"
        })

        # Create args namespace
        args = Namespace(
            db_path=populated_db,
            query_text="Find AI topics",
            format="table"
        )

        # Patch the API key check
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            result = history_cli.cmd_query(args)

        # Should succeed
        assert result == 0 or result is None

    @patch('query_engine.call_llm')
    def test_cli_query_json_output(self, mock_api, populated_db):
        """Query command should support JSON output format."""
        import history_cli
        from argparse import Namespace
        import io
        from contextlib import redirect_stdout

        mock_api.return_value = json.dumps({
            "function": "search_topics",
            "parameters": {"query": "OpenAI"},
            "reasoning": "Search"
        })

        args = Namespace(
            db_path=populated_db,
            query_text="Find OpenAI articles",
            format="json"
        )

        # Capture stdout
        f = io.StringIO()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            with redirect_stdout(f):
                history_cli.cmd_query(args)

        output = f.getvalue()
        # Should be valid JSON
        data = json.loads(output)
        assert "success" in data
        assert "query_type" in data


# =============================================================================
# CLI Error Handling Tests
# =============================================================================

class TestCliErrorHandling:
    """Tests for CLI error handling."""

    def test_cli_search_nonexistent_db(self, tmp_path):
        """Search should fail gracefully with nonexistent database."""
        db_path = str(tmp_path / "nonexistent.db")
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", db_path, "search", "test"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 1
        assert "not found" in result.stdout.lower() or "init" in result.stdout.lower()

    def test_cli_search_no_results(self, populated_db):
        """Search should handle no results gracefully."""
        result = subprocess.run(
            [sys.executable, "src/history_cli.py", "--db-path", populated_db,
             "search", "nonexistent_topic_xyz123"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        assert result.returncode == 0
        assert "No topics found" in result.stdout
