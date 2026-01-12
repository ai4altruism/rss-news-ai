# Sprint 13 Summary: Semantic Deduplication

**Completed:** 2026-01-12
**Version:** v2.2

## Overview

Sprint 13 implements embedding-based semantic deduplication to filter out duplicate stories that cover the same news event but come from different sources with different URLs.

## Problem Solved

The existing URL-based deduplication missed:
- Same story reported by multiple outlets (TechCrunch, Verge, Wired all covering the same announcement)
- Updated/rewritten stories with new URLs
- Similar coverage of the same news event

This resulted in repetitive content in hourly summaries.

## Solution

Use OpenAI's `text-embedding-3-small` model to generate semantic fingerprints of articles, then compare new articles against recent embeddings using cosine similarity.

## Key Deliverables

| File | Purpose |
|------|---------|
| `src/embeddings.py` | Core embedding generation and similarity comparison |
| `src/history_db.py` | Added `article_embeddings` table and query functions |
| `src/pricing.py` | Added embedding pricing ($0.02/1M tokens) |
| `src/main.py` | Integrated semantic dedup into pipeline |
| `tests/test_embeddings.py` | 36 unit tests |

## Configuration

```bash
ENABLE_SEMANTIC_DEDUP=true      # Enable/disable (default: true)
SIMILARITY_THRESHOLD=0.85       # 0.0-1.0, higher = stricter
DEDUP_LOOKBACK_DAYS=7          # Days to compare against
EMBEDDING_RETENTION_DAYS=30     # Days to retain embeddings
```

Command line: `--no-semantic-dedup` to disable

## Pipeline Integration

```
RSS Feeds → URL Dedup → Semantic Dedup → LLM Filter → Summarize → Output
                              ↑
                        (new in v2.2)
```

## Cost Impact

Minimal:
- `text-embedding-3-small`: $0.02 per million tokens
- ~60 tokens per article (title + lead sentence)
- 100 articles/day: ~$0.00012/day (~$0.004/month)

## First Production Run

```
401 articles fetched
 → 10 duplicates filtered by semantic dedup
 → 391 unique articles
 → 5 articles after LLM filtering
 → Published to Slack
```

## Test Results

- 36 new tests for embeddings module
- **321 total tests passing**

## Database Schema

```sql
CREATE TABLE article_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    lead_text TEXT,
    embedding BLOB NOT NULL,
    embedding_model TEXT DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Migration

For existing deployments:
```bash
python src/history_cli.py init --force
```

This creates the new table without affecting existing data.
