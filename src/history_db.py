# src/history_db.py
"""
Database operations for storing and querying historical summaries.
Uses SQLite for persistent storage of topics, articles, and summaries.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

# Default database path
DEFAULT_DB_PATH = "data/history.db"

# SQL schema for creating tables
SCHEMA_SQL = """
-- Stores each run's complete output
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TIMESTAMP NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Normalized topics for efficient querying
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    summary_text TEXT,
    article_count INTEGER DEFAULT 0,
    FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE CASCADE
);

-- Articles linked to topics (preserves original URLs for retrieval)
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    source TEXT,
    published_date TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Handle topic name variations ("OpenAI" vs "OpenAI News")
CREATE TABLE IF NOT EXISTS topic_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_summaries_generated_at ON summaries(generated_at);
CREATE INDEX IF NOT EXISTS idx_topics_summary_id ON topics(summary_id);
CREATE INDEX IF NOT EXISTS idx_topics_normalized_name ON topics(normalized_name);
CREATE INDEX IF NOT EXISTS idx_articles_topic_id ON articles(topic_id);
CREATE INDEX IF NOT EXISTS idx_articles_link ON articles(link);
"""


def get_db_path() -> str:
    """Get database path from environment or use default."""
    return os.environ.get("HISTORY_DB_PATH", DEFAULT_DB_PATH)


@contextmanager
def get_db_connection(db_path: Optional[str] = None, readonly: bool = False):
    """
    Get database connection with proper cleanup.

    Parameters:
        db_path: Path to database file. If None, uses environment variable or default.
        readonly: If True, open connection in read-only mode.

    Yields:
        sqlite3.Connection with row_factory set to sqlite3.Row
    """
    if db_path is None:
        db_path = get_db_path()

    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Build connection URI
    if readonly:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
    finally:
        conn.close()


def init_database(db_path: Optional[str] = None) -> bool:
    """
    Initialize database schema.

    Parameters:
        db_path: Path to database file. If None, uses environment variable or default.

    Returns:
        True if successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            logging.info(f"Database initialized at {db_path or get_db_path()}")
            return True
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        return False


def normalize_topic_name(name: str) -> str:
    """
    Normalize topic name for consistent matching.

    Parameters:
        name: The topic name to normalize.

    Returns:
        Lowercase, trimmed topic name.
    """
    return name.lower().strip()


def get_canonical_topic_name(name: str, conn: sqlite3.Connection) -> str:
    """
    Return canonical name if alias exists, otherwise return normalized name.

    Parameters:
        name: The topic name to look up.
        conn: Database connection.

    Returns:
        Canonical topic name or normalized input name.
    """
    normalized = normalize_topic_name(name)
    cursor = conn.execute(
        "SELECT canonical_name FROM topic_aliases WHERE alias = ?",
        (normalized,)
    )
    row = cursor.fetchone()
    if row:
        return row["canonical_name"]
    return normalized


def save_summary_to_db(summary: Dict[str, Any], db_path: Optional[str] = None) -> Optional[int]:
    """
    Save a summary and its topics/articles to the database.

    Parameters:
        summary: Summary dictionary with 'topics' and optionally 'generated_at'.
        db_path: Path to database file. If None, uses environment variable or default.

    Returns:
        The summary ID if successful, None otherwise.
    """
    if not summary:
        logging.warning("Empty summary provided, nothing to save")
        return None

    # Get or set generated_at timestamp
    generated_at = summary.get("generated_at", datetime.now().isoformat())

    # Get topics list
    topics = summary.get("topics", [])

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Insert summary record
            cursor.execute(
                "INSERT INTO summaries (generated_at, raw_json) VALUES (?, ?)",
                (generated_at, json.dumps(summary))
            )
            summary_id = cursor.lastrowid

            # Insert topics and their articles
            for topic_data in topics:
                topic_name = topic_data.get("topic", "Unknown Topic")
                canonical_name = get_canonical_topic_name(topic_name, conn)
                summary_text = topic_data.get("summary", "")
                articles = topic_data.get("articles", [])

                cursor.execute(
                    """INSERT INTO topics
                       (summary_id, name, normalized_name, summary_text, article_count)
                       VALUES (?, ?, ?, ?, ?)""",
                    (summary_id, topic_name, canonical_name, summary_text, len(articles))
                )
                topic_id = cursor.lastrowid

                # Insert articles for this topic
                for article in articles:
                    cursor.execute(
                        """INSERT INTO articles
                           (topic_id, title, link, source, published_date)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            topic_id,
                            article.get("title", ""),
                            article.get("link", ""),
                            article.get("source"),
                            article.get("published_date") or article.get("published")
                        )
                    )

            conn.commit()
            logging.info(f"Saved summary {summary_id} with {len(topics)} topics to database")
            return summary_id

    except Exception as e:
        logging.error(f"Failed to save summary to database: {e}")
        return None


def get_summary_count(db_path: Optional[str] = None) -> int:
    """
    Get total number of summaries in database.

    Parameters:
        db_path: Path to database file.

    Returns:
        Number of summaries stored.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM summaries")
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception as e:
        logging.error(f"Failed to get summary count: {e}")
        return 0


def get_topic_count(db_path: Optional[str] = None) -> int:
    """
    Get total number of topics in database.

    Parameters:
        db_path: Path to database file.

    Returns:
        Number of topics stored.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM topics")
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception as e:
        logging.error(f"Failed to get topic count: {e}")
        return 0


def get_article_count(db_path: Optional[str] = None) -> int:
    """
    Get total number of articles in database.

    Parameters:
        db_path: Path to database file.

    Returns:
        Number of articles stored.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM articles")
            row = cursor.fetchone()
            return row["count"] if row else 0
    except Exception as e:
        logging.error(f"Failed to get article count: {e}")
        return 0


def get_recent_summaries(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get most recent summaries.

    Parameters:
        limit: Maximum number of summaries to return.
        db_path: Path to database file.

    Returns:
        List of summary dictionaries with id, generated_at, and topic_count.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute(
                """SELECT s.id, s.generated_at, s.created_at,
                          COUNT(t.id) as topic_count
                   FROM summaries s
                   LEFT JOIN topics t ON s.id = t.summary_id
                   GROUP BY s.id
                   ORDER BY s.generated_at DESC
                   LIMIT ?""",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Failed to get recent summaries: {e}")
        return []


def get_summary_by_id(summary_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get a summary by ID with all its topics and articles.

    Parameters:
        summary_id: The summary ID to retrieve.
        db_path: Path to database file.

    Returns:
        Full summary dictionary or None if not found.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            # Get summary
            cursor = conn.execute(
                "SELECT id, generated_at, raw_json FROM summaries WHERE id = ?",
                (summary_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            # Return the original JSON (preserves exact structure)
            return json.loads(row["raw_json"])

    except Exception as e:
        logging.error(f"Failed to get summary {summary_id}: {e}")
        return None


def import_json_file(filepath: str, db_path: Optional[str] = None) -> Optional[int]:
    """
    Import a JSON summary file into the database.

    Parameters:
        filepath: Path to JSON file to import.
        db_path: Path to database file.

    Returns:
        The summary ID if successful, None otherwise.
    """
    try:
        with open(filepath, 'r') as f:
            summary = json.load(f)

        # Use file modification time if no generated_at
        if 'generated_at' not in summary:
            mtime = os.path.getmtime(filepath)
            summary['generated_at'] = datetime.fromtimestamp(mtime).isoformat()

        summary_id = save_summary_to_db(summary, db_path)
        if summary_id:
            logging.info(f"Imported {filepath} as summary {summary_id}")
        return summary_id

    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {filepath}: {e}")
        return None
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except Exception as e:
        logging.error(f"Failed to import {filepath}: {e}")
        return None


# =============================================================================
# Query Functions (Sprint 2)
# =============================================================================

def topic_counts_by_period(
    start_date: str,
    end_date: str,
    period: str = "week",
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Count stories by topic over a time period.

    Parameters:
        start_date: Start date (ISO format: YYYY-MM-DD)
        end_date: End date (ISO format: YYYY-MM-DD)
        period: Aggregation period - 'day', 'week', or 'month'
        db_path: Path to database file.

    Returns:
        List of dicts with period, topic, story_count, and articles.
    """
    # SQLite strftime format for period grouping
    period_formats = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m"
    }

    if period not in period_formats:
        logging.error(f"Invalid period: {period}. Use 'day', 'week', or 'month'")
        return []

    period_format = period_formats[period]

    try:
        with get_db_connection(db_path, readonly=True) as conn:
            # Get topic counts grouped by period
            cursor = conn.execute(
                f"""SELECT
                        strftime('{period_format}', s.generated_at) as period,
                        t.normalized_name as topic,
                        COUNT(DISTINCT t.id) as story_count,
                        SUM(t.article_count) as article_count
                    FROM topics t
                    JOIN summaries s ON t.summary_id = s.id
                    WHERE date(s.generated_at) BETWEEN date(?) AND date(?)
                    GROUP BY period, t.normalized_name
                    ORDER BY period, story_count DESC""",
                (start_date, end_date)
            )

            results = []
            for row in cursor.fetchall():
                # Get sample articles for this topic in this period
                article_cursor = conn.execute(
                    f"""SELECT DISTINCT a.title, a.link
                        FROM articles a
                        JOIN topics t ON a.topic_id = t.id
                        JOIN summaries s ON t.summary_id = s.id
                        WHERE t.normalized_name = ?
                          AND strftime('{period_format}', s.generated_at) = ?
                        LIMIT 5""",
                    (row["topic"], row["period"])
                )
                articles = [dict(a) for a in article_cursor.fetchall()]

                results.append({
                    "period": row["period"],
                    "topic": row["topic"],
                    "story_count": row["story_count"],
                    "article_count": row["article_count"],
                    "articles": articles
                })

            return results

    except Exception as e:
        logging.error(f"Failed to get topic counts by period: {e}")
        return []


def top_topics_comparison(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    limit: int = 10,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare top topics between two time periods.

    Parameters:
        period1_start: Start date of first period (ISO format)
        period1_end: End date of first period (ISO format)
        period2_start: Start date of second period (ISO format)
        period2_end: End date of second period (ISO format)
        limit: Number of top topics to return per period
        db_path: Path to database file.

    Returns:
        Dict with period1_topics, period2_topics, and comparison stats.
    """
    def get_top_topics(conn, start, end, limit):
        cursor = conn.execute(
            """SELECT
                    t.normalized_name as topic,
                    COUNT(DISTINCT t.id) as story_count,
                    SUM(t.article_count) as article_count
                FROM topics t
                JOIN summaries s ON t.summary_id = s.id
                WHERE date(s.generated_at) BETWEEN date(?) AND date(?)
                GROUP BY t.normalized_name
                ORDER BY story_count DESC
                LIMIT ?""",
            (start, end, limit)
        )
        results = []
        for row in cursor.fetchall():
            # Get sample articles
            article_cursor = conn.execute(
                """SELECT DISTINCT a.title, a.link
                    FROM articles a
                    JOIN topics t ON a.topic_id = t.id
                    JOIN summaries s ON t.summary_id = s.id
                    WHERE t.normalized_name = ?
                      AND date(s.generated_at) BETWEEN date(?) AND date(?)
                    LIMIT 3""",
                (row["topic"], start, end)
            )
            articles = [dict(a) for a in article_cursor.fetchall()]

            results.append({
                "topic": row["topic"],
                "story_count": row["story_count"],
                "article_count": row["article_count"],
                "articles": articles
            })
        return results

    try:
        with get_db_connection(db_path, readonly=True) as conn:
            period1_topics = get_top_topics(conn, period1_start, period1_end, limit)
            period2_topics = get_top_topics(conn, period2_start, period2_end, limit)

            # Calculate comparison stats
            p1_topic_names = {t["topic"] for t in period1_topics}
            p2_topic_names = {t["topic"] for t in period2_topics}

            common_topics = p1_topic_names & p2_topic_names
            new_in_p2 = p2_topic_names - p1_topic_names
            dropped_from_p1 = p1_topic_names - p2_topic_names

            return {
                "period1": {
                    "start": period1_start,
                    "end": period1_end,
                    "topics": period1_topics
                },
                "period2": {
                    "start": period2_start,
                    "end": period2_end,
                    "topics": period2_topics
                },
                "comparison": {
                    "common_topics": list(common_topics),
                    "new_in_period2": list(new_in_p2),
                    "dropped_from_period1": list(dropped_from_p1)
                }
            }

    except Exception as e:
        logging.error(f"Failed to compare topics: {e}")
        return {"period1": {"topics": []}, "period2": {"topics": []}, "comparison": {}}


def topic_search(
    query: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for topics by name with optional date filtering.

    Parameters:
        query: Search string (case-insensitive, partial match)
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        limit: Maximum number of results
        db_path: Path to database file.

    Returns:
        List of matching topics with their articles.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            # Build query with optional date filters
            sql = """SELECT
                        t.id,
                        t.name as topic_name,
                        t.normalized_name,
                        t.summary_text,
                        t.article_count,
                        s.generated_at,
                        s.id as summary_id
                    FROM topics t
                    JOIN summaries s ON t.summary_id = s.id
                    WHERE t.normalized_name LIKE ?"""

            params = [f"%{query.lower()}%"]

            if start_date:
                sql += " AND date(s.generated_at) >= date(?)"
                params.append(start_date)

            if end_date:
                sql += " AND date(s.generated_at) <= date(?)"
                params.append(end_date)

            sql += " ORDER BY s.generated_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                # Get articles for this topic
                article_cursor = conn.execute(
                    """SELECT title, link, source, published_date
                        FROM articles
                        WHERE topic_id = ?""",
                    (row["id"],)
                )
                articles = [dict(a) for a in article_cursor.fetchall()]

                results.append({
                    "topic_name": row["topic_name"],
                    "normalized_name": row["normalized_name"],
                    "summary_text": row["summary_text"],
                    "article_count": row["article_count"],
                    "generated_at": row["generated_at"],
                    "summary_id": row["summary_id"],
                    "articles": articles
                })

            return results

    except Exception as e:
        logging.error(f"Failed to search topics: {e}")
        return []


def get_date_range(db_path: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Get the date range of data in the database.

    Parameters:
        db_path: Path to database file.

    Returns:
        Dict with 'earliest' and 'latest' dates, or None if no data.
    """
    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute(
                """SELECT
                        MIN(date(generated_at)) as earliest,
                        MAX(date(generated_at)) as latest
                    FROM summaries"""
            )
            row = cursor.fetchone()
            if row:
                return {
                    "earliest": row["earliest"],
                    "latest": row["latest"]
                }
            return {"earliest": None, "latest": None}

    except Exception as e:
        logging.error(f"Failed to get date range: {e}")
        return {"earliest": None, "latest": None}
