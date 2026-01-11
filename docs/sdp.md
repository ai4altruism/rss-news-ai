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
| Sprint 7: Multi-Provider Abstraction | 1 week | **Planned** | TBD |
| Sprint 8: xAI Grok Integration | 1 week | **Planned** | TBD |
| Sprint 9: Anthropic Claude Integration | 2 weeks | **Planned** | TBD |
| Sprint 10: Google Gemini Integration | 2 weeks | **Planned** | TBD |
| Sprint 11: Provider Testing & Hardening | 1 week | **Planned** | TBD |

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
| Sprint 7 | 141 | 15 | 156 |
| Sprint 8 | 156 | 10 | 166 |
| Sprint 9 | 166 | 15 | 181 |
| Sprint 10 | 181 | 15 | 196 |
| Sprint 11 | 196 | 20 | 216+ |

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

This Software Development Plan documents the completed work from Sprints 1-6 and provides a comprehensive roadmap for adding multi-provider LLM support in Sprints 7-11. The plan follows a phased approach:

1. **Sprint 7**: Create provider abstraction layer with backward compatibility
2. **Sprint 8**: Add xAI Grok (easiest, OpenAI-compatible)
3. **Sprint 9**: Add Anthropic Claude (different API format)
4. **Sprint 10**: Add Google Gemini (different API format + safety settings)
5. **Sprint 11**: Comprehensive testing, benchmarking, and documentation

The design prioritizes:
- **Backward compatibility**: Existing configurations continue to work
- **Clean abstraction**: Provider details hidden behind common interface
- **Flexibility**: Mix and match providers for different tasks
- **Testing**: Comprehensive unit, integration, and manual tests
- **Documentation**: Clear guides for each provider

Upon completion, users will be able to configure any combination of OpenAI, xAI, Anthropic, and Google models for filtering, grouping, summarization, and querying tasks.
