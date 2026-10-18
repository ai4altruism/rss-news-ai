# tests/test_rss_reader.py
"""
rss_reader.fetch_feeds with HTTP stubbed (requests.get) and the on-disk
cache redirected to tmp_path. feedparser runs for real on inline XML.
"""

import os
import sys
import time
from email.utils import formatdate
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import rss_reader
from embeddings import get_embedding_text
from llm_filter import filter_stories
from tests.fakes import known_bug

FEED_URL = "https://feeds.example.invalid/rss"


def rss(items):
    body = "".join(
        f"<item><title>{t}</title><link>{l}</link>"
        f"<description>{d}</description>"
        + (f"<pubDate>{p}</pubDate>" if p else "") + "</item>"
        for t, l, d, p in items)
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>T</title>{body}</channel></rss>")


def http(text, status=200, headers=None):
    return MagicMock(status_code=status, text=text, headers=headers or {})


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(rss_reader, "CACHE_FILE", str(tmp_path / "cache.json"))


def fetch(responses, urls=(FEED_URL,), **kwargs):
    with patch("rss_reader.requests.get", side_effect=responses) as get:
        return rss_reader.fetch_feeds(list(urls), **kwargs), get


class TestFetchFeeds:

    def test_parses_entries(self):
        feed = rss([("One", "https://e.com/1", "first", None)])
        articles, _ = fetch([http(feed)])
        assert articles == [{"title": "One", "link": "https://e.com/1",
                             "summary": "first", "published": ""}]

    def test_non_200_feed_is_skipped(self):
        articles, _ = fetch([http("", status=503)])
        assert articles == []

    def test_network_exception_does_not_stop_other_feeds(self):
        good = http(rss([("One", "https://e.com/1", "x", None)]))
        articles, _ = fetch([OSError("down"), good], urls=("https://a.invalid", "https://b.invalid"))
        assert [a["title"] for a in articles] == ["One"]

    def test_stale_entries_are_dropped_and_undated_kept(self):
        old = formatdate(time.time() - 90 * 86400)
        new = formatdate(time.time() - 1 * 86400)
        feed = rss([("Old", "https://e.com/old", "x", old),
                    ("New", "https://e.com/new", "x", new),
                    ("Undated", "https://e.com/u", "x", None)])
        articles, _ = fetch([http(feed)], max_age_days=30)
        assert sorted(a["title"] for a in articles) == ["New", "Undated"]

    def test_age_guard_can_be_disabled(self):
        old = formatdate(time.time() - 900 * 86400)
        articles, _ = fetch([http(rss([("Old", "https://e.com/old", "x", old)]))],
                            max_age_days=0)
        assert len(articles) == 1

    def test_exact_link_duplicates_across_feeds_are_dropped(self):
        same = http(rss([("One", "https://e.com/1", "x", None)]))
        articles, _ = fetch([same, same], urls=("https://a.invalid", "https://b.invalid"))
        assert len(articles) == 1

    def test_304_reuses_cached_content_and_sends_validators(self):
        feed = rss([("One", "https://e.com/1", "x", None)])
        fetch([http(feed, headers={"ETag": '"v1"', "Last-Modified": "Mon, 01 Jan 2026 00:00:00 GMT"})])

        articles, get = fetch([http("", status=304)])

        assert [a["title"] for a in articles] == ["One"]
        sent = get.call_args.kwargs["headers"]
        assert sent["If-None-Match"] == '"v1"'
        assert sent["If-Modified-Since"].startswith("Mon, 01 Jan 2026")

    def test_request_has_timeout_and_user_agent(self):
        _, get = fetch([http(rss([]))])
        assert get.call_args.kwargs["timeout"] == 10
        assert "RSSFeedMonitor" in get.call_args.kwargs["headers"]["User-Agent"]


class TestFeedParserEdgeCases:

    MALFORMED_BUT_USABLE = (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>T</title>'
        "<item><title>Salvageable</title><link>https://e.com/s</link>"
        "<description>Tom & Jerry ship a model</description></item></channel></rss>"
    )

    def test_fixture_really_is_bozo_with_entries(self):
        import feedparser
        parsed = feedparser.parse(self.MALFORMED_BUT_USABLE)
        assert parsed.bozo and len(parsed.entries) == 1

    @known_bug("feedparser bozo flag drops a whole feed even when entries were parsed")
    def test_bozo_feed_with_parsed_entries_is_not_dropped(self):
        articles, _ = fetch([http(self.MALFORMED_BUT_USABLE)])
        assert [a["title"] for a in articles] == ["Salvageable"]


class TestHtmlSummaries:
    HTML_FEED = rss([("One", "https://e.com/1",
                      "&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;", None)])

    def _article(self):
        articles, _ = fetch([http(self.HTML_FEED)])
        return articles[0]

    def test_html_reaches_us_as_markup_today(self):
        assert self._article()["summary"] == "<p>Hello <b>world</b></p>"

    @known_bug("HTML summaries are kept as raw markup in the article dict")
    def test_fetched_summary_is_plain_text(self):
        assert self._article()["summary"] == "Hello world"

    @known_bug("raw HTML tags reach the filter prompt")
    def test_filter_prompt_has_no_html_tags(self):
        article = self._article()
        with patch("llm_filter.call_llm", return_value='{"decisions": []}') as llm:
            filter_stories([article], "p", "gpt-4o-mini", "k")
        assert "<p>" not in llm.call_args.kwargs["prompt"]

    @known_bug("raw HTML tags reach the embedding text")
    def test_embedding_text_has_no_html_tags(self):
        assert "<" not in get_embedding_text(self._article())
