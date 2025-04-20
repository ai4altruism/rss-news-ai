# src/scheduler.py

import time
import subprocess
import os
import logging
import argparse
from dotenv import dotenv_values
from utils import setup_logger


def run_scheduler(
    output="slack", interval=None, history_retention=None, ignore_history=False
):
    """
    Run the RSS Feed Monitor at regular intervals.

    Parameters:
        output (str): Output method (console, slack, email, web)
        interval (int): Interval in minutes between runs (defaults to PROCESS_INTERVAL in .env)
        history_retention (int): Number of days to retain article history
        ignore_history (bool): Whether to ignore article history
    """
    logger = setup_logger()
    logger.info("Starting RSS Feed Monitor Scheduler...")

    # Load environment variables
    env_vars = dotenv_values(".env")

    # Get interval from parameter, .env, or default to 60 minutes
    if interval is None:
        interval = int(env_vars.get("PROCESS_INTERVAL", 60))

    # Get history retention period
    if history_retention is None:
        history_retention = int(env_vars.get("HISTORY_RETENTION_DAYS", 30))

    logger.info(f"Running with {output} output method every {interval} minutes")
    logger.info(f"Article history retention: {history_retention} days")

    if ignore_history:
        logger.info("Article history will be ignored (all articles will be processed)")

    while True:
        logger.info(f"Running RSS Feed Monitor...")

        try:
            # Run the main.py script as a subprocess
            cmd = [
                "python",
                "src/main.py",
                "--output",
                output,
                "--history-retention",
                str(history_retention),
            ]

            if ignore_history:
                cmd.append("--ignore-history")

            subprocess.run(cmd, check=True)
            logger.info(f"RSS Feed Monitor run completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running RSS Feed Monitor: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        # Wait for the next interval
        next_run_time = time.time() + (interval * 60)
        logger.info(
            f"Next run scheduled at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run_time))}"
        )

        try:
            time.sleep(interval * 60)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS Feed Monitor Scheduler")
    parser.add_argument(
        "--output",
        choices=["console", "slack", "email", "web"],
        default="slack",
        help="Output method (default: slack)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Interval in minutes between runs (defaults to PROCESS_INTERVAL in .env)",
    )
    parser.add_argument(
        "--history-retention",
        type=int,
        help="Number of days to retain article history (defaults to HISTORY_RETENTION_DAYS in .env)",
    )
    parser.add_argument(
        "--ignore-history",
        action="store_true",
        help="Ignore article history (process all articles)",
    )
    args = parser.parse_args()

    run_scheduler(
        output=args.output,
        interval=args.interval,
        history_retention=args.history_retention,
        ignore_history=args.ignore_history,
    )
