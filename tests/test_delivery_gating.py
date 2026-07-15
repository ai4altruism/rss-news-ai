# tests/test_delivery_gating.py
"""
Tests for the Sprint 14 reliability fixes: delivery-gated state commits,
rejected-article tracking, self-match exclusion in semantic dedup,
LLM output grounding, and the reduced JSON sanitizer.
"""

import json
import os
import sys
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from json_utils import sanitize_json_string, validate_json
from llm_filter import filter_stories
from summarizer import group_and_summarize
from embeddings import filter_semantic_duplicates, find_similar_articles, persist_embeddings
from article_history import ArticleHistory


class TestJsonUtils:
    """The sanitizer must recover common wrappers without corrupting content."""

    def test_valid_json_passthrough(self):
        ok, result = validate_json('{"decisions": [{"index": 1, "decision": "Yes"}]}')
        assert ok
        assert result["decisions"][0]["decision"] == "Yes"

    def test_strips_markdown_fences(self):
        wrapped = '```json\n{"topics": []}\n```'
        assert sanitize_json_string(wrapped) == '{"topics": []}'
        ok, result = validate_json(wrapped)
        assert ok
        assert result == {"topics": []}

    def test_extracts_outermost_object_from_prose(self):
        ok, result = validate_json('Here is the JSON:\n{"topics": [{"topic": "AI"}]}\nDone.')
        assert ok
        assert result["topics"][0]["topic"] == "AI"

    def test_does_not_corrupt_strings_containing_quotes(self):
        # The old regex "repairs" re-escaped quotes mid-string and broke
        # valid JSON like this.
        payload = json.dumps({"title": 'OpenAI says "AGI is near", critics disagree'})
        ok, result = validate_json(payload)
        assert ok
        assert result["title"] == 'OpenAI says "AGI is near", critics disagree'

    def test_unrecoverable_returns_false(self):
        ok, result = validate_json('not json at all')
        assert not ok


class TestFilterTriage:
    """filter_stories must sort every article into accepted/rejected/errored."""

    ARTICLES = [
        {"title": f"Article {i}", "link": f"https://example.com/{i}", "summary": "s"}
        for i in range(1, 4)
    ]

    @patch("llm_filter.call_llm")
    def test_yes_no_and_omitted(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "decisions": [
                {"index": 1, "decision": "Yes"},
                {"index": 2, "decision": "No"},
                # index 3 omitted by the LLM
            ]
        })
        accepted, rejected, errored = filter_stories(
            self.ARTICLES, "prompt", "gpt-4o-mini", "key"
        )
        assert [a["title"] for a in accepted] == ["Article 1"]
        assert [a["title"] for a in rejected] == ["Article 2"]
        assert [a["title"] for a in errored] == ["Article 3"]

    @patch("llm_filter.call_llm")
    def test_unparseable_response_errors_whole_batch(self, mock_llm):
        mock_llm.return_value = "I cannot help with that."
        accepted, rejected, errored = filter_stories(
            self.ARTICLES, "prompt", "gpt-4o-mini", "key"
        )
        assert accepted == []
        assert rejected == []
        assert len(errored) == 3

    @patch("llm_filter.call_llm")
    def test_llm_exception_errors_whole_batch(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API down")
        accepted, rejected, errored = filter_stories(
            self.ARTICLES, "prompt", "gpt-4o-mini", "key"
        )
        assert accepted == []
        assert len(errored) == 3

    @patch("llm_filter.call_llm")
    def test_empty_response_errors_whole_batch(self, mock_llm):
        mock_llm.return_value = "   "
        accepted, rejected, errored = filter_stories(
            self.ARTICLES, "prompt", "gpt-4o-mini", "key"
        )
        assert accepted == []
        assert len(errored) == 3

    @patch("llm_filter.call_llm")
    def test_ambiguous_decision_is_errored_not_rejected(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "decisions": [
                {"index": 1, "decision": "Unknown"},
                {"index": 2, "decision": "yes."},
                {"index": 3, "decision": '"No"'},
            ]
        })
        accepted, rejected, errored = filter_stories(
            self.ARTICLES, "prompt", "gpt-4o-mini", "key"
        )
        assert [a["title"] for a in accepted] == ["Article 2"]
        assert [a["title"] for a in rejected] == ["Article 3"]
        assert [a["title"] for a in errored] == ["Article 1"]


class TestGrounding:
    """group_and_summarize must never publish LLM-echoed titles/links."""

    ARTICLES = [
        {"title": "Alpha Story", "link": "https://example.com/alpha", "summary": "About alpha."},
        {"title": "Beta Story", "link": "https://example.com/beta", "summary": "About beta."},
        {"title": "Gamma Story", "link": "https://example.com/gamma", "summary": "About gamma."},
    ]

    @staticmethod
    def _mock_llm(group_response):
        def side_effect(*args, **kwargs):
            if kwargs.get("task_type") == "group":
                return group_response
            return "A concise summary."
        return side_effect

    @patch("summarizer.call_llm")
    def test_paraphrased_title_grounds_by_link(self, mock_llm):
        mock_llm.side_effect = self._mock_llm(json.dumps({
            "topics": [{
                "topic": "AI News",
                "articles": [
                    # paraphrased title, correct link
                    {"title": "The Alpha story (updated)", "link": "https://example.com/alpha"},
                    {"title": "Beta Story", "link": "https://example.com/beta"},
                    {"title": "Gamma Story", "link": "https://example.com/gamma"},
                ],
            }]
        }))
        result = group_and_summarize(self.ARTICLES, "m", "m", "key")
        topic = result["topics"][0]
        # Published output carries the SOURCE title, not the LLM's paraphrase
        assert {"title": "Alpha Story", "link": "https://example.com/alpha"} in topic["articles"]

    @patch("summarizer.call_llm")
    def test_hallucinated_link_dropped_omitted_article_in_catchall(self, mock_llm):
        mock_llm.side_effect = self._mock_llm(json.dumps({
            "topics": [{
                "topic": "AI News",
                "articles": [
                    {"title": "Alpha Story", "link": "https://example.com/alpha"},
                    # hallucinated: unknown title AND unknown link
                    {"title": "Invented Story", "link": "https://evil.example.com/x"},
                ],
            }]
        }))
        result = group_and_summarize(self.ARTICLES, "m", "m", "key")
        all_links = [a["link"] for t in result["topics"] for a in t["articles"]]
        # Hallucinated link never published
        assert "https://evil.example.com/x" not in all_links
        # Omitted beta/gamma still delivered via catch-all
        assert "https://example.com/beta" in all_links
        assert "https://example.com/gamma" in all_links
        assert any(t["topic"] == "Additional stories" for t in result["topics"])

    @patch("summarizer.call_llm")
    def test_grouping_failure_falls_back_to_source_list(self, mock_llm):
        def side_effect(*args, **kwargs):
            if kwargs.get("task_type") == "group":
                raise RuntimeError("API down")
            return "A concise summary."
        mock_llm.side_effect = side_effect
        result = group_and_summarize(self.ARTICLES, "m", "m", "key")
        all_links = [a["link"] for t in result["topics"] for a in t["articles"]]
        assert sorted(all_links) == sorted(a["link"] for a in self.ARTICLES)

    @patch("summarizer.call_llm")
    def test_duplicate_placement_kept_in_first_topic_only(self, mock_llm):
        mock_llm.side_effect = self._mock_llm(json.dumps({
            "topics": [
                {"topic": "T1", "articles": [
                    {"title": "Alpha Story", "link": "https://example.com/alpha"}]},
                {"topic": "T2", "articles": [
                    {"title": "Alpha Story", "link": "https://example.com/alpha"},
                    {"title": "Beta Story", "link": "https://example.com/beta"}]},
            ]
        }))
        result = group_and_summarize(self.ARTICLES, "m", "m", "key")
        alpha_count = sum(
            1 for t in result["topics"] for a in t["articles"]
            if a["link"] == "https://example.com/alpha"
        )
        assert alpha_count == 1


class TestSelfMatchExclusion:
    """An article must never be suppressed as a duplicate of itself."""

    def test_exclude_url_skips_own_embedding(self):
        emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        recent = [{
            "url": "https://example.com/self",
            "title": "Self",
            "embedding": emb.tobytes(),
        }]
        # Without exclusion: perfect self-match
        assert find_similar_articles(emb, recent, threshold=0.85)
        # With exclusion: no match
        assert not find_similar_articles(
            emb, recent, threshold=0.85, exclude_url="https://example.com/self"
        )

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_article_from_failed_run_not_dropped(
        self, mock_cleanup, mock_save, mock_recent, mock_batch
    ):
        """Simulates the retry after a failed run: the article's own
        embedding is already in the store but must not suppress it."""
        emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_recent.return_value = [{
            "url": "https://example.com/retry",
            "title": "Retry Me",
            "embedding": emb.tobytes(),
        }]
        mock_batch.return_value = ([emb], 50)

        articles = [{
            "title": "Retry Me",
            "link": "https://example.com/retry",
            "summary": "s",
        }]
        unique, stats = filter_semantic_duplicates(articles, api_key="k")
        assert len(unique) == 1
        assert stats["duplicates"] == 0


class TestDeferredEmbeddings:
    """defer_saves must not write to the DB; persist_embeddings does."""

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_defer_saves_returns_pending_without_writing(
        self, mock_cleanup, mock_save, mock_recent, mock_batch
    ):
        mock_recent.return_value = []
        emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_batch.return_value = ([emb], 50)

        articles = [{"title": "A", "link": "https://example.com/a", "summary": "s"}]
        unique, stats = filter_semantic_duplicates(articles, api_key="k", defer_saves=True)

        assert len(unique) == 1
        mock_save.assert_not_called()
        assert len(stats["pending_embeddings"]) == 1
        assert stats["pending_embeddings"][0]["url"] == "https://example.com/a"

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_default_still_saves_inline(
        self, mock_cleanup, mock_save, mock_recent, mock_batch
    ):
        mock_recent.return_value = []
        emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_batch.return_value = ([emb], 50)

        articles = [{"title": "A", "link": "https://example.com/a", "summary": "s"}]
        unique, stats = filter_semantic_duplicates(articles, api_key="k")

        mock_save.assert_called_once()
        assert stats["pending_embeddings"] == []

    @patch('embeddings.save_article_embedding')
    def test_persist_embeddings_writes_entries(self, mock_save):
        pending = [{
            "url": "https://example.com/a",
            "title": "A",
            "lead_text": "A. lead",
            "embedding": b"\x00\x00\x80?",
            "embedding_model": "text-embedding-3-small",
        }]
        assert persist_embeddings(pending) == 1
        mock_save.assert_called_once()

    @patch('embeddings.generate_embeddings_batch')
    @patch('embeddings.get_recent_embeddings')
    @patch('embeddings.save_article_embedding')
    @patch('embeddings.cleanup_old_embeddings')
    def test_intra_run_duplicates_still_detected_when_deferred(
        self, mock_cleanup, mock_save, mock_recent, mock_batch
    ):
        """Two near-identical articles in the same run: second is dropped
        even though nothing has been persisted yet."""
        mock_recent.return_value = []
        emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        near = np.array([0.999, 0.01, 0.0], dtype=np.float32)
        mock_batch.return_value = ([emb, near], 100)

        articles = [
            {"title": "A", "link": "https://example.com/a", "summary": "s"},
            {"title": "A again", "link": "https://example.com/a2", "summary": "s"},
        ]
        unique, stats = filter_semantic_duplicates(articles, api_key="k", defer_saves=True)
        assert len(unique) == 1
        assert stats["duplicates"] == 1


class TestRejectedTracking:
    """Rejected articles are recorded and not reprocessed."""

    def test_mark_rejected_and_filter(self, tmp_path):
        history = ArticleHistory(history_file=str(tmp_path / "history.json"))
        rejected = [{"title": "R", "link": "https://example.com/r"}]
        history.mark_as_published(rejected, status="rejected")

        entry = history.history["articles"]["https://example.com/r"]
        assert entry["status"] == "rejected"

        # Reload from disk: still filtered out
        history2 = ArticleHistory(history_file=str(tmp_path / "history.json"))
        remaining = history2.filter_published(
            [{"title": "R", "link": "https://example.com/r"},
             {"title": "New", "link": "https://example.com/new"}]
        )
        assert [a["link"] for a in remaining] == ["https://example.com/new"]

    def test_published_entries_have_no_status_field(self, tmp_path):
        history = ArticleHistory(history_file=str(tmp_path / "history.json"))
        history.mark_as_published([{"title": "P", "link": "https://example.com/p"}])
        entry = history.history["articles"]["https://example.com/p"]
        assert "status" not in entry  # format unchanged for published articles


class TestDeliveryGating:
    """main() must commit history/embeddings only after successful delivery."""

    ACCEPTED = {"title": "Good", "link": "https://example.com/good", "summary": "s"}
    REJECTED = {"title": "Bad", "link": "https://example.com/bad", "summary": "s"}

    def _run_main(self, tmp_path, monkeypatch, slack_ok):
        import main as main_mod

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "OPENAI_API_KEY=test-key\n"
            "SLACK_WEBHOOK_URL=https://hooks.slack.com/test\n"
        )
        monkeypatch.setattr(sys, "argv", ["main.py", "--output", "slack"])

        articles = [self.ACCEPTED, self.REJECTED]
        pending = [
            {"url": a["link"], "title": a["title"], "lead_text": "t",
             "embedding": b"\x00", "embedding_model": "m"}
            for a in articles
        ]

        persisted_urls = []

        monkeypatch.setattr(main_mod, "fetch_feeds", lambda urls: list(articles))
        monkeypatch.setattr(
            main_mod, "filter_semantic_duplicates",
            lambda **kw: (list(articles), {
                "total": 2, "unique": 2, "duplicates": 0,
                "filtered": [], "pending_embeddings": pending,
            }),
        )
        monkeypatch.setattr(
            main_mod, "persist_embeddings",
            lambda entries, db_path=None: persisted_urls.extend(
                e["url"] for e in entries) or len(entries),
        )
        monkeypatch.setattr(
            main_mod, "filter_stories",
            lambda *a, **kw: ([self.ACCEPTED], [self.REJECTED], []),
        )
        monkeypatch.setattr(
            main_mod, "group_and_summarize",
            lambda *a, **kw: {"topics": [{
                "topic": "T", "summary": "s",
                "articles": [{"title": "Good", "link": "https://example.com/good"}],
            }]},
        )
        monkeypatch.setattr(main_mod, "publish_to_slack", lambda *a, **kw: slack_ok)
        monkeypatch.setattr(main_mod, "save_summary_to_db", lambda s: 1)

        main_mod.main()

        with open(tmp_path / "data" / "article_history.json") as f:
            recorded = json.load(f)["articles"]
        return recorded, persisted_urls

    def test_successful_delivery_commits_everything(self, tmp_path, monkeypatch):
        recorded, persisted = self._run_main(tmp_path, monkeypatch, slack_ok=True)
        assert "https://example.com/good" in recorded
        assert "https://example.com/bad" in recorded
        assert recorded["https://example.com/bad"]["status"] == "rejected"
        assert sorted(persisted) == [
            "https://example.com/bad", "https://example.com/good",
        ]

    def test_failed_delivery_retries_accepted_articles(self, tmp_path, monkeypatch):
        recorded, persisted = self._run_main(tmp_path, monkeypatch, slack_ok=False)
        # Rejected article is still recorded (its fate is decided)...
        assert "https://example.com/bad" in recorded
        assert "https://example.com/bad" in persisted
        # ...but the accepted article must NOT be committed anywhere,
        # so the next run retries it.
        assert "https://example.com/good" not in recorded
        assert "https://example.com/good" not in persisted
