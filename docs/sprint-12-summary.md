# Sprint 12: Token Usage Monitoring - Summary

**Created**: 2026-01-12
**Status**: Planned
**Duration**: 1 week

## Overview

Sprint 12 adds comprehensive token usage tracking and cost monitoring for all LLM calls across the 4 providers (OpenAI, xAI, Anthropic, Google). This enables visibility into API usage, costs, and performance metrics.

## Key Features

1. **Persistent Token Tracking**
   - New SQLite table: `llm_usage`
   - Tracks: tokens (input/output/total), cost, response time
   - Indexed for efficient querying

2. **Provider Interface Enhancement**
   - Modified `BaseProvider.complete()` returns tuple: `(text, LLMUsageMetadata)`
   - All 4 providers extract token counts from their API responses
   - Automatic usage logging in `call_llm()`

3. **Cost Estimation**
   - Provider pricing configuration (`src/pricing.py`)
   - Per-call cost calculation in USD
   - Supports all current models for all 4 providers

4. **Usage Reporting CLI**
   - `src/usage_cli.py` - comprehensive reporting tool
   - Summary statistics, breakdowns by provider/task/model
   - Date range filtering, CSV export

5. **Response Time Tracking**
   - Measure API response time per call
   - Store in milliseconds for performance analysis

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-12.1 | SQLite table for token usage tracking | Must Have |
| FR-12.2 | Capture usage metrics from all provider APIs | Must Have |
| FR-12.3 | Modified provider interface to return usage metadata | Must Have |
| FR-12.4 | Cost estimation per call using provider pricing | Should Have |
| FR-12.5 | CLI script for usage reporting and analysis | Must Have |
| FR-12.6 | Response time tracking per LLM call | Should Have |

## Task Breakdown (20 tasks)

### Database (Tasks S12-1, S12-2)
- Design and implement `llm_usage` table schema
- Add indexes for common query patterns

### Cost Estimation (Tasks S12-3, S12-12)
- Create pricing configuration for all providers
- Implement cost calculation utility

### Provider Modifications (Tasks S12-4 to S12-9)
- Design `LLMUsageMetadata` dataclass
- Update `BaseProvider` interface to return tuple
- Extract token usage from all 4 provider APIs:
  - OpenAI: `usage.prompt_tokens`, `usage.completion_tokens`
  - xAI: Same as OpenAI (compatible API)
  - Anthropic: `usage.input_tokens`, `usage.output_tokens`
  - Google: `usage_metadata.prompt_token_count`, `usage_metadata.candidates_token_count`

### Integration (Tasks S12-10, S12-11)
- Update `call_llm()` to log usage to database
- Add response time measurement
- Add `task_type` parameter to track purpose (filter/group/summarize/query)

### CLI Tool (Tasks S12-13, S12-14)
- Create `src/usage_cli.py` with commands:
  - `stats` - overall statistics
  - `by-provider` - breakdown by provider
  - `by-task` - breakdown by task type
  - `by-model` - breakdown by model
  - `range` - filter by date range
  - `costs` - cost analysis
  - `export` - CSV export
- Add query functions to `history_db.py`

### Testing (Tasks S12-15 to S12-19)
- Unit tests for database operations (8 tests)
- Unit tests for provider metadata extraction (20 tests)
- Unit tests for cost estimation (5 tests)
- Integration tests for end-to-end tracking (5 tests)
- Update all 261 existing tests for new return signature (15 tests affected)

### Documentation (Task S12-20)
- README section on usage monitoring
- CLI usage examples

## Deliverables

| Component | File | Description |
|-----------|------|-------------|
| Database Schema | `src/history_db.py` | `llm_usage` table + query functions |
| Provider Interface | `src/providers/base.py` | `LLMUsageMetadata` dataclass, updated abstract methods |
| Provider Implementations | `src/providers/*_provider.py` | Token extraction for all 4 providers |
| Usage Tracking | `src/utils.py` | Updated `call_llm()` with logging |
| Cost Estimation | `src/pricing.py` | Pricing config + calculation utility |
| CLI Tool | `src/usage_cli.py` | Usage reporting and analysis |
| Tests | `tests/test_*.py` | 53+ new tests, 261 updated tests |
| Documentation | `README.md` | Usage monitoring guide |

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provider TEXT NOT NULL,           -- 'openai', 'xai', 'anthropic', 'google'
    model TEXT NOT NULL,              -- 'gpt-4o-mini', 'grok-3', etc.
    task_type TEXT NOT NULL,          -- 'filter', 'group', 'summarize', 'query'
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL,                    -- Estimated cost in USD
    response_time_ms INTEGER,         -- Response time in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Interface Changes

### Before (Sprint 11)
```python
response = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str
```

### After (Sprint 12)
```python
response, usage = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str
# usage is LLMUsageMetadata(input_tokens=5, output_tokens=10, ...)
```

### For `call_llm()` Users
No changes needed! `call_llm()` still returns `str`, but now logs usage automatically:

```python
# Before Sprint 12
response = call_llm(model_config="openai:gpt-4o-mini", prompt="Hello", api_keys=keys)

# After Sprint 12 (same code, but usage is logged automatically)
response = call_llm(
    model_config="openai:gpt-4o-mini",
    prompt="Hello",
    api_keys=keys,
    task_type="filter"  # NEW optional parameter
)
```

## Usage CLI Examples

```bash
# Overall statistics
python src/usage_cli.py stats
# Total Calls: 1,247
# Total Tokens: 632,127
# Estimated Cost: $12.45 USD

# By provider
python src/usage_cli.py by-provider
# Provider      Calls    Cost (USD)
# ----------  -------  ------------
# openai          834        $5.23
# anthropic       287        $6.12

# By task type
python src/usage_cli.py by-task
# Task Type      Calls    Cost (USD)
# -----------  -------  ------------
# filter           412        $2.34
# group            398        $5.67

# Date range
python src/usage_cli.py range --start 2026-01-01 --end 2026-01-10

# Export to CSV
python src/usage_cli.py export --output usage_report.csv
```

## Test Coverage

| Test File | New Tests | Description |
|-----------|-----------|-------------|
| `tests/test_history_db.py` | +8 | `llm_usage` table operations |
| `tests/test_providers.py` | +20 | Provider metadata extraction |
| `tests/test_pricing.py` | +5 | Cost estimation |
| `tests/test_usage_cli.py` | +10 | CLI commands |
| `tests/test_integration_usage.py` | +5 | End-to-end tracking |
| Various existing tests | Updated | Handle new tuple return type |

**Expected Test Count**: 261 → 314 tests

## Call Sites to Update

Add `task_type` parameter to `call_llm()` calls in:

1. **`src/llm_filter.py`** → `task_type="filter"`
2. **`src/summarizer.py`** (grouping) → `task_type="group"`
3. **`src/summarizer.py`** (summarization) → `task_type="summarize"`
4. **`src/query_engine.py`** → `task_type="query"`

## Provider Pricing (as of Jan 2026)

| Provider | Model | Input (per 1M) | Output (per 1M) |
|----------|-------|----------------|-----------------|
| OpenAI | gpt-4o-mini | $0.15 | $0.60 |
| OpenAI | gpt-5-mini | $1.00 | $4.00 |
| xAI | grok-3-mini | $0.20 | $0.80 |
| Anthropic | claude-sonnet-4 | $3.00 | $15.00 |
| Anthropic | claude-haiku | $0.25 | $1.25 |
| Google | gemini-2.0-flash | $0.075 | $0.30 |

## Technical Considerations

1. **Non-Fatal Logging**: Usage logging failures won't break the pipeline
2. **Task Type Tracking**: Manual labeling at call sites (filter/group/summarize/query)
3. **Provider-Specific Extraction**: Each provider API returns usage differently
4. **Backward Compatibility**: All existing tests need updating for new return type
5. **Cost Accuracy**: Prices configurable, warns if pricing not found

## Testing Milestones

- **Day 2**: Database schema and basic logging tests complete
- **Day 4**: All provider implementations updated with tests
- **Day 6**: CLI tool complete with integration tests
- **Day 7**: All tests passing, documentation complete

## Success Criteria

- ✅ `llm_usage` table created and indexed
- ✅ All 4 providers return usage metadata
- ✅ Usage automatically logged for all LLM calls
- ✅ CLI tool provides comprehensive usage analysis
- ✅ Cost estimation working for all providers
- ✅ Response time tracking implemented
- ✅ All 314 tests passing
- ✅ Documentation complete with examples

## Git Operations

```bash
# Create feature branch
git checkout -b feature/sprint-12-token-usage-monitoring

# Daily commits with conventional messages
git commit -m "feat(usage): add llm_usage database schema"
git commit -m "feat(providers): update BaseProvider to return usage metadata"
git commit -m "feat(usage): add cost estimation utility"
git commit -m "feat(usage): create usage CLI tool"

# Create PR
gh pr create --title "Sprint 12: Token Usage Monitoring" --body "..."

# After review, merge to master
git checkout master
git merge feature/sprint-12-token-usage-monitoring
```

## Dependencies

- **Prerequisite**: Sprint 11 complete (all 4 providers working)
- **Blocks**: None (this is a monitoring/observability feature)
- **Enables**: Future cost optimization, provider performance comparison

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Update systematically, verify all 261 tests |
| Provider API changes | Use try-except for extraction, default to 0 tokens |
| Cost estimation inaccuracy | Make pricing configurable, warn on missing prices |
| Database write failures | Non-fatal logging, log warnings but continue |

## Next Steps After Sprint 12

Possible future enhancements:
1. **Dashboard**: Web UI for usage visualization (charts, graphs)
2. **Alerts**: Cost/usage threshold alerts
3. **Budget**: Monthly budget tracking and warnings
4. **Optimization**: Automatic provider selection based on cost/performance
5. **Analytics**: Usage trends, peak times, cost forecasting
