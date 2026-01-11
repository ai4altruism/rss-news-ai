# Development Progress

**Last Updated:** 2026-01-10
**Last Session:** Sprint 7 completed, production deployment updated

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
| **7** | **Provider Abstraction** | **30** | ✅ **Complete** |

**Total Tests:** 171 passing

### Sprint 7 Deliverables (Just Completed)
- `src/providers/base.py` - BaseProvider abstract class
- `src/providers/openai_provider.py` - OpenAI implementation (gpt-4 and gpt-5 support)
- `src/providers/__init__.py` - Provider factory with config parser
- Updated `src/utils.py` - New `call_llm()` + backward-compatible `call_responses_api()`
- `tests/test_providers.py` - 30 unit tests

**New Configuration Format:**
```bash
# Old format (still works)
FILTER_MODEL=gpt-4o-mini

# New format (provider:model)
FILTER_MODEL=openai:gpt-4o-mini
FILTER_MODEL=anthropic:claude-sonnet-4-20250514
FILTER_MODEL=google:gemini-2.0-flash
FILTER_MODEL=xai:grok-3-mini
```

## Next Up: Sprint 8 (xAI Grok Integration)

### Goal
Add xAI Grok support (easiest since it's OpenAI-compatible API).

### Tasks
1. Create `src/providers/xai_provider.py`
2. Register xAI in provider factory
3. Add `XAI_API_KEY` environment variable support
4. Write unit tests
5. Manual testing with real xAI API
6. Update documentation

### To Start Sprint 8
```bash
cd /Users/theo/work/rss-news-ai
source .venv/bin/activate
git checkout -b feature/sprint-8-xai-integration
```

## Key Files

| File | Purpose |
|------|---------|
| `docs/sdp.md` | Software Development Plan (Sprints 1-11) |
| `docs/sprint-*-summary.md` | Individual sprint summaries |
| `src/providers/` | LLM provider abstraction layer |
| `src/utils.py` | Main LLM calling utilities |
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
call_llm() or call_responses_api()
    ↓
get_provider(model_config)
    ↓
parse_model_config() → (provider_name, model_name)
    ↓
ProviderFactory → OpenAIProvider / XAIProvider / etc.
    ↓
provider.complete(prompt, instructions, max_tokens, temperature)
```

## Pending Items

1. **Sprint 8:** xAI Grok integration (1 week)
2. **Sprint 9:** Anthropic Claude integration (2 weeks)
3. **Sprint 10:** Google Gemini integration (2 weeks)
4. **Sprint 11:** Provider testing & hardening (1 week)

See `docs/sdp.md` for full sprint details and task breakdowns.
