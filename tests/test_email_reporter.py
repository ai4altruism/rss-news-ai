# tests/test_email_reporter.py
"""
email_reporter.generate_email_html and send_email (SMTP stubbed).

Title, summary and link come from RSS feeds and LLM output, so they are
untrusted; they must be HTML-escaped before landing in the message body.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_reporter import generate_email_html, send_email
from tests.fakes import known_bug

SMTP = {"server": "smtp.example.invalid", "port": 587,
        "username": "bot@example.invalid", "password": "pw", "use_tls": True}


def summary(name="Models", text="A summary.", title="Alpha", link="https://example.com/a"):
    return {"topics": [{"topic": name, "summary": text,
                        "articles": [{"title": title, "link": link}]}]}


class TestGenerateEmailHtml:

    def test_renders_topic_summary_and_link(self):
        html = generate_email_html(summary())
        assert '<h2 class="topic-title">Models</h2>' in html
        assert "<p>A summary.</p>" in html
        assert '<a href="https://example.com/a" target="_blank">Alpha</a>' in html

    def test_empty_topics_renders_shell_only(self):
        html = generate_email_html({"topics": []})
        assert "RSS AI News Monitor" in html
        assert 'class="topic"' not in html

    def test_missing_fields_use_defaults(self):
        html = generate_email_html({"topics": [{"articles": [{}]}]})
        assert "Uncategorized" in html
        assert "No summary available." in html
        assert ">Untitled</a>" in html

    @known_bug("topic, summary, title and link are interpolated into HTML without escaping")
    @pytest.mark.parametrize("field,payload", [
        ("topic", "<script>alert(1)</script>"),
        ("summary", "<img src=x onerror=alert(1)>"),
        ("title", "<b onmouseover=alert(1)>t</b>"),
        ("link", 'https://e.com/"><script>alert(1)</script>'),
    ])
    def test_untrusted_fields_are_escaped(self, field, payload):
        kwargs = {{"topic": "name", "summary": "text"}.get(field, field): payload}
        html = generate_email_html(summary(**kwargs))
        assert payload not in html


class TestSendEmail:

    def test_sends_multipart_over_starttls(self):
        server = MagicMock()
        with patch("email_reporter.smtplib.SMTP", return_value=server) as smtp:
            ok = send_email(summary(), SMTP, ["a@example.invalid", "b@example.invalid"])

        assert ok is True
        smtp.assert_called_once_with("smtp.example.invalid", 587)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("bot@example.invalid", "pw")
        recipients = server.sendmail.call_args.args[1]
        assert recipients == ["a@example.invalid", "b@example.invalid"]
        body = server.sendmail.call_args.args[2]
        assert "text/plain" in body and "text/html" in body

    def test_ssl_mode_when_tls_disabled(self):
        server = MagicMock()
        with patch("email_reporter.smtplib.SMTP_SSL", return_value=server) as ssl_cls:
            send_email(summary(), dict(SMTP, use_tls=False, port=465), ["a@example.invalid"])
        ssl_cls.assert_called_once_with("smtp.example.invalid", 465)
        server.starttls.assert_not_called()

    def test_smtp_failure_returns_false(self):
        with patch("email_reporter.smtplib.SMTP", side_effect=OSError("down")):
            assert send_email(summary(), SMTP, ["a@example.invalid"]) is False

    def test_plain_text_part_lists_articles(self):
        server = MagicMock()
        with patch("email_reporter.smtplib.SMTP", return_value=server):
            send_email(summary(), SMTP, ["a@example.invalid"])
        body = server.sendmail.call_args.args[2]
        assert "Alpha" in body
