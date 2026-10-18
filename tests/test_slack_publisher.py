# tests/test_slack_publisher.py
"""
slack_publisher: block formatting, Slack limits, escaping and paging.

All HTTP is stubbed; no webhook is ever contacted.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from slack_publisher import (
    MAX_ARTICLES_PER_TOPIC,
    MAX_BLOCKS_PER_MESSAGE,
    MAX_TOPICS_PER_MESSAGE,
    format_for_slack,
    publish_to_slack,
    send_slack_message,
)
from tests.fakes import known_bug

SLACK_SECTION_TEXT_LIMIT = 3000
WEBHOOK = "https://hooks.example.invalid/T000/B000/XXXX"


def topic(name="Models", summary="A summary.", n_articles=1, link="https://example.com/a"):
    return {"topic": name, "summary": summary,
            "articles": [{"title": f"Article {i}", "link": link}
                         for i in range(n_articles)]}


def section_texts(blocks):
    return [b["text"]["text"] for b in blocks if b["type"] == "section"]


class TestFormatForSlack:

    def test_header_divider_and_topic_sections(self):
        blocks = format_for_slack({"topics": [topic()]})

        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "divider"
        texts = section_texts(blocks)
        assert texts[0] == "*Models*"
        assert texts[1] == "A summary."
        assert "<https://example.com/a|Article 0>" in texts[2]

    def test_no_pagination_banner_for_small_message(self):
        blocks = format_for_slack({"topics": [topic()]})
        assert not any("Page " in t for t in section_texts(blocks))

    def test_pagination_banner_for_large_message(self):
        data = {"topics": [topic(f"T{i}") for i in range(MAX_TOPICS_PER_MESSAGE + 2)]}
        blocks = format_for_slack(data, MAX_TOPICS_PER_MESSAGE, MAX_TOPICS_PER_MESSAGE + 2)
        assert "Page 2 of 2" in section_texts(blocks)[0]

    def test_article_list_is_capped_with_omitted_note(self):
        blocks = format_for_slack({"topics": [topic(n_articles=MAX_ARTICLES_PER_TOPIC + 3)]})
        links = section_texts(blocks)[2]
        assert links.count("<https://") == MAX_ARTICLES_PER_TOPIC
        assert "+3 more articles not shown" in links

    def test_long_titles_are_truncated_to_80_chars(self):
        data = {"topics": [{"topic": "T", "summary": "s",
                           "articles": [{"title": "x" * 200, "link": "https://e.com"}]}]}
        links = section_texts(format_for_slack(data))[2]
        assert "x" * 77 + "..." in links
        assert "x" * 78 not in links

    def test_defaults_for_missing_fields(self):
        texts = section_texts(format_for_slack({"topics": [{}]}))
        assert texts[0] == "*Uncategorized*"
        assert texts[1] == "No summary available."


class TestSlackLimitsAndEscaping:

    @known_bug("summary is posted as one section with no 3000-char cap; Slack rejects the whole message")
    def test_section_text_never_exceeds_slack_limit_for_long_summary(self):
        blocks = format_for_slack({"topics": [topic(summary="word " * 1000)]})
        assert all(len(t) <= SLACK_SECTION_TEXT_LIMIT for t in section_texts(blocks))

    @known_bug("article list section has no 3000-char cap when links are long")
    def test_section_text_never_exceeds_slack_limit_for_long_links(self):
        data = {"topics": [topic(n_articles=MAX_ARTICLES_PER_TOPIC,
                                 link="https://example.com/" + "p" * 400)]}
        blocks = format_for_slack(data)
        assert all(len(t) <= SLACK_SECTION_TEXT_LIMIT for t in section_texts(blocks))

    @known_bug("topic name, summary and article title are inserted unescaped, so <!channel> pings the channel")
    @pytest.mark.parametrize("field", ["topic", "summary", "title"])
    def test_broadcast_mention_is_escaped(self, field):
        t = topic()
        if field == "title":
            t["articles"][0]["title"] = "<!channel> breaking"
        else:
            t[field] = "<!channel> breaking"

        texts = section_texts(format_for_slack({"topics": [t]}))

        assert not any("<!channel>" in x for x in texts)


class TestPublishAndSend:

    def test_no_topics_is_success_without_http(self):
        with patch("slack_publisher.requests.post") as post:
            assert publish_to_slack({"topics": []}, WEBHOOK) is True
        post.assert_not_called()

    def test_small_summary_is_one_message(self):
        with patch("slack_publisher.send_slack_message", return_value=True) as send:
            assert publish_to_slack({"topics": [topic()]}, WEBHOOK) is True
        assert send.call_count == 1

    def test_large_summary_is_split_into_pages(self):
        data = {"topics": [topic(f"T{i}") for i in range(MAX_TOPICS_PER_MESSAGE * 2 + 1)]}
        with patch("slack_publisher.send_slack_message", return_value=True) as send:
            publish_to_slack(data, WEBHOOK)
        assert send.call_count == 3

    def test_send_posts_blocks_and_reports_success(self):
        with patch("slack_publisher.requests.post",
                   return_value=MagicMock(status_code=200)) as post:
            assert send_slack_message(WEBHOOK, [{"type": "divider"}]) is True
        assert post.call_args.kwargs["json"] == {"blocks": [{"type": "divider"}]}

    def test_send_non_200_is_failure(self):
        with patch("slack_publisher.requests.post",
                   return_value=MagicMock(status_code=400, text="invalid_blocks")):
            assert send_slack_message(WEBHOOK, [{"type": "divider"}]) is False

    def test_send_network_exception_is_failure(self):
        with patch("slack_publisher.requests.post", side_effect=OSError("boom")):
            assert send_slack_message(WEBHOOK, [{"type": "divider"}]) is False

    def test_send_truncates_over_block_limit_with_note(self):
        blocks = [{"type": "divider"}] * (MAX_BLOCKS_PER_MESSAGE + 10)
        with patch("slack_publisher.requests.post",
                   return_value=MagicMock(status_code=200)) as post:
            send_slack_message(WEBHOOK, blocks)
        sent = post.call_args.kwargs["json"]["blocks"]
        assert len(sent) == MAX_BLOCKS_PER_MESSAGE
        assert "truncated" in sent[-1]["text"]["text"]

    def test_failed_page_makes_publish_return_false(self):
        data = {"topics": [topic(f"T{i}") for i in range(MAX_TOPICS_PER_MESSAGE + 1)]}
        with patch("slack_publisher.send_slack_message", side_effect=[True, False]):
            assert publish_to_slack(data, WEBHOOK) is False


class TestPartialPublishDuplicates:

    @known_bug("page 1 posts, page 2 fails, publish returns False, so the retry reposts page 1")
    def test_retry_after_partial_failure_does_not_repost_delivered_topics(self):
        data = {"topics": [topic(f"T{i}") for i in range(MAX_TOPICS_PER_MESSAGE + 1)]}
        delivered = []

        def make_send(fail_on_call):
            counter = {"n": 0}

            def send(_url, blocks):
                counter["n"] += 1
                if counter["n"] == fail_on_call:
                    return False
                delivered.extend(
                    t for t in section_texts(blocks) if t.startswith("*T"))
                return True
            return send

        with patch("slack_publisher.send_slack_message", side_effect=make_send(2)):
            first = publish_to_slack(data, WEBHOOK)   # page 1 posts, page 2 fails
        with patch("slack_publisher.send_slack_message", side_effect=make_send(0)):
            publish_to_slack(data, WEBHOOK)           # next run, same articles

        assert first is False
        assert len(delivered) == len(set(delivered)), f"reposted: {delivered}"
