# src/web_dashboard.py

from flask import Flask, render_template, jsonify, request
import json
import os
import sys
from datetime import datetime
from dotenv import dotenv_values

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)
SUMMARY_FILE = "data/latest_summary.json"

# Load environment variables
env_vars = dotenv_values(".env")

# Import history database functions (optional - may not be initialized)
try:
    from history_db import (
        get_db_path,
        get_date_range,
        topic_counts_by_period,
        top_topics_comparison,
        topic_search,
        get_summary_count,
        get_topic_count,
        get_article_count,
    )
    HISTORY_DB_AVAILABLE = True
except ImportError:
    HISTORY_DB_AVAILABLE = False

# Import query engine (optional - requires API key)
try:
    from query_engine import QueryEngine
    QUERY_ENGINE_AVAILABLE = True
except ImportError:
    QUERY_ENGINE_AVAILABLE = False

def save_summary(summary_data):
    """
    Save the summary data to a JSON file with timestamp.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
    """
    # Add timestamp
    summary_data["generated_at"] = datetime.now().isoformat()
    
    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary_data, f)

@app.route('/')
def home():
    """Render the dashboard homepage."""
    try:
        with open(SUMMARY_FILE, "r") as f:
            summary_data = json.load(f)
        
        return render_template('dashboard.html', 
                              summary=summary_data, 
                              timestamp=datetime.fromisoformat(summary_data.get("generated_at", datetime.now().isoformat())))
    except (FileNotFoundError, json.JSONDecodeError):
        return render_template('dashboard.html', summary={"topics": []}, timestamp=datetime.now())

@app.route('/api/summary')
def api_summary():
    """API endpoint to get the latest summary as JSON."""
    try:
        with open(SUMMARY_FILE, "r") as f:
            summary_data = json.load(f)
        return jsonify(summary_data)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"topics": [], "generated_at": datetime.now().isoformat()})


# =============================================================================
# History API Endpoints
# =============================================================================

@app.route('/history')
def history_page():
    """Render the history query interface."""
    if not HISTORY_DB_AVAILABLE:
        return render_template('error.html',
                             error="History database not available",
                             message="The historical database module is not installed.")

    # Get database stats for display
    db_path = get_db_path()
    stats = {
        "summaries": get_summary_count(db_path),
        "topics": get_topic_count(db_path),
        "articles": get_article_count(db_path),
        "date_range": get_date_range(db_path)
    }

    return render_template('history.html',
                          stats=stats,
                          query_available=QUERY_ENGINE_AVAILABLE)


@app.route('/api/history/stats')
def api_history_stats():
    """Get database statistics."""
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    db_path = get_db_path()
    return jsonify({
        "summaries": get_summary_count(db_path),
        "topics": get_topic_count(db_path),
        "articles": get_article_count(db_path),
        "date_range": get_date_range(db_path)
    })


@app.route('/api/trends')
def api_trends():
    """Get topic trends over time.

    Query params:
        start: Start date (YYYY-MM-DD) - required
        end: End date (YYYY-MM-DD) - required
        period: Aggregation period (day, week, month) - default: week
    """
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    period = request.args.get('period', 'week')

    if not start_date or not end_date:
        return jsonify({"error": "start and end date parameters required"}), 400

    if period not in ['day', 'week', 'month']:
        return jsonify({"error": "period must be day, week, or month"}), 400

    db_path = get_db_path()
    data = topic_counts_by_period(start_date, end_date, period, db_path)

    return jsonify({
        "start": start_date,
        "end": end_date,
        "period": period,
        "data": data
    })


@app.route('/api/compare')
def api_compare():
    """Compare topics between two time periods.

    Query params:
        p1_start: Period 1 start date (YYYY-MM-DD) - required
        p1_end: Period 1 end date (YYYY-MM-DD) - required
        p2_start: Period 2 start date (YYYY-MM-DD) - required
        p2_end: Period 2 end date (YYYY-MM-DD) - required
        limit: Number of top topics per period - default: 10
    """
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    p1_start = request.args.get('p1_start')
    p1_end = request.args.get('p1_end')
    p2_start = request.args.get('p2_start')
    p2_end = request.args.get('p2_end')
    limit = request.args.get('limit', 10, type=int)

    if not all([p1_start, p1_end, p2_start, p2_end]):
        return jsonify({"error": "All period parameters required (p1_start, p1_end, p2_start, p2_end)"}), 400

    db_path = get_db_path()
    data = top_topics_comparison(p1_start, p1_end, p2_start, p2_end, limit, db_path)

    return jsonify(data)


@app.route('/api/topics')
def api_topics_search():
    """Search for topics by name.

    Query params:
        search: Search term - required
        start: Optional start date filter (YYYY-MM-DD)
        end: Optional end date filter (YYYY-MM-DD)
        limit: Maximum results - default: 50
    """
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    search_term = request.args.get('search')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    limit = request.args.get('limit', 50, type=int)

    if not search_term:
        return jsonify({"error": "search parameter required"}), 400

    db_path = get_db_path()
    data = topic_search(search_term, start_date, end_date, limit, db_path)

    return jsonify({
        "query": search_term,
        "count": len(data),
        "results": data
    })


@app.route('/api/query', methods=['POST'])
def api_natural_language_query():
    """Execute a natural language query.

    Request body (JSON):
        query: Natural language query string - required

    Returns:
        success: boolean
        query_type: string (trends, comparison, search, custom)
        response: Natural language response
        data: Structured result data
    """
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    if not QUERY_ENGINE_AVAILABLE:
        return jsonify({"error": "Query engine not available"}), 503

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY") or env_vars.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OpenAI API key not configured"}), 503

    # Get query from request
    data = request.get_json()
    if not data or not data.get('query'):
        return jsonify({"error": "query field required in request body"}), 400

    query_text = data['query']

    try:
        engine = QueryEngine(openai_api_key=api_key)
        result = engine.classify_and_execute(query_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "response": f"Query failed: {str(e)}"
        }), 500


def run_dashboard(host='0.0.0.0', port=5002, debug=False, use_reloader=False):
    """Run the dashboard server."""
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)

if __name__ == "__main__":
    run_dashboard(debug=True)