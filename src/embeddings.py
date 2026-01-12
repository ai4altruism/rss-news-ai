# src/embeddings.py

"""
Semantic deduplication using OpenAI embeddings.

Generates embeddings for article titles + lead sentences, compares them
against recent articles using cosine similarity, and filters out
semantically similar articles to reduce repetitive content.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from openai import OpenAI

from history_db import (
    save_article_embedding,
    get_recent_embeddings,
    save_llm_usage,
    cleanup_old_embeddings,
)
from pricing import calculate_embedding_cost


# Default configuration
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_RETENTION_DAYS = 30


def get_embedding_text(article: Dict[str, Any]) -> str:
    """
    Extract text for embedding: title + lead sentence.

    Creates a compact text representation of the article for embedding.
    The lead sentence provides important context beyond just the title.

    Args:
        article: Article dict with 'title' and 'summary' fields

    Returns:
        Combined text for embedding (typically 50-100 tokens)
    """
    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()

    # Extract first sentence from summary
    lead = ""
    if summary:
        # Handle common sentence endings
        for delimiter in [". ", ".\n", ".\t", "! ", "? "]:
            if delimiter in summary:
                lead = summary.split(delimiter)[0] + delimiter[0]
                break
        else:
            # No sentence boundary found, take first 200 chars
            lead = summary[:200].strip()
            # Try to end at a word boundary
            if len(lead) == 200 and " " in lead:
                lead = lead.rsplit(" ", 1)[0]

    if lead:
        return f"{title}. {lead}"
    return title


def generate_embedding(
    text: str,
    api_key: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> Tuple[Optional[np.ndarray], int]:
    """
    Generate embedding for text using OpenAI's embedding API.

    Args:
        text: Text to embed
        api_key: OpenAI API key
        model: Embedding model name (default: text-embedding-3-small)

    Returns:
        Tuple of (embedding array, token count), or (None, 0) on error
    """
    if not text:
        logging.warning("Empty text provided for embedding")
        return None, 0

    try:
        client = OpenAI(api_key=api_key)

        start_time = time.time()
        response = client.embeddings.create(
            input=text,
            model=model,
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract embedding and token count
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        tokens = response.usage.total_tokens

        # Log usage to database (non-fatal)
        _log_embedding_usage(
            model=model,
            tokens=tokens,
            response_time_ms=response_time_ms,
        )

        return embedding, tokens

    except Exception as e:
        logging.error(f"Failed to generate embedding: {e}")
        return None, 0


def generate_embeddings_batch(
    texts: List[str],
    api_key: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> Tuple[List[Optional[np.ndarray]], int]:
    """
    Generate embeddings for multiple texts in a single API call.

    More efficient than individual calls for processing many articles.

    Args:
        texts: List of texts to embed
        api_key: OpenAI API key
        model: Embedding model name

    Returns:
        Tuple of (list of embedding arrays, total token count)
    """
    if not texts:
        return [], 0

    # Filter out empty texts, keeping track of indices
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text)
            valid_indices.append(i)

    if not valid_texts:
        return [None] * len(texts), 0

    try:
        client = OpenAI(api_key=api_key)

        start_time = time.time()
        response = client.embeddings.create(
            input=valid_texts,
            model=model,
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        total_tokens = response.usage.total_tokens

        # Map embeddings back to original positions
        embeddings = [None] * len(texts)
        for data, orig_idx in zip(response.data, valid_indices):
            embeddings[orig_idx] = np.array(data.embedding, dtype=np.float32)

        # Log usage
        _log_embedding_usage(
            model=model,
            tokens=total_tokens,
            response_time_ms=response_time_ms,
        )

        return embeddings, total_tokens

    except Exception as e:
        logging.error(f"Failed to generate batch embeddings: {e}")
        return [None] * len(texts), 0


def _log_embedding_usage(
    model: str,
    tokens: int,
    response_time_ms: int,
) -> None:
    """Log embedding API usage to the database."""
    try:
        cost = calculate_embedding_cost("openai", model, tokens)
        save_llm_usage(
            provider="openai",
            model=model,
            task_type="embedding",
            input_tokens=tokens,
            output_tokens=0,
            total_tokens=tokens,
            cost_usd=cost,
            response_time_ms=response_time_ms,
        )
    except Exception as e:
        logging.warning(f"Failed to log embedding usage: {e}")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def find_similar_articles(
    new_embedding: np.ndarray,
    recent_embeddings: List[Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> List[Tuple[str, float, str]]:
    """
    Find articles similar to the new embedding.

    Args:
        new_embedding: Embedding vector for the new article
        recent_embeddings: List of dicts with 'url', 'title', 'embedding' (bytes)
        threshold: Minimum similarity score to consider as duplicate

    Returns:
        List of (url, similarity_score, title) for articles exceeding threshold
    """
    similar = []

    for stored in recent_embeddings:
        # Deserialize stored embedding from bytes
        stored_embedding = np.frombuffer(stored["embedding"], dtype=np.float32)

        similarity = cosine_similarity(new_embedding, stored_embedding)

        if similarity >= threshold:
            similar.append((
                stored["url"],
                similarity,
                stored.get("title", "Unknown"),
            ))

    # Sort by similarity (highest first)
    similar.sort(key=lambda x: x[1], reverse=True)
    return similar


def filter_semantic_duplicates(
    articles: List[Dict[str, Any]],
    api_key: str,
    similarity_threshold: Optional[float] = None,
    lookback_days: Optional[int] = None,
    embedding_model: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter out semantically duplicate articles.

    Main entry point for semantic deduplication. Compares new articles
    against recent embeddings stored in the database, filters duplicates,
    and stores embeddings for new unique articles.

    Args:
        articles: List of article dicts to filter
        api_key: OpenAI API key for embedding generation
        similarity_threshold: Minimum similarity to consider duplicate (0.0-1.0)
        lookback_days: Days to look back for duplicate comparison
        embedding_model: OpenAI embedding model to use
        db_path: Optional database path override

    Returns:
        Tuple of:
        - List of unique articles (not semantically similar to recent)
        - Stats dict with filtering information
    """
    if not articles:
        return [], {"total": 0, "unique": 0, "duplicates": 0, "filtered": []}

    # Get configuration from environment or use defaults
    threshold = similarity_threshold or float(
        os.environ.get("SIMILARITY_THRESHOLD", DEFAULT_SIMILARITY_THRESHOLD)
    )
    days = lookback_days or int(
        os.environ.get("DEDUP_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS)
    )
    model = embedding_model or os.environ.get(
        "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
    )

    logging.info(
        f"Semantic deduplication: {len(articles)} articles, "
        f"threshold={threshold}, lookback={days} days"
    )

    # Get recent embeddings from database
    recent = get_recent_embeddings(days=days, db_path=db_path)
    logging.info(f"Loaded {len(recent)} recent embeddings for comparison")

    # Generate embedding texts for all articles
    embedding_texts = [get_embedding_text(article) for article in articles]

    # Generate embeddings in batch
    embeddings, total_tokens = generate_embeddings_batch(
        embedding_texts, api_key, model
    )

    unique_articles = []
    filtered_info = []

    for article, embedding, embed_text in zip(articles, embeddings, embedding_texts):
        if embedding is None:
            # Failed to generate embedding, include article anyway
            logging.warning(
                f"No embedding for article: {article.get('title', 'Unknown')}"
            )
            unique_articles.append(article)
            continue

        # Check for similar articles
        similar = find_similar_articles(embedding, recent, threshold)

        if similar:
            # Article is a duplicate
            most_similar = similar[0]
            filtered_info.append({
                "title": article.get("title", "Unknown"),
                "url": article.get("link", ""),
                "similar_to": most_similar[2],
                "similar_url": most_similar[0],
                "similarity": most_similar[1],
            })
            logging.debug(
                f"Filtered duplicate: '{article.get('title')}' "
                f"similar to '{most_similar[2]}' (score: {most_similar[1]:.3f})"
            )
        else:
            # Article is unique
            unique_articles.append(article)

            # Store embedding for future comparisons
            url = article.get("link", "")
            title = article.get("title", "")
            if url:
                save_article_embedding(
                    url=url,
                    title=title,
                    lead_text=embed_text,
                    embedding=embedding.tobytes(),
                    embedding_model=model,
                    db_path=db_path,
                )
                # Add to recent list for checking remaining articles
                recent.append({
                    "url": url,
                    "title": title,
                    "embedding": embedding.tobytes(),
                })

    # Cleanup old embeddings periodically
    retention_days = int(
        os.environ.get("EMBEDDING_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)
    )
    cleanup_old_embeddings(days=retention_days, db_path=db_path)

    stats = {
        "total": len(articles),
        "unique": len(unique_articles),
        "duplicates": len(filtered_info),
        "tokens_used": total_tokens,
        "threshold": threshold,
        "filtered": filtered_info,
    }

    logging.info(
        f"Semantic deduplication complete: "
        f"{stats['duplicates']} duplicates filtered, "
        f"{stats['unique']} unique articles remain"
    )

    return unique_articles, stats
