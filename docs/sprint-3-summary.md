# Sprint 3 Summary: LLM Query Engine

**Status**: Complete
**Branch**: `feature/sprint-3-llm-query-engine`
**Completed**: 2025-12-13

## Goal
Natural language queries powered by LLM with function calling and SQL safety guardrails.

## Deliverables

### New Module: query_engine.py (~400 lines)
| Component | Purpose |
|-----------|---------|
| `QueryEngine` class | LLM-powered query classification and execution |
| `validate_sql()` | SQL safety validation (SELECT-only, forbidden keywords) |
| `execute_safe_sql()` | Read-only SQL execution with guardrails |
| `query()` | Convenience function for natural language queries |

### New Environment Variable
| Variable | Purpose | Default |
|----------|---------|---------|
| `QUERY_MODEL` | LLM model for natural language query classification | `gpt-4o-mini` |

This allows separate model configuration for querying vs. filtering/summarizing.

### Query Classification
The LLM classifies natural language queries into one of four functions:

| Function | Description | Example Query |
|----------|-------------|---------------|
| `get_trends` | Topic trends over time | "What were hot topics last month?" |
| `compare_periods` | Compare two time periods | "Compare Q1 vs Q2 themes" |
| `search_topics` | Search for specific topics | "Find articles about OpenAI" |
| `execute_sql` | Custom SQL for complex queries | "Which topic has the most articles?" |

### SQL Guardrails
Protects against SQL injection and dangerous queries:

| Protection | Description |
|------------|-------------|
| SELECT-only | Only SELECT queries allowed |
| Forbidden keywords | Blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, etc. |
| Multiple statements | Blocks semicolon-separated statements |
| Comment injection | Blocks -- and /* */ comments |
| Read-only connection | Database opened in read-only mode |

### New CLI Command
```bash
# Natural language query
python src/history_cli.py query "What were the top themes in November?"
python src/history_cli.py query "Compare Q1 vs Q2"
python src/history_cli.py query "Find articles about OpenAI"

# JSON output for scripting
python src/history_cli.py query "Show trends" --format json
```

### Response Formatting
- Natural language responses with article URLs
- Structured data available via JSON output
- Includes sample articles with links for all query types

## Test Results

```
85 passed in 3.08s

Sprint 1-2 Tests (39):
- Database operations, query functions, CLI commands

Sprint 3 Tests (46):
- TestSqlGuardrails (14 tests)
  - Allows valid SELECT queries
  - Blocks DELETE, DROP, UPDATE, INSERT, TRUNCATE, ALTER, CREATE
  - Blocks multiple statements, comments
  - Blocks all forbidden keywords

- TestExecuteSafeSql (4 tests)
  - Valid query execution
  - Rejects invalid queries
  - Handles SQL errors

- TestQueryClassification (6 tests)
  - Classifies trends queries
  - Classifies comparison queries
  - Classifies search queries
  - Classifies complex queries to SQL
  - Handles malformed responses
  - Handles API errors

- TestResponseFormatting (2 tests)
  - Search includes article URLs
  - Trends includes article URLs

- TestQueryEngineInit (3 tests)
  - Requires API key
  - Accepts API key parameter
  - Reads from environment

- TestQueryFunction (1 test)
  - Convenience function works

- TestCliBasics (4 tests)
- TestCliQueryCommands (6 tests)
- TestCliNaturalLanguageQuery (2 tests)
- TestCliQueryWithMockedApi (2 tests)
- TestCliErrorHandling (2 tests)
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  User Query     │────►│  Query Engine    │
│  (natural lang) │     │  classify_and_   │
└─────────────────┘     │  execute()       │
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │get_trends │ │search_    │ │execute_   │
            │           │ │topics     │ │safe_sql   │
            └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                  │             │             │
                  ▼             ▼             ▼
            ┌─────────────────────────────────────┐
            │         history_db.py               │
            │   (pre-built query functions)       │
            └──────────────────┬──────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  SQLite DB   │
                        │ (read-only)  │
                        └──────────────┘
```

## Files Modified/Created

| File | Changes |
|------|---------|
| `src/query_engine.py` | **New** - LLM query engine (~400 lines) |
| `src/history_cli.py` | Added `query` command and import (~50 lines) |
| `.env.example` | Added `QUERY_MODEL` environment variable |
| `tests/test_query_engine.py` | **New** - 30 query engine tests |
| `tests/test_history_cli.py` | **New** - 16 CLI integration tests |

## Key Features

### Natural Language Understanding
- Interprets relative dates ("last month", "Q1 2024")
- Extracts search terms from queries
- Chooses appropriate function based on intent

### Safety First
- All SQL validated before execution
- Database opened read-only for custom queries
- Comprehensive forbidden keyword list
- No SQL injection possible

### Rich Responses
- Natural language summaries
- Article URLs always included
- Both human-readable and JSON formats

## Usage Example

```python
from query_engine import QueryEngine

engine = QueryEngine()

# Natural language query
result = engine.classify_and_execute("What were the top AI topics in January 2024?")

if result["success"]:
    print(result["response"])
    # Access structured data
    for item in result["data"]:
        print(f"- {item['topic']}: {item['story_count']} stories")
```

## Configuration

Add to your `.env` file:
```bash
# Model for natural language query classification
QUERY_MODEL=gpt-4o-mini
```

## Next Sprint

**Sprint 4: Web Interface & API** - Add browser-based query interface and REST API endpoints.
