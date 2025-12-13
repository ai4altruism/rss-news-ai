# Sprint 4 Summary: Web Interface & API

**Status**: Complete
**Branch**: `feature/sprint-4-web-interface`
**Completed**: 2025-12-13

## Goal
Browser-based query interface and REST API endpoints for historical news data.

## Deliverables

### New API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/history` | GET | History query interface page |
| `/api/history/stats` | GET | Database statistics (summaries, topics, articles, date range) |
| `/api/trends` | GET | Topic trends over time with period aggregation |
| `/api/compare` | GET | Compare top topics between two time periods |
| `/api/topics` | GET | Search topics by name with optional date filtering |
| `/api/query` | POST | Natural language query (requires OpenAI API key) |

### New Templates
| File | Purpose |
|------|---------|
| `templates/history.html` | Chat interface for natural language queries |
| `templates/error.html` | Error page template |

### Docker Volume Configuration
Database persistence outside the container for easy backup and monitoring:

```bash
# Run with volume mounts
docker run -d \
  -v /var/lib/rss-news-ai/data:/app/data \
  -v /var/lib/rss-news-ai/logs:/app/logs \
  -p 5002:5002 \
  --env-file .env \
  rss-news-ai
```

The Dockerfile sets `HISTORY_DB_PATH=/app/data/history.db` by default.

## API Usage Examples

### Get Database Statistics
```bash
curl http://localhost:5002/api/history/stats
```

### Get Topic Trends
```bash
curl "http://localhost:5002/api/trends?start=2024-01-01&end=2024-12-31&period=month"
```

### Compare Two Periods
```bash
curl "http://localhost:5002/api/compare?p1_start=2024-01-01&p1_end=2024-03-31&p2_start=2024-04-01&p2_end=2024-06-30"
```

### Search Topics
```bash
curl "http://localhost:5002/api/topics?search=OpenAI&limit=10"
```

### Natural Language Query
```bash
curl -X POST http://localhost:5002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What were the top topics last month?"}'
```

## Test Results

```
106 passed in 3.82s

Sprint 1-2 Tests (39)
Sprint 3 Tests (46)
Sprint 4 Tests (21):
- TestHistoryPage (2 tests)
  - History page renders
  - Shows database stats

- TestStatsApi (1 test)
  - Returns database statistics

- TestTrendsApi (4 tests)
  - Returns trend data
  - Requires date params
  - Validates period param
  - Respects date filters

- TestCompareApi (2 tests)
  - Returns comparison data
  - Requires all params

- TestTopicsSearchApi (4 tests)
  - Returns search results
  - Requires search term
  - Handles no results
  - Includes article URLs

- TestQueryApi (5 tests)
  - Requires request body
  - Requires query field
  - Requires API key
  - Success with mocked engine
  - Handles errors gracefully

- TestErrorHandling (1 test)
- TestHomePage (2 tests)
```

## Web Interface Features

### History Page (`/history`)
- Database statistics dashboard (summaries, topics, articles, date range)
- Chat-style natural language query interface
- Quick query buttons for common questions
- Interactive Chart.js visualization for trends
- Article links clickable to original sources
- JSON output support for API responses

### Design
- Consistent styling with existing dashboard
- Gradient header with navigation
- Responsive Bootstrap 5 layout
- Loading indicator during queries
- Error message display

## Files Modified/Created

| File | Changes |
|------|---------|
| `src/web_dashboard.py` | Added 6 API endpoints (~180 lines) |
| `src/templates/history.html` | **New** - Chat interface (~350 lines) |
| `src/templates/error.html` | **New** - Error page template |
| `Dockerfile` | Added volume mount documentation, HISTORY_DB_PATH |
| `tests/test_history_api.py` | **New** - 21 API tests |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser                               │
├─────────────────────────────────────────────────────────────┤
│  /                    │  /history                           │
│  Dashboard            │  Query Interface                    │
│  (latest summary)     │  (chat + visualization)             │
└───────────┬───────────┴───────────────┬─────────────────────┘
            │                           │
            ▼                           ▼
┌───────────────────────────────────────────────────────────────┐
│                    Flask (web_dashboard.py)                    │
├───────────────────────────────────────────────────────────────┤
│  /api/summary      │  /api/trends      │  /api/query          │
│  /api/history/stats│  /api/compare     │  (NL queries)        │
│                    │  /api/topics      │                      │
└─────────┬──────────┴────────┬─────────┴──────────┬───────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ latest_summary  │  │   history_db    │  │  query_engine   │
│    .json        │  │   (SQLite)      │  │   (LLM)         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ /app/data/      │  ← Volume Mount
                     │ history.db      │
                     └─────────────────┘
```

## Docker Deployment

### Build
```bash
docker build -t rss-news-ai .
```

### Run with Volume Mounts
```bash
# Create host directories
mkdir -p /var/lib/rss-news-ai/data
mkdir -p /var/lib/rss-news-ai/logs

# Run container with volumes
docker run -d \
  --name rss-news-ai \
  -v /var/lib/rss-news-ai/data:/app/data \
  -v /var/lib/rss-news-ai/logs:/app/logs \
  -p 5002:5002 \
  --env-file .env \
  rss-news-ai --output slack web
```

### Access Database from Host
```bash
# View database
sqlite3 /var/lib/rss-news-ai/data/history.db

# Backup database
cp /var/lib/rss-news-ai/data/history.db /backup/history_$(date +%Y%m%d).db

# Monitor size
ls -lh /var/lib/rss-news-ai/data/history.db
```

## Next Sprint

**Sprint 5: Polish & Production Readiness** - Topic alias management, advanced visualizations, CSV/JSON export, and documentation.
