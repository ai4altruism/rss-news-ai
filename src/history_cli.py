#!/usr/bin/env python3
# src/history_cli.py
"""
Command-line interface for managing historical news data.
"""

import os
import sys
import argparse
import glob
import json
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
    get_date_range,
    topic_counts_by_period,
    top_topics_comparison,
    topic_search,
)


# =============================================================================
# Output Formatting
# =============================================================================

def format_table(headers, rows, col_widths=None):
    """Format data as a text table."""
    if not rows:
        return "No data found."

    # Calculate column widths
    if col_widths is None:
        col_widths = []
        for i, h in enumerate(headers):
            max_width = len(str(h))
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(min(max_width, 50))  # Cap at 50 chars

    # Build table
    lines = []

    # Header
    header_line = " | ".join(
        str(h).ljust(col_widths[i]) for i, h in enumerate(headers)
    )
    lines.append(header_line)
    lines.append("-" * len(header_line))

    # Rows
    for row in rows:
        row_line = " | ".join(
            str(row[i] if i < len(row) else "").ljust(col_widths[i])[:col_widths[i]]
            for i in range(len(headers))
        )
        lines.append(row_line)

    return "\n".join(lines)


def truncate(text, max_len=50):
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."


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
    date_range = get_date_range(db_path)

    print(f"Database: {db_path}")
    print(f"  Summaries: {summary_count}")
    print(f"  Topics:    {topic_count}")
    print(f"  Articles:  {article_count}")

    if date_range["earliest"]:
        print(f"  Date range: {date_range['earliest']} to {date_range['latest']}")

    if summary_count > 0:
        print(f"\nRecent summaries:")
        recent = get_recent_summaries(5, db_path)
        for s in recent:
            print(f"  [{s['id']}] {s['generated_at']} - {s['topic_count']} topics")

    return 0


def cmd_trends(args):
    """Show topic trends over time."""
    db_path = args.db_path or get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run 'init' first.")
        return 1

    results = topic_counts_by_period(
        args.start,
        args.end,
        args.period,
        db_path
    )

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return 0

    # Table format
    if not results:
        print(f"No data found for period {args.start} to {args.end}")
        return 0

    print(f"\nTopic Trends ({args.period}ly): {args.start} to {args.end}")
    print("=" * 70)

    # Group by period for display
    current_period = None
    for item in results:
        if item["period"] != current_period:
            current_period = item["period"]
            print(f"\n{current_period}")
            print("-" * 40)

        article_links = ", ".join(
            truncate(a["title"], 30) for a in item["articles"][:2]
        )
        print(f"  {item['topic']}: {item['story_count']} stories, {item['article_count']} articles")
        if article_links:
            print(f"    Examples: {article_links}")

    return 0


def cmd_compare(args):
    """Compare topics between two periods."""
    db_path = args.db_path or get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run 'init' first.")
        return 1

    results = top_topics_comparison(
        args.period1[0],
        args.period1[1],
        args.period2[0],
        args.period2[1],
        args.limit,
        db_path
    )

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return 0

    # Table format
    p1 = results["period1"]
    p2 = results["period2"]
    comp = results["comparison"]

    print(f"\nPeriod Comparison")
    print("=" * 70)

    print(f"\nPeriod 1: {p1['start']} to {p1['end']}")
    print("-" * 40)
    if p1["topics"]:
        headers = ["Rank", "Topic", "Stories", "Articles"]
        rows = [
            (i+1, t["topic"], t["story_count"], t["article_count"])
            for i, t in enumerate(p1["topics"])
        ]
        print(format_table(headers, rows))
    else:
        print("  No topics found")

    print(f"\nPeriod 2: {p2['start']} to {p2['end']}")
    print("-" * 40)
    if p2["topics"]:
        headers = ["Rank", "Topic", "Stories", "Articles"]
        rows = [
            (i+1, t["topic"], t["story_count"], t["article_count"])
            for i, t in enumerate(p2["topics"])
        ]
        print(format_table(headers, rows))
    else:
        print("  No topics found")

    print(f"\nComparison")
    print("-" * 40)
    print(f"  Common topics: {len(comp.get('common_topics', []))}")
    if comp.get("common_topics"):
        print(f"    {', '.join(comp['common_topics'][:5])}")
    print(f"  New in Period 2: {len(comp.get('new_in_period2', []))}")
    if comp.get("new_in_period2"):
        print(f"    {', '.join(comp['new_in_period2'][:5])}")
    print(f"  Dropped from Period 1: {len(comp.get('dropped_from_period1', []))}")
    if comp.get("dropped_from_period1"):
        print(f"    {', '.join(comp['dropped_from_period1'][:5])}")

    return 0


def cmd_search(args):
    """Search for topics."""
    db_path = args.db_path or get_db_path()

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run 'init' first.")
        return 1

    results = topic_search(
        args.query,
        args.start,
        args.end,
        args.limit,
        db_path
    )

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return 0

    # Table format
    if not results:
        print(f"No topics found matching '{args.query}'")
        return 0

    print(f"\nSearch Results for '{args.query}'")
    print("=" * 70)

    for item in results:
        print(f"\n{item['topic_name']} ({item['generated_at'][:10]})")
        print(f"  Summary: {truncate(item['summary_text'], 100)}")
        print(f"  Articles ({item['article_count']}):")
        for article in item["articles"][:3]:
            print(f"    - {truncate(article['title'], 60)}")
            print(f"      {article['link']}")

    print(f"\nTotal: {len(results)} results")
    return 0


def main():
    """Main entry point."""
    # Load environment variables
    env_vars = dotenv_values(".env")
    default_db_path = env_vars.get("HISTORY_DB_PATH", "data/history.db")

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Manage and query historical news data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/history_cli.py init
  python src/history_cli.py import data/latest_summary.json
  python src/history_cli.py stats

  # Query commands
  python src/history_cli.py trends --start 2024-01-01 --end 2024-06-30 --period month
  python src/history_cli.py compare --period1 2024-01-01 2024-03-31 --period2 2024-04-01 2024-06-30
  python src/history_cli.py search "OpenAI" --start 2024-01-01
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
    subparsers.add_parser("stats", help="Show database statistics")

    # Trends command
    trends_parser = subparsers.add_parser(
        "trends", help="Show topic trends over time"
    )
    trends_parser.add_argument(
        "--start", required=True,
        help="Start date (YYYY-MM-DD)"
    )
    trends_parser.add_argument(
        "--end", required=True,
        help="End date (YYYY-MM-DD)"
    )
    trends_parser.add_argument(
        "--period", choices=["day", "week", "month"], default="week",
        help="Aggregation period (default: week)"
    )
    trends_parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)"
    )

    # Compare command
    compare_parser = subparsers.add_parser(
        "compare", help="Compare topics between two time periods"
    )
    compare_parser.add_argument(
        "--period1", nargs=2, required=True, metavar=("START", "END"),
        help="First period (START END in YYYY-MM-DD format)"
    )
    compare_parser.add_argument(
        "--period2", nargs=2, required=True, metavar=("START", "END"),
        help="Second period (START END in YYYY-MM-DD format)"
    )
    compare_parser.add_argument(
        "--limit", type=int, default=10,
        help="Number of top topics to compare (default: 10)"
    )
    compare_parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)"
    )

    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search for topics by name"
    )
    search_parser.add_argument(
        "query",
        help="Search string (case-insensitive, partial match)"
    )
    search_parser.add_argument(
        "--start",
        help="Filter by start date (YYYY-MM-DD)"
    )
    search_parser.add_argument(
        "--end",
        help="Filter by end date (YYYY-MM-DD)"
    )
    search_parser.add_argument(
        "--limit", type=int, default=50,
        help="Maximum results (default: 50)"
    )
    search_parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)"
    )

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
    elif args.command == "trends":
        return cmd_trends(args)
    elif args.command == "compare":
        return cmd_compare(args)
    elif args.command == "search":
        return cmd_search(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
