#!/usr/bin/env python3
# src/usage_cli.py

"""
CLI tool for querying and analyzing LLM usage data.

Commands:
    stats       - Show overall usage statistics
    by-provider - Show usage breakdown by provider
    by-task     - Show usage breakdown by task type
    by-model    - Show usage breakdown by model
    by-date     - Show usage breakdown by date
    costs       - Show cost analysis
    export      - Export usage data to CSV

Usage:
    python src/usage_cli.py stats
    python src/usage_cli.py by-provider --start 2026-01-01 --end 2026-01-31
    python src/usage_cli.py export --output usage_report.csv
"""

import argparse
import sys
from datetime import datetime

from history_db import (
    init_database,
    get_usage_stats,
    get_usage_by_provider,
    get_usage_by_task_type,
    get_usage_by_model,
    get_usage_by_date,
    export_usage_csv,
)
from pricing import format_cost


def cmd_stats(args):
    """Show overall usage statistics."""
    stats = get_usage_stats()

    if not stats or stats.get("total_calls", 0) == 0:
        print("No usage data found.")
        return

    print("\n=== LLM Usage Statistics ===\n")
    print(f"Total API Calls:      {stats['total_calls']:,}")
    print(f"Total Input Tokens:   {stats['total_input_tokens']:,}")
    print(f"Total Output Tokens:  {stats['total_output_tokens']:,}")
    print(f"Total Tokens:         {stats['total_tokens']:,}")
    print(f"Total Cost:           {format_cost(stats['total_cost_usd'])}")
    print(f"Avg Response Time:    {stats['avg_response_time_ms']:.0f} ms")

    if stats.get("first_call"):
        print(f"\nFirst Call:           {stats['first_call']}")
    if stats.get("last_call"):
        print(f"Last Call:            {stats['last_call']}")

    print()


def cmd_by_provider(args):
    """Show usage breakdown by provider."""
    data = get_usage_by_provider(
        start_date=args.start,
        end_date=args.end,
    )

    if not data:
        print("No usage data found.")
        return

    print("\n=== Usage by Provider ===\n")

    # Print header
    header = f"{'Provider':<12} {'Calls':>8} {'Input Tok':>12} {'Output Tok':>12} {'Total Tok':>12} {'Cost':>12} {'Avg Time':>10}"
    print(header)
    print("-" * len(header))

    for row in data:
        print(
            f"{row['provider']:<12} "
            f"{row['call_count']:>8,} "
            f"{row['input_tokens']:>12,} "
            f"{row['output_tokens']:>12,} "
            f"{row['total_tokens']:>12,} "
            f"{format_cost(row['total_cost_usd']):>12} "
            f"{row['avg_response_time_ms']:>9.0f}ms"
        )

    print()


def cmd_by_task(args):
    """Show usage breakdown by task type."""
    data = get_usage_by_task_type(
        start_date=args.start,
        end_date=args.end,
    )

    if not data:
        print("No usage data found.")
        return

    print("\n=== Usage by Task Type ===\n")

    # Print header
    header = f"{'Task Type':<12} {'Calls':>8} {'Input Tok':>12} {'Output Tok':>12} {'Total Tok':>12} {'Cost':>12} {'Avg Time':>10}"
    print(header)
    print("-" * len(header))

    for row in data:
        print(
            f"{row['task_type']:<12} "
            f"{row['call_count']:>8,} "
            f"{row['input_tokens']:>12,} "
            f"{row['output_tokens']:>12,} "
            f"{row['total_tokens']:>12,} "
            f"{format_cost(row['total_cost_usd']):>12} "
            f"{row['avg_response_time_ms']:>9.0f}ms"
        )

    print()


def cmd_by_model(args):
    """Show usage breakdown by model."""
    data = get_usage_by_model(
        start_date=args.start,
        end_date=args.end,
    )

    if not data:
        print("No usage data found.")
        return

    print("\n=== Usage by Model ===\n")

    # Print header
    header = f"{'Provider':<10} {'Model':<25} {'Calls':>8} {'Total Tok':>12} {'Cost':>12} {'Avg Time':>10}"
    print(header)
    print("-" * len(header))

    for row in data:
        model = row['model'][:24] if len(row['model']) > 24 else row['model']
        print(
            f"{row['provider']:<10} "
            f"{model:<25} "
            f"{row['call_count']:>8,} "
            f"{row['total_tokens']:>12,} "
            f"{format_cost(row['total_cost_usd']):>12} "
            f"{row['avg_response_time_ms']:>9.0f}ms"
        )

    print()


def cmd_by_date(args):
    """Show usage breakdown by date."""
    data = get_usage_by_date(
        start_date=args.start,
        end_date=args.end,
    )

    if not data:
        print("No usage data found.")
        return

    print("\n=== Usage by Date ===\n")

    # Print header
    header = f"{'Date':<12} {'Calls':>8} {'Input Tok':>12} {'Output Tok':>12} {'Total Tok':>12} {'Cost':>12}"
    print(header)
    print("-" * len(header))

    for row in data:
        print(
            f"{row['date']:<12} "
            f"{row['call_count']:>8,} "
            f"{row['input_tokens']:>12,} "
            f"{row['output_tokens']:>12,} "
            f"{row['total_tokens']:>12,} "
            f"{format_cost(row['total_cost_usd']):>12}"
        )

    print()


def cmd_costs(args):
    """Show detailed cost analysis."""
    stats = get_usage_stats()
    by_provider = get_usage_by_provider(start_date=args.start, end_date=args.end)
    by_task = get_usage_by_task_type(start_date=args.start, end_date=args.end)

    print("\n=== Cost Analysis ===\n")

    if stats and stats.get("total_calls", 0) > 0:
        total_cost = stats.get("total_cost_usd", 0) or 0
        total_calls = stats.get("total_calls", 1)
        total_tokens = stats.get("total_tokens", 1)

        print(f"Total Cost:           {format_cost(total_cost)}")
        print(f"Cost per Call:        {format_cost(total_cost / total_calls)}")
        print(f"Cost per 1K Tokens:   {format_cost(total_cost / (total_tokens / 1000) if total_tokens > 0 else 0)}")
        print()

    if by_provider:
        print("Cost by Provider:")
        for row in by_provider:
            pct = (row['total_cost_usd'] / stats['total_cost_usd'] * 100) if stats.get('total_cost_usd') else 0
            print(f"  {row['provider']:<12} {format_cost(row['total_cost_usd']):>12} ({pct:5.1f}%)")
        print()

    if by_task:
        print("Cost by Task Type:")
        for row in by_task:
            pct = (row['total_cost_usd'] / stats['total_cost_usd'] * 100) if stats.get('total_cost_usd') else 0
            print(f"  {row['task_type']:<12} {format_cost(row['total_cost_usd']):>12} ({pct:5.1f}%)")
        print()


def cmd_export(args):
    """Export usage data to CSV."""
    csv_data = export_usage_csv(
        start_date=args.start,
        end_date=args.end,
    )

    if not csv_data:
        print("No usage data to export.")
        return

    if args.output:
        with open(args.output, 'w') as f:
            f.write(csv_data)
        print(f"Exported to {args.output}")
    else:
        print(csv_data)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Usage Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show overall usage statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # by-provider command
    provider_parser = subparsers.add_parser("by-provider", help="Show usage by provider")
    provider_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    provider_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    provider_parser.set_defaults(func=cmd_by_provider)

    # by-task command
    task_parser = subparsers.add_parser("by-task", help="Show usage by task type")
    task_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    task_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    task_parser.set_defaults(func=cmd_by_task)

    # by-model command
    model_parser = subparsers.add_parser("by-model", help="Show usage by model")
    model_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    model_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    model_parser.set_defaults(func=cmd_by_model)

    # by-date command
    date_parser = subparsers.add_parser("by-date", help="Show usage by date")
    date_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    date_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    date_parser.set_defaults(func=cmd_by_date)

    # costs command
    costs_parser = subparsers.add_parser("costs", help="Show cost analysis")
    costs_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    costs_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    costs_parser.set_defaults(func=cmd_costs)

    # export command
    export_parser = subparsers.add_parser("export", help="Export usage data to CSV")
    export_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    export_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize database (creates tables if needed)
    init_database()

    # Run the command
    args.func(args)


if __name__ == "__main__":
    main()
