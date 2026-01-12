# tests/test_embeddings.py
"""
Unit tests for the semantic deduplication embeddings module.
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from embeddings import (
    get_embedding_text,
    cosine_similarity,
    find_similar_articles,
    generate_embedding,
    generate_embeddings_batch,
    filter_semantic_duplicates,
    DEFAULT_SIMILARITY_THRESHOLD,
)
from history_db import (
    init_database,
    save_article_embedding,
    get_recent_embeddings,
    get_embedding_by_url,
    get_embedding_count,
    cleanup_old_embeddings,
    get_embedding_stats,
)


class TestGetEmbeddingText:
    """Tests for extracting embedding text from articles."""

    def test_title_only(self):
        """Article with only title."""
        article = {"title": "OpenAI Releases GPT-5"}
        result = get_embedding_text(article)
        assert result == "OpenAI Releases GPT-5"

    def test_title_and_summary(self):
        """Article with title and summary."""
        article = {
            "title": "OpenAI Releases GPT-5",
            "summary": "The company announced today. More details to follow."
        }
        result = get_embedding_text(article)
        assert result == "OpenAI Releases GPT-5. The company announced today."

    def test_summary_with_exclamation(self):
        """Summary ending with exclamation mark."""
        article = {
            "title": "Breaking News",
            "summary": "This is amazing! More info here."
        }
        result = get_embedding_text(article)
        assert result == "Breaking News. This is amazing!"

    def test_summary_with_question(self):
        """Summary ending with question mark."""
        article = {
            "title": "AI Ethics",
            "summary": "Should AI be regulated? Experts weigh in."
        }
        result = get_embedding_text(article)
        assert result == "AI Ethics. Should AI be regulated?"

    def test_long_summary_without_sentence_boundary(self):
        """Summary without clear sentence boundary uses truncation."""
        article = {
            "title": "Tech News",
            "summary": "A" * 300  # Long text without periods
        }
        result = get_embedding_text(article)
        assert result.startswith("Tech News. ")
        assert len(result) <= 220  # Title + ". " + ~200 chars

    def test_empty_title_and_summary(self):
        """Empty article returns empty string."""
        article = {"title": "", "summary": ""}
        result = get_embedding_text(article)
        assert result == ""

    def test_whitespace_handling(self):
        """Whitespace is properly stripped."""
        article = {
            "title": "  Title with spaces  ",
            "summary": "  Summary text.  More text.  "
        }
        result = get_embedding_text(article)
        assert result == "Title with spaces. Summary text."

    def test_missing_fields(self):
        """Missing fields handled gracefully."""
        article = {}
        result = get_embedding_text(article)
        assert result == ""


class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""

    def test_identical_vectors(self):
        """Identical vectors have similarity of 1."""
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_opposite_vectors(self):
        """Opposite vectors have similarity of -1."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors have similarity of 0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_similar_vectors(self):
        """Similar vectors have high similarity."""
        a = np.array([1.0, 0.1, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        similarity = cosine_similarity(a, b)
        assert similarity > 0.9

    def test_zero_vector(self):
        """Zero vector returns 0 similarity."""
        a = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == 0.0

    def test_realistic_embeddings(self):
        """Test with realistic embedding dimensions."""
        np.random.seed(42)
        a = np.random.randn(1536).astype(np.float32)
        b = a + np.random.randn(1536).astype(np.float32) * 0.1  # Small perturbation
        similarity = cosine_similarity(a, b)
        assert 0.8 < similarity < 1.0


class TestFindSimilarArticles:
    """Tests for finding similar articles."""

    def test_no_similar_articles(self):
        """Returns empty list when no similar articles."""
        new_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        recent = [
            {
                "url": "https://example.com/1",
                "title": "Article 1",
                "embedding": np.array([0.0, 1.0, 0.0], dtype=np.float32).tobytes()
            }
        ]
        similar = find_similar_articles(new_embedding, recent, threshold=0.85)
        assert len(similar) == 0

    def test_finds_similar_article(self):
        """Finds article above threshold."""
        new_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        recent = [
            {
                "url": "https://example.com/1",
                "title": "Similar Article",
                "embedding": np.array([0.99, 0.1, 0.0], dtype=np.float32).tobytes()
            }
        ]
        similar = find_similar_articles(new_embedding, recent, threshold=0.85)
        assert len(similar) == 1
        assert similar[0][0] == "https://example.com/1"
        assert similar[0][1] > 0.85
        assert similar[0][2] == "Similar Article"

    def test_multiple_similar_articles(self):
        """Returns all articles above threshold, sorted by similarity."""
        new_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        recent = [
            {
                "url": "https://example.com/1",
                "title": "Most Similar",
                "embedding": np.array([0.99, 0.01, 0.0], dtype=np.float32).tobytes()
            },
            {
                "url": "https://example.com/2",
                "title": "Less Similar",
                "embedding": np.array([0.9, 0.2, 0.0], dtype=np.float32).tobytes()
            },
            {
                "url": "https://example.com/3",
                "title": "Not Similar",
                "embedding": np.array([0.0, 1.0, 0.0], dtype=np.float32).tobytes()
            }
        ]
        similar = find_similar_articles(new_embedding, recent, threshold=0.85)
        assert len(similar) == 2
        # Verify sorted by similarity (highest first)
        assert similar[0][2] == "Most Similar"
        assert similar[1][2] == "Less Similar"

    def test_threshold_boundary(self):
        """Articles exactly at threshold are included."""
        new_embedding = np.array([1.0, 0.0], dtype=np.float32)
        # Create a vector that will give exactly 0.85 similarity
        # cos(theta) = 0.85 means theta ~= 31.8 degrees
        angle = np.arccos(0.85)
        boundary_vec = np.array([np.cos(angle), np.sin(angle)], dtype=np.float32)

        recent = [
            {
                "url": "https://example.com/1",
                "title": "Boundary Article",
                "embedding": boundary_vec.tobytes()
            }
        ]
        similar = find_similar_articles(new_embedding, recent, threshold=0.85)
        assert len(similar) == 1


class TestDatabaseEmbeddingFunctions:
    """Tests for embedding database operations."""

    def test_save_and_retrieve_embedding(self, temp_db_path):
        """Save embedding and retrieve it."""
        init_database(temp_db_path)

        embedding = np.random.randn(1536).astype(np.float32)
        result = save_article_embedding(
            url="https://example.com/test",
            title="Test Article",
            lead_text="This is a test.",
            embedding=embedding.tobytes(),
            embedding_model="text-embedding-3-small",
            db_path=temp_db_path,
        )
        assert result is not None

        # Retrieve by URL
        stored = get_embedding_by_url("https://example.com/test", temp_db_path)
        assert stored is not None
        assert stored["title"] == "Test Article"
        assert stored["lead_text"] == "This is a test."
        assert stored["embedding_model"] == "text-embedding-3-small"

        # Verify embedding data
        stored_embedding = np.frombuffer(stored["embedding"], dtype=np.float32)
        np.testing.assert_array_almost_equal(embedding, stored_embedding)

    def test_get_recent_embeddings(self, temp_db_path):
        """Get embeddings from last N days."""
        init_database(temp_db_path)

        # Add multiple embeddings
        for i in range(5):
            embedding = np.random.randn(1536).astype(np.float32)
            save_article_embedding(
                url=f"https://example.com/test-{i}",
                title=f"Test Article {i}",
                lead_text=f"Lead text {i}",
                embedding=embedding.tobytes(),
                db_path=temp_db_path,
            )

        recent = get_recent_embeddings(days=7, db_path=temp_db_path)
        assert len(recent) == 5

    def test_get_embedding_count(self, temp_db_path):
        """Count total embeddings."""
        init_database(temp_db_path)

        assert get_embedding_count(temp_db_path) == 0

        for i in range(3):
            embedding = np.random.randn(1536).astype(np.float32)
            save_article_embedding(
                url=f"https://example.com/test-{i}",
                title=f"Test Article {i}",
                lead_text=f"Lead text {i}",
                embedding=embedding.tobytes(),
                db_path=temp_db_path,
            )

        assert get_embedding_count(temp_db_path) == 3

    def test_get_embedding_stats(self, temp_db_path):
        """Get embedding statistics."""
        init_database(temp_db_path)

        embedding = np.random.randn(1536).astype(np.float32)
        save_article_embedding(
            url="https://example.com/test",
            title="Test Article",
            lead_text="Test lead",
            embedding=embedding.tobytes(),
            db_path=temp_db_path,
        )

        stats = get_embedding_stats(temp_db_path)
        assert stats["total_count"] == 1
        assert len(stats["by_model"]) == 1
        assert stats["by_model"][0]["embedding_model"] == "text-embedding-3-small"

    def test_embedding_table_created(self, temp_db_path):
        """Verify article_embeddings table is created."""
        init_database(temp_db_path)

        from history_db import get_db_connection
        with get_db_connection(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='article_embeddings'"
            )
            tables = [row["name"] for row in cursor.fetchall()]

        assert "article_embeddings" in tables


class TestGenerateEmbedding:
    """Tests for embedding generation with mocked API."""

    @patch('embeddings.OpenAI')
    @patch('embeddings._log_embedding_usage')
    def test_generate_embedding_success(self, mock_log, mock_openai_class):
        """Successfully generate embedding."""
        # Mock OpenAI response
        mock_embedding = np.random.randn(1536).astype(np.float32).tolist()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_response.usage = Mock(total_tokens=42)

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embedding, tokens = generate_embedding(
            "Test text",
            api_key="test-key",
            model="text-embedding-3-small"
        )

        assert embedding is not None
        assert len(embedding) == 1536
        assert tokens == 42
        mock_client.embeddings.create.assert_called_once()

    @patch('embeddings.OpenAI')
    @patch('embeddings._log_embedding_usage')
    def test_generate_embedding_empty_text(self, mock_log, mock_openai_class):
        """Empty text returns None."""
        embedding, tokens = generate_embedding(
            "",
            api_key="test-key",
        )
        assert embedding is None
        assert tokens == 0

    @patch('embeddings.OpenAI')
    @patch('embeddings._log_embedding_usage')
    def test_generate_embedding_api_error(self, mock_log, mock_openai_class):
        """API error returns None."""
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        embedding, tokens = generate_embedding(
            "Test text",
            api_key="test-key",
        )
        assert embedding is None
        assert tokens == 0


class TestGenerateEmbeddingsBatch:
    """Tests for batch embedding generation."""

    @patch('embeddings.OpenAI')
    @patch('embeddings._log_embedding_usage')
    def test_batch_generation(self, mock_log, mock_openai_class):
        """Generate embeddings for multiple texts."""
        mock_embeddings = [
            Mock(embedding=np.random.randn(1536).tolist()),
            Mock(embedding=np.random.randn(1536).tolist()),
        ]
        mock_response = Mock()
        mock_response.data = mock_embeddings
        mock_response.usage = Mock(total_tokens=100)

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embeddings, tokens = generate_embeddings_batch(
            ["Text 1", "Text 2"],
            api_key="test-key",
        )

        assert len(embeddings) == 2
        assert all(e is not None for e in embeddings)
        assert tokens == 100

    @patch('embeddings.OpenAI')
    @patch('embeddings._log_embedding_usage')
    def test_batch_with_empty_texts(self, mock_log, mock_openai_class):
        """Empty texts are skipped in batch."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=np.random.randn(1536).tolist())]
        mock_response.usage = Mock(total_tokens=50)

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embeddings, tokens = generate_embeddings_batch(
            ["Text 1", "", ""],  # Two empty texts
            api_key="test-key",
        )

        assert len(embeddings) == 3
        assert embeddings[0] is not None
        assert embeddings[1] is None
        assert embeddings[2] is None

    def test_empty_text_list(self):
        """Empty list returns empty results."""
        embeddings, tokens = generate_embeddings_batch([], api_key="test-key")
        assert embeddings == []
        assert tokens == 0


class TestFilterSemanticDuplicates:
    """Tests for the main semantic deduplication function."""

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_filter_with_duplicates(
        self,
        mock_cleanup,
        mock_save,
        mock_recent,
        mock_batch,
    ):
        """Filter out duplicate articles."""
        # Set up mock embeddings
        existing_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        new_similar_embedding = np.array([0.99, 0.1, 0.0], dtype=np.float32)
        new_unique_embedding = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        mock_recent.return_value = [
            {
                "url": "https://example.com/existing",
                "title": "Existing Article",
                "embedding": existing_embedding.tobytes(),
            }
        ]

        mock_batch.return_value = (
            [new_similar_embedding, new_unique_embedding],
            100,
        )

        articles = [
            {
                "title": "Similar to Existing",
                "link": "https://example.com/similar",
                "summary": "Similar content."
            },
            {
                "title": "Completely Different",
                "link": "https://example.com/different",
                "summary": "Different content."
            }
        ]

        unique, stats = filter_semantic_duplicates(
            articles,
            api_key="test-key",
            similarity_threshold=0.85,
        )

        assert len(unique) == 1
        assert unique[0]["title"] == "Completely Different"
        assert stats["total"] == 2
        assert stats["unique"] == 1
        assert stats["duplicates"] == 1
        assert len(stats["filtered"]) == 1

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_filter_no_duplicates(
        self,
        mock_cleanup,
        mock_save,
        mock_recent,
        mock_batch,
    ):
        """All unique articles pass through."""
        mock_recent.return_value = []

        unique_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_batch.return_value = ([unique_embedding], 50)

        articles = [
            {
                "title": "Unique Article",
                "link": "https://example.com/unique",
                "summary": "Unique content."
            }
        ]

        unique, stats = filter_semantic_duplicates(
            articles,
            api_key="test-key",
        )

        assert len(unique) == 1
        assert stats["duplicates"] == 0
        mock_save.assert_called_once()

    def test_filter_empty_list(self):
        """Empty input returns empty output."""
        unique, stats = filter_semantic_duplicates(
            [],
            api_key="test-key",
        )

        assert unique == []
        assert stats["total"] == 0
        assert stats["unique"] == 0
        assert stats["duplicates"] == 0

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_filter_handles_failed_embeddings(
        self,
        mock_cleanup,
        mock_save,
        mock_recent,
        mock_batch,
    ):
        """Articles with failed embeddings are still included."""
        mock_recent.return_value = []
        mock_batch.return_value = ([None], 0)  # Failed embedding

        articles = [
            {
                "title": "Article with Failed Embedding",
                "link": "https://example.com/failed",
                "summary": "Content."
            }
        ]

        unique, stats = filter_semantic_duplicates(
            articles,
            api_key="test-key",
        )

        # Article should still be included even with failed embedding
        assert len(unique) == 1
        assert stats["total"] == 1


class TestPricingIntegration:
    """Tests for embedding pricing integration."""

    def test_embedding_pricing_exists(self):
        """Verify embedding pricing is defined."""
        from pricing import EMBEDDING_PRICING

        assert "openai" in EMBEDDING_PRICING
        assert "text-embedding-3-small" in EMBEDDING_PRICING["openai"]

    def test_calculate_embedding_cost(self):
        """Calculate embedding cost."""
        from pricing import calculate_embedding_cost

        # text-embedding-3-small costs $0.02 per 1M tokens
        cost = calculate_embedding_cost("openai", "text-embedding-3-small", 1000)
        assert cost == pytest.approx(0.00002)

        # 1 million tokens
        cost = calculate_embedding_cost("openai", "text-embedding-3-small", 1_000_000)
        assert cost == pytest.approx(0.02)

    def test_unknown_model_returns_none(self):
        """Unknown model returns None cost."""
        from pricing import calculate_embedding_cost

        cost = calculate_embedding_cost("openai", "unknown-model", 1000)
        assert cost is None
