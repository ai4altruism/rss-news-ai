#!/usr/bin/env python3
# src/history_cli.py
"""
Command-line interface for managing historical news data.
"""

import os
import sys
import argparse
import glob
from dotenv import dotenv_values

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from history_db import (
    init_database,
    import_json_file,
    get_db_path,
    get_summary_count,
    get_topic_count,
    get_article_count,
    get_recent_summaries,
)


def cmd_init(args):
    """Initialize the database."""
    db_path = args.db_path or get_db_path()
    print(f"Initializing database at: {db_path}")

    if os.path.exists(db_path) and not args.force:
        print(f"Database already exists at {db_path}")
        print("Use --force to reinitialize (this will NOT delete existing data)")
        return 1

    success = init_database(db_path)
    if success:
        print("Database initialized successfully.")
        return 0
    else:
        print("Failed to initialize database.")
        return 1


def cmd_import(args):
    """Import JSON summary files into the database."""
    db_path = args.db_path or get_db_path()

    # Ensure database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run 'init' first.")
        return 1

    # Expand glob patterns
    files = []
    for pattern in args.files:
        expanded = glob.glob(pattern)
        if expanded:
            files.extend(expanded)
        else:
            print(f"Warning: No files match pattern '{pattern}'")

    if not files:
        print("No files to import.")
        return 1

    print(f"Importing {len(files)} file(s)...")
    success_count = 0
    fail_count = 0

    for filepath in files:
        summary_id = import_json_file(filepath, db_path)
        if summary_id:
            print(f"  Imported: {filepath} (ID: {summary_id})")
            success_count += 1
        else:
            print(f"  Failed: {filepath}")
            fail_count += 1

    print(f"\nImport complete: {success_count} succeeded, {fail_count} failed")
    return 0 if fail_count == 0 else 1


def cmd_stats(args):
    """Show database statistics."""
    db_path = args.db_path or get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run 'init' first.")
        return 1

    summary_count = get_summary_count(db_path)
    topic_count = get_topic_count(db_path)
    article_count = get_article_count(db_path)

    print(f"Database: {db_path}")
    print(f"  Summaries: {summary_count}")
    print(f"  Topics:    {topic_count}")
    print(f"  Articles:  {article_count}")

    if summary_count > 0:
        print(f"\nRecent summaries:")
        recent = get_recent_summaries(5, db_path)
        for s in recent:
            print(f"  [{s['id']}] {s['generated_at']} - {s['topic_count']} topics")

    return 0


def main():
    """Main entry point."""
    # Load environment variables
    env_vars = dotenv_values(".env")
    default_db_path = env_vars.get("HISTORY_DB_PATH", "data/history.db")

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Manage historical news data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/history_cli.py init
  python src/history_cli.py import data/latest_summary.json
  python src/history_cli.py import backups/*.json
  python src/history_cli.py stats
        """,
    )

    parser.add_argument(
        "--db-path",
        default=None,
        help=f"Path to database file (default: {default_db_path})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize the database")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Force initialization even if database exists",
    )

    # Import command
    import_parser = subparsers.add_parser(
        "import", help="Import JSON summary files into the database"
    )
    import_parser.add_argument(
        "files",
        nargs="+",
        help="JSON files to import (supports glob patterns)",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to command handler
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "import":
        return cmd_import(args)
    elif args.command == "stats":
        return cmd_stats(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
