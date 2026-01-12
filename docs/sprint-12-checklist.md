# Sprint 12: Token Usage Monitoring - Implementation Checklist

**Status**: Ready to Start
**Duration**: 1 week (7 days)
**Expected Test Count**: 261 → 314 tests

## Day 1-2: Database & Schema Design

### Database Schema (S12-1, S12-2)
- [ ] Design `llm_usage` table schema
  - [ ] Fields: id, timestamp, provider, model, task_type, input_tokens, output_tokens, total_tokens, cost_usd, response_time_ms
  - [ ] Indexes: provider, task_type, timestamp, model
- [ ] Add table creation SQL to `SCHEMA_SQL` in `history_db.py`
- [ ] Test database initialization
- [ ] Write tests for `llm_usage` table operations (8 tests)

### Pricing Configuration (S12-3)
- [ ] Create `src/pricing.py`
- [ ] Add `PROVIDER_PRICING` dictionary with all providers/models
  - [ ] OpenAI: gpt-4o, gpt-4o-mini, gpt-5, gpt-5-mini
  - [ ] xAI: grok-3, grok-3-mini
  - [ ] Anthropic: claude-sonnet-4, claude-haiku, claude-opus-4
  - [ ] Google: gemini-2.0-flash, gemini-pro, gemini-2.0-flash-thinking
- [ ] Write tests for pricing configuration (5 tests)

## Day 3-4: Provider Interface Changes

### Base Provider Updates (S12-4, S12-5)
- [ ] Add `LLMUsageMetadata` dataclass to `src/providers/base.py`
  - [ ] Fields: input_tokens, output_tokens, total_tokens, model, provider, response_time_ms
  - [ ] Add `__post_init__` to calculate total_tokens if needed
- [ ] Update `BaseProvider.complete()` signature: `-> Tuple[str, LLMUsageMetadata]`
- [ ] Update docstrings

### OpenAI Provider (S12-6)
- [ ] Extract usage from OpenAI API response
  - [ ] `resp_json["usage"]["prompt_tokens"]`
  - [ ] `resp_json["usage"]["completion_tokens"]`
  - [ ] `resp_json["usage"]["total_tokens"]`
- [ ] Return tuple: `(parsed_text, usage_metadata)`
- [ ] Handle gpt-5 models correctly
- [ ] Write tests (5 tests)

### xAI Provider (S12-7)
- [ ] Extract usage from xAI API response (same as OpenAI)
- [ ] Return tuple: `(parsed_text, usage_metadata)`
- [ ] Write tests (5 tests)

### Anthropic Provider (S12-8)
- [ ] Extract usage from Anthropic API response
  - [ ] `resp_json["usage"]["input_tokens"]`
  - [ ] `resp_json["usage"]["output_tokens"]`
- [ ] Return tuple: `(parsed_text, usage_metadata)`
- [ ] Write tests (5 tests)

### Google Gemini Provider (S12-9)
- [ ] Extract usage from Google API response
  - [ ] `resp_json["usageMetadata"]["promptTokenCount"]`
  - [ ] `resp_json["usageMetadata"]["candidatesTokenCount"]`
  - [ ] `resp_json["usageMetadata"]["totalTokenCount"]`
- [ ] Return tuple: `(parsed_text, usage_metadata)`
- [ ] Write tests (5 tests)

## Day 5: Integration & Utils

### Cost Estimation (S12-12)
- [ ] Add `estimate_cost()` function to `pricing.py`
- [ ] Handle missing pricing gracefully (return 0.0, log warning)
- [ ] Test with various providers/models

### Update call_llm() (S12-10, S12-11)
- [ ] Import necessary functions (time, estimate_cost, log_llm_usage)
- [ ] Add `task_type` parameter (default: "unknown")
- [ ] Add response time measurement
- [ ] Unpack provider response: `response_text, usage_metadata = provider.complete(...)`
- [ ] Calculate response time and add to metadata
- [ ] Call `estimate_cost()` to get cost_usd
- [ ] Call `log_llm_usage()` in try-except (non-fatal)
- [ ] Return just the text (backward compatible)
- [ ] Write tests (5 tests)

### Update Call Sites
- [ ] Update `src/llm_filter.py`: add `task_type="filter"`
- [ ] Update `src/summarizer.py` (grouping): add `task_type="group"`
- [ ] Update `src/summarizer.py` (summarization): add `task_type="summarize"`
- [ ] Update `src/query_engine.py`: add `task_type="query"`

## Day 6: CLI & Database Functions

### Database Functions (S12-14)
- [ ] Add `log_llm_usage()` function to `history_db.py`
  - [ ] Parameters: provider, model, task_type, input_tokens, output_tokens, total_tokens, cost_usd, response_time_ms
  - [ ] INSERT INTO llm_usage
- [ ] Add `get_usage_stats()` - overall statistics
- [ ] Add `get_usage_by_provider()` - breakdown by provider
- [ ] Add `get_usage_by_task()` - breakdown by task type
- [ ] Add `get_usage_by_model()` - breakdown by model (optional provider filter)
- [ ] Add `get_usage_by_date_range()` - filter by date range
- [ ] Write tests (8 tests in test_history_db.py)

### Usage CLI (S12-13)
- [ ] Create `src/usage_cli.py`
- [ ] Add argument parser with subcommands
- [ ] Implement `stats` command - show overall statistics
- [ ] Implement `by-provider` command - provider breakdown
- [ ] Implement `by-task` command - task type breakdown
- [ ] Implement `by-model` command - model breakdown
- [ ] Implement `range` command - date range filter
- [ ] Implement `costs` command - cost analysis
- [ ] Implement `export` command - CSV export
- [ ] Add table formatting (tabulate library)
- [ ] Write tests (10 tests in test_usage_cli.py)

## Day 7: Testing & Documentation

### Update Existing Tests (S12-19)
- [ ] Update `tests/test_providers.py` - handle tuple returns
  - [ ] OpenAI tests
  - [ ] xAI tests
  - [ ] Anthropic tests
  - [ ] Google tests
  - [ ] Factory tests
- [ ] Update `tests/test_utils.py` - handle new call_llm() behavior
- [ ] Update any integration tests that call providers directly
- [ ] Run full test suite: `PYTHONPATH=src pytest tests/ -v`
- [ ] Verify 314 tests passing

### Integration Tests (S12-18)
- [ ] Create `tests/test_integration_usage.py`
- [ ] Test end-to-end: call_llm() creates database entry
- [ ] Test with all 4 providers
- [ ] Test with all 4 task types
- [ ] Test cost calculation accuracy
- [ ] Test response time measurement
- [ ] Write 5+ integration tests

### Documentation (S12-20)
- [ ] Update README.md with "Token Usage Monitoring" section
- [ ] Add CLI usage examples
- [ ] Add database schema documentation
- [ ] Add cost estimation notes
- [ ] Update configuration examples
- [ ] Add "Monitoring Costs" guide

## Final Verification

### Code Quality
- [ ] All functions have docstrings
- [ ] All imports are correct
- [ ] No unused imports
- [ ] Code follows PEP 8 style
- [ ] No hardcoded values (use constants/config)

### Testing
- [ ] All 314 tests passing
- [ ] Test coverage above 85% for new code
- [ ] No flaky tests
- [ ] All edge cases covered

### Functionality
- [ ] Usage logged for all LLM calls
- [ ] All 4 providers extract usage correctly
- [ ] Cost estimation works for all models
- [ ] Response time measured accurately
- [ ] CLI tool produces correct output
- [ ] CSV export works
- [ ] Date range filtering works

### Error Handling
- [ ] Missing pricing handled gracefully
- [ ] Database write failures don't break pipeline
- [ ] Provider API changes handled gracefully
- [ ] Invalid task types logged but don't fail

### Documentation
- [ ] README updated
- [ ] All new functions documented
- [ ] CLI help text clear
- [ ] Examples provided

## Git Workflow

### Branch Setup
```bash
git checkout master
git pull origin master
git checkout -b feature/sprint-12-token-usage-monitoring
```

### Daily Commits
```bash
# Day 1-2
git add src/history_db.py src/pricing.py tests/
git commit -m "feat(usage): add llm_usage database schema and pricing config"

# Day 3-4
git add src/providers/
git commit -m "feat(providers): update all providers to return usage metadata"

# Day 5
git add src/utils.py src/llm_filter.py src/summarizer.py src/query_engine.py
git commit -m "feat(usage): integrate usage tracking in call_llm()"

# Day 6
git add src/usage_cli.py src/history_db.py tests/
git commit -m "feat(usage): add usage CLI tool and query functions"

# Day 7
git add tests/ README.md docs/
git commit -m "test(usage): update all tests and documentation"
```

### Pull Request
```bash
# Push to remote
git push origin feature/sprint-12-token-usage-monitoring

# Create PR
gh pr create --title "Sprint 12: Token Usage Monitoring" --body "$(cat <<'EOF'
## Summary
Add comprehensive token usage tracking and cost monitoring for all LLM calls.

## Features
- SQLite table for persistent usage tracking
- Token count extraction from all 4 provider APIs
- Cost estimation using provider pricing
- CLI tool for usage analysis and reporting
- Response time tracking

## Changes
- Modified `BaseProvider` interface to return `(text, usage_metadata)` tuple
- Updated all 4 provider implementations
- Added `pricing.py` for cost estimation
- Added `usage_cli.py` for CLI reporting
- Updated `call_llm()` to log usage automatically
- Added `task_type` parameter to track purpose

## Testing
- 53 new tests added
- 261 existing tests updated
- All 314 tests passing

## Documentation
- README updated with usage monitoring guide
- CLI usage examples provided
- Cost estimation documented

## Backward Compatibility
- `call_llm()` still returns `str` (no breaking changes for users)
- Provider interface change only affects direct provider users (rare)

## Resolves
- FR-12.1: SQLite table for token usage tracking
- FR-12.2: Capture usage metrics from all providers
- FR-12.3: Modified provider interface
- FR-12.4: Cost estimation
- FR-12.5: CLI reporting tool
- FR-12.6: Response time tracking
EOF
)"

# After review and approval
git checkout master
git merge feature/sprint-12-token-usage-monitoring
git push origin master
```

## Success Metrics

- [ ] ✅ All 314 tests passing
- [ ] ✅ `llm_usage` table created with indexes
- [ ] ✅ All 4 providers return usage metadata
- [ ] ✅ Usage logged for every LLM call
- [ ] ✅ Cost estimation working for all models
- [ ] ✅ Response time tracked accurately
- [ ] ✅ CLI tool produces correct reports
- [ ] ✅ Documentation complete with examples
- [ ] ✅ No breaking changes for existing code
- [ ] ✅ PR approved and merged

## Dependencies & Prerequisites

### Required Files Exist
- [x] `src/providers/base.py`
- [x] `src/providers/openai_provider.py`
- [x] `src/providers/xai_provider.py`
- [x] `src/providers/anthropic_provider.py`
- [x] `src/providers/gemini_provider.py`
- [x] `src/utils.py`
- [x] `src/history_db.py`
- [x] `tests/test_providers.py`
- [x] `tests/test_utils.py`
- [x] `tests/test_history_db.py`

### Python Packages
- [x] sqlite3 (built-in)
- [x] dataclasses (built-in)
- [x] typing (built-in)
- [x] time (built-in)
- [ ] tabulate (may need: `pip install tabulate`)

## Troubleshooting

### Common Issues

**Issue**: Tests fail with tuple unpacking error
```python
# Fix: Update test to handle tuple
response, usage = provider.complete(prompt="test")
assert response == "expected"
```

**Issue**: "No pricing found" warnings
```python
# Fix: Add model to PROVIDER_PRICING in pricing.py
"new-model": {"input": 0.0, "output": 0.0}
```

**Issue**: Database write failures
```python
# Expected: Non-fatal, logs warning, continues execution
# No fix needed - this is intentional behavior
```

**Issue**: Token counts are 0
```python
# Fix: Check provider API response structure
# Verify extraction path is correct for the provider
```

## Next Steps After Sprint 12

Potential future enhancements:
1. Web dashboard with charts/graphs
2. Cost threshold alerts (email/Slack)
3. Monthly budget tracking
4. Automatic provider optimization
5. Usage trend analysis and forecasting
6. Response caching to reduce costs
