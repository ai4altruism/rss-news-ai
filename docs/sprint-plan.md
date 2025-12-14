# Historical Storage & Trend Analysis - Sprint Plan

## Project Goal
Add persistent storage of summaries and LLM-powered trend analysis to enable queries like:
- "Plot stories by theme over 6 months"
- "Compare Q1 vs Q2 2025 themes"
- "What were big AI announcements in October?"
- "Show me all OpenAI articles from last month" (with original URLs)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  main.py    │────►│ history_db.py│────►│ data/history.db │
│ (existing)  │     │   (new)      │     │   (SQLite)      │
└─────────────┘     └──────────────┘     └─────────────────┘
                           ▲
                           │
┌─────────────┐     ┌──────────────┐
│   CLI /     │────►│query_engine  │
│   Web API   │     │   (new)      │
└─────────────┘     └──────────────┘
```

## Database Schema (SQLite)

```sql
-- Stores each run's complete output
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY,
    generated_at TIMESTAMP NOT NULL,
    raw_json TEXT NOT NULL
);

-- Normalized topics for efficient querying
CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    summary_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,  -- lowercase for matching variations
    summary_text TEXT,
    article_count INTEGER DEFAULT 0,
    FOREIGN KEY (summary_id) REFERENCES summaries(id)
);

-- Articles linked to topics (preserves original URLs for retrieval)
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,           -- Original news story URL (always returned in queries)
    source TEXT,                  -- RSS feed source name
    published_date TIMESTAMP,     -- Original publication date
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

-- Handle topic name variations ("OpenAI" vs "OpenAI News")
CREATE TABLE topic_aliases (
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE
);
```

## Git Workflow (per sprint)

Each sprint follows this workflow:
1. Create feature branch: `git checkout -b feature/sprint-N-description`
2. Implement stories with tests
3. Run all tests: `pytest tests/`
4. Commit with descriptive message
5. Push to GitHub: `git push -u origin feature/sprint-N-description`
6. Create PR for review

---

## Sprint 0: Project Setup (Pre-Sprint)

**Goal**: Set up documentation and testing infrastructure

**Tasks**:
1. Create `docs/` directory and `docs/sprint-plan.md`
2. Set up `tests/` directory with pytest configuration
3. Add `pytest` to `requirements.txt`
4. Create `tests/conftest.py` with shared fixtures

**Git**: Branch `feature/testing-infrastructure`

---

## Sprint 1: Database Foundation & Data Capture

**Goal**: Start persisting data immediately so history begins accumulating

**Stories**:
1. Create `history_db.py` module
   - SQLite schema creation (summaries, topics, articles, topic_aliases tables)
   - `init_database()` function
   - `save_summary_to_db()` function (extracts/normalizes topics, preserves article URLs)

2. Integrate with main pipeline
   - Modify `main.py` to call `save_summary_to_db()` after summarization
   - Add `HISTORY_DB_PATH` to `.env.example`
   - Error handling (DB failure shouldn't break existing flow)

3. Basic CLI scaffolding
   - Create `history_cli.py` with `init` and `import` commands
   - Import command for backfilling existing JSON files (if any)

### Testing (Sprint 1)

**File**: `tests/test_history_db.py`

| Test Name | Description |
|-----------|-------------|
| `test_init_database_creates_tables()` | Verify schema creation |
| `test_save_summary_creates_records()` | Verify data insertion |
| `test_save_summary_normalizes_topics()` | Verify topic normalization |
| `test_save_summary_preserves_article_urls()` | Verify URLs stored correctly |
| `test_save_summary_handles_empty_topics()` | Edge case handling |
| `test_db_failure_doesnt_break_main_pipeline()` | Integration test |

**Run Tests**: `pytest tests/test_history_db.py -v`

**Git**: Branch `feature/sprint-1-database-foundation`

**Deliverables**:
- Every run saves to `data/history.db`
- `python src/history_cli.py init` creates database
- `python src/history_cli.py import <files>` backfills history
- All tests passing

---

## Sprint 2: CLI Query Interface

**Goal**: Working command-line queries against historical data

**Stories**:
1. Pre-built query functions
   - `topic_counts_by_period(start, end, period)` - stories by theme over time
   - `top_topics_comparison(range1, range2)` - compare periods
   - `topic_search(name, start, end)` - find articles by topic
   - `recent_summaries(limit)` - latest N summaries
   - All queries return article URLs

2. CLI query commands
   - `python src/history_cli.py trends --start X --end Y --period week`
   - `python src/history_cli.py compare --period1 X Y --period2 X Y`
   - `python src/history_cli.py search "OpenAI" --start X --end Y`

3. Output formatting
   - Table format (default, human-readable)
   - JSON format (for piping/scripting)
   - Include article URLs in all outputs

### Testing (Sprint 2)

**File**: `tests/test_history_db.py` (additions)

| Test Name | Description |
|-----------|-------------|
| `test_topic_counts_by_period_daily()` | Verify daily aggregation |
| `test_topic_counts_by_period_weekly()` | Verify weekly aggregation |
| `test_topic_counts_by_period_monthly()` | Verify monthly aggregation |
| `test_top_topics_comparison()` | Verify period comparison |
| `test_topic_search_returns_urls()` | Verify URLs in results |
| `test_topic_search_date_filtering()` | Verify date range works |

**File**: `tests/test_history_cli.py` (integration)

| Test Name | Description |
|-----------|-------------|
| `test_cli_trends_command()` | End-to-end trends command |
| `test_cli_compare_command()` | End-to-end compare command |
| `test_cli_search_command()` | End-to-end search command |
| `test_cli_json_output_format()` | Verify JSON formatting |
| `test_cli_table_output_format()` | Verify table formatting |

**Run Tests**: `pytest tests/test_history_db.py tests/test_history_cli.py -v`

**Git**: Branch `feature/sprint-2-cli-queries`

**Deliverables**:
- Working CLI for structured queries
- Trend data with article links
- Both table and JSON output formats
- All tests passing

---

## Sprint 3: LLM Query Engine

**Goal**: Natural language queries powered by LLM

**Stories**:
1. Create `query_engine.py` module
   - Query classifier (maps natural language to pre-built function or custom SQL)
   - Function-calling interface for pre-built queries
   - Response formatting (natural language summaries with article links)

2. SQL generation with guardrails
   - Schema-aware prompt for SQL generation
   - Safety validation (SELECT-only, forbidden keywords)
   - Read-only database connection wrapper

3. Integrate with CLI
   - `python src/history_cli.py query "What were the top themes in November?"`
   - Natural language responses with supporting data
   - Article URLs included in responses

### Testing (Sprint 3)

**File**: `tests/test_query_engine.py`

| Test Name | Description |
|-----------|-------------|
| `test_classify_trends_query()` | Maps "show trends" to trends function |
| `test_classify_comparison_query()` | Maps "compare Q1 vs Q2" to compare function |
| `test_classify_search_query()` | Maps "articles about X" to search function |
| `test_classify_complex_query()` | Recognizes need for custom SQL |
| `test_sql_guardrails_blocks_delete()` | Rejects DELETE statements |
| `test_sql_guardrails_blocks_drop()` | Rejects DROP statements |
| `test_sql_guardrails_blocks_update()` | Rejects UPDATE statements |
| `test_sql_guardrails_allows_select()` | Allows valid SELECT |
| `test_response_includes_article_urls()` | Verify URLs in formatted response |

**File**: `tests/test_history_cli.py` (additions)

| Test Name | Description |
|-----------|-------------|
| `test_cli_query_natural_language()` | End-to-end NL query |

**Run Tests**: `pytest tests/test_query_engine.py tests/test_history_cli.py -v`

**Git**: Branch `feature/sprint-3-llm-query-engine`

**Deliverables**:
- `python src/history_cli.py query "<natural language>"` works
- LLM interprets queries and returns analysis
- Safety guardrails prevent harmful SQL
- All tests passing

---

## Sprint 4: Web Interface & API

**Goal**: Browser-based query interface and REST API

**Stories**:
1. API endpoints in `web_dashboard.py`
   - `POST /api/query` - natural language query
   - `GET /api/trends?start=X&end=Y&period=Z` - trend data
   - `GET /api/topics?search=X` - topic search with articles
   - All endpoints return article URLs

2. Chat interface page
   - Create `templates/history.html` with chat UI
   - Query input, response display, conversation history
   - Article links clickable to original sources

3. Basic visualization
   - Chart.js integration for trend charts
   - Topic frequency over time visualization
   - Responsive design matching existing dashboard

### Testing (Sprint 4)

**File**: `tests/test_history_api.py`

| Test Name | Description |
|-----------|-------------|
| `test_api_query_endpoint_success()` | POST /api/query returns results |
| `test_api_query_endpoint_empty_query()` | Handles missing query param |
| `test_api_query_endpoint_error_handling()` | Handles LLM errors gracefully |
| `test_api_trends_endpoint()` | GET /api/trends returns data |
| `test_api_trends_endpoint_date_params()` | Validates date parameters |
| `test_api_topics_search_endpoint()` | GET /api/topics?search=X works |
| `test_api_responses_include_urls()` | All endpoints return article URLs |
| `test_history_page_renders()` | GET /history returns 200 |

**Optional Integration Tests**:
| Test Name | Description |
|-----------|-------------|
| `test_chat_ui_submits_query()` | Browser automation test |

**Run Tests**: `pytest tests/test_history_api.py -v`

**Git**: Branch `feature/sprint-4-web-interface`

**Deliverables**:
- `/history` page with chat interface
- REST API for external integrations
- Basic trend visualizations
- All tests passing

---

## Sprint 5: Polish & Production Readiness

**Goal**: Production-ready feature with docs and tooling

**Stories**:
1. Topic alias management
   - CLI command to merge/alias topics
   - LLM-assisted alias suggestions (batch job)
   - Web UI for alias management (optional)

2. Advanced visualizations
   - Interactive charts (click to drill down)
   - Export charts as images
   - CSV/JSON data export

3. Docker & deployment
   - Update Dockerfile for volume persistence
   - Docker Compose example with proper mounts
   - Health checks for database

4. Documentation
   - README updates with usage examples
   - API documentation
   - Query examples and tips

### Testing (Sprint 5)

**File**: `tests/test_history_db.py` (additions)

| Test Name | Description |
|-----------|-------------|
| `test_add_topic_alias()` | Verify alias creation |
| `test_topic_alias_applied_on_query()` | Alias affects search results |
| `test_merge_topics()` | Verify topic merging works |

**File**: `tests/test_history_cli.py` (additions)

| Test Name | Description |
|-----------|-------------|
| `test_cli_alias_command()` | CLI alias management |
| `test_cli_export_csv()` | Export to CSV format |
| `test_cli_export_json()` | Export to JSON format |

**Manual Docker Tests**:
- Verify volume persistence across container restarts
- Verify database survives container rebuild

**Run Tests**: `pytest tests/ -v` (full regression suite)

**Git**: Branch `feature/sprint-5-production-ready`

**Deliverables**:
- Topic normalization tools
- Export functionality
- Production deployment ready
- Documentation complete
- All tests passing (full regression)

---

## Sprint 6: Security Hardening

**Goal**: Secure all exposed endpoints and harden the application for production deployment

**Stories**:

1. **API Authentication** (High Priority)
   - Add API key authentication for all `/api/*` endpoints
   - Generate and manage API keys via environment variable `API_SECRET_KEY`
   - Return 401 Unauthorized for missing/invalid keys
   - Exclude public pages (`/`, `/history`) from auth requirement

2. **Rate Limiting** (High Priority)
   - Add Flask-Limiter for request throttling
   - Configure limits: 100 requests/minute for API, 10/minute for `/api/query` (LLM)
   - Return 429 Too Many Requests when exceeded
   - Add `RATE_LIMIT_ENABLED` env var to disable in development

3. **Security Headers** (High Priority)
   - Add Flask-Talisman for security headers
   - Content-Security-Policy (CSP)
   - X-Frame-Options (prevent clickjacking)
   - X-Content-Type-Options
   - Strict-Transport-Security (HTTPS)
   - Configure CSP to allow Chart.js and Bootstrap CDN

4. **Input Validation** (Medium Priority)
   - Add maximum length limits on all query parameters (1000 chars)
   - Strict date format validation (YYYY-MM-DD regex)
   - Sanitize search terms before use
   - Validate `limit` parameters (max 1000)

5. **LLM Prompt Injection Mitigation** (Medium Priority)
   - Sanitize user queries before including in prompts
   - Add input length limits (500 chars for natural language queries)
   - Add prompt guardrails to detect manipulation attempts
   - Log suspicious query patterns

6. **Error Handling** (Medium Priority)
   - Generic error messages for production (hide internal details)
   - Add `DEBUG` mode toggle for detailed errors in development
   - Structured error responses with error codes

7. **CORS Configuration** (Low Priority)
   - Add Flask-CORS with configurable allowed origins
   - Default to same-origin only
   - Add `CORS_ORIGINS` env var for allowed domains

8. **Audit Logging** (Low Priority)
   - Log all API requests with timestamp, IP, endpoint, user-agent
   - Log failed authentication attempts
   - Log rate limit violations
   - Separate security log file

### Testing (Sprint 6)

**File**: `tests/test_security.py`

| Test Name | Description |
|-----------|-------------|
| `test_api_requires_auth()` | Endpoints return 401 without key |
| `test_api_accepts_valid_key()` | Endpoints work with valid key |
| `test_api_rejects_invalid_key()` | Endpoints return 401 with bad key |
| `test_rate_limiting_enforced()` | Returns 429 after limit exceeded |
| `test_rate_limiting_resets()` | Limit resets after window |
| `test_security_headers_present()` | CSP, X-Frame-Options, etc. |
| `test_input_length_validation()` | Rejects oversized inputs |
| `test_date_format_validation()` | Rejects invalid dates |
| `test_query_length_limit()` | Rejects long NL queries |
| `test_error_messages_generic()` | No stack traces in production |
| `test_cors_same_origin_default()` | Cross-origin blocked by default |

**Run Tests**: `pytest tests/test_security.py -v`

**Git**: Branch `feature/sprint-6-security-hardening`

**New Dependencies** (add to requirements.txt):
```
Flask-Limiter>=3.5.0
Flask-Talisman>=1.1.0
Flask-CORS>=4.0.0
```

**New Environment Variables** (add to .env.example):
```bash
# Security Configuration
API_SECRET_KEY=your-secret-api-key-here
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=https://yourdomain.com
DEBUG=false
```

**Deliverables**:
- All API endpoints require authentication
- Rate limiting prevents abuse
- Security headers protect against common attacks
- Input validation prevents malformed requests
- LLM prompts protected from injection
- Audit trail for security events
- All tests passing (full regression)

---

## CLI Usage Examples

```bash
# Initialize database
python src/history_cli.py init

# Natural language query
python src/history_cli.py query "Top AI themes in November?"

# Trend analysis
python src/history_cli.py trends --start 2024-06-01 --end 2024-12-01 --period month

# Compare periods
python src/history_cli.py compare --period1 2024-01-01 2024-03-31 \
                                  --period2 2024-04-01 2024-06-30

# Import existing data
python src/history_cli.py import backups/*.json
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/query` | POST | Required | Natural language query |
| `/api/trends` | GET | Required | Time-series trend data |
| `/api/compare` | GET | Required | Period comparison |
| `/api/topics` | GET | Required | Topic search with articles |
| `/api/history/stats` | GET | Required | Database statistics |
| `/history` | GET | Public | Chat interface page |
| `/` | GET | Public | Dashboard homepage |

**Authentication**: Include `X-API-Key` header with your `API_SECRET_KEY` value for protected endpoints.

## New Files Summary

| File | Purpose |
|------|---------|
| `docs/sprint-plan.md` | This document |
| `src/history_db.py` | Database init, save, query operations |
| `src/query_engine.py` | LLM query classification + execution |
| `src/history_cli.py` | CLI tool for queries |
| `src/templates/history.html` | Web chat interface |
| `tests/test_history_db.py` | Unit tests for database operations |
| `tests/test_query_engine.py` | Unit tests for query engine |
| `tests/test_history_cli.py` | Integration tests for CLI |
| `tests/test_history_api.py` | Integration tests for web API |
| `tests/test_security.py` | Security tests (Sprint 6) |
| `tests/conftest.py` | Shared pytest fixtures |

## Modified Files Summary

| File | Change |
|------|--------|
| `src/main.py` | Add `save_summary_to_db()` call after summarization |
| `src/web_dashboard.py` | Add `/history`, `/api/query`, `/api/trends` routes + security middleware |
| `.env.example` | Add `HISTORY_DB_PATH`, `API_SECRET_KEY`, `RATE_LIMIT_ENABLED`, `CORS_ORIGINS`, `DEBUG` |
| `Dockerfile` | Ensure `data/` volume persistence |
| `requirements.txt` | Add `pytest`, `Flask-Limiter`, `Flask-Talisman`, `Flask-CORS` |
