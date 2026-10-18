# src/rss_reader.py

import calendar
import feedparser
import requests
import json
import os
import logging
import re
import time
from html.parser import HTMLParser

CACHE_FILE = os.path.join("data", "cache.json")

# Skip feed entries older than this. Guards against archive-style feeds
# (e.g. a blog feed serving every post back to 2020) flooding the
# pipeline with stale articles. Set MAX_ARTICLE_AGE_DAYS=0 to disable.
DEFAULT_MAX_ARTICLE_AGE_DAYS = 30

class _TextExtractor(HTMLParser):
    """Collects the text of an HTML fragment, skipping script/style bodies."""

    BLOCK_TAGS = {"p", "br", "div", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)  # decodes &amp; &#8217; etc.
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def strip_html(text):
    """Reduce an RSS summary to plain text: tags removed, entities decoded,
    whitespace collapsed. Feeds often carry HTML here, which would otherwise
    reach the filter prompt and the embedding text as markup."""
    if not text:
        return ""
    extractor = _TextExtractor()
    try:
        extractor.feed(text)
        extractor.close()
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", text)).strip()
    return re.sub(r"\s+", " ", "".join(extractor.parts)).strip()


def load_cache():
    """Load cache from file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading cache: {e}")
    return {}

def save_cache(cache):
    """Save cache to file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        logging.error(f"Error saving cache: {e}")

def fetch_feeds(rss_feed_urls, max_age_days=None):
    """Fetch articles from RSS feeds.

    Parameters:
        rss_feed_urls (list): Feed URLs to fetch.
        max_age_days (int): Skip entries published more than this many
            days ago (default DEFAULT_MAX_ARTICLE_AGE_DAYS; 0 disables).
            Entries without a parseable date are kept.
    """
    if max_age_days is None:
        max_age_days = DEFAULT_MAX_ARTICLE_AGE_DAYS
    cutoff = None
    if max_age_days and max_age_days > 0:
        cutoff = time.time() - max_age_days * 86400

    articles = []
    stale_count = 0
    cache = load_cache()
    headers = {
        "User-Agent": "RSSFeedMonitor/1.0 (+team@ai4altruism.org)",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
    }

    for url in rss_feed_urls:
        url = url.strip()
        feed_headers = headers.copy()

        if url in cache:
            cached_info = cache[url]
            if cached_info.get("etag"):
                feed_headers["If-None-Match"] = cached_info["etag"]
            if cached_info.get("last_modified"):
                feed_headers["If-Modified-Since"] = cached_info["last_modified"]

        try:
            response = requests.get(url, headers=feed_headers, timeout=10)
            if response.status_code == 304:
                logging.info(f"Feed not modified: {url}")
                feed_content = cache[url].get("content", "")
            elif response.status_code == 200:
                feed_content = response.text
                cache[url] = {
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "content": feed_content
                }
            else:
                logging.warning(f"Received status code {response.status_code} for {url}")
                continue

            parsed_feed = feedparser.parse(feed_content)
            if parsed_feed.bozo:
                # bozo flags any well-formedness problem, including ones
                # feedparser recovered from; keep whatever it parsed
                if not parsed_feed.entries:
                    logging.warning(f"Error parsing feed: {url}. Error: {parsed_feed.bozo_exception}")
                    continue
                logging.warning(
                    f"Feed {url} is malformed ({parsed_feed.bozo_exception}); "
                    f"keeping {len(parsed_feed.entries)} parsed entries"
                )

            for entry in parsed_feed.entries:
                # Age guard: feedparser normalizes *_parsed to UTC
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if cutoff and published:
                    try:
                        if calendar.timegm(published) < cutoff:
                            stale_count += 1
                            continue
                    except (TypeError, ValueError, OverflowError):
                        pass
                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": strip_html(entry.get("summary", "")),
                    "published": entry.get("published", ""),
                })

        except Exception as e:
            logging.error(f"Exception fetching feed {url}: {e}")

    save_cache(cache)

    if stale_count:
        logging.info(
            f"Skipped {stale_count} feed entries older than {max_age_days} days"
        )

    # Drop exact-link duplicates across feeds (e.g. an aggregator feed
    # carrying the same URL as the publisher's own feed), keeping the
    # first occurrence.
    seen_links = set()
    deduped = []
    for article in articles:
        link = article.get("link", "")
        if link and link in seen_links:
            continue
        seen_links.add(link)
        deduped.append(article)
    if len(deduped) < len(articles):
        logging.info(
            f"Dropped {len(articles) - len(deduped)} exact-link duplicates across feeds"
        )
    return deduped
