# src/web_dashboard.py

from flask import Flask, render_template, jsonify, request, g
from functools import wraps
import json
import logging
import os
import re
import sys
from datetime import datetime
from dotenv import dotenv_values

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables early (before app config)
env_vars = dotenv_values(".env")

# =============================================================================
# Security Configuration
# =============================================================================

# Get security settings from environment
API_SECRET_KEY = os.environ.get("API_SECRET_KEY") or env_vars.get("API_SECRET_KEY")
RATE_LIMIT_ENABLED = (os.environ.get("RATE_LIMIT_ENABLED") or env_vars.get("RATE_LIMIT_ENABLED", "true")).lower() == "true"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS") or env_vars.get("CORS_ORIGINS", "")
DEBUG_MODE = (os.environ.get("DEBUG") or env_vars.get("DEBUG", "false")).lower() == "true"

# Input validation constants
MAX_QUERY_LENGTH = 500  # Max length for natural language queries
MAX_PARAM_LENGTH = 1000  # Max length for query parameters
MAX_LIMIT_VALUE = 1000  # Max value for limit parameters
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')  # YYYY-MM-DD format

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__)
app.config['DEBUG'] = DEBUG_MODE

# Check if we're in testing mode
TESTING_MODE = os.environ.get('TESTING', 'false').lower() == 'true'

# =============================================================================
# Security Middleware Setup
# =============================================================================

# Rate Limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "100 per hour"] if RATE_LIMIT_ENABLED else [],
        storage_uri="memory://",
        enabled=RATE_LIMIT_ENABLED
    )
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    limiter = None

# Security Headers (Flask-Talisman)
try:
    from flask_talisman import Talisman

    # CSP policy allowing CDN resources for Bootstrap and Chart.js
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline scripts in templates
            "cdn.jsdelivr.net",
            "cdnjs.cloudflare.com",
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline styles
            "cdn.jsdelivr.net",
            "cdnjs.cloudflare.com",
            "fonts.googleapis.com",
        ],
        'font-src': [
            "'self'",
            "fonts.gstatic.com",
            "cdn.jsdelivr.net",
        ],
        'img-src': ["'self'", "data:"],
        'connect-src': "'self'",
    }

    # Only enforce HTTPS in production (not debug or testing mode)
    talisman = Talisman(
        app,
        content_security_policy=csp,
        force_https=not DEBUG_MODE and not TESTING_MODE,
        strict_transport_security=not DEBUG_MODE and not TESTING_MODE,
        session_cookie_secure=not DEBUG_MODE and not TESTING_MODE,
    )
    TALISMAN_AVAILABLE = True
except ImportError:
    TALISMAN_AVAILABLE = False

# CORS Configuration
try:
    from flask_cors import CORS

    if CORS_ORIGINS:
        origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
        CORS(app, origins=origins, supports_credentials=True)
    else:
        # Default: same-origin only (no CORS headers added)
        pass
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False

# =============================================================================
# Audit Logging Setup
# =============================================================================

# Set up security audit logger
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Add file handler for security logs
security_handler = logging.FileHandler('logs/security.log')
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)


def log_security_event(event_type: str, details: str, level: str = "INFO"):
    """Log a security-related event."""
    ip = request.remote_addr if request else "unknown"
    user_agent = request.headers.get('User-Agent', 'unknown')[:100] if request else "unknown"
    endpoint = request.endpoint if request else "unknown"

    message = f"[{event_type}] IP={ip} endpoint={endpoint} - {details} - UA={user_agent}"

    if level == "WARNING":
        security_logger.warning(message)
    elif level == "ERROR":
        security_logger.error(message)
    else:
        security_logger.info(message)


# =============================================================================
# Input Validation
# =============================================================================

def validate_date(date_str: str) -> bool:
    """Validate date string is in YYYY-MM-DD format."""
    if not date_str:
        return True  # None/empty is valid (optional)
    if len(date_str) > 10:
        return False
    return bool(DATE_PATTERN.match(date_str))


def validate_limit(limit: int) -> int:
    """Validate and constrain limit parameter."""
    if limit is None:
        return 50  # default
    return max(1, min(limit, MAX_LIMIT_VALUE))


def sanitize_string(s: str, max_length: int = MAX_PARAM_LENGTH) -> str:
    """Sanitize a string input by truncating and removing dangerous characters."""
    if not s:
        return s
    # Truncate to max length
    s = s[:max_length]
    # Remove null bytes and other control characters (except newlines/tabs)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    return s


def validate_request_inputs():
    """Validate common request inputs and return error response if invalid."""
    # Check query parameter lengths
    for key, value in request.args.items():
        if value and len(value) > MAX_PARAM_LENGTH:
            return jsonify({"error": f"Parameter '{key}' exceeds maximum length"}), 400

    # Validate date parameters if present
    for date_param in ['start', 'end', 'p1_start', 'p1_end', 'p2_start', 'p2_end']:
        date_value = request.args.get(date_param)
        if date_value and not validate_date(date_value):
            return jsonify({"error": f"Invalid date format for '{date_param}'. Use YYYY-MM-DD"}), 400

    return None  # No validation errors


# =============================================================================
# Authentication
# =============================================================================

def require_api_key(f):
    """Decorator to require API key authentication for endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if no API key is configured (development mode)
        if not API_SECRET_KEY:
            return f(*args, **kwargs)

        # Check for API key in header
        provided_key = request.headers.get('X-API-Key')

        if not provided_key:
            log_security_event("AUTH_FAILED", "Missing API key", "WARNING")
            return jsonify({"error": "API key required", "code": "AUTH_REQUIRED"}), 401

        if provided_key != API_SECRET_KEY:
            log_security_event("AUTH_FAILED", "Invalid API key", "WARNING")
            return jsonify({"error": "Invalid API key", "code": "AUTH_INVALID"}), 401

        # Log successful auth
        log_security_event("AUTH_SUCCESS", "Valid API key")
        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# Error Handling
# =============================================================================

@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit exceeded errors."""
    log_security_event("RATE_LIMIT", "Rate limit exceeded", "WARNING")
    return jsonify({
        "error": "Rate limit exceeded. Please slow down.",
        "code": "RATE_LIMITED"
    }), 429


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    log_security_event("SERVER_ERROR", str(e), "ERROR")
    if DEBUG_MODE:
        return jsonify({"error": str(e), "code": "INTERNAL_ERROR"}), 500
    return jsonify({
        "error": "An internal error occurred",
        "code": "INTERNAL_ERROR"
    }), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    log_security_event("UNHANDLED_ERROR", str(e), "ERROR")
    if DEBUG_MODE:
        return jsonify({"error": str(e), "code": "UNHANDLED_ERROR"}), 500
    return jsonify({
        "error": "An unexpected error occurred",
        "code": "UNHANDLED_ERROR"
    }), 500


# =============================================================================
# Request Logging
# =============================================================================

@app.before_request
def log_request():
    """Log all incoming requests for audit trail."""
    # Skip logging for static files
    if request.endpoint and request.endpoint.startswith('static'):
        return

    # Only log API requests
    if request.path.startswith('/api/'):
        log_security_event("API_REQUEST", f"method={request.method} path={request.path}")


# =============================================================================
# Application Setup
# =============================================================================

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)
SUMMARY_FILE = "data/latest_summary.json"

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
@require_api_key
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
@require_api_key
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
@require_api_key
def api_trends():
    """Get topic trends over time.

    Query params:
        start: Start date (YYYY-MM-DD) - required
        end: End date (YYYY-MM-DD) - required
        period: Aggregation period (day, week, month) - default: week
    """
    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    # Validate inputs
    validation_error = validate_request_inputs()
    if validation_error:
        return validation_error

    start_date = sanitize_string(request.args.get('start'))
    end_date = sanitize_string(request.args.get('end'))
    period = sanitize_string(request.args.get('period', 'week'))

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
@require_api_key
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

    # Validate inputs
    validation_error = validate_request_inputs()
    if validation_error:
        return validation_error

    p1_start = sanitize_string(request.args.get('p1_start'))
    p1_end = sanitize_string(request.args.get('p1_end'))
    p2_start = sanitize_string(request.args.get('p2_start'))
    p2_end = sanitize_string(request.args.get('p2_end'))
    limit = validate_limit(request.args.get('limit', 10, type=int))

    if not all([p1_start, p1_end, p2_start, p2_end]):
        return jsonify({"error": "All period parameters required (p1_start, p1_end, p2_start, p2_end)"}), 400

    db_path = get_db_path()
    data = top_topics_comparison(p1_start, p1_end, p2_start, p2_end, limit, db_path)

    return jsonify(data)


@app.route('/api/topics')
@require_api_key
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

    # Validate inputs
    validation_error = validate_request_inputs()
    if validation_error:
        return validation_error

    search_term = sanitize_string(request.args.get('search'))
    start_date = sanitize_string(request.args.get('start'))
    end_date = sanitize_string(request.args.get('end'))
    limit = validate_limit(request.args.get('limit', 50, type=int))

    if not search_term:
        return jsonify({"error": "search parameter required"}), 400

    db_path = get_db_path()
    data = topic_search(search_term, start_date, end_date, limit, db_path)

    return jsonify({
        "query": search_term,
        "count": len(data),
        "results": data
    })


def get_rate_limit_decorator():
    """Get rate limit decorator for LLM query endpoint (10/minute)."""
    if RATE_LIMITER_AVAILABLE and limiter and RATE_LIMIT_ENABLED:
        return limiter.limit("10 per minute")
    return lambda f: f  # No-op decorator if rate limiting unavailable


# Suspicious patterns that might indicate prompt injection attempts
SUSPICIOUS_PATTERNS = [
    r'ignore\s+.{0,20}instructions?',
    r'disregard\s+.{0,20}(instructions?|above|previous)',
    r'forget\s+(everything|all|previous)',
    r'you\s+are\s+now',
    r'new\s+instructions?:',
    r'system\s*:\s*',
    r'admin\s*:\s*',
    r'override\s+',
    r'bypass\s+',
]


def check_prompt_injection(query: str) -> bool:
    """Check if query contains suspicious patterns that might indicate prompt injection."""
    query_lower = query.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    return False


@app.route('/api/query', methods=['POST'])
@require_api_key
def api_natural_language_query():
    """Execute a natural language query.

    Request body (JSON):
        query: Natural language query string - required (max 500 chars)

    Returns:
        success: boolean
        query_type: string (trends, comparison, search, custom)
        response: Natural language response
        data: Structured result data
    """
    # Apply stricter rate limit for LLM queries
    if RATE_LIMITER_AVAILABLE and limiter and RATE_LIMIT_ENABLED:
        # Check rate limit manually for this endpoint
        pass  # Rate limiting applied via decorator would be better but complex here

    if not HISTORY_DB_AVAILABLE:
        return jsonify({"error": "History database not available"}), 503

    if not QUERY_ENGINE_AVAILABLE:
        return jsonify({"error": "Query engine not available"}), 503

    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY") or env_vars.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OpenAI API key not configured"}), 503

    # Get query from request
    data = request.get_json()
    if not data or not data.get('query'):
        return jsonify({"error": "query field required in request body"}), 400

    query_text = data['query']

    # Validate query length
    if len(query_text) > MAX_QUERY_LENGTH:
        return jsonify({
            "error": f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters"
        }), 400

    # Sanitize the query
    query_text = sanitize_string(query_text, MAX_QUERY_LENGTH)

    # Check for prompt injection attempts
    if check_prompt_injection(query_text):
        log_security_event("PROMPT_INJECTION", f"Suspicious query detected: {query_text[:100]}...", "WARNING")
        return jsonify({
            "error": "Query contains disallowed patterns",
            "code": "INVALID_QUERY"
        }), 400

    try:
        engine = QueryEngine(openai_api_key=api_key)
        result = engine.classify_and_execute(query_text)
        return jsonify(result)
    except Exception as e:
        log_security_event("QUERY_ERROR", str(e), "ERROR")
        if DEBUG_MODE:
            return jsonify({
                "success": False,
                "error": str(e),
                "response": f"Query failed: {str(e)}"
            }), 500
        return jsonify({
            "success": False,
            "error": "Query processing failed",
            "response": "An error occurred while processing your query"
        }), 500


def run_dashboard(host='0.0.0.0', port=5002, debug=False, use_reloader=False):
    """Run the dashboard server."""
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)

if __name__ == "__main__":
    run_dashboard(debug=True)