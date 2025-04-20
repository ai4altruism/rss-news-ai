# src/web_dashboard.py

from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)
SUMMARY_FILE = "data/latest_summary.json"

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

def run_dashboard(host='0.0.0.0', port=5002, debug=False, use_reloader=False):
    """Run the dashboard server."""
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)

if __name__ == "__main__":
    run_dashboard(debug=True)