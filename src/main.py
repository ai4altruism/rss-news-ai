# src/main.py

import os
import json
import logging
import argparse
from dotenv import dotenv_values
from rss_reader import fetch_feeds
from llm_filter import filter_stories
from summarizer import group_and_summarize
from utils import setup_logger
from article_history import ArticleHistory

# Import optional output modules
try:
    from slack_publisher import publish_to_slack
except ImportError:
    publish_to_slack = None

try:
    from email_reporter import send_email
except ImportError:
    send_email = None

try:
    from web_dashboard import save_summary, run_dashboard
except ImportError:
    save_summary = None
    run_dashboard = None

try:
    from history_db import save_summary_to_db, init_database
except ImportError:
    save_summary_to_db = None
    init_database = None

try:
    from embeddings import filter_semantic_duplicates, persist_embeddings
except ImportError:
    filter_semantic_duplicates = None
    persist_embeddings = None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="RSS Feed Monitor")
    parser.add_argument(
        "--output",
        choices=["console", "slack", "email", "web"],
        default="console",
        help="Output method (default: console)",
    )
    parser.add_argument(
        "--web-server", action="store_true", help="Run the web dashboard server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for web dashboard (default: WEB_DASHBOARD_PORT in .env, or 5001)",
    )
    parser.add_argument(
        "--history-retention",
        type=int,
        default=None,
        help="Number of days to retain article history (default: HISTORY_RETENTION_DAYS in .env, or 30)",
    )
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Ignore article history (process all articles)",
    )
    parser.add_argument(
        "--no-semantic-dedup",
        action="store_true",
        help="Disable semantic deduplication (embedding-based duplicate detection)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Load environment variables manually to properly handle multi-line values.
    # .env file values take precedence; the process environment (e.g. docker
    # run --env-file, which sets env vars but creates no file) is the
    # fallback so both deployment styles work.
    env_vars = {
        **os.environ,
        **{k: v for k, v in dotenv_values(".env").items() if v is not None},
    }
    openai_api_key = env_vars.get("OPENAI_API_KEY")

    # Setup logger
    logger = setup_logger()
    logger.info("Starting RSS Feed Monitor...")

    # Parse RSS feeds from .env
    rss_feeds = env_vars.get("RSS_FEEDS", "")

    if "\n" in rss_feeds:
        rss_feed_list = [url.strip() for url in rss_feeds.split("\n") if url.strip()]
    else:
        rss_feed_list = [url.strip() for url in rss_feeds.split(",") if url.strip()]

    logger.info(f"Final RSS Feed List: {rss_feed_list}")

    # Parse model configuration
    filter_prompt = env_vars.get("FILTER_PROMPT", "")
    filter_model = env_vars.get("FILTER_MODEL", "gpt-4o-mini")
    group_model = env_vars.get("GROUP_MODEL", "gpt-4o-mini")
    summarize_model = env_vars.get("SUMMARIZE_MODEL", "gpt-4o-mini")

    # Get history retention period from args or env
    history_retention_days = (
        args.history_retention
        if args.history_retention is not None
        else int(env_vars.get("HISTORY_RETENTION_DAYS", 30))
    )

    # Get web dashboard port from args or env
    web_port = (
        args.port if args.port is not None else int(env_vars.get("WEB_DASHBOARD_PORT", 5001))
    )

    if not openai_api_key:
        logger.error("OPENAI_API_KEY is not set in the .env file")
        return

    # Check if we should run the web server only
    if args.web_server and run_dashboard:
        logger.info(f"Starting web dashboard server on port {web_port}...")
        run_dashboard(port=web_port, debug=False)
        return

    def emit_empty_summary(message):
        """Emit an empty summary for outputs that expect one. For web
        output, still serve the dashboard so the container does not exit
        just because one cycle produced nothing."""
        empty_summary = {"topics": [], "message": message}
        if args.output == "web" and save_summary:
            save_summary(empty_summary)
        if args.output == "console":
            print(json.dumps(empty_summary, indent=4))
        if args.output == "web" and run_dashboard:
            logger.info(f"Starting web dashboard server on port {web_port}...")
            run_dashboard(port=web_port, debug=False, use_reloader=False)

    # Initialize article history
    article_history = ArticleHistory(retention_days=history_retention_days)

    # Fetch articles
    logger.info("Fetching RSS feeds...")
    articles = fetch_feeds(rss_feed_list)
    logger.info(f"Fetched {len(articles)} articles.")

    # Filter out previously published articles unless --ignore-history is specified
    if not args.ignore_history:
        unique_articles = article_history.filter_published(articles)
        logger.info(
            f"{len(unique_articles)} unique articles after filtering previously published ones."
        )

        # If no new articles, exit early with appropriate messaging
        if not unique_articles:
            logger.info("No new articles to process.")
            emit_empty_summary("No new articles found since last update.")
            return
    else:
        logger.info("Article history check skipped (--ignore-history flag used).")
        unique_articles = articles

    # Semantic deduplication (embedding-based duplicate detection).
    # Embedding persistence is deferred: an embedding is stored only once
    # its article's fate is decided (delivered, or rejected by the LLM
    # filter). Persisting earlier would let a failed run permanently
    # suppress its articles — on the next run they would match their own
    # stored embedding and be dropped as duplicates.
    semantic_dedup_enabled = (
        filter_semantic_duplicates is not None
        and not args.no_semantic_dedup
        and env_vars.get("ENABLE_SEMANTIC_DEDUP", "true").lower() == "true"
    )

    pending_embeddings = []
    if semantic_dedup_enabled and unique_articles:
        logger.info("Running semantic deduplication...")
        try:
            # Tunables pass through as None when unset so embeddings.py's
            # DEFAULT_* constants remain the single source of truth
            unique_articles, dedup_stats = filter_semantic_duplicates(
                articles=unique_articles,
                api_key=openai_api_key,
                similarity_threshold=(
                    float(env_vars["SIMILARITY_THRESHOLD"])
                    if env_vars.get("SIMILARITY_THRESHOLD") else None
                ),
                lookback_days=(
                    int(env_vars["DEDUP_LOOKBACK_DAYS"])
                    if env_vars.get("DEDUP_LOOKBACK_DAYS") else None
                ),
                embedding_model=env_vars.get("EMBEDDING_MODEL") or None,
                retention_days=(
                    int(env_vars["EMBEDDING_RETENTION_DAYS"])
                    if env_vars.get("EMBEDDING_RETENTION_DAYS") else None
                ),
                defer_saves=True,
            )
            pending_embeddings = dedup_stats.get("pending_embeddings", [])
            logger.info(
                f"Semantic dedup: {dedup_stats['duplicates']} duplicates filtered, "
                f"{dedup_stats['unique']} unique articles remain"
            )
        except Exception as e:
            logger.warning(f"Semantic deduplication failed (continuing without): {e}")
    elif not semantic_dedup_enabled:
        logger.debug("Semantic deduplication disabled or not available")

    pending_by_url = {e["url"]: e for e in pending_embeddings}

    def persist_embeddings_for(article_list):
        """Persist deferred embeddings for the given articles' URLs."""
        if not persist_embeddings:
            return
        entries = [
            pending_by_url[a.get("link")]
            for a in article_list
            if a.get("link") in pending_by_url
        ]
        if entries:
            saved = persist_embeddings(entries)
            logger.info(f"Persisted {saved} article embeddings.")

    # If no articles remain after deduplication, exit early
    if not unique_articles:
        logger.info("No unique articles to process after deduplication.")
        emit_empty_summary("No unique articles found after deduplication.")
        return

    # Filter articles using LLM
    logger.info("Filtering articles using LLM...")
    filtered_articles, rejected_articles, errored_articles = filter_stories(
        unique_articles, filter_prompt, filter_model, openai_api_key
    )
    logger.info(
        f"{len(filtered_articles)} articles remain after filtering "
        f"({len(rejected_articles)} rejected, "
        f"{len(errored_articles)} errored and will be retried next run)."
    )

    # Record rejected articles so they are not re-filtered on every run,
    # and persist their embeddings so future near-duplicates from other
    # outlets stay suppressed. Errored articles are deliberately left
    # unrecorded so they get retried.
    if rejected_articles:
        if not args.ignore_history:
            article_history.mark_as_published(rejected_articles, status="rejected")
        persist_embeddings_for(rejected_articles)

    # If no articles remain after filtering, exit early without sending reports
    if not filtered_articles:
        logger.info("No articles passed the LLM filter.")
        emit_empty_summary("No relevant articles found since last update.")
        return

    # Group and summarize
    logger.info("Grouping and summarizing articles...")
    summary = group_and_summarize(
        filtered_articles, group_model, summarize_model, openai_api_key
    )

    # Output handling based on selected method. Articles are marked as
    # published (and their embeddings persisted) only after the selected
    # output succeeds, so a failed delivery is retried on the next run
    # instead of being silently lost.
    delivered = False

    if args.output == "console":
        # Output the structured JSON summary to console
        output_json = json.dumps(summary, indent=4)
        logger.info("Summary generated:")
        print(output_json)
        delivered = True

    elif args.output == "web":
        # Delivery for web output means the summary was saved for the
        # dashboard, not merely printed
        if save_summary:
            save_summary(summary)
            logger.info("Summary saved for web dashboard.")
            delivered = True
        else:
            logger.error(
                "Web dashboard module not available; articles will be retried next run."
            )

    elif args.output == "slack":
        if not summary.get("topics") or len(summary.get("topics")) == 0:
            logger.info("No content to publish to Slack; skipping empty message.")
        else:
            if publish_to_slack:
                # Get Slack webhook URL from environment
                slack_webhook = env_vars.get("SLACK_WEBHOOK_URL")
                if not slack_webhook:
                    logger.error("SLACK_WEBHOOK_URL is not set in the .env file")
                    return

                logger.info("Publishing to Slack...")
                delivered = publish_to_slack(summary, slack_webhook)
                if delivered:
                    logger.info("Successfully published to Slack.")
                else:
                    logger.error(
                        "Failed to publish to Slack. Articles will be retried next run."
                    )
            else:
                logger.error(
                    "Slack publisher module not available. Install required dependencies."
                )

    elif args.output == "email":
        if send_email:
            # Get email configuration from environment
            smtp_config = {
                "server": env_vars.get("SMTP_SERVER"),
                "port": int(env_vars.get("SMTP_PORT", 587)),
                "username": env_vars.get("SMTP_USERNAME"),
                "password": env_vars.get("SMTP_PASSWORD"),
                "use_tls": env_vars.get("SMTP_USE_TLS", "True").lower() == "true",
            }

            recipients = [
                r.strip()
                for r in env_vars.get("EMAIL_RECIPIENTS", "").split(",")
                if r.strip()
            ]

            if not all(
                [
                    smtp_config["server"],
                    smtp_config["username"],
                    smtp_config["password"],
                ]
            ):
                logger.error("Email configuration incomplete in .env file")
                return

            if not recipients:
                logger.error("No email recipients specified")
                return

            logger.info(f"Sending email to {len(recipients)} recipients...")
            delivered = send_email(summary, smtp_config, recipients)
            if delivered:
                logger.info("Email sent successfully.")
            else:
                logger.error("Failed to send email. Articles will be retried next run.")
        else:
            logger.error(
                "Email reporter module not available. Install required dependencies."
            )

    # Post-delivery bookkeeping: only a delivered article is committed to
    # history and the embedding store.
    if delivered:
        if not args.ignore_history:
            article_history.mark_as_published(filtered_articles)
            logger.info(f"Marked {len(filtered_articles)} articles as published.")
        persist_embeddings_for(filtered_articles)

        # Save to historical database (non-fatal if it fails)
        if save_summary_to_db:
            try:
                summary_id = save_summary_to_db(summary)
                if summary_id:
                    logger.info(f"Summary saved to historical database (ID: {summary_id})")
                else:
                    logger.warning("Failed to save summary to historical database")
            except Exception as e:
                logger.warning(f"Could not save to historical database: {e}")

    # Run web server if requested (after history bookkeeping — this call blocks)
    if args.output == "web" and delivered and run_dashboard:
        logger.info(f"Starting web dashboard server on port {web_port}...")
        run_dashboard(port=web_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
