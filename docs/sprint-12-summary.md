# Sprint 12 Summary: Token Usage Monitoring

**Status**: Complete
**Branch**: `feature/sprint-12-token-usage-monitoring`
**Completed**: 2026-01-12

## Goal
Track and persist token usage, costs, and performance metrics for all LLM calls across all 4 providers.

## Deliverables

### New Files Created
| File | Purpose |
|------|---------|
| `src/pricing.py` | Provider pricing configuration and cost estimation |
| `src/usage_cli.py` | CLI tool for usage reporting and analysis |
| `tests/test_usage_tracking.py` | 24 new tests for usage tracking |

### Files Modified
| File | Change |
|------|--------|
| `src/providers/base.py` | Added `LLMUsageMetadata` dataclass, updated `complete()` signature |
| `src/providers/openai_provider.py` | Extract token usage from API response |
| `src/providers/xai_provider.py` | Extract token usage from API response |
| `src/providers/anthropic_provider.py` | Extract token usage from API response |
| `src/providers/gemini_provider.py` | Extract token usage from API response |
| `src/history_db.py` | Added `llm_usage` table and query functions |
| `src/utils.py` | Updated `call_llm()` to log usage with `task_type` parameter |
| `src/llm_filter.py` | Added `task_type="filter"` to LLM calls |
| `src/summarizer.py` | Added `task_type="group"` and `task_type="summarize"` |
| `src/query_engine.py` | Added `task_type="query"` to LLM calls |

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_llm_usage_provider ON llm_usage(provider);
CREATE INDEX idx_llm_usage_task_type ON llm_usage(task_type);
CREATE INDEX idx_llm_usage_timestamp ON llm_usage(timestamp);
CREATE INDEX idx_llm_usage_model ON llm_usage(model);
```

## Provider Interface Changes

### Before Sprint 12
```python
response = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str
```

### After Sprint 12
```python
response, usage = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str
# usage is LLMUsageMetadata(input_tokens=5, output_tokens=10, ...)
```

For `call_llm()` users, no changes needed—it still returns `str` but now logs usage automatically.

## Usage CLI Commands

```bash
# Overall statistics
python src/usage_cli.py stats

# Breakdown by provider
python src/usage_cli.py by-provider

# Breakdown by task type (filter, group, summarize, query)
python src/usage_cli.py by-task

# Breakdown by model
python src/usage_cli.py by-model

# Cost analysis
python src/usage_cli.py costs

# Export to CSV
python src/usage_cli.py export --output usage_report.csv
```

## Test Results

```
285 passed in 15.81s

Sprint 1-11 Tests (261)
Sprint 12 Tests (24):

- TestLLMUsageMetadata (3 tests)
  - Create basic metadata
  - Auto-calculate total tokens
  - Default values

- TestPricing (11 tests)
  - Get pricing for all 4 providers
  - Handle unknown models/providers
  - Calculate costs
  - Format cost display

- TestUsageDatabase (6 tests)
  - Save usage records
  - Get usage statistics
  - Get usage by provider/task/model
  - Export to CSV

- TestProviderUsageExtraction (4 tests)
  - OpenAI extracts usage
  - Anthropic extracts usage
  - xAI extracts usage
  - Gemini extracts usage
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│  (llm_filter.py, summarizer.py, query_engine.py)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ call_llm(model, prompt, task_type="filter")
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     utils.py - call_llm()                        │
│  1. Get provider instance                                        │
│  2. Start timer                                                  │
│  3. Call provider.complete() → (text, usage_metadata)            │
│  4. Calculate response time                                      │
│  5. Estimate cost via pricing.py                                 │
│  6. Log to database (non-fatal)                                  │
│  7. Return text to caller                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐      ┌─────────────────────────────┐
│ Provider Layer  │      │    history_db.py            │
│ (4 providers)   │      │    log_llm_usage()          │
│                 │      │                             │
│ Extract usage   │      │  INSERT INTO llm_usage      │
│ from API resp   │      │  (provider, model, tokens,  │
└─────────────────┘      │   cost, response_time)      │
                         └─────────────┬───────────────┘
                                       │
                                       ▼
                         ┌──────────────────────────────┐
                         │   usage_cli.py               │
                         │   Query & Report             │
                         └──────────────────────────────┘
```

## Provider Pricing (as of Jan 2026)

| Provider | Model | Input (per 1M) | Output (per 1M) |
|----------|-------|----------------|-----------------|
| OpenAI | gpt-4o-mini | $0.15 | $0.60 |
| OpenAI | gpt-5-mini | $1.00 | $4.00 |
| xAI | grok-3-mini | $0.20 | $0.80 |
| Anthropic | claude-sonnet-4 | $3.00 | $15.00 |
| Anthropic | claude-haiku | $0.25 | $1.25 |
| Google | gemini-2.0-flash | $0.075 | $0.30 |

## Key Design Decisions

1. **Non-Fatal Logging**: Usage logging failures don't break the pipeline—warnings are logged but execution continues
2. **Task Type Labels**: Manual labeling at call sites (filter/group/summarize/query) for analytics
3. **Provider-Specific Extraction**: Each provider's API returns usage differently; handled in each provider class
4. **Backward Compatibility**: `call_llm()` still returns `str`; providers return tuple internally

## Sprint Summary

All twelve sprints are now complete:

| Sprint | Focus | Tests |
|--------|-------|-------|
| Sprint 1-6 | Core features | 141 |
| Sprint 7-11 | Multi-provider LLM | 120 |
| Sprint 12 | Token usage monitoring | 24 |

**Total: 285 tests passing**
