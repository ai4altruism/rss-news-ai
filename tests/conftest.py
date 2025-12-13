# tests/conftest.py
"""
Shared pytest fixtures for RSS News AI tests.
"""

import os
import sys
import json
import tempfile
import pytest
from datetime import datetime, timedelta

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test_history.db")


@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)


@pytest.fixture
def sample_summary():
    """Provide a sample summary structure for testing."""
    return {
        "topics": [
            {
                "topic": "OpenAI Developments",
                "summary": "OpenAI announced new features for GPT-4 including improved reasoning capabilities and faster response times.",
                "articles": [
                    {
                        "title": "OpenAI Launches GPT-4 Turbo",
                        "link": "https://example.com/openai-gpt4-turbo"
                    },
                    {
                        "title": "New API Features from OpenAI",
                        "link": "https://example.com/openai-api-features"
                    }
                ]
            },
            {
                "topic": "Google AI Updates",
                "summary": "Google released updates to their Gemini model with enhanced multimodal capabilities.",
                "articles": [
                    {
                        "title": "Google Gemini Gets Major Update",
                        "link": "https://example.com/google-gemini-update"
                    }
                ]
            }
        ],
        "generated_at": datetime.now().isoformat()
    }


@pytest.fixture
def sample_summary_empty():
    """Provide an empty summary structure for testing edge cases."""
    return {
        "topics": [],
        "message": "No new articles found since last update.",
        "generated_at": datetime.now().isoformat()
    }


@pytest.fixture
def sample_articles():
    """Provide sample article data for testing."""
    return [
        {
            "title": "OpenAI Launches GPT-4 Turbo",
            "link": "https://example.com/openai-gpt4-turbo",
            "summary": "OpenAI has announced GPT-4 Turbo with improved performance.",
            "published": "2024-11-15T10:00:00Z",
            "source": "TechCrunch"
        },
        {
            "title": "Google Gemini Gets Major Update",
            "link": "https://example.com/google-gemini-update",
            "summary": "Google releases significant updates to Gemini AI model.",
            "published": "2024-11-14T09:00:00Z",
            "source": "The Verge"
        },
        {
            "title": "Anthropic Releases Claude 3",
            "link": "https://example.com/anthropic-claude-3",
            "summary": "Anthropic announces Claude 3 with enhanced capabilities.",
            "published": "2024-11-13T08:00:00Z",
            "source": "VentureBeat"
        }
    ]


@pytest.fixture
def sample_summaries_multi_day():
    """Provide multiple summaries across different dates for trend testing."""
    base_date = datetime(2024, 11, 1)
    summaries = []

    topics_by_day = [
        ["OpenAI Developments", "Google AI Updates"],
        ["OpenAI Developments", "Anthropic News"],
        ["Google AI Updates", "Microsoft AI"],
        ["OpenAI Developments", "Google AI Updates", "Anthropic News"],
        ["Microsoft AI", "Meta AI Updates"],
    ]

    for i, topics in enumerate(topics_by_day):
        date = base_date + timedelta(days=i * 7)  # Weekly intervals
        summary = {
            "topics": [
                {
                    "topic": topic,
                    "summary": f"Summary for {topic} on {date.strftime('%Y-%m-%d')}",
                    "articles": [
                        {
                            "title": f"{topic} Article {j+1}",
                            "link": f"https://example.com/{topic.lower().replace(' ', '-')}-{j+1}"
                        }
                        for j in range(2)
                    ]
                }
                for topic in topics
            ],
            "generated_at": date.isoformat()
        }
        summaries.append(summary)

    return summaries


@pytest.fixture
def mock_env_vars(monkeypatch, temp_db_path):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("HISTORY_DB_PATH", temp_db_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    return {
        "HISTORY_DB_PATH": temp_db_path,
        "OPENAI_API_KEY": "test-api-key"
    }


@pytest.fixture
def flask_test_client():
    """Provide a Flask test client for API testing."""
    from web_dashboard import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
