# Development Progress

**Last Updated:** 2026-01-12
**Last Session:** Sprint 12 (Token Usage Monitoring) - Complete

## Current State

### Production Deployment (dive02)
- **Container:** `a4a-ai-news` running on dive02
- **Image:** `rss-news-ai:v2.0`
- **Status:** Running with mixed model configuration
- **Config location:** `~/a4a-ai-news/.env`

**Current .env model configuration:**
```bash
FILTER_MODEL=gpt-4o-mini      # Fast filtering (changed from gpt-5-mini)
GROUP_MODEL=gpt-5-mini        # Quality grouping
SUMMARIZE_MODEL=gpt-5-mini    # Quality summaries
QUERY_MODEL=gpt-5-mini        # Not used in Slack-only mode
```

**Docker run command:**
```bash
docker run -d \
  --name a4a-ai-news \
  --restart unless-stopped \
  -v /var/lib/rss-news-ai/data:/app/data \
  -v /var/lib/rss-news-ai/logs:/app/logs \
  -v ~/a4a-ai-news/.env:/app/.env:ro \
  --entrypoint python \
  rss-news-ai:v2.0 \
  src/scheduler.py --output slack
```

### Completed Sprints

| Sprint | Focus | Tests | Status |
|--------|-------|-------|--------|
| 1 | Database Foundation | 22 | ✅ Complete |
| 2 | CLI Query Interface | 17 | ✅ Complete |
| 3 | LLM Query Engine | 46 | ✅ Complete |
| 4 | Web Interface & API | 21 | ✅ Complete |
| 5 | Polish & Production | 13 | ✅ Complete |
| 6 | Security Hardening | 22 | ✅ Complete |
| 7 | Provider Abstraction | 30 | ✅ Complete |
| 8 | xAI Grok Integration | 13 | ✅ Complete |
| 9 | Anthropic Claude Integration | 15 | ✅ Complete |
| 10 | Google Gemini Integration | 17 | ✅ Complete |
| 11 | Provider Testing & Hardening | 45 | ✅ Complete |
| **12** | **Token Usage Monitoring** | **24** | ✅ Complete |

**Total Tests:** 285 passing

### Sprint 12 Deliverables (Complete)
- `src/history_db.py` - `llm_usage` table schema and query functions
- `src/providers/base.py` - `LLMUsageMetadata` dataclass
- `src/pricing.py` - Provider pricing and cost estimation
- Updated provider implementations - Token usage extraction
- `src/utils.py` - Usage logging in `call_llm()` with `task_type` parameter
- `src/usage_cli.py` - CLI tool for usage reporting
- Updated `src/llm_filter.py` - Uses `call_llm()` with `task_type="filter"`
- Updated `src/summarizer.py` - Uses `call_llm()` with `task_type="group"` and `task_type="summarize"`
- Updated `src/query_engine.py` - Uses `call_llm()` with `task_type="query"`

### Sprint 11 Deliverables (Complete)
- `tests/test_cross_provider.py` - 45 cross-provider integration tests
- Updated `README.md` - Provider comparison table and recommended configurations
- Cross-provider test coverage for all 4 providers
- Error handling consistency tests
- Backward compatibility verification

### Sprint 10 Deliverables (Complete)
- `src/providers/gemini_provider.py` - Google Gemini provider using Generative Language API
- Updated `src/providers/__init__.py` - Added GeminiProvider to factory
- Updated `tests/test_providers.py` - 17 new Gemini tests

### Sprint 9 Deliverables (Complete)
- `src/providers/anthropic_provider.py` - Anthropic Claude provider using Messages API
- Updated `src/providers/__init__.py` - Added AnthropicProvider to factory
- Updated `tests/test_providers.py` - 15 new Anthropic tests

### Sprint 8 Deliverables (Complete)
- `src/providers/xai_provider.py` - xAI Grok provider using OpenAI-compatible Chat Completions API
- Updated `src/providers/__init__.py` - Added XAIProvider to factory
- Updated `tests/test_providers.py` - 13 new xAI tests

### Sprint 7 Deliverables (Complete)
- `src/providers/base.py` - BaseProvider abstract class
- `src/providers/openai_provider.py` - OpenAI implementation (gpt-4 and gpt-5 support)
- `src/providers/__init__.py` - Provider factory with config parser
- Updated `src/utils.py` - New `call_llm()` + backward-compatible `call_responses_api()`
- `tests/test_providers.py` - 30 unit tests

**Configuration Format:**
```bash
# Old format (still works)
FILTER_MODEL=gpt-4o-mini

# New format (provider:model)
FILTER_MODEL=openai:gpt-4o-mini
FILTER_MODEL=xai:grok-3-mini
FILTER_MODEL=anthropic:claude-sonnet-4-20250514
FILTER_MODEL=google:gemini-2.0-flash
```

## Sprint 11: Final Sprint

### Completed Tasks
1. ~~Create cross-provider test suite~~ ✅ (45 tests)
2. ~~Add provider comparison documentation~~ ✅
3. ~~Error handling consistency tests~~ ✅
4. ~~Backward compatibility tests~~ ✅
5. ~~Update documentation~~ ✅
6. Create PR and merge

## 🎉 Multi-Provider LLM Support Complete!

All 4 LLM providers are fully implemented and tested:

| Provider | Models | Provider Tests | Cross-Provider Tests |
|----------|--------|----------------|---------------------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-5, gpt-5-mini | 30 | ✅ |
| **xAI** | grok-3, grok-3-mini | 13 | ✅ |
| **Anthropic** | claude-sonnet-4-20250514, claude-haiku | 15 | ✅ |
| **Google** | gemini-2.0-flash, gemini-pro | 17 | ✅ |

**Total Provider Tests:** 75 + 45 cross-provider + 24 usage = 144 provider-related tests
**Total All Tests:** 285 passing

### Key Achievements
- Clean provider abstraction with `BaseProvider` interface
- Backward compatible with existing configuration
- Mix-and-match providers for different tasks
- Comprehensive error handling for all providers
- Provider comparison and recommendation documentation

## Key Files

| File | Purpose |
|------|---------|
| `docs/sdp.md` | Software Development Plan (Sprints 1-12) |
| `docs/sprint-*-summary.md` | Individual sprint summaries |
| `src/providers/` | LLM provider abstraction layer |
| `src/utils.py` | Main LLM calling utilities |
| `src/pricing.py` | LLM pricing and cost estimation |
| `src/usage_cli.py` | Usage reporting CLI tool |
| `.env` | Local development config (not committed) |

## Development Environment

```bash
# Activate virtual environment
cd /Users/theo/work/rss-news-ai
source .venv/bin/activate

# Run tests
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_providers.py -v
```

## Production Commands (dive02)

```bash
# SSH to server
ssh theo@dive02

# Check container status
docker ps | grep a4a-ai-news
docker logs -f a4a-ai-news

# Restart container
docker stop a4a-ai-news && docker rm a4a-ai-news
# Then run docker run command above

# Check historical database
sqlite3 /var/lib/rss-news-ai/data/history.db "SELECT COUNT(*) FROM summaries;"
```

## Notes

### gpt-5-mini Quirks
- Does NOT support `temperature` parameter
- Uses reasoning tokens that count against `max_output_tokens`
- Returns response as `[reasoning_block, message_block]`
- Use `reasoning: {effort: "low"}` for faster responses
- All handled in `OpenAIProvider._is_gpt5_model()`

### Provider Architecture
```
call_llm(task_type="filter") or call_responses_api()
    ↓
get_provider(model_config)
    ↓
parse_model_config() → (provider_name, model_name)
    ↓
ProviderFactory → OpenAIProvider / XAIProvider / etc.
    ↓
provider.complete() → (response_text, LLMUsageMetadata)
    ↓
_log_usage() → saves to llm_usage table (non-fatal)
```

## 🎉 All Sprints Complete!

**Sprint 12: Token Usage Monitoring** ✅ Complete (2026-01-12)

All 12 sprints have been completed. Sprint 12 features:
- Token usage tracking across all 4 providers
- Cost estimation based on provider pricing
- Response time tracking
- SQLite persistence in `llm_usage` table
- CLI tool for usage reporting (`src/usage_cli.py`)
- Task type labeling: filter, group, summarize, query

### Usage CLI Commands
```bash
python src/usage_cli.py stats         # Overall statistics
python src/usage_cli.py by-provider   # Breakdown by provider
python src/usage_cli.py by-task       # Breakdown by task type
python src/usage_cli.py by-model      # Breakdown by model
python src/usage_cli.py costs         # Cost analysis
python src/usage_cli.py export        # Export to CSV
```

See `docs/sdp.md` and `docs/sprint-12-summary.md` for full sprint details.
