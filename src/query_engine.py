# src/query_engine.py
"""
LLM-powered query engine for natural language queries against historical data.
Uses function calling to route queries to pre-built functions or generate safe SQL.
"""

import os
import re
import json
import logging
import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dotenv import dotenv_values

from utils import call_llm
from history_db import (
    get_db_path,
    get_db_connection,
    topic_counts_by_period,
    top_topics_comparison,
    topic_search,
    get_date_range,
    get_recent_summaries,
)


# =============================================================================
# Query Classification
# =============================================================================

# Query types that map to pre-built functions
QUERY_TYPES = {
    "trends": "Show topic trends over time",
    "comparison": "Compare topics between two time periods",
    "search": "Search for articles about a specific topic",
    "stats": "Show database statistics",
    "recent": "Show recent summaries",
    "custom": "Complex query requiring custom SQL"
}

# Function definitions for OpenAI function calling
FUNCTION_DEFINITIONS = [
    {
        "name": "get_trends",
        "description": "Get topic trends over a time period, showing how topics change over days, weeks, or months",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "period": {
                    "type": "string",
                    "enum": ["day", "week", "month"],
                    "description": "Aggregation period"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "compare_periods",
        "description": "Compare top topics between two time periods to see what's new, dropped, or common",
        "parameters": {
            "type": "object",
            "properties": {
                "period1_start": {
                    "type": "string",
                    "description": "Start date of first period (YYYY-MM-DD)"
                },
                "period1_end": {
                    "type": "string",
                    "description": "End date of first period (YYYY-MM-DD)"
                },
                "period2_start": {
                    "type": "string",
                    "description": "Start date of second period (YYYY-MM-DD)"
                },
                "period2_end": {
                    "type": "string",
                    "description": "End date of second period (YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top topics to compare (default: 10)"
                }
            },
            "required": ["period1_start", "period1_end", "period2_start", "period2_end"]
        }
    },
    {
        "name": "search_topics",
        "description": "Search for topics and articles matching a search term",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find in topic names"
                },
                "start_date": {
                    "type": "string",
                    "description": "Optional start date filter (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string",
                    "description": "Optional end date filter (YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 20)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "execute_sql",
        "description": "Execute a custom SQL query for complex analysis not covered by other functions. Only use for SELECT queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL SELECT query to execute"
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this query does"
                }
            },
            "required": ["sql", "explanation"]
        }
    }
]


# =============================================================================
# SQL Guardrails
# =============================================================================

# Forbidden SQL keywords (case-insensitive)
FORBIDDEN_SQL_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "GRANT", "REVOKE", "ATTACH", "DETACH", "VACUUM", "REINDEX",
    "PRAGMA", "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE"
]

# Forbidden SQL patterns (regex)
FORBIDDEN_SQL_PATTERNS = [
    r";\s*\w",  # Multiple statements
    r"--",      # SQL comments (could hide malicious code)
    r"/\*",     # Block comments
]


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validate that SQL query is safe to execute.

    Parameters:
        sql: SQL query string to validate.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query"

    sql_upper = sql.upper().strip()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed"

    # Check for forbidden keywords
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        # Use word boundary to avoid false positives (e.g., "SELECTED")
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden keyword: {keyword}"

    # Check for forbidden patterns
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Forbidden SQL pattern detected"

    # Check for subqueries that might contain write operations
    # Allow subqueries but validate them too
    subquery_match = re.findall(r'\(\s*SELECT[^)]+\)', sql, re.IGNORECASE)
    for subquery in subquery_match:
        # Subqueries are OK as long as they're SELECT
        pass  # Already validated by forbidden keyword check

    return True, ""


def execute_safe_sql(sql: str, db_path: Optional[str] = None) -> Tuple[bool, Any]:
    """
    Execute a validated SQL query in read-only mode.

    Parameters:
        sql: SQL query to execute (must pass validation).
        db_path: Path to database file.

    Returns:
        Tuple of (success, result). Result is list of dicts or error message.
    """
    # First validate
    is_valid, error = validate_sql(sql)
    if not is_valid:
        return False, error

    try:
        with get_db_connection(db_path, readonly=True) as conn:
            cursor = conn.execute(sql)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            return True, results

    except sqlite3.Error as e:
        return False, f"SQL error: {str(e)}"
    except Exception as e:
        return False, f"Query execution error: {str(e)}"


# =============================================================================
# Query Engine
# =============================================================================

# Database schema for LLM context
DATABASE_SCHEMA = """
Tables in the database:

1. summaries - Each run's complete output
   - id: INTEGER PRIMARY KEY
   - generated_at: TIMESTAMP (when summary was created)
   - raw_json: TEXT (full JSON output)
   - created_at: TIMESTAMP

2. topics - Normalized topics for querying
   - id: INTEGER PRIMARY KEY
   - summary_id: INTEGER (foreign key to summaries)
   - name: TEXT (original topic name)
   - normalized_name: TEXT (lowercase for matching)
   - summary_text: TEXT (topic summary)
   - article_count: INTEGER

3. articles - Articles linked to topics (has original URLs)
   - id: INTEGER PRIMARY KEY
   - topic_id: INTEGER (foreign key to topics)
   - title: TEXT
   - link: TEXT (original article URL - always include in results)
   - source: TEXT (RSS feed source)
   - published_date: TIMESTAMP

4. topic_aliases - Topic name variations
   - id: INTEGER PRIMARY KEY
   - canonical_name: TEXT
   - alias: TEXT
   - created_at: TIMESTAMP
"""


class QueryEngine:
    """
    LLM-powered query engine for natural language queries.
    """

    def __init__(self, openai_api_key: Optional[str] = None, model: Optional[str] = None,
                 db_path: Optional[str] = None):
        """
        Initialize the query engine.

        Parameters:
            openai_api_key: OpenAI API key. If None, reads from environment.
            model: Model to use for query classification. Defaults to QUERY_MODEL from env.
            db_path: Path to database file. If None, uses default.
        """
        env_vars = dotenv_values(".env")

        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY") or env_vars.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("QUERY_MODEL") or env_vars.get("QUERY_MODEL", "gpt-4o-mini")
        self.db_path = db_path or get_db_path()

        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass to constructor.")

    def _get_date_context(self) -> str:
        """Get date context for LLM prompts."""
        today = datetime.now()
        date_range = get_date_range(self.db_path)

        context = f"Today's date: {today.strftime('%Y-%m-%d')}\n"
        if date_range["earliest"]:
            context += f"Database contains data from {date_range['earliest']} to {date_range['latest']}"
        else:
            context += "Database is empty (no data yet)"

        return context

    def classify_and_execute(self, user_query: str) -> Dict[str, Any]:
        """
        Classify a natural language query and execute the appropriate function.

        Parameters:
            user_query: Natural language query from user.

        Returns:
            Dict with 'success', 'query_type', 'data', and 'response'.
        """
        # Build classification prompt
        prompt = f"""You are a query classifier for a news article database. Given a user's natural language query,
determine which function to call and extract the parameters.

{self._get_date_context()}

{DATABASE_SCHEMA}

Available functions:
1. get_trends - For questions about trends over time (e.g., "What were the hot topics last month?", "Show me weekly trends")
2. compare_periods - For comparing two time periods (e.g., "Compare Q1 vs Q2", "What changed between January and February?")
3. search_topics - For finding specific topics or articles (e.g., "Find articles about OpenAI", "Show me Google news")
4. execute_sql - ONLY for complex queries not covered by other functions (e.g., "Which topic has the most articles?", "Count unique sources")

User query: {user_query}

Respond with a JSON object containing:
- "function": the function name to call
- "parameters": object with the function parameters
- "reasoning": brief explanation of why you chose this function

For dates, use YYYY-MM-DD format. Interpret relative dates like "last month" or "Q1" based on today's date.
If the user mentions "Q1", "Q2", etc., interpret as:
- Q1: January 1 to March 31
- Q2: April 1 to June 30
- Q3: July 1 to September 30
- Q4: October 1 to December 31

IMPORTANT: Only use execute_sql when the other functions cannot answer the question.
"""

        try:
            # Call LLM to classify query
            response = call_llm(
                model_config=self.model,
                prompt=prompt,
                api_keys={"openai": self.api_key},
                instructions="You classify database queries and extract parameters. Always respond with valid JSON.",
                max_tokens=1000,
                temperature=0.0,
                task_type="query"
            )

            # Parse LLM response
            classification = self._parse_classification(response)
            if not classification:
                return {
                    "success": False,
                    "query_type": "unknown",
                    "data": None,
                    "response": "I couldn't understand your query. Please try rephrasing it."
                }

            # Execute the classified function
            return self._execute_function(classification, user_query)

        except Exception as e:
            logging.error(f"Query classification error: {e}")
            return {
                "success": False,
                "query_type": "error",
                "data": None,
                "response": f"Error processing query: {str(e)}"
            }

    def _parse_classification(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM classification response."""
        try:
            # Try to extract JSON from response
            # Handle markdown code blocks
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)

            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to find JSON object in response
            match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            logging.error(f"Failed to parse classification response: {response}")
            return None

    def _execute_function(self, classification: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Execute the classified function and format response."""
        func_name = classification.get("function", "")
        params = classification.get("parameters", {})
        reasoning = classification.get("reasoning", "")

        logging.info(f"Executing {func_name} with params: {params}")

        if func_name == "get_trends":
            return self._execute_trends(params, user_query)
        elif func_name == "compare_periods":
            return self._execute_comparison(params, user_query)
        elif func_name == "search_topics":
            return self._execute_search(params, user_query)
        elif func_name == "execute_sql":
            return self._execute_custom_sql(params, user_query)
        else:
            return {
                "success": False,
                "query_type": "unknown",
                "data": None,
                "response": f"Unknown function: {func_name}"
            }

    def _execute_trends(self, params: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Execute trends query and format response."""
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        period = params.get("period", "week")

        if not start_date or not end_date:
            return {
                "success": False,
                "query_type": "trends",
                "data": None,
                "response": "Could not determine date range for trends query."
            }

        data = topic_counts_by_period(start_date, end_date, period, self.db_path)

        if not data:
            return {
                "success": True,
                "query_type": "trends",
                "data": [],
                "response": f"No data found for the period {start_date} to {end_date}."
            }

        # Generate natural language response
        response = self._format_trends_response(data, start_date, end_date, period, user_query)

        return {
            "success": True,
            "query_type": "trends",
            "data": data,
            "response": response
        }

    def _execute_comparison(self, params: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Execute period comparison and format response."""
        p1_start = params.get("period1_start")
        p1_end = params.get("period1_end")
        p2_start = params.get("period2_start")
        p2_end = params.get("period2_end")
        limit = params.get("limit", 10)

        if not all([p1_start, p1_end, p2_start, p2_end]):
            return {
                "success": False,
                "query_type": "comparison",
                "data": None,
                "response": "Could not determine both time periods for comparison."
            }

        data = top_topics_comparison(p1_start, p1_end, p2_start, p2_end, limit, self.db_path)

        # Generate natural language response
        response = self._format_comparison_response(data, user_query)

        return {
            "success": True,
            "query_type": "comparison",
            "data": data,
            "response": response
        }

    def _execute_search(self, params: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Execute topic search and format response."""
        query = params.get("query", "")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        limit = params.get("limit", 20)

        if not query:
            return {
                "success": False,
                "query_type": "search",
                "data": None,
                "response": "No search term provided."
            }

        data = topic_search(query, start_date, end_date, limit, self.db_path)

        if not data:
            date_filter = ""
            if start_date and end_date:
                date_filter = f" between {start_date} and {end_date}"
            elif start_date:
                date_filter = f" after {start_date}"
            elif end_date:
                date_filter = f" before {end_date}"

            return {
                "success": True,
                "query_type": "search",
                "data": [],
                "response": f"No topics found matching '{query}'{date_filter}."
            }

        # Generate natural language response
        response = self._format_search_response(data, query, user_query)

        return {
            "success": True,
            "query_type": "search",
            "data": data,
            "response": response
        }

    def _execute_custom_sql(self, params: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Execute custom SQL query with guardrails."""
        sql = params.get("sql", "")
        explanation = params.get("explanation", "Custom query")

        if not sql:
            return {
                "success": False,
                "query_type": "custom",
                "data": None,
                "response": "No SQL query generated."
            }

        # Validate and execute
        success, result = execute_safe_sql(sql, self.db_path)

        if not success:
            return {
                "success": False,
                "query_type": "custom",
                "data": None,
                "response": f"Query failed: {result}"
            }

        # Generate natural language response
        response = self._format_custom_response(result, explanation, user_query)

        return {
            "success": True,
            "query_type": "custom",
            "data": result,
            "response": response
        }

    def _format_trends_response(self, data: List[Dict], start_date: str, end_date: str,
                                period: str, user_query: str) -> str:
        """Format trends data into natural language response."""
        # Group by period
        periods = {}
        for item in data:
            p = item["period"]
            if p not in periods:
                periods[p] = []
            periods[p].append(item)

        lines = [f"Topic trends from {start_date} to {end_date} (by {period}):\n"]

        for period_key in sorted(periods.keys()):
            items = periods[period_key]
            lines.append(f"\n**{period_key}**")

            # Sort by story count and take top 5
            top_items = sorted(items, key=lambda x: x["story_count"], reverse=True)[:5]

            for item in top_items:
                lines.append(f"- {item['topic']}: {item['story_count']} stories, {item['article_count']} articles")
                if item.get("articles"):
                    for article in item["articles"][:2]:
                        lines.append(f"  - {article['title']}")
                        lines.append(f"    {article['link']}")

        return "\n".join(lines)

    def _format_comparison_response(self, data: Dict, user_query: str) -> str:
        """Format comparison data into natural language response."""
        p1 = data.get("period1", {})
        p2 = data.get("period2", {})
        comp = data.get("comparison", {})

        lines = [
            f"Comparing {p1.get('start', '?')} - {p1.get('end', '?')} vs {p2.get('start', '?')} - {p2.get('end', '?')}:\n"
        ]

        # Period 1 top topics
        p1_topics = p1.get("topics", [])
        if p1_topics:
            lines.append("**Period 1 Top Topics:**")
            for i, t in enumerate(p1_topics[:5], 1):
                lines.append(f"{i}. {t['topic']} ({t['story_count']} stories)")

        # Period 2 top topics
        p2_topics = p2.get("topics", [])
        if p2_topics:
            lines.append("\n**Period 2 Top Topics:**")
            for i, t in enumerate(p2_topics[:5], 1):
                lines.append(f"{i}. {t['topic']} ({t['story_count']} stories)")

        # Comparison insights
        lines.append("\n**Analysis:**")

        common = comp.get("common_topics", [])
        new = comp.get("new_in_period2", [])
        dropped = comp.get("dropped_from_period1", [])

        if common:
            lines.append(f"- Consistent topics: {', '.join(common[:5])}")
        if new:
            lines.append(f"- New in Period 2: {', '.join(new[:5])}")
        if dropped:
            lines.append(f"- Dropped from Period 1: {', '.join(dropped[:5])}")

        return "\n".join(lines)

    def _format_search_response(self, data: List[Dict], query: str, user_query: str) -> str:
        """Format search results into natural language response."""
        lines = [f"Found {len(data)} results for '{query}':\n"]

        for item in data[:10]:  # Limit display
            lines.append(f"\n**{item['topic_name']}** ({item['generated_at'][:10]})")
            if item.get("summary_text"):
                # Truncate summary
                summary = item["summary_text"][:200]
                if len(item["summary_text"]) > 200:
                    summary += "..."
                lines.append(f"  {summary}")

            if item.get("articles"):
                lines.append(f"  Articles ({item['article_count']}):")
                for article in item["articles"][:3]:
                    lines.append(f"  - {article['title']}")
                    lines.append(f"    {article['link']}")

        if len(data) > 10:
            lines.append(f"\n... and {len(data) - 10} more results")

        return "\n".join(lines)

    def _format_custom_response(self, data: List[Dict], explanation: str, user_query: str) -> str:
        """Format custom SQL results into natural language response."""
        if not data:
            return "Query returned no results."

        lines = [f"{explanation}\n"]

        # Format as simple table for small results
        if len(data) <= 20:
            # Get column names from first row
            if data:
                columns = list(data[0].keys())
                lines.append(" | ".join(columns))
                lines.append("-" * 50)

                for row in data:
                    values = [str(row.get(col, ""))[:30] for col in columns]
                    lines.append(" | ".join(values))
        else:
            lines.append(f"Returned {len(data)} rows. Showing first 10:")
            columns = list(data[0].keys())
            lines.append(" | ".join(columns))
            lines.append("-" * 50)

            for row in data[:10]:
                values = [str(row.get(col, ""))[:30] for col in columns]
                lines.append(" | ".join(values))

        return "\n".join(lines)


def query(user_query: str, db_path: Optional[str] = None,
          openai_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to execute a natural language query.

    Parameters:
        user_query: Natural language query string.
        db_path: Optional path to database file.
        openai_api_key: Optional OpenAI API key.

    Returns:
        Dict with 'success', 'query_type', 'data', and 'response'.
    """
    engine = QueryEngine(openai_api_key=openai_api_key, db_path=db_path)
    return engine.classify_and_execute(user_query)
