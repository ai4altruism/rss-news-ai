# Software Development Plan: RSS News AI

## Document Information
- **Version**: 1.0
- **Last Updated**: 2026-01-10
- **Sprint Duration**: 1-2 weeks
- **Source Documents**:
  - README.md
  - Sprint Summaries (Sprint 1-6)

## 1. Project Overview

### 1.1 Project Summary
RSS News AI is a Python-based application that monitors RSS feeds for generative AI news, filters relevant stories using LLM APIs, groups them by topic, and presents summaries through multiple output formats including web dashboard, Slack, and email. The application includes a SQLite database for historical storage, natural language query capabilities, and comprehensive security features.

### 1.2 Success Criteria
- All core features operational: RSS monitoring, LLM filtering, topic grouping, summarization
- Multi-provider LLM support with seamless configuration and switching
- Historical database with natural language query interface
- Web dashboard with responsive design
- Production-ready with security hardening (authentication, rate limiting, input validation)
- Test coverage above 80% for new features
- Clean provider abstraction allowing easy addition of future LLM providers

### 1.3 Timeline Overview
| Phase | Duration | Status | Dates |
|-------|----------|--------|-------|
| Sprint 1: Database Foundation | 1 week | **Complete** | 2025-12-13 |
| Sprint 2: CLI Query Interface | 1 week | **Complete** | 2025-12-13 |
| Sprint 3: LLM Query Engine | 1 week | **Complete** | 2025-12-13 |
| Sprint 4: Web Interface & API | 1 week | **Complete** | 2025-12-13 |
| Sprint 5: Polish & Production Readiness | 1 week | **Complete** | 2025-12-13 |
| Sprint 6: Security Hardening | 1 week | **Complete** | 2025-12-14 |
| Sprint 7: Multi-Provider Abstraction | 1 week | **Complete** | 2026-01-07 |
| Sprint 8: xAI Grok Integration | 1 week | **Complete** | 2026-01-08 |
| Sprint 9: Anthropic Claude Integration | 2 weeks | **Complete** | 2026-01-08 |
| Sprint 10: Google Gemini Integration | 2 weeks | **Complete** | 2026-01-10 |
| Sprint 11: Provider Testing & Hardening | 1 week | **Complete** | 2026-01-11 |
| Sprint 12: Token Usage Monitoring | 1 week | **Complete** | 2026-01-12 |

## 2. Team and Resources

### 2.1 Roles and Responsibilities
| Role | Responsibilities | Tools/Agents |
|------|-----------------|--------------|
| Backend Development | LLM provider integration, API abstraction | python-backend |
| Testing | Unit tests, integration tests, provider-specific tests | test-engineer |
| Documentation | README updates, API documentation, provider guides | technical-writer |
| Project Planning | Sprint planning, requirements, tracking | - |

### 2.2 Tools and Infrastructure
| Category | Tool | Purpose |
|----------|------|---------|
| Version Control | Git/GitHub | Code repository |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Testing | pytest | Unit and integration tests |
| Dependency Management | pip, requirements.txt | Python package management |
| Database | SQLite | Historical data storage |
| Web Framework | Flask | REST API and web dashboard |
| LLM Providers | OpenAI, Anthropic, Google, xAI | Model inference |

## 3. Git Workflow

### 3.1 Branching Strategy
```
master (production)
  ├── feature/sprint-7-provider-abstraction
  ├── feature/sprint-8-xai-integration
  ├── feature/sprint-9-anthropic-integration
  ├── feature/sprint-10-gemini-integration
  └── feature/sprint-11-provider-testing
```

### 3.2 Branch Naming Convention
| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/sprint-N-description` | `feature/sprint-7-provider-abstraction` |
| Bug Fix | `fix/issue-description` | `fix/anthropic-streaming-error` |
| Hotfix | `hotfix/description` | `hotfix/api-key-validation` |

### 3.3 Commit Message Convention
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(providers): add Anthropic Claude provider support

- Implement AnthropicProvider class with Messages API
- Add streaming support for Claude models
- Add Claude-specific error handling

Implements: Sprint 9
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### 3.4 Pull Request Process
1. Create feature branch from `master`
2. Implement changes with comprehensive tests
3. Create PR with description template
4. Pass automated checks (lint, test, build)
5. Code review approval
6. Merge to `master` with squash

### 3.5 Release Process
1. All sprint tests passing
2. Update version in relevant files
3. Update README with new provider documentation
4. Create release tag (e.g., `v2.0.0`)
5. Deploy to production

## 4. Testing Strategy

### 4.1 Testing Levels
| Level | Scope | Coverage Target | Agent | When |
|-------|-------|-----------------|-------|------|
| Unit | Functions, classes | 85% | test-engineer | Every commit |
| Integration | Provider API calls, end-to-end flows | 75% | test-engineer | Every PR |
| Manual | Provider-specific behavior, UI testing | Key scenarios | - | Pre-release |

### 4.2 Testing Requirements per Sprint
- All new provider classes must have unit tests (test-engineer)
- Provider integration tests with mocked API responses
- Error handling tests for rate limits, auth failures, malformed responses
- Configuration validation tests
- Test coverage must not decrease below current baseline (141 tests passing)
- Critical user flows need integration coverage

### 4.3 Definition of Done
- [ ] Code complete and follows Python style guidelines (PEP 8)
- [ ] Unit tests written and passing (85%+ coverage for new code)
- [ ] Integration tests written and passing
- [ ] Provider-specific documentation added
- [ ] Code reviewed and approved
- [ ] No known critical or high-severity defects
- [ ] README updated with provider usage examples
- [ ] Merged to master branch

## 5. Completed Sprints (1-6)

### Sprint 1: Database Foundation (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-1-database-foundation`
**Completed**: 2025-12-13
**Tests**: 22 passed

#### Goal
Start persisting data immediately so history begins accumulating.

#### Deliverables
| Component | Status |
|-----------|--------|
| `src/history_db.py` - SQLite database operations | ✅ |
| `src/history_cli.py` - CLI with init, import, stats | ✅ |
| Database schema (summaries, topics, articles, aliases) | ✅ |
| Auto-save from main pipeline | ✅ |
| 22 unit tests for database operations | ✅ |

#### Key Features
- Database schema with summaries, topics, articles, and topic_aliases tables
- Auto-initialization on first save
- Topic name normalization for consistent querying
- CLI commands: `init`, `import`, `stats`
- Non-fatal database saves (main pipeline continues on errors)

---

### Sprint 2: CLI Query Interface (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-2-cli-queries`
**Completed**: 2025-12-13
**Tests**: 39 passed (22 from Sprint 1 + 17 new)

#### Goal
Working command-line queries against historical data with trend analysis and search capabilities.

#### Deliverables
| Component | Status |
|-----------|--------|
| `topic_counts_by_period()` - Trends over time | ✅ |
| `top_topics_comparison()` - Compare two periods | ✅ |
| `topic_search()` - Search topics by name | ✅ |
| `get_date_range()` - Database date range | ✅ |
| CLI commands: trends, compare, search | ✅ |
| Table and JSON output formats | ✅ |
| 17 new unit tests for query functions | ✅ |

#### Key Features
- Trend analysis by day/week/month
- Period comparison (e.g., Q1 vs Q2)
- Topic search with date filtering
- Flexible output formats (table, JSON)

---

### Sprint 3: LLM Query Engine (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-3-llm-query-engine`
**Completed**: 2025-12-13
**Tests**: 85 passed (39 from Sprint 1-2 + 46 new)

#### Goal
Natural language queries powered by LLM with function calling and SQL safety guardrails.

#### Deliverables
| Component | Status |
|-----------|--------|
| `src/query_engine.py` - LLM-powered query classification | ✅ |
| SQL validation and guardrails | ✅ |
| Natural language query classification | ✅ |
| CLI command: `query` | ✅ |
| `QUERY_MODEL` environment variable | ✅ |
| 46 new tests (SQL guardrails, classification, formatting) | ✅ |

#### Key Features
- LLM classifies queries into: trends, comparison, search, or custom SQL
- SQL guardrails: SELECT-only, forbidden keywords, read-only connection
- Natural language understanding (relative dates, Q1/Q2, etc.)
- Rich responses with article URLs
- Configurable query model separate from filtering/summarization

---

### Sprint 4: Web Interface & API (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-4-web-interface`
**Completed**: 2025-12-13
**Tests**: 106 passed (85 from Sprint 1-3 + 21 new)

#### Goal
Browser-based query interface and REST API endpoints for historical news data.

#### Deliverables
| Component | Status |
|-----------|--------|
| 6 new API endpoints (/api/history/stats, /api/trends, etc.) | ✅ |
| `templates/history.html` - Chat interface | ✅ |
| Docker volume configuration | ✅ |
| 21 new API endpoint tests | ✅ |

#### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/history` | GET | History query interface page |
| `/api/history/stats` | GET | Database statistics |
| `/api/trends` | GET | Topic trends over time |
| `/api/compare` | GET | Compare two time periods |
| `/api/topics` | GET | Search topics by name |
| `/api/query` | POST | Natural language query |

#### Key Features
- Chat-style natural language query interface
- Database statistics dashboard
- Interactive Chart.js visualizations
- Responsive Bootstrap 5 design
- Docker deployment with volume mounts for database persistence

---

### Sprint 5: Polish & Production Readiness (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-5-production-ready`
**Completed**: 2025-12-13
**Tests**: 119 passed (106 from Sprint 1-4 + 13 new)

#### Goal
Production-ready feature with topic alias management, data export, and documentation.

#### Deliverables
| Component | Status |
|-----------|--------|
| Topic alias management (add, remove, list) | ✅ |
| Data export (CSV, JSON) | ✅ |
| CLI commands: `alias`, `export` | ✅ |
| Comprehensive README documentation | ✅ |
| 13 new tests (aliases, export) | ✅ |

#### Key Features
- Topic alias normalization (e.g., "OpenAI News" → "OpenAI")
- Export topics and articles to CSV
- Export complete database to JSON for backup
- Updated README with all features documented
- Production-ready Docker deployment guide

---

### Sprint 6: Security Hardening (COMPLETE)
**Status**: ✅ Complete
**Branch**: `feature/sprint-6-security-hardening`
**Completed**: 2025-12-14
**Tests**: 141 passed (119 from Sprint 1-5 + 22 new)

#### Goal
Secure all exposed endpoints and harden the application for production deployment.

#### Deliverables
| Component | Priority | Status |
|-----------|----------|--------|
| API key authentication (X-API-Key header) | High | ✅ |
| Rate limiting (Flask-Limiter) | High | ✅ |
| Security headers (Flask-Talisman) | High | ✅ |
| Input validation and sanitization | Medium | ✅ |
| LLM prompt injection mitigation | Medium | ✅ |
| Error handling (generic messages in prod) | Medium | ✅ |
| CORS configuration (Flask-CORS) | Low | ✅ |
| Audit logging (security.log) | Low | ✅ |
| 22 new security tests | - | ✅ |

#### Key Features
- API key authentication required for all `/api/*` endpoints
- Rate limiting: 200/day, 100/hour for API; 10/min for LLM queries
- Security headers: CSP, X-Frame-Options, HSTS
- Input validation: length limits, date format validation, sanitization
- Prompt injection detection with pattern matching
- Comprehensive audit logging
- Production deployment checklist

---

## 6. New Sprint Plans: Multi-Provider LLM Support

### Sprint 7: Multi-Provider Abstraction Layer (NEW)
**Goal**: Create a clean provider abstraction layer that allows seamless switching between LLM providers without changing calling code.

**Duration**: 1 week
**Status**: Planned

#### Requirements Addressed
- **FR-7.1**: Provider abstraction layer (Must Have)
- **FR-7.2**: Configuration format with provider:model syntax (Must Have)
- **FR-7.3**: Backward compatibility with existing config (Must Have)
- **FR-7.4**: Provider-specific error handling (Should Have)
- **FR-7.5**: Token usage tracking per provider (Could Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S7-1 | Design provider abstraction interface (BaseProvider class) | M | None | FR-7.1 |
| S7-2 | Create `src/providers/base.py` with abstract base class | M | S7-1 | FR-7.1 |
| S7-3 | Create `src/providers/openai_provider.py` (refactor existing) | L | S7-2 | FR-7.1 |
| S7-4 | Implement model config parser (parse "provider:model" format) | S | S7-2 | FR-7.2 |
| S7-5 | Add backward compatibility layer (detect old vs new config) | M | S7-4 | FR-7.3 |
| S7-6 | Update `utils.py` to use provider abstraction | L | S7-3 | FR-7.1 |
| S7-7 | Add provider factory pattern for instantiation | M | S7-3, S7-6 | FR-7.1 |
| S7-8 | Write unit tests for base provider and factory | M | S7-2, S7-7 | - |
| S7-9 | Write unit tests for OpenAI provider | M | S7-3 | - |
| S7-10 | Write integration tests for backward compatibility | M | S7-5 | FR-7.3 |
| S7-11 | Update documentation for new config format | S | S7-4 | - |
| S7-12 | Test with existing LLM calls (filter, summarize, query) | L | S7-6 | - |

**Effort Key**: S = 2-4h, M = 4-8h, L = 8-16h

#### Deliverables
- `src/providers/` directory structure
- `src/providers/base.py` - BaseProvider abstract class
- `src/providers/openai_provider.py` - OpenAI implementation
- `src/providers/__init__.py` - Provider factory
- Updated `src/utils.py` using provider abstraction
- Configuration parser supporting both formats:
  - Old: `FILTER_MODEL=gpt-4o-mini`
  - New: `FILTER_MODEL=openai:gpt-4o-mini`
- Backward compatibility tests
- Unit tests: 15+ new tests

#### Provider Interface Design
```python
class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, instructions: str = "",
                 max_tokens: int = 500, temperature: float = 1.0) -> str:
        """Generate completion for given prompt."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration (API key, etc.)."""
        pass
```

#### Git Operations
- Create branch: `feature/sprint-7-provider-abstraction`
- Daily commits with conventional messages
- PR review before merge to `master`

#### Testing Milestones
- Day 3: Base provider and factory tests complete
- Day 5: OpenAI provider tests complete
- Day 7: All integration tests passing, backward compatibility verified

---

### Sprint 8: xAI Grok Integration (NEW)
**Goal**: Add xAI Grok support (easiest since it's OpenAI-compatible).

**Duration**: 1 week
**Status**: Planned

#### Requirements Addressed
- **FR-8.1**: xAI Grok provider implementation (Must Have)
- **FR-8.2**: Support for grok-3-mini, grok-3 models (Must Have)
- **FR-8.3**: OpenAI-compatible API adapter (Must Have)
- **FR-8.4**: xAI-specific error handling (Should Have)
- **FR-8.5**: Configuration validation for xAI API keys (Must Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S8-1 | Research xAI API differences from OpenAI | S | Sprint 7 | FR-8.3 |
| S8-2 | Create `src/providers/xai_provider.py` | M | S8-1 | FR-8.1 |
| S8-3 | Implement OpenAI-compatible adapter | M | S8-2 | FR-8.3 |
| S8-4 | Add xAI-specific error handling (rate limits, quotas) | S | S8-2 | FR-8.4 |
| S8-5 | Add xAI API key configuration validation | S | S8-2 | FR-8.5 |
| S8-6 | Update provider factory to include xAI | S | S8-2 | FR-8.1 |
| S8-7 | Write unit tests for xAI provider | M | S8-2 | - |
| S8-8 | Write integration tests with mocked xAI API | M | S8-7 | - |
| S8-9 | Manual testing with real xAI API (grok-3-mini) | M | S8-2 | FR-8.2 |
| S8-10 | Update .env.example with xAI configuration | S | S8-5 | - |
| S8-11 | Update README with xAI usage examples | S | S8-9 | - |

#### Deliverables
- `src/providers/xai_provider.py` - xAI Grok provider
- xAI configuration validation
- Environment variables:
  - `XAI_API_KEY` - xAI API key
  - Example: `FILTER_MODEL=xai:grok-3-mini`
- Unit tests: 10+ new tests
- Integration tests with mocked API responses
- README section for xAI Grok usage
- Manual test results with real xAI API

#### Configuration Example
```bash
# .env
XAI_API_KEY=xai-...
FILTER_MODEL=xai:grok-3-mini
GROUP_MODEL=openai:gpt-4o-mini
SUMMARIZE_MODEL=xai:grok-3
QUERY_MODEL=openai:gpt-4o-mini
```

#### Git Operations
- Create branch: `feature/sprint-8-xai-integration`
- PR review with xAI test results

#### Testing Milestones
- Day 3: Unit tests complete
- Day 5: Integration tests with mocked API complete
- Day 7: Manual testing complete, documentation updated

---

### Sprint 9: Anthropic Claude Integration (NEW)
**Goal**: Add Anthropic Claude support with Messages API.

**Duration**: 2 weeks
**Status**: Planned

#### Requirements Addressed
- **FR-9.1**: Anthropic Claude provider implementation (Must Have)
- **FR-9.2**: Support for claude-sonnet-4-20250514, claude-haiku, etc. (Must Have)
- **FR-9.3**: Anthropic Messages API integration (Must Have)
- **FR-9.4**: Request/response format conversion (Must Have)
- **FR-9.5**: Claude-specific error handling (Should Have)
- **FR-9.6**: Streaming support for Claude models (Could Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S9-1 | Research Anthropic Messages API documentation | M | Sprint 7 | FR-9.3 |
| S9-2 | Create `src/providers/anthropic_provider.py` | L | S9-1 | FR-9.1 |
| S9-3 | Implement request format conversion (prompt → messages) | L | S9-2 | FR-9.4 |
| S9-4 | Implement response format conversion (content → text) | M | S9-2 | FR-9.4 |
| S9-5 | Add Claude-specific error handling (rate limits, overloaded) | M | S9-2 | FR-9.5 |
| S9-6 | Handle Claude system prompts vs user messages | M | S9-3 | FR-9.4 |
| S9-7 | Add support for claude-sonnet-4-20250514 | S | S9-2 | FR-9.2 |
| S9-8 | Add support for claude-haiku models | S | S9-2 | FR-9.2 |
| S9-9 | Add Anthropic API key validation | S | S9-2 | FR-9.1 |
| S9-10 | Update provider factory to include Anthropic | S | S9-2 | FR-9.1 |
| S9-11 | Write unit tests for Anthropic provider | L | S9-2 | - |
| S9-12 | Write integration tests with mocked Anthropic API | L | S9-11 | - |
| S9-13 | Manual testing with real Anthropic API | L | S9-2 | FR-9.2 |
| S9-14 | Test with filtering, grouping, summarization workloads | L | S9-13 | - |
| S9-15 | Add streaming support (optional) | M | S9-2 | FR-9.6 |
| S9-16 | Update .env.example with Anthropic configuration | S | S9-9 | - |
| S9-17 | Update README with Anthropic usage examples | M | S9-13 | - |

#### Deliverables
- `src/providers/anthropic_provider.py` - Anthropic Claude provider
- Request/response format conversion utilities
- Claude-specific error handling for 529 (overloaded), rate limits
- Environment variables:
  - `ANTHROPIC_API_KEY` - Anthropic API key
  - Example: `FILTER_MODEL=anthropic:claude-sonnet-4-20250514`
- Unit tests: 15+ new tests
- Integration tests with mocked API responses
- README section for Anthropic Claude usage
- Manual test results with real Anthropic API
- Optional: Streaming support for real-time responses

#### Key Technical Considerations
- **Request Format**: Anthropic uses `messages` array instead of single `prompt` string
  ```python
  # OpenAI format
  {"prompt": "Hello", "instructions": "Be helpful"}

  # Anthropic format
  {"messages": [{"role": "user", "content": "Hello"}],
   "system": "Be helpful"}
  ```
- **Response Format**: Anthropic returns `content` array with text blocks
- **Error Codes**: 529 (overloaded), 529 (rate limit) need retry logic
- **Model Names**: Full version strings (e.g., `claude-sonnet-4-20250514`)

#### Configuration Example
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
FILTER_MODEL=anthropic:claude-haiku-20250320
GROUP_MODEL=anthropic:claude-sonnet-4-20250514
SUMMARIZE_MODEL=anthropic:claude-sonnet-4-20250514
QUERY_MODEL=openai:gpt-4o-mini
```

#### Git Operations
- Create branch: `feature/sprint-9-anthropic-integration`
- PR review with Anthropic test results

#### Testing Milestones
- Week 1, Day 3: Unit tests complete
- Week 1, Day 5: Integration tests with mocked API complete
- Week 2, Day 3: Manual testing complete
- Week 2, Day 5: Documentation and streaming (optional) complete

---

### Sprint 10: Google Gemini Integration (NEW)
**Goal**: Add Google Gemini support with Generative Language API.

**Duration**: 2 weeks
**Status**: Planned

#### Requirements Addressed
- **FR-10.1**: Google Gemini provider implementation (Must Have)
- **FR-10.2**: Support for gemini-2.0-flash, gemini-pro models (Must Have)
- **FR-10.3**: Google Generative Language API integration (Must Have)
- **FR-10.4**: Request/response format conversion for Gemini (Must Have)
- **FR-10.5**: Gemini-specific error handling (Should Have)
- **FR-10.6**: Safety settings configuration (Should Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S10-1 | Research Google Gemini API documentation | M | Sprint 7 | FR-10.3 |
| S10-2 | Create `src/providers/gemini_provider.py` | L | S10-1 | FR-10.1 |
| S10-3 | Implement request format conversion (prompt → parts) | L | S10-2 | FR-10.4 |
| S10-4 | Implement response format conversion (candidates → text) | M | S10-2 | FR-10.4 |
| S10-5 | Add Gemini-specific error handling | M | S10-2 | FR-10.5 |
| S10-6 | Implement safety settings configuration | M | S10-2 | FR-10.6 |
| S10-7 | Handle Gemini generation config (temperature, max_tokens) | M | S10-2 | FR-10.4 |
| S10-8 | Add support for gemini-2.0-flash | S | S10-2 | FR-10.2 |
| S10-9 | Add support for gemini-pro | S | S10-2 | FR-10.2 |
| S10-10 | Add Google API key validation | S | S10-2 | FR-10.1 |
| S10-11 | Update provider factory to include Google | S | S10-2 | FR-10.1 |
| S10-12 | Write unit tests for Gemini provider | L | S10-2 | - |
| S10-13 | Write integration tests with mocked Gemini API | L | S10-12 | - |
| S10-14 | Manual testing with real Gemini API | L | S10-2 | FR-10.2 |
| S10-15 | Test with filtering, grouping, summarization workloads | L | S10-14 | - |
| S10-16 | Handle safety filter blocks gracefully | M | S10-6 | FR-10.6 |
| S10-17 | Update .env.example with Google configuration | S | S10-10 | - |
| S10-18 | Update README with Google Gemini usage examples | M | S10-14 | - |

#### Deliverables
- `src/providers/gemini_provider.py` - Google Gemini provider
- Request/response format conversion for Gemini API
- Safety settings configuration
- Gemini-specific error handling (safety blocks, quota errors)
- Environment variables:
  - `GOOGLE_API_KEY` - Google API key
  - `GEMINI_SAFETY_SETTINGS` - Optional safety configuration
  - Example: `FILTER_MODEL=google:gemini-2.0-flash`
- Unit tests: 15+ new tests
- Integration tests with mocked API responses
- README section for Google Gemini usage
- Manual test results with real Gemini API

#### Key Technical Considerations
- **Request Format**: Gemini uses `contents` array with `parts`
  ```python
  # Gemini format
  {"contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
   "generationConfig": {"temperature": 0.5, "maxOutputTokens": 500}}
  ```
- **Response Format**: Gemini returns `candidates` array with `content.parts`
- **Safety Settings**: Control thresholds for hate, harassment, dangerous content
- **Error Handling**: Safety filter blocks, quota exceeded, invalid API key
- **Model Names**: Use `models/gemini-2.0-flash` or `gemini-2.0-flash` format

#### Configuration Example
```bash
# .env
GOOGLE_API_KEY=AIza...
FILTER_MODEL=google:gemini-2.0-flash
GROUP_MODEL=google:gemini-pro
SUMMARIZE_MODEL=anthropic:claude-sonnet-4-20250514
QUERY_MODEL=openai:gpt-4o-mini
```

#### Git Operations
- Create branch: `feature/sprint-10-gemini-integration`
- PR review with Gemini test results

#### Testing Milestones
- Week 1, Day 3: Unit tests complete
- Week 1, Day 5: Integration tests with mocked API complete
- Week 2, Day 3: Manual testing complete
- Week 2, Day 5: Documentation and safety settings complete

---

### Sprint 11: Provider Testing & Hardening (NEW)
**Goal**: Comprehensive testing across all providers, performance benchmarking, and production hardening.

**Duration**: 1 week
**Status**: Planned

#### Requirements Addressed
- **FR-11.1**: Cross-provider integration tests (Must Have)
- **FR-11.2**: Performance benchmarking per provider (Should Have)
- **FR-11.3**: Error recovery and fallback mechanisms (Should Have)
- **FR-11.4**: Provider health checks (Could Have)
- **FR-11.5**: Documentation completeness (Must Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S11-1 | Create cross-provider test suite | L | Sprints 7-10 | FR-11.1 |
| S11-2 | Test same prompt across all 4 providers | M | S11-1 | FR-11.1 |
| S11-3 | Benchmark response times per provider | M | S11-1 | FR-11.2 |
| S11-4 | Benchmark cost per 1000 tokens per provider | M | S11-1 | FR-11.2 |
| S11-5 | Test error handling for all providers (rate limits, auth) | L | S11-1 | FR-11.1 |
| S11-6 | Implement provider fallback mechanism (optional) | L | S11-5 | FR-11.3 |
| S11-7 | Add provider health check endpoint (optional) | M | All providers | FR-11.4 |
| S11-8 | Update README with comprehensive provider guide | M | All providers | FR-11.5 |
| S11-9 | Create provider comparison table (cost, speed, quality) | S | S11-3, S11-4 | FR-11.5 |
| S11-10 | Add troubleshooting guide for provider issues | M | S11-5 | FR-11.5 |
| S11-11 | Verify all 141+ existing tests still pass | M | All providers | - |
| S11-12 | End-to-end test: full pipeline with each provider | L | All providers | FR-11.1 |

#### Deliverables
- Cross-provider test suite (20+ tests)
- Performance benchmark results
- Provider comparison table (cost, speed, quality)
- Updated README with comprehensive provider guide
- Troubleshooting documentation
- Optional: Provider fallback mechanism
- Optional: Health check API endpoint
- All tests passing (141+ base + 75+ new = 216+ total)

#### Provider Comparison Table (Example)
| Provider | Model | Cost (per 1M tokens) | Avg Response Time | Quality Score |
|----------|-------|---------------------|-------------------|---------------|
| OpenAI | gpt-4o-mini | Input: $0.15, Output: $0.60 | 1.2s | 9/10 |
| OpenAI | gpt-4o | Input: $2.50, Output: $10.00 | 2.5s | 10/10 |
| xAI | grok-3-mini | TBD | TBD | TBD |
| Anthropic | claude-haiku-20250320 | Input: $0.25, Output: $1.25 | 0.8s | 8/10 |
| Anthropic | claude-sonnet-4-20250514 | Input: $3.00, Output: $15.00 | 2.0s | 10/10 |
| Google | gemini-2.0-flash | Input: $0.075, Output: $0.30 | 1.0s | 8/10 |
| Google | gemini-pro | Input: $0.50, Output: $1.50 | 1.5s | 9/10 |

#### Configuration Examples
```bash
# Mix and match providers for different tasks
FILTER_MODEL=google:gemini-2.0-flash      # Fast, cheap filtering
GROUP_MODEL=anthropic:claude-haiku-20250320  # Fast, accurate grouping
SUMMARIZE_MODEL=anthropic:claude-sonnet-4-20250514  # High-quality summaries
QUERY_MODEL=openai:gpt-4o-mini            # Cost-effective queries

# All Anthropic
FILTER_MODEL=anthropic:claude-haiku-20250320
GROUP_MODEL=anthropic:claude-haiku-20250320
SUMMARIZE_MODEL=anthropic:claude-sonnet-4-20250514
QUERY_MODEL=anthropic:claude-haiku-20250320

# All Google
FILTER_MODEL=google:gemini-2.0-flash
GROUP_MODEL=google:gemini-pro
SUMMARIZE_MODEL=google:gemini-pro
QUERY_MODEL=google:gemini-2.0-flash
```

#### Git Operations
- Create branch: `feature/sprint-11-provider-testing`
- Final PR review with comprehensive test results
- Merge to `master` and create v2.0.0 release tag

#### Testing Milestones
- Day 2: Cross-provider tests complete
- Day 4: Performance benchmarks complete
- Day 6: Documentation complete
- Day 7: All tests passing, ready for release

---

### Sprint 12: Token Usage Monitoring (COMPLETE)
**Goal**: Track and persist token usage, costs, and performance metrics for all LLM calls across providers.

**Duration**: 1 week
**Status**: ✅ Complete
**Completed**: 2026-01-12
**Tests**: 24 new tests (285 total)

#### Requirements Addressed
- **FR-12.1**: SQLite table for token usage tracking (Must Have)
- **FR-12.2**: Capture usage metrics from all provider APIs (Must Have)
- **FR-12.3**: Modified provider interface to return usage metadata (Must Have)
- **FR-12.4**: Cost estimation per call using provider pricing (Should Have)
- **FR-12.5**: CLI script for usage reporting and analysis (Must Have)
- **FR-12.6**: Response time tracking per LLM call (Should Have)

#### Task Breakdown
| Task ID | Task | Effort | Dependencies | Requirement |
|---------|------|--------|--------------|-------------|
| S12-1 | Design `llm_usage` database schema | S | None | FR-12.1 |
| S12-2 | Add `llm_usage` table to `history_db.py` | M | S12-1 | FR-12.1 |
| S12-3 | Create pricing table/config for all 4 providers | S | None | FR-12.4 |
| S12-4 | Design `LLMUsageMetadata` dataclass for return values | S | None | FR-12.3 |
| S12-5 | Modify `BaseProvider.complete()` to return tuple (text, metadata) | M | S12-4 | FR-12.3 |
| S12-6 | Update `OpenAIProvider` to extract token usage from API response | M | S12-5 | FR-12.2 |
| S12-7 | Update `XAIProvider` to extract token usage from API response | S | S12-5 | FR-12.2 |
| S12-8 | Update `AnthropicProvider` to extract token usage from API response | M | S12-5 | FR-12.2 |
| S12-9 | Update `GeminiProvider` to extract token usage from API response | M | S12-5 | FR-12.2 |
| S12-10 | Update `call_llm()` in `utils.py` to log usage to database | L | S12-2, S12-5 | FR-12.2 |
| S12-11 | Add response time measurement to `call_llm()` | S | S12-10 | FR-12.6 |
| S12-12 | Create cost estimation utility function | M | S12-3 | FR-12.4 |
| S12-13 | Create `src/usage_cli.py` with usage query commands | L | S12-2 | FR-12.5 |
| S12-14 | Add usage reporting functions to `history_db.py` | M | S12-2 | FR-12.5 |
| S12-15 | Write unit tests for usage tracking | M | S12-2, S12-10 | - |
| S12-16 | Write unit tests for provider metadata extraction | L | S12-6-S12-9 | - |
| S12-17 | Write unit tests for cost estimation | S | S12-12 | - |
| S12-18 | Write integration tests for end-to-end usage tracking | M | S12-10 | - |
| S12-19 | Update existing tests to handle new return signature | L | S12-5 | - |
| S12-20 | Update README with usage monitoring documentation | M | S12-13 | - |

**Effort Key**: S = 2-4h, M = 4-8h, L = 8-16h

#### Deliverables
- **Database Schema**:
  - New `llm_usage` table in `history_db.py`
  - Indexes for common query patterns (provider, task_type, date)
- **Provider Modifications**:
  - `src/providers/base.py` - Updated interface with `LLMUsageMetadata` dataclass
  - All 4 provider implementations updated to extract and return usage
- **Usage Tracking**:
  - Updated `src/utils.py` - `call_llm()` logs usage to database
  - `src/usage_cli.py` - CLI for usage analysis
  - Usage query functions in `history_db.py`
- **Cost Estimation**:
  - Provider pricing configuration (`src/pricing.py`)
  - Cost calculation utility
- **Testing**:
  - Unit tests: 20+ new tests
  - Integration tests: 5+ new tests
  - Updated existing tests: ~261 tests updated
- **Documentation**:
  - README section on usage monitoring
  - Usage CLI command examples

#### Database Schema Design

```sql
-- Track token usage and costs per LLM call
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

#### Provider Interface Changes

```python
# src/providers/base.py
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class LLMUsageMetadata:
    """Metadata about an LLM API call."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    provider: str
    response_time_ms: Optional[int] = None

    def __post_init__(self):
        # Ensure total_tokens is correct
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        instructions: str = "",
        max_tokens: int = 500,
        temperature: float = 1.0,
    ) -> Tuple[str, LLMUsageMetadata]:
        """
        Generate a completion for the given prompt.

        Returns:
            Tuple of (response_text, usage_metadata)
        """
        pass
```

#### Cost Estimation Configuration

```python
# src/pricing.py
"""
Provider pricing configuration for cost estimation.
Prices are per 1 million tokens (USD).
Updated as of January 2026.
"""

PROVIDER_PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-5": {"input": 10.00, "output": 30.00},
        "gpt-5-mini": {"input": 1.00, "output": 4.00},
    },
    "xai": {
        "grok-3": {"input": 2.00, "output": 10.00},
        "grok-3-mini": {"input": 0.20, "output": 0.80},
    },
    "anthropic": {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-20250320": {"input": 0.25, "output": 1.25},
        "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    },
    "google": {
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
        "gemini-pro": {"input": 0.50, "output": 1.50},
        "gemini-2.0-flash-thinking": {"input": 0.075, "output": 0.30},
    },
}


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate cost in USD for an LLM call.

    Args:
        provider: Provider name ('openai', 'xai', 'anthropic', 'google')
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD, or 0.0 if pricing not found
    """
    pricing = PROVIDER_PRICING.get(provider, {}).get(model)
    if not pricing:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
```

#### Usage CLI Examples

```bash
# Show overall usage statistics
python src/usage_cli.py stats

# Output:
# Token Usage Statistics
# =====================
# Total Calls: 1,247
# Total Input Tokens: 542,893
# Total Output Tokens: 89,234
# Total Tokens: 632,127
# Estimated Total Cost: $12.45 USD

# Usage by provider
python src/usage_cli.py by-provider

# Output:
# Provider      Calls    Input Tokens    Output Tokens    Cost (USD)
# ----------  -------  --------------  ---------------  ------------
# openai          834          342,123           45,678        $5.23
# anthropic       287          156,234           32,456        $6.12
# google          126           44,536           11,100        $1.10

# Usage by task type
python src/usage_cli.py by-task

# Output:
# Task Type      Calls    Input Tokens    Output Tokens    Cost (USD)
# -----------  -------  --------------  ---------------  ------------
# filter           412          123,456           12,345        $2.34
# group            398          198,234           34,567        $5.67
# summarize        398          187,654           38,901        $4.23
# query             39           33,549            3,421        $0.21

# Usage for specific date range
python src/usage_cli.py range --start 2026-01-01 --end 2026-01-10

# Usage by model
python src/usage_cli.py by-model --provider openai

# Cost breakdown
python src/usage_cli.py costs --breakdown

# Export usage data to CSV
python src/usage_cli.py export --output usage_report.csv
```

#### Integration with `call_llm()`

```python
# src/utils.py (updated)
def call_llm(
    model_config: str,
    prompt: str,
    api_keys: dict,
    instructions: str = "",
    max_tokens: int = 500,
    temperature: float = 1.0,
    task_type: str = "unknown",  # NEW: track what this call is for
) -> str:
    """
    Call an LLM using the provider abstraction layer.

    Now automatically logs usage to database.
    """
    import time
    from pricing import estimate_cost
    from history_db import log_llm_usage

    provider = get_provider(
        model_config,
        openai_api_key=api_keys.get("openai"),
        anthropic_api_key=api_keys.get("anthropic"),
        google_api_key=api_keys.get("google"),
        xai_api_key=api_keys.get("xai"),
    )

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

    return response_text
```

#### Key Technical Considerations

1. **Backward Compatibility**:
   - Provider interface change from `-> str` to `-> Tuple[str, LLMUsageMetadata]`
   - All 261 existing tests need updating to handle new return type
   - Wrapper function needed for backward compatibility if any external code uses providers directly

2. **Provider-Specific Token Extraction**:
   - **OpenAI**: `response.usage.prompt_tokens`, `response.usage.completion_tokens`
   - **xAI**: Same as OpenAI (OpenAI-compatible API)
   - **Anthropic**: `response.usage.input_tokens`, `response.usage.output_tokens`
   - **Google**: `response.usage_metadata.prompt_token_count`, `response.usage_metadata.candidates_token_count`

3. **Error Handling**:
   - Usage logging failures should NOT break the main pipeline
   - Log warnings but continue execution
   - Database write failures should be non-fatal

4. **Task Type Tracking**:
   - Task types: `filter`, `group`, `summarize`, `query`
   - Need to update all call sites in:
     - `llm_filter.py` → task_type="filter"
     - `summarizer.py` (grouping) → task_type="group"
     - `summarizer.py` (summarization) → task_type="summarize"
     - `query_engine.py` → task_type="query"

5. **Cost Estimation Accuracy**:
   - Prices should be configurable and updatable
   - Consider environment variable overrides
   - Log warning if model pricing not found

#### Git Operations
- Create branch: `feature/sprint-12-token-usage-monitoring`
- Daily commits with conventional messages
- PR review with usage tracking examples
- Merge to `master` after all tests pass

#### Testing Milestones
- Day 2: Database schema and basic logging tests complete
- Day 4: All provider implementations updated with tests
- Day 6: CLI tool complete with full integration tests
- Day 7: All tests passing, documentation complete, ready for merge

#### Success Criteria
- [ ] `llm_usage` table created and indexed
- [ ] All 4 providers return usage metadata
- [ ] Usage automatically logged for all LLM calls
- [ ] CLI tool provides comprehensive usage analysis
- [ ] Cost estimation working for all providers
- [ ] Response time tracking implemented
- [ ] All 261+ existing tests updated and passing
- [ ] 20+ new unit tests added
- [ ] 5+ integration tests added
- [ ] Documentation complete with examples

#### Test Coverage Updates

| Test File | Changes Required | New Tests |
|-----------|-----------------|-----------|
| `tests/test_providers.py` | Update all provider tests to expect tuple returns | +20 |
| `tests/test_utils.py` | Update `call_llm()` tests | +5 |
| `tests/test_history_db.py` | Add `llm_usage` table tests | +8 |
| `tests/test_usage_cli.py` | NEW: CLI command tests | +10 |
| `tests/test_pricing.py` | NEW: Cost estimation tests | +5 |
| `tests/test_integration_usage.py` | NEW: End-to-end usage tracking | +5 |

**Expected Final Test Count**: 261 (current) + 53 (new) = 314 tests

#### Migration Path

For existing code that may call providers directly:

```python
# OLD (before Sprint 12)
response = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str

# NEW (Sprint 12+)
response, usage = provider.complete(prompt="Hello", instructions="Be helpful")
# response is str, usage is LLMUsageMetadata

# If you only need the text (ignore usage):
response = provider.complete(prompt="Hello", instructions="Be helpful")[0]
```

For `call_llm()` users (most code), no changes needed as it still returns `str`.

---

## 7. Risk Management

### 7.1 Identified Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Provider API changes or deprecations | Medium | High | Version pin, adapter pattern, comprehensive tests |
| API rate limits during testing | Medium | Medium | Use mocked tests, test with low-tier plans first |
| Provider-specific response format issues | High | Medium | Extensive response parsing tests, fallback handling |
| Cost overruns from API usage | Medium | Low | Use smallest models for testing, monitor usage |
| Authentication/key management complexity | Low | Medium | Clear documentation, validation on startup |
| Backward compatibility breaking | Low | High | Comprehensive backward compatibility tests |
| Provider quota/billing issues | Medium | Medium | Document quota requirements, provide fallback options |

### 7.2 Contingency Planning
- 10% time buffer built into each sprint
- Provider abstraction allows quick switching if one provider has issues
- Mocked tests reduce dependency on live APIs during development
- Backward compatibility ensures existing deployments continue working

---

## 8. Quality Gates

### 8.1 Sprint Exit Criteria
- [ ] All planned tasks complete or explicitly deferred
- [ ] Unit test coverage above 85% for new code
- [ ] Integration tests passing
- [ ] No critical or high-severity bugs open
- [ ] Documentation updated (README, .env.example)
- [ ] Manual testing complete for new providers
- [ ] Code review approved

### 8.2 Release Criteria (v2.0.0)
- [ ] All "Must Have" requirements implemented
- [ ] All 4 providers working (OpenAI, xAI, Anthropic, Google)
- [ ] Backward compatibility verified
- [ ] 216+ tests passing
- [ ] Performance benchmarks documented
- [ ] README comprehensive with provider guide
- [ ] Production deployment tested

---

## 9. Architecture Overview

### 9.1 Current Architecture (Sprints 1-6)
```
┌─────────────────────────────────────────────────────────────┐
│                    CLI / Web Interface                       │
├─────────────────────────────────────────────────────────────┤
│  main.py            │  web_dashboard.py  │  history_cli.py  │
│  scheduler.py       │  API endpoints     │  Query commands  │
└─────────────┬───────────────────┬─────────────┬─────────────┘
              │                   │             │
              ▼                   ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  rss_reader.py      │  llm_filter.py    │  summarizer.py   │
│  article_history.py │  query_engine.py  │                  │
└─────────────┬───────────────────┬─────────────┬─────────────┘
              │                   │             │
              ▼                   ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                         Utils                                │
├─────────────────────────────────────────────────────────────┤
│  utils.py - call_responses_api() - SINGLE PROVIDER (OpenAI) │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenAI Responses API (ONLY)                     │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 New Architecture (Sprints 7-11)
```
┌─────────────────────────────────────────────────────────────┐
│                    CLI / Web Interface                       │
├─────────────────────────────────────────────────────────────┤
│  main.py            │  web_dashboard.py  │  history_cli.py  │
│  scheduler.py       │  API endpoints     │  Query commands  │
└─────────────┬───────────────────┬─────────────┬─────────────┘
              │                   │             │
              ▼                   ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  rss_reader.py      │  llm_filter.py    │  summarizer.py   │
│  article_history.py │  query_engine.py  │                  │
└─────────────┬───────────────────┬─────────────┬─────────────┘
              │                   │             │
              ▼                   ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                Provider Abstraction Layer (NEW)              │
├─────────────────────────────────────────────────────────────┤
│  utils.py - get_provider(config) → BaseProvider instance     │
│  providers/__init__.py - ProviderFactory                     │
│  providers/base.py - BaseProvider (ABC)                      │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Provider Implementations                  │
├────────────────┬────────────────┬────────────────┬──────────┤
│ OpenAIProvider │ XAIProvider    │AnthropicProvider│ GeminiProvider│
│ (existing)     │ (Sprint 8)     │ (Sprint 9)     │ (Sprint 10)│
└────────┬───────┴────────┬───────┴────────┬───────┴─────┬────┘
         │                │                │             │
         ▼                ▼                ▼             ▼
┌────────────────┬────────────────┬────────────────┬──────────┐
│ OpenAI API     │ xAI API        │ Anthropic API  │ Google API│
│ (Responses)    │ (compatible)   │ (Messages)     │ (Gemini)  │
└────────────────┴────────────────┴────────────────┴──────────┘
```

### 9.3 Provider Interface (Sprint 7)
```python
# providers/base.py
class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, instructions: str = "",
                 max_tokens: int = 500, temperature: float = 1.0) -> str:
        """Generate completion for given prompt."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration (API key, etc.)."""
        pass

# providers/__init__.py
def get_provider(model_config: str) -> BaseProvider:
    """Factory function to get provider instance.

    Args:
        model_config: Either "model-name" (old format, defaults to OpenAI)
                     or "provider:model-name" (new format)

    Returns:
        BaseProvider instance
    """
    if ":" in model_config:
        provider_name, model_name = model_config.split(":", 1)
    else:
        # Backward compatibility: assume OpenAI
        provider_name, model_name = "openai", model_config

    providers = {
        "openai": OpenAIProvider,
        "xai": XAIProvider,
        "anthropic": AnthropicProvider,
        "google": GeminiProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")

    return provider_class(model_name)
```

---

## Appendices

### A. Effort Estimation Guide
| Size | Hours | Complexity | Examples |
|------|-------|------------|----------|
| S | 2-4h | Simple, well-understood | Add field, simple endpoint, config update |
| M | 4-8h | Moderate, some unknowns | New component, CRUD endpoint, format conversion |
| L | 8-16h | Complex, multiple parts | Provider implementation, integration testing |
| XL | 16-32h | Very complex, significant unknowns | Complete new subsystem, major refactor |

### B. Test Coverage Targets
| Sprint | Base Tests | New Tests | Total Tests |
|--------|------------|-----------|-------------|
| Sprint 1 | 0 | 22 | 22 |
| Sprint 2 | 22 | 17 | 39 |
| Sprint 3 | 39 | 46 | 85 |
| Sprint 4 | 85 | 21 | 106 |
| Sprint 5 | 106 | 13 | 119 |
| Sprint 6 | 119 | 22 | 141 |
| Sprint 7 | 141 | 30 | 171 |
| Sprint 8 | 171 | 13 | 184 |
| Sprint 9 | 184 | 15 | 199 |
| Sprint 10 | 199 | 17 | 216 |
| Sprint 11 | 216 | 45 | 261 |
| Sprint 12 | 261 | 24 | 285 |

### C. Provider API Reference
| Provider | API Documentation | Key Differences |
|----------|------------------|-----------------|
| OpenAI | https://platform.openai.com/docs/api-reference/responses | Responses API format (used currently) |
| xAI | https://docs.x.ai/api | OpenAI-compatible, different endpoint |
| Anthropic | https://docs.anthropic.com/en/api/messages | Messages array, system prompt separate |
| Google | https://ai.google.dev/api/rest | Contents with parts, safety settings |

### D. Configuration Migration Guide
```bash
# OLD FORMAT (still supported for backward compatibility)
FILTER_MODEL=gpt-4o-mini
GROUP_MODEL=gpt-4o
SUMMARIZE_MODEL=gpt-4o
QUERY_MODEL=gpt-4o-mini

# NEW FORMAT (explicit provider)
FILTER_MODEL=openai:gpt-4o-mini
GROUP_MODEL=openai:gpt-4o
SUMMARIZE_MODEL=openai:gpt-4o
QUERY_MODEL=openai:gpt-4o-mini

# MULTI-PROVIDER (mix and match)
FILTER_MODEL=google:gemini-2.0-flash
GROUP_MODEL=anthropic:claude-haiku-20250320
SUMMARIZE_MODEL=anthropic:claude-sonnet-4-20250514
QUERY_MODEL=openai:gpt-4o-mini
```

### E. API Key Configuration
```bash
# OpenAI (existing)
OPENAI_API_KEY=sk-proj-...

# xAI Grok (new)
XAI_API_KEY=xai-...

# Anthropic Claude (new)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini (new)
GOOGLE_API_KEY=AIza...
```

### F. Sprint Calendar Template
| Week | Monday | Tuesday | Wednesday | Thursday | Friday |
|------|--------|---------|-----------|----------|--------|
| 1 | Sprint start, planning | Dev | Dev | Dev | Dev |
| 2 | Dev | Dev | Testing | Review | Merge, retro |

### G. LLM Call Points (Refactoring Targets)
Current locations where LLMs are called (all must be updated to use provider abstraction):

1. **llm_filter.py**
   - Line 132: `call_responses_api()` for article filtering
   - Change to: `get_provider(filter_model).complete()`

2. **summarizer.py**
   - Line 181: `call_responses_api()` for grouping
   - Line 264: `call_responses_api()` for summarization
   - Change both to: `get_provider(group_model).complete()` and `get_provider(summarize_model).complete()`

3. **query_engine.py**
   - Line 357: `call_responses_api()` for query classification
   - Change to: `get_provider(query_model).complete()`

Total LLM call points: **4** (all in critical paths)

---

## Summary

This Software Development Plan documents the completed work from Sprints 1-12. All sprints are now complete:

1. **Sprints 1-6**: Core features (database, CLI, LLM query, web UI, security)
2. **Sprint 7**: Provider abstraction layer with backward compatibility
3. **Sprint 8**: xAI Grok integration (OpenAI-compatible)
4. **Sprint 9**: Anthropic Claude integration (Messages API)
5. **Sprint 10**: Google Gemini integration (Generative Language API)
6. **Sprint 11**: Comprehensive cross-provider testing and documentation
7. **Sprint 12**: Token usage monitoring with cost tracking

The design achieved:
- **Backward compatibility**: Existing configurations continue to work
- **Clean abstraction**: Provider details hidden behind common interface
- **Flexibility**: Mix and match providers for different tasks
- **Testing**: 285 tests across all components
- **Documentation**: Clear guides for each provider
- **Usage Monitoring**: Track tokens, costs, and response times per LLM call

Users can configure any combination of OpenAI, xAI, Anthropic, and Google models for filtering, grouping, summarization, and querying tasks, with full usage tracking and cost analysis.
