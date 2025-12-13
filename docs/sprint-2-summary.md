# Sprint 2 Summary: CLI Query Interface

**Status**: Complete
**Branch**: `feature/sprint-2-cli-queries`
**Completed**: 2025-12-13

## Goal
Working command-line queries against historical data with trend analysis and search capabilities.

## Deliverables

### New Query Functions (history_db.py)
| Function | Purpose |
|----------|---------|
| `topic_counts_by_period()` | Count stories by topic over time (day/week/month) |
| `top_topics_comparison()` | Compare top topics between two periods |
| `topic_search()` | Search topics by name with date filtering |
| `get_date_range()` | Get earliest/latest dates in database |

### New CLI Commands
| Command | Description |
|---------|-------------|
| `trends` | Show topic trends over time |
| `compare` | Compare topics between two periods |
| `search` | Search for topics by name |

### Output Formats
- **Table** (default): Human-readable formatted output
- **JSON**: Machine-readable, pipe-able output

## CLI Usage Examples

```bash
# Show topic trends by week
python src/history_cli.py trends --start 2024-01-01 --end 2024-06-30 --period week

# Show monthly trends as JSON
python src/history_cli.py trends --start 2024-01-01 --end 2024-12-31 --period month --format json

# Compare Q1 vs Q2 topics
python src/history_cli.py compare --period1 2024-01-01 2024-03-31 --period2 2024-04-01 2024-06-30

# Search for OpenAI articles
python src/history_cli.py search "OpenAI"

# Search with date filter
python src/history_cli.py search "Google" --start 2024-06-01 --end 2024-12-31

# Get JSON output for scripting
python src/history_cli.py search "AI" --format json
```

## Test Results

```
39 passed in 0.90s

Sprint 1 Tests (22):
- TestInitDatabase (3 tests)
- TestSaveSummary (7 tests)
- TestTopicNormalization (3 tests)
- TestQueryFunctions (3 tests)
- TestImportJson (4 tests)
- TestDatabaseIntegrity (2 tests)

Sprint 2 Tests (17):
- TestTopicCountsByPeriod (6 tests)
- TestTopTopicsComparison (3 tests)
- TestTopicSearch (6 tests)
- TestGetDateRange (2 tests)
```

## Key Features

### Trends Command
- Aggregate by day, week, or month
- Shows story count and article count per topic
- Includes sample article titles
- Groups output by period

### Compare Command
- Compare any two date ranges
- Shows top N topics per period (default: 10)
- Identifies:
  - Common topics (in both periods)
  - New topics (only in period 2)
  - Dropped topics (only in period 1)
- Includes sample articles for each topic

### Search Command
- Case-insensitive partial matching
- Optional date range filtering
- Returns:
  - Topic name and summary text
  - Article titles and URLs
  - Date generated

### Output Formatting
- Table format with smart column widths
- JSON format for piping/scripting
- Truncation for long text fields
- All outputs include article URLs

## Files Modified

| File | Changes |
|------|---------|
| `src/history_db.py` | Added 4 query functions (~300 lines) |
| `src/history_cli.py` | Added 3 commands, output formatting (~200 lines) |
| `tests/test_history_db.py` | Added 17 tests for query functions |

## Next Sprint

**Sprint 3: LLM Query Engine** - Add natural language query support with function calling.
