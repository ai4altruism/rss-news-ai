# tests/test_query_engine_gaps.py
"""
query_engine gaps: SQL validator false positives and classification parsing.

validate_sql is a keyword blocklist, so a harmless string literal containing
"update" is rejected, and read-only WITH (CTE) queries never pass the
"must start with SELECT" rule. The fallback JSON extractor uses a regex that
cannot match nested braces.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from query_engine import QueryEngine, validate_sql, execute_safe_sql
from history_db import init_database
from tests.fakes import known_bug


@pytest.fixture
def engine(tmp_path):
    return QueryEngine(openai_api_key="key", model="gpt-4o-mini",
                       db_path=str(tmp_path / "q.db"))


class TestValidateSqlStillBlocksWrites:

    @pytest.mark.parametrize("sql", [
        "DELETE FROM topics",
        "SELECT 1; DROP TABLE topics",
        "SELECT * FROM topics -- comment",
        "SELECT /* hidden */ 1",
        "UPDATE topics SET name = 'x'",
        "SELECT * FROM topics WHERE 1=1 UNION SELECT 1 ; PRAGMA writable_schema=1",
        "",
        "   ",
    ])
    def test_rejected(self, sql):
        assert validate_sql(sql)[0] is False

    @pytest.mark.parametrize("sql", [
        "SELECT updated_at FROM topics",
        "SELECT * FROM topics WHERE name LIKE '%openai%'",
        "select count(*) from topics",
    ])
    def test_accepted(self, sql):
        assert validate_sql(sql) == (True, "")


class TestValidateSqlFalsePositives:

    @known_bug("a string literal containing a blocked keyword ('update') is rejected")
    def test_keyword_inside_string_literal_is_allowed(self):
        ok, err = validate_sql("SELECT * FROM articles WHERE title LIKE '%update%'")
        assert ok, err

    @known_bug("read-only WITH (CTE) queries are rejected by the startswith(SELECT) rule")
    def test_read_only_cte_is_allowed(self):
        ok, err = validate_sql(
            "WITH recent AS (SELECT * FROM topics) SELECT COUNT(*) FROM recent")
        assert ok, err

    def test_execute_safe_sql_rejects_write_without_touching_db(self, tmp_path):
        db = str(tmp_path / "s.db")
        init_database(db)
        ok, _ = execute_safe_sql("DELETE FROM topics", db)
        assert ok is False


class TestParseClassification:

    def test_plain_json(self, engine):
        got = engine._parse_classification('{"function": "get_trends", "parameters": {}}')
        assert got["function"] == "get_trends"

    def test_fenced_json(self, engine):
        got = engine._parse_classification('```json\n{"function": "get_trends"}\n```')
        assert got["function"] == "get_trends"

    def test_flat_object_in_prose(self, engine):
        got = engine._parse_classification('Sure: {"function": "get_trends"} hope that helps')
        assert got["function"] == "get_trends"

    def test_garbage_returns_none(self, engine):
        assert engine._parse_classification("no json here") is None

    @known_bug("fallback regex [^{}]* cannot match nested braces, so it returns the inner parameters object")
    def test_nested_object_wrapped_in_prose(self, engine):
        response = ('Here you go: {"function": "search_topics", '
                    '"parameters": {"query": "openai"}} Let me know.')

        got = engine._parse_classification(response)

        assert got is not None
        assert got.get("function") == "search_topics"
        assert got["parameters"] == {"query": "openai"}
