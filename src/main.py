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
        "--port", type=int, default=5001, help="Port for web dashboard (default: 5001)"
    )
    parser.add_argument(
        "--history-retention",
        type=int,
        default=30,
        help="Number of days to retain article history (default: 30)",
    )
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Ignore article history (process all articles)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Load environment variables manually to properly handle multi-line values
    env_vars = dotenv_values(".env")
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
    history_retention_days = args.history_retention or int(
        env_vars.get("HISTORY_RETENTION_DAYS", 14)
    )

    if not openai_api_key:
        logger.error("OPENAI_API_KEY is not set in the .env file")
        return

    # Check if we should run the web server only
    if args.web_server and run_dashboard:
        logger.info(f"Starting web dashboard server on port {args.port}...")
        run_dashboard(port=args.port, debug=True)
        return

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
            # Create an empty summary for outputs that expect one
            empty_summary = {
                "topics": [],
                "message": "No new articles found since last update.",
            }

            # Handle outputs that need a summary even when empty
            if args.output == "web" and save_summary:
                save_summary(empty_summary)

            if args.output == "console":
                print(json.dumps(empty_summary, indent=4))

            return
    else:
        logger.info("Article history check skipped (--ignore-history flag used).")
        unique_articles = articles

    # Filter articles using LLM
    logger.info("Filtering articles using LLM...")
    filtered_articles = filter_stories(
        unique_articles, filter_prompt, filter_model, openai_api_key
    )
    logger.info(f"{len(filtered_articles)} articles remain after filtering.")

    # Group and summarize
    logger.info("Grouping and summarizing articles...")
    summary = group_and_summarize(
        filtered_articles, group_model, summarize_model, openai_api_key
    )

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

    # Mark articles as published only if successfully processed and history tracking is enabled
    if filtered_articles and not args.ignore_history:
        article_history.mark_as_published(filtered_articles)
        logger.info(f"Marked {len(filtered_articles)} articles as published.")

    # Output handling based on selected method
    if args.output == "console" or args.output == "web":
        # Output the structured JSON summary to console
        output_json = json.dumps(summary, indent=4)
        logger.info("Summary generated:")
        print(output_json)

        # Save for web dashboard if requested
        if args.output == "web" and save_summary:
            save_summary(summary)
            logger.info("Summary saved for web dashboard.")

            # Run web server if requested
            if run_dashboard:
                logger.info(f"Starting web dashboard server on port {args.port}...")
                run_dashboard(port=args.port, debug=True, use_reloader=False)

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
                success = publish_to_slack(summary, slack_webhook)
                if success:
                    logger.info("Successfully published to Slack.")
                else:
                    logger.error("Failed to publish to Slack.")
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

            recipients = env_vars.get("EMAIL_RECIPIENTS", "").split(",")

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
            success = send_email(summary, smtp_config, recipients)
            if success:
                logger.info("Email sent successfully.")
            else:
                logger.error("Failed to send email.")
        else:
            logger.error(
                "Email reporter module not available. Install required dependencies."
            )


if __name__ == "__main__":
    main()
