# Sprint 1 Summary: Database Foundation & Data Capture

**Status**: Complete
**Branch**: `feature/sprint-1-database-foundation`
**Completed**: 2025-12-13

## Goal
Start persisting data immediately so history begins accumulating.

## Deliverables

### Files Created
| File | Purpose |
|------|---------|
| `src/history_db.py` | SQLite database operations - schema, save, query |
| `src/history_cli.py` | CLI tool with `init`, `import`, `stats` commands |
| `tests/test_history_db.py` | 22 unit tests for database operations |

### Files Modified
| File | Change |
|------|--------|
| `src/main.py` | Added `save_summary_to_db()` call after summarization |
| `.env.example` | Added `HISTORY_DB_PATH` configuration |

## Database Schema

```sql
summaries (id, generated_at, raw_json, created_at)
    └── topics (id, summary_id, name, normalized_name, summary_text, article_count)
            └── articles (id, topic_id, title, link, source, published_date)

topic_aliases (id, canonical_name, alias, created_at)
```

## CLI Usage

```bash
# Initialize database
python src/history_cli.py init

# Import existing JSON files
python src/history_cli.py import data/latest_summary.json
python src/history_cli.py import backups/*.json

# Show statistics
python src/history_cli.py stats
```

## Test Results

```
22 passed in 0.44s

TestInitDatabase (3 tests)
TestSaveSummary (7 tests)
TestTopicNormalization (3 tests)
TestQueryFunctions (3 tests)
TestImportJson (4 tests)
TestDatabaseIntegrity (2 tests)
```

## Integration Notes

- Database save is **non-fatal**: if it fails, the main pipeline continues
- Database auto-initializes on first save (creates `data/` directory if needed)
- Topic names are normalized (lowercase, trimmed) for consistent querying
- Original article URLs are preserved in the `articles` table

## Next Sprint

**Sprint 2: CLI Query Interface** - Add query commands for trends, comparison, and search.
