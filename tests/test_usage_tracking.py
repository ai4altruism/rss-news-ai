# tests/test_usage_tracking.py

"""
Tests for Sprint 12: Token Usage Monitoring.

Tests the LLM usage tracking, pricing estimation, and database operations.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from providers.base import LLMUsageMetadata
from pricing import calculate_cost, get_model_pricing, format_cost
from history_db import (
    init_database,
    save_llm_usage,
    get_usage_stats,
    get_usage_by_provider,
    get_usage_by_task_type,
    get_usage_by_model,
    export_usage_csv,
)


class TestLLMUsageMetadata:
    """Tests for the LLMUsageMetadata dataclass."""

    def test_create_basic_metadata(self):
        """Should create metadata with basic values."""
        usage = LLMUsageMetadata(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            response_time_ms=500
        )
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150
        assert usage.response_time_ms == 500

    def test_auto_calculate_total_tokens(self):
        """Should auto-calculate total_tokens if not provided."""
        usage = LLMUsageMetadata(
            input_tokens=100,
            output_tokens=50
        )
        assert usage.total_tokens == 150

    def test_default_values(self):
        """Should have sensible defaults."""
        usage = LLMUsageMetadata()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.response_time_ms is None


class TestPricing:
    """Tests for the pricing module."""

    def test_get_openai_pricing(self):
        """Should return OpenAI model pricing."""
        pricing = get_model_pricing("openai", "gpt-4o-mini")
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 0.15
        assert pricing["output"] == 0.60

    def test_get_anthropic_pricing(self):
        """Should return Anthropic model pricing."""
        pricing = get_model_pricing("anthropic", "claude-sonnet-4")
        assert pricing is not None
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00

    def test_get_xai_pricing(self):
        """Should return xAI model pricing."""
        pricing = get_model_pricing("xai", "grok-3-mini")
        assert pricing is not None
        assert pricing["input"] == 0.20
        assert pricing["output"] == 0.80

    def test_get_google_pricing(self):
        """Should return Google model pricing."""
        pricing = get_model_pricing("google", "gemini-2.0-flash")
        assert pricing is not None
        assert pricing["input"] == 0.075
        assert pricing["output"] == 0.30

    def test_unknown_model_returns_none(self):
        """Unknown models should return None."""
        pricing = get_model_pricing("openai", "unknown-model-xyz")
        assert pricing is None

    def test_unknown_provider_returns_none(self):
        """Unknown providers should return None."""
        pricing = get_model_pricing("unknown-provider", "gpt-4o-mini")
        assert pricing is None

    def test_calculate_cost(self):
        """Should calculate cost correctly."""
        cost = calculate_cost(
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500
        )
        # Input: 1000/1M * $0.15 = $0.00015
        # Output: 500/1M * $0.60 = $0.0003
        # Total: $0.00045
        assert cost is not None
        assert cost == pytest.approx(0.00045, rel=1e-4)

    def test_calculate_cost_unknown_model(self):
        """Should return None for unknown models."""
        cost = calculate_cost(
            provider="openai",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500
        )
        assert cost is None

    def test_format_cost_small(self):
        """Should format small costs with 4 decimal places."""
        assert format_cost(0.00045) == "$0.0004"

    def test_format_cost_larger(self):
        """Should format larger costs with 2 decimal places."""
        assert format_cost(1.23) == "$1.23"

    def test_format_cost_none(self):
        """Should return N/A for None."""
        assert format_cost(None) == "N/A"


class TestUsageDatabase:
    """Tests for usage tracking database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        init_database(db_path)
        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_save_usage(self, temp_db):
        """Should save usage record to database."""
        record_id = save_llm_usage(
            provider="openai",
            model="gpt-4o-mini",
            task_type="filter",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            response_time_ms=500,
            db_path=temp_db
        )
        assert record_id is not None
        assert record_id > 0

    def test_get_usage_stats(self, temp_db):
        """Should retrieve usage statistics."""
        # Add some test data
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, response_time_ms=500, db_path=temp_db
        )
        save_llm_usage(
            provider="anthropic", model="claude-sonnet-4", task_type="summarize",
            input_tokens=200, output_tokens=100, total_tokens=300,
            cost_usd=0.002, response_time_ms=600, db_path=temp_db
        )

        stats = get_usage_stats(db_path=temp_db)
        assert stats["total_calls"] == 2
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 150
        assert stats["total_tokens"] == 450
        assert stats["total_cost_usd"] == pytest.approx(0.003, rel=1e-4)

    def test_get_usage_by_provider(self, temp_db):
        """Should group usage by provider."""
        # Add test data
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, db_path=temp_db
        )
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="summarize",
            input_tokens=200, output_tokens=100, total_tokens=300,
            cost_usd=0.002, db_path=temp_db
        )
        save_llm_usage(
            provider="anthropic", model="claude-sonnet-4", task_type="filter",
            input_tokens=150, output_tokens=75, total_tokens=225,
            cost_usd=0.003, db_path=temp_db
        )

        by_provider = get_usage_by_provider(db_path=temp_db)
        assert len(by_provider) == 2

        # Find OpenAI and Anthropic entries
        openai_stats = next((p for p in by_provider if p["provider"] == "openai"), None)
        anthropic_stats = next((p for p in by_provider if p["provider"] == "anthropic"), None)

        assert openai_stats is not None
        assert openai_stats["call_count"] == 2
        assert openai_stats["total_tokens"] == 450

        assert anthropic_stats is not None
        assert anthropic_stats["call_count"] == 1
        assert anthropic_stats["total_tokens"] == 225

    def test_get_usage_by_task_type(self, temp_db):
        """Should group usage by task type."""
        # Add test data
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, db_path=temp_db
        )
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, db_path=temp_db
        )
        save_llm_usage(
            provider="anthropic", model="claude-sonnet-4", task_type="summarize",
            input_tokens=200, output_tokens=100, total_tokens=300,
            cost_usd=0.003, db_path=temp_db
        )

        by_task = get_usage_by_task_type(db_path=temp_db)
        assert len(by_task) == 2

        filter_stats = next((t for t in by_task if t["task_type"] == "filter"), None)
        summarize_stats = next((t for t in by_task if t["task_type"] == "summarize"), None)

        assert filter_stats is not None
        assert filter_stats["call_count"] == 2

        assert summarize_stats is not None
        assert summarize_stats["call_count"] == 1

    def test_get_usage_by_model(self, temp_db):
        """Should group usage by model."""
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, db_path=temp_db
        )
        save_llm_usage(
            provider="openai", model="gpt-5-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.002, db_path=temp_db
        )

        by_model = get_usage_by_model(db_path=temp_db)
        assert len(by_model) == 2

    def test_export_usage_csv(self, temp_db):
        """Should export usage data as CSV."""
        save_llm_usage(
            provider="openai", model="gpt-4o-mini", task_type="filter",
            input_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.001, response_time_ms=500, db_path=temp_db
        )

        csv_data = export_usage_csv(db_path=temp_db)
        assert "timestamp" in csv_data
        assert "provider" in csv_data
        assert "model" in csv_data
        assert "openai" in csv_data
        assert "gpt-4o-mini" in csv_data
        assert "filter" in csv_data


class TestProviderUsageExtraction:
    """Tests for provider usage metadata extraction."""

    @patch('providers.openai_provider.requests.post')
    def test_openai_extracts_usage(self, mock_post):
        """OpenAI provider should extract usage from response."""
        from providers import OpenAIProvider

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Hello"}]}],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15
            }
        }
        mock_post.return_value = mock_response

        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test")
        result, usage = provider.complete("Hi")

        assert result == "Hello"
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5
        assert usage.total_tokens == 15
        assert usage.response_time_ms is not None

    @patch('providers.anthropic_provider.requests.post')
    def test_anthropic_extracts_usage(self, mock_post):
        """Anthropic provider should extract usage from response."""
        from providers import AnthropicProvider

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello"}],
            "usage": {
                "input_tokens": 20,
                "output_tokens": 10
            }
        }
        mock_post.return_value = mock_response

        provider = AnthropicProvider(model="claude-sonnet-4", api_key="test")
        result, usage = provider.complete("Hi")

        assert result == "Hello"
        assert usage.input_tokens == 20
        assert usage.output_tokens == 10
        assert usage.total_tokens == 30

    @patch('providers.xai_provider.requests.post')
    def test_xai_extracts_usage(self, mock_post):
        """xAI provider should extract usage from response."""
        from providers import XAIProvider

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello"}}],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "total_tokens": 23
            }
        }
        mock_post.return_value = mock_response

        provider = XAIProvider(model="grok-3-mini", api_key="test")
        result, usage = provider.complete("Hi")

        assert result == "Hello"
        assert usage.input_tokens == 15
        assert usage.output_tokens == 8
        assert usage.total_tokens == 23

    @patch('providers.gemini_provider.requests.post')
    def test_gemini_extracts_usage(self, mock_post):
        """Gemini provider should extract usage from response."""
        from providers import GeminiProvider

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Hello"}]}}],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 6,
                "totalTokenCount": 18
            }
        }
        mock_post.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.0-flash", api_key="test")
        result, usage = provider.complete("Hi")

        assert result == "Hello"
        assert usage.input_tokens == 12
        assert usage.output_tokens == 6
        assert usage.total_tokens == 18
