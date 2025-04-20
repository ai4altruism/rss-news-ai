# src/rss_reader.py

import feedparser
import requests
import json
import os
import logging

CACHE_FILE = os.path.join("data", "cache.json")

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

def fetch_feeds(rss_feed_urls):
    """Fetch articles from RSS feeds."""
    articles = []
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
                logging.warning(f"Error parsing feed: {url}. Error: {parsed_feed.bozo_exception}")
                continue

            for entry in parsed_feed.entries:
                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                })

        except Exception as e:
            logging.error(f"Exception fetching feed {url}: {e}")

    save_cache(cache)
    return articles
