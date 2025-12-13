# tests/test_history_api.py
"""
Tests for the history API endpoints.
"""

import os
import sys
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
    db_path = str(tmp_path / "test_api.db")
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
                        {"title": "OpenAI Funding", "link": "https://example.com/funding"},
                    ]
                },
                {
                    "topic": "Google AI",
                    "summary": "Google AI updates.",
                    "articles": [
                        {"title": "Gemini Update", "link": "https://example.com/gemini"},
                    ]
                }
            ]
        },
        {
            "generated_at": "2024-02-20T10:00:00",
            "topics": [
                {
                    "topic": "OpenAI News",
                    "summary": "More OpenAI updates.",
                    "articles": [
                        {"title": "ChatGPT Plus", "link": "https://example.com/chatgpt"},
                    ]
                },
                {
                    "topic": "Anthropic",
                    "summary": "Claude 3 released.",
                    "articles": [
                        {"title": "Claude 3", "link": "https://example.com/claude3"},
                    ]
                }
            ]
        }
    ]

    for summary in summaries:
        save_summary_to_db(summary, temp_db)

    return temp_db


@pytest.fixture
def app_client(populated_db):
    """Create a test client for the Flask app."""
    # Patch the database path before importing the app
    with patch.dict(os.environ, {"HISTORY_DB_PATH": populated_db}):
        # Need to reload the module to pick up the new path
        import importlib
        import web_dashboard
        importlib.reload(web_dashboard)

        web_dashboard.app.config['TESTING'] = True
        with web_dashboard.app.test_client() as client:
            yield client


@pytest.fixture
def app_client_no_db(tmp_path):
    """Create a test client with no database."""
    db_path = str(tmp_path / "nonexistent.db")
    with patch.dict(os.environ, {"HISTORY_DB_PATH": db_path}):
        import importlib
        import web_dashboard
        importlib.reload(web_dashboard)

        web_dashboard.app.config['TESTING'] = True
        with web_dashboard.app.test_client() as client:
            yield client


# =============================================================================
# History Page Tests
# =============================================================================

class TestHistoryPage:
    """Tests for the /history page."""

    def test_history_page_renders(self, app_client):
        """GET /history should return 200."""
        response = app_client.get('/history')
        assert response.status_code == 200
        assert b'AI News History' in response.data

    def test_history_page_shows_stats(self, app_client):
        """History page should show database stats."""
        response = app_client.get('/history')
        assert response.status_code == 200
        # Should show stats numbers
        assert b'Summaries' in response.data
        assert b'Topics' in response.data
        assert b'Articles' in response.data


# =============================================================================
# Stats API Tests
# =============================================================================

class TestStatsApi:
    """Tests for /api/history/stats endpoint."""

    def test_api_stats_returns_data(self, app_client):
        """GET /api/history/stats should return database statistics."""
        response = app_client.get('/api/history/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'summaries' in data
        assert 'topics' in data
        assert 'articles' in data
        assert 'date_range' in data
        assert data['summaries'] == 2
        assert data['topics'] == 4


# =============================================================================
# Trends API Tests
# =============================================================================

class TestTrendsApi:
    """Tests for /api/trends endpoint."""

    def test_api_trends_returns_data(self, app_client):
        """GET /api/trends should return trend data."""
        response = app_client.get('/api/trends?start=2024-01-01&end=2024-12-31&period=month')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'start' in data
        assert 'end' in data
        assert 'period' in data
        assert 'data' in data
        assert data['period'] == 'month'

    def test_api_trends_requires_dates(self, app_client):
        """GET /api/trends without dates should return 400."""
        response = app_client.get('/api/trends')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_api_trends_validates_period(self, app_client):
        """GET /api/trends with invalid period should return 400."""
        response = app_client.get('/api/trends?start=2024-01-01&end=2024-12-31&period=invalid')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'period' in data['error']

    def test_api_trends_date_params(self, app_client):
        """GET /api/trends should respect date parameters."""
        response = app_client.get('/api/trends?start=2024-01-01&end=2024-01-31&period=day')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['start'] == '2024-01-01'
        assert data['end'] == '2024-01-31'


# =============================================================================
# Compare API Tests
# =============================================================================

class TestCompareApi:
    """Tests for /api/compare endpoint."""

    def test_api_compare_returns_data(self, app_client):
        """GET /api/compare should return comparison data."""
        response = app_client.get(
            '/api/compare?p1_start=2024-01-01&p1_end=2024-01-31&p2_start=2024-02-01&p2_end=2024-02-28'
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'period1' in data
        assert 'period2' in data
        assert 'comparison' in data

    def test_api_compare_requires_all_params(self, app_client):
        """GET /api/compare without all params should return 400."""
        response = app_client.get('/api/compare?p1_start=2024-01-01')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data


# =============================================================================
# Topics Search API Tests
# =============================================================================

class TestTopicsSearchApi:
    """Tests for /api/topics endpoint."""

    def test_api_topics_search_returns_results(self, app_client):
        """GET /api/topics should return search results."""
        response = app_client.get('/api/topics?search=OpenAI')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'query' in data
        assert 'count' in data
        assert 'results' in data
        assert data['count'] > 0

    def test_api_topics_search_requires_term(self, app_client):
        """GET /api/topics without search term should return 400."""
        response = app_client.get('/api/topics')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_api_topics_search_no_results(self, app_client):
        """GET /api/topics with no matches should return empty results."""
        response = app_client.get('/api/topics?search=nonexistent_xyz')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] == 0
        assert data['results'] == []

    def test_api_responses_include_urls(self, app_client):
        """Search results should include article URLs."""
        response = app_client.get('/api/topics?search=OpenAI')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['count'] > 0

        # Check that results include articles with links
        for result in data['results']:
            assert 'articles' in result
            if result['articles']:
                for article in result['articles']:
                    assert 'link' in article
                    assert article['link'].startswith('http')


# =============================================================================
# Query API Tests
# =============================================================================

class TestQueryApi:
    """Tests for /api/query endpoint."""

    def test_api_query_requires_body(self, app_client):
        """POST /api/query without body should return 400 (with API key)."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            response = app_client.post('/api/query',
                                       content_type='application/json',
                                       data=json.dumps({}))
            assert response.status_code == 400

            data = json.loads(response.data)
            assert 'error' in data

    def test_api_query_requires_query_field(self, app_client):
        """POST /api/query without query field should return 400 (with API key)."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            response = app_client.post('/api/query',
                                       content_type='application/json',
                                       data=json.dumps({"other": "field"}))
            assert response.status_code == 400

            data = json.loads(response.data)
            assert 'error' in data

    def test_api_query_requires_api_key(self, app_client):
        """POST /api/query without API key should return 503."""
        # Clear any API key
        with patch.dict(os.environ, {}, clear=True):
            response = app_client.post('/api/query',
                                       content_type='application/json',
                                       data=json.dumps({"query": "test"}))
            # Should get 503 because no API key
            assert response.status_code == 503

    @patch('web_dashboard.QueryEngine')
    def test_api_query_success(self, mock_engine_class, app_client):
        """POST /api/query should call query engine and return results."""
        # Mock the query engine
        mock_engine = MagicMock()
        mock_engine.classify_and_execute.return_value = {
            "success": True,
            "query_type": "search",
            "response": "Found 5 results",
            "data": []
        }
        mock_engine_class.return_value = mock_engine

        # Set API key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            response = app_client.post('/api/query',
                                       content_type='application/json',
                                       data=json.dumps({"query": "Find AI articles"}))

        # Should succeed
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True

    @patch('web_dashboard.QueryEngine')
    def test_api_query_handles_error(self, mock_engine_class, app_client):
        """POST /api/query should handle errors gracefully."""
        # Mock engine to raise exception
        mock_engine_class.side_effect = Exception("API error")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
            response = app_client.post('/api/query',
                                       content_type='application/json',
                                       data=json.dumps({"query": "Test query"}))

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'error' in data


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for API error handling."""

    def test_trends_without_db(self, app_client_no_db):
        """Trends endpoint should handle missing database gracefully."""
        # The endpoint checks if database functions are available
        # With no DB, it should return an error
        response = app_client_no_db.get('/api/trends?start=2024-01-01&end=2024-12-31&period=month')
        # May return 200 with empty data or 503 depending on implementation
        assert response.status_code in [200, 503]


# =============================================================================
# Home Page Tests (existing functionality)
# =============================================================================

class TestHomePage:
    """Tests for the home dashboard."""

    def test_home_page_renders(self, app_client):
        """GET / should return 200."""
        response = app_client.get('/')
        assert response.status_code == 200
        assert b'Generative AI News Tracker' in response.data

    def test_api_summary_returns_json(self, app_client):
        """GET /api/summary should return JSON."""
        response = app_client.get('/api/summary')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
