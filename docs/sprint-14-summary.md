# Sprint 14 Summary: Delivery Reliability Hardening

**Completed:** 2026-07-15
**Version:** v2.3

## Overview

Sprint 14 eliminates a family of silent article-loss failure modes found during a fleet-wide reliability review. The same defect classes were previously found and fixed in the sibling apps rss-feed-monitor (PRs #8-#10) and rss-alert-monitor (PRs #2-#6); this sprint ports those fixes and closes one failure mode unique to this app's semantic deduplication.

## Problems Solved

1. **History committed before delivery.** Articles were marked as published before the Slack webhook was called. A failed delivery permanently suppressed those articles.

2. **Embeddings committed before anything.** Semantic dedup stored each unique article's embedding before the LLM filter, grouping, or delivery ran, and similarity matching had no same-URL exclusion. Any failure downstream of dedup meant the article matched its own stored embedding on the next run and was silently dropped as a "duplicate" forever.

3. **LLM-echoed links published verbatim.** The grouping model's title/link echoes went straight to Slack, so a paraphrased title or corrupted/hallucinated link could reach readers, and articles the LLM omitted from its grouping response vanished silently despite being marked as published.

4. **JSON sanitizer corruption.** The regex "repairs" (re-escaping quotes mid-string, quoting bare keys, appending quotes to odd-quote lines) could turn nearly-valid JSON into unparseable output.

5. **No timeouts.** LLM provider calls, the Slack post, and the scheduler's subprocess had no timeouts; one hung socket stalled the bot indefinitely.

6. **Submodule errors lost.** Only the named `RSSFeedMonitor` logger wrote to `logs/app.log`; errors from `llm_filter`, `summarizer`, and `slack_publisher` went to the root logger and disappeared with container stdout.

## Solution

**Delivery-gated state commits.** Nothing is persisted until an article's fate is decided. The filter now triages every article into accepted / rejected / errored. Rejected articles are recorded immediately (with `status: rejected`) and their embeddings persisted, so they are not re-filtered every run. Accepted articles are marked as published, their embeddings persisted, and the summary saved to the history DB only after the selected output reports success. Errored articles (LLM call failed, response unparseable, decision omitted) are left unrecorded so they retry next run. `filter_semantic_duplicates(defer_saves=True)` returns pending embeddings instead of writing them; `persist_embeddings()` commits them at the decision points. `find_similar_articles` gained an `exclude_url` parameter so an article can never be suppressed by its own stored embedding.

**Grounding.** Titles/links in the LLM's grouping output are now lookup keys only: each is grounded to a source article (by exact link, exact title, then normalized title) and the published output carries source data verbatim. Ungroundable entries are dropped with a warning, an article placed in multiple topics is kept in the first, and articles missing from the LLM response land in an "Additional stories" catch-all instead of vanishing.

**Safe JSON recovery.** The per-module sanitizers were replaced by a shared `json_utils.py` that only strips markdown fences and extracts the outermost JSON object; both are non-mutating. Structural fallbacks (retry next run, raw article listing) handle the rest.

**Timeouts and logging.** All four provider HTTP calls use `timeout=(10, 180)`, the Slack post uses `timeout=30`, and the scheduler kills any run exceeding its interval. `setup_logger()` now configures the root logger so submodule errors reach `app.log`.

## Key Deliverables

| File | Change |
|------|--------|
| `src/json_utils.py` | New: shared safe JSON sanitization/validation |
| `src/llm_filter.py` | Accepted/rejected/errored triage; word-boundary decision matching; string-index coercion |
| `src/summarizer.py` | Grounding phase; catch-all topic; shared JSON recovery; string-stub tolerance |
| `src/embeddings.py` | `exclude_url`, `defer_saves`, `persist_embeddings()` |
| `src/rss_reader.py` | Exact-link dedup across feeds (an aggregator carrying a publisher's URL) |
| `src/article_history.py` | `status="rejected"` tracking; atomic history writes |
| `src/main.py` | Delivery-gated bookkeeping; env plumbing for dedup tunables; `debug=False` |
| `src/providers/*.py` | HTTP timeouts |
| `src/slack_publisher.py` | HTTP timeout |
| `src/scheduler.py` | Subprocess timeout backstop |
| `src/utils.py` | Root-logger capture to `app.log` |
| `tests/test_delivery_gating.py` | 24 new tests for all of the above |

## Hygiene Fixes

- `HISTORY_RETENTION_DAYS` and `WEB_DASHBOARD_PORT` from `.env` are honored (argparse defaults previously shadowed them).
- `SIMILARITY_THRESHOLD`, `DEDUP_LOOKBACK_DAYS`, `EMBEDDING_MODEL`, and `EMBEDDING_RETENTION_DAYS` are now read from `.env` and passed explicitly (they were read from process env, which `dotenv_values` never populates, so they silently fell back to defaults).
- Flask dashboard never starts with `debug=True` (Werkzeug debugger on 0.0.0.0 is remotely exploitable).
- Empty `EMAIL_RECIPIENTS` no longer yields a single blank recipient.

## Test Results

351 tests passing (321 existing + 30 new), no regressions.

## Operational Notes

- Existing `article_history.json` and `history.db` formats are unchanged; rejected tracking adds an optional `status` key to new entries only.
- After deployment, expect the hourly "unique articles after filtering previously published ones" count to drop sharply over the first day: rejected articles are now URL-tracked instead of being re-embedded and re-suppressed every cycle (~700/hour previously).
- A new "Additional stories" topic may occasionally appear in Slack: those are articles the grouping model omitted, which were previously lost silently.
- Keep `DEDUP_LOOKBACK_DAYS` ≤ `HISTORY_RETENTION_DAYS` (defaults 7 and 30 are fine). Because similarity matching now excludes an article's own URL, an article that ages out of URL history while its embedding is still within the lookback window would no longer be suppressed by its own embedding.
- The scheduler's per-run timeout is `max(interval, 30 min)` and is disabled for `--output web` (which blocks in the dashboard server by design).
