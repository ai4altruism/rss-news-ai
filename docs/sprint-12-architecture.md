# Sprint 12: Token Usage Monitoring - Architecture

## Data Flow Diagram

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
│  5. Estimate cost                                                │
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
│ OpenAI          │      │  INSERT INTO llm_usage      │
│ xAI             │      │  VALUES (provider, model,   │
│ Anthropic       │      │          task_type,         │
│ Google          │      │          tokens, cost,      │
│                 │      │          response_time)     │
└─────────┬───────┘      └─────────────┬───────────────┘
          │                            │
          │ Extract usage from         │ Persist to SQLite
          │ API response               │
          ▼                            ▼
┌─────────────────┐      ┌─────────────────────────────┐
│ LLM Provider    │      │   data/history.db           │
│ APIs            │      │   ┌─────────────────────┐   │
│                 │      │   │ llm_usage table     │   │
│ OpenAI API      │      │   │ - timestamp         │   │
│ xAI API         │      │   │ - provider          │   │
│ Anthropic API   │      │   │ - model             │   │
│ Google API      │      │   │ - task_type         │   │
└─────────────────┘      │   │ - input_tokens      │   │
                         │   │ - output_tokens     │   │
                         │   │ - total_tokens      │   │
                         │   │ - cost_usd          │   │
                         │   │ - response_time_ms  │   │
                         │   └─────────────────────┘   │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │   usage_cli.py               │
                         │   Query & Report             │
                         │                              │
                         │   - stats                    │
                         │   - by-provider              │
                         │   - by-task                  │
                         │   - by-model                 │
                         │   - range                    │
                         │   - costs                    │
                         │   - export                   │
                         └──────────────────────────────┘
```

## Provider Interface Changes

### Before Sprint 12

```python
class BaseProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, ...) -> str:
        """Returns just the text response."""
        pass
```

### After Sprint 12

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass
class LLMUsageMetadata:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    provider: str
    response_time_ms: Optional[int] = None

class BaseProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, ...) -> Tuple[str, LLMUsageMetadata]:
        """Returns (text_response, usage_metadata)."""
        pass
```

## Provider-Specific Token Extraction

### OpenAI & xAI
```python
# API Response Structure
{
    "output": [...],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 75,
        "total_tokens": 225
    }
}

# Extraction
usage = LLMUsageMetadata(
    input_tokens=resp_json["usage"]["prompt_tokens"],
    output_tokens=resp_json["usage"]["completion_tokens"],
    total_tokens=resp_json["usage"]["total_tokens"],
    model=self.model,
    provider=self.get_provider_name()
)
```

### Anthropic
```python
# API Response Structure
{
    "content": [...],
    "usage": {
        "input_tokens": 150,
        "output_tokens": 75
    }
}

# Extraction
usage = LLMUsageMetadata(
    input_tokens=resp_json["usage"]["input_tokens"],
    output_tokens=resp_json["usage"]["output_tokens"],
    total_tokens=0,  # Will be calculated in __post_init__
    model=self.model,
    provider=self.get_provider_name()
)
```

### Google Gemini
```python
# API Response Structure
{
    "candidates": [...],
    "usageMetadata": {
        "promptTokenCount": 150,
        "candidatesTokenCount": 75,
        "totalTokenCount": 225
    }
}

# Extraction
usage = LLMUsageMetadata(
    input_tokens=resp_json["usageMetadata"]["promptTokenCount"],
    output_tokens=resp_json["usageMetadata"]["candidatesTokenCount"],
    total_tokens=resp_json["usageMetadata"]["totalTokenCount"],
    model=self.model,
    provider=self.get_provider_name()
)
```

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

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage(provider);
CREATE INDEX IF NOT EXISTS idx_llm_usage_task_type ON llm_usage(task_type);
CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp ON llm_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_llm_usage_model ON llm_usage(model);
```

## Cost Estimation

```python
# pricing.py
PROVIDER_PRICING = {
    "openai": {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # per 1M tokens
        "gpt-5-mini": {"input": 1.00, "output": 4.00},
    },
    # ... other providers
}

def estimate_cost(provider: str, model: str,
                  input_tokens: int, output_tokens: int) -> float:
    pricing = PROVIDER_PRICING.get(provider, {}).get(model)
    if not pricing:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
```

## Usage Tracking in `call_llm()`

```python
def call_llm(model_config: str, prompt: str, api_keys: dict,
             instructions: str = "", max_tokens: int = 500,
             temperature: float = 1.0, task_type: str = "unknown") -> str:
    """
    Call an LLM with automatic usage tracking.

    Args:
        task_type: One of 'filter', 'group', 'summarize', 'query', 'unknown'

    Returns:
        str: The LLM response text
    """
    import time
    from pricing import estimate_cost
    from history_db import log_llm_usage

    # Get provider
    provider = get_provider(model_config, ...)

    # Measure response time
    start_time = time.time()

    # Call provider (now returns tuple)
    response_text, usage_metadata = provider.complete(
        prompt=prompt,
        instructions=instructions,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    usage_metadata.response_time_ms = response_time_ms

    # Estimate cost
    cost_usd = estimate_cost(
        provider=usage_metadata.provider,
        model=usage_metadata.model,
        input_tokens=usage_metadata.input_tokens,
        output_tokens=usage_metadata.output_tokens,
    )

    # Log to database (non-fatal)
    try:
        log_llm_usage(
            provider=usage_metadata.provider,
            model=usage_metadata.model,
            task_type=task_type,
            input_tokens=usage_metadata.input_tokens,
            output_tokens=usage_metadata.output_tokens,
            total_tokens=usage_metadata.total_tokens,
            cost_usd=cost_usd,
            response_time_ms=response_time_ms,
        )
    except Exception as e:
        logging.warning(f"Failed to log LLM usage: {e}")

    # Return just the text (backward compatible)
    return response_text
```

## Call Sites to Update

### 1. llm_filter.py
```python
# Before
response = call_responses_api(model, prompt, api_key, ...)

# After
response = call_llm(model, prompt, api_keys, task_type="filter", ...)
```

### 2. summarizer.py (grouping)
```python
# Before
response = call_responses_api(group_model, prompt, api_key, ...)

# After
response = call_llm(group_model, prompt, api_keys, task_type="group", ...)
```

### 3. summarizer.py (summarization)
```python
# Before
response = call_responses_api(summarize_model, prompt, api_key, ...)

# After
response = call_llm(summarize_model, prompt, api_keys, task_type="summarize", ...)
```

### 4. query_engine.py
```python
# Before
response = call_responses_api(query_model, prompt, api_key, ...)

# After
response = call_llm(query_model, prompt, api_keys, task_type="query", ...)
```

## Query Functions in history_db.py

```python
def get_usage_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get overall usage statistics."""
    # SELECT COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
    # FROM llm_usage

def get_usage_by_provider(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get usage breakdown by provider."""
    # SELECT provider, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
    # FROM llm_usage GROUP BY provider

def get_usage_by_task(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get usage breakdown by task type."""
    # SELECT task_type, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
    # FROM llm_usage GROUP BY task_type

def get_usage_by_model(provider: Optional[str] = None,
                       db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get usage breakdown by model."""
    # SELECT model, COUNT(*), SUM(input_tokens), SUM(output_tokens), SUM(cost_usd)
    # FROM llm_usage WHERE provider = ? GROUP BY model

def get_usage_by_date_range(start_date: str, end_date: str,
                            db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get usage for a specific date range."""
    # SELECT * FROM llm_usage
    # WHERE date(timestamp) BETWEEN date(?) AND date(?)
```

## Usage CLI Commands

```bash
# Overall statistics
python src/usage_cli.py stats

# By provider
python src/usage_cli.py by-provider

# By task type
python src/usage_cli.py by-task

# By model (optionally filtered by provider)
python src/usage_cli.py by-model
python src/usage_cli.py by-model --provider openai

# Date range
python src/usage_cli.py range --start 2026-01-01 --end 2026-01-10

# Cost breakdown
python src/usage_cli.py costs --breakdown

# Export to CSV
python src/usage_cli.py export --output usage_report.csv
```

## File Structure

```
src/
├── providers/
│   ├── base.py              # LLMUsageMetadata + BaseProvider (modified)
│   ├── openai_provider.py   # Extract usage from OpenAI API (modified)
│   ├── xai_provider.py      # Extract usage from xAI API (modified)
│   ├── anthropic_provider.py# Extract usage from Anthropic API (modified)
│   └── gemini_provider.py   # Extract usage from Google API (modified)
├── pricing.py               # NEW: Provider pricing + cost estimation
├── utils.py                 # call_llm() with usage logging (modified)
├── history_db.py            # llm_usage table + query functions (modified)
├── usage_cli.py             # NEW: CLI tool for usage analysis
├── llm_filter.py            # Add task_type="filter" (modified)
├── summarizer.py            # Add task_type="group"/"summarize" (modified)
└── query_engine.py          # Add task_type="query" (modified)

tests/
├── test_providers.py        # Update for tuple returns (modified +20 tests)
├── test_utils.py            # Update call_llm() tests (modified +5 tests)
├── test_history_db.py       # llm_usage table tests (modified +8 tests)
├── test_pricing.py          # NEW: Cost estimation tests (+5 tests)
├── test_usage_cli.py        # NEW: CLI command tests (+10 tests)
└── test_integration_usage.py# NEW: End-to-end tracking tests (+5 tests)
```

## Error Handling Strategy

1. **Provider Token Extraction**:
   ```python
   try:
       usage = extract_usage_from_response(resp_json)
   except (KeyError, TypeError) as e:
       logging.warning(f"Failed to extract usage: {e}")
       # Return default usage with 0 tokens
       usage = LLMUsageMetadata(0, 0, 0, model, provider)
   ```

2. **Database Logging**:
   ```python
   try:
       log_llm_usage(...)
   except Exception as e:
       logging.warning(f"Failed to log usage: {e}")
       # Continue execution - don't break the pipeline
   ```

3. **Cost Estimation**:
   ```python
   pricing = PROVIDER_PRICING.get(provider, {}).get(model)
   if not pricing:
       logging.warning(f"No pricing found for {provider}:{model}")
       return 0.0  # Return 0 cost rather than failing
   ```

## Testing Strategy

### Unit Tests
- Test each provider extracts usage correctly
- Test cost estimation with known inputs
- Test database logging functions
- Test CLI command parsing and output

### Integration Tests
- Test end-to-end: call_llm() → database entry created
- Test with all 4 providers
- Test with all 4 task types
- Verify cost calculation matches expected

### Existing Tests
- Update all provider tests to handle tuple returns
- Most changes: `response = provider.complete(...)` → `response, _ = provider.complete(...)`
- Or: `response = provider.complete(...)[0]`

## Backward Compatibility

### For Direct Provider Users (rare)
```python
# Old code (breaks after Sprint 12)
response = provider.complete(prompt="Hello")

# Fix option 1: Unpack tuple
response, usage = provider.complete(prompt="Hello")

# Fix option 2: Take first element
response = provider.complete(prompt="Hello")[0]
```

### For `call_llm()` Users (most code)
```python
# No changes needed!
response = call_llm(model, prompt, api_keys)
# Still returns str, but now logs usage automatically
```

### For Tests
```python
# Before Sprint 12
assert provider.complete(prompt="test") == "expected output"

# After Sprint 12
assert provider.complete(prompt="test")[0] == "expected output"
# or
response, usage = provider.complete(prompt="test")
assert response == "expected output"
assert usage.input_tokens > 0
```

## Performance Considerations

1. **Database Writes**: Non-blocking, failures don't stop pipeline
2. **Response Time**: Measured with minimal overhead (~1ms)
3. **Cost Calculation**: Simple arithmetic, negligible overhead
4. **Query Performance**: Indexes on provider, task_type, timestamp, model

## Future Enhancements

After Sprint 12, possible additions:
1. **Web Dashboard**: Visual charts and graphs for usage
2. **Alerts**: Email/Slack alerts for cost thresholds
3. **Budgets**: Monthly budget tracking and warnings
4. **Analytics**: Usage trends, forecasting, anomaly detection
5. **Optimization**: Automatic provider selection based on cost/performance
6. **Caching**: Cache expensive calls to reduce costs
