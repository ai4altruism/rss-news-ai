# Generative AI News Tracker

A Python-based application that monitors RSS feeds for generative AI news, filters relevant stories using LLM APIs (OpenAI, xAI Grok, and more), groups them by topic, and presents summaries through multiple output formats including web dashboard, Slack, and email.

## Features

- **RSS Feed Monitoring**: Tracks multiple AI-focused RSS feeds for the latest news
- **Smart Filtering**: Uses LLM APIs to identify relevant generative AI stories
- **Multi-Provider LLM Support**: OpenAI (GPT-4, GPT-5), xAI (Grok), Anthropic (Claude), with Google coming soon
- **Topic Grouping**: Automatically groups related news into coherent topics
- **Intelligent Summarization**: Creates concise summaries of each topic
- **Multiple Output Formats**:
  - Web dashboard with responsive design
  - Slack channel integration
  - Email delivery
  - Console output
- **Deduplication**: Prevents the same stories from appearing repeatedly
- **History Management**: Maintains a configurable article history to avoid duplicates
- **Scheduled Processing**: Can run as a daemon to periodically check for new content
- **Historical Database**: SQLite storage for trend analysis and historical queries
- **Natural Language Queries**: Ask questions about historical data using LLM
- **Topic Aliases**: Normalize topic variations (e.g., "OpenAI News" → "OpenAI")
- **Data Export**: Export topics and articles to CSV or JSON formats
- **REST API**: Programmatic access to trends, comparisons, and search

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/genai-news-tracker.git
   cd genai-news-tracker
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy the example environment file and edit it with your settings:
   ```bash
   cp .env.example .env
   ```

4. Set up your environment variables in `.env`:
   - Add your OpenAI API key
   - Configure RSS feed URLs
   - Set your preferred output methods
   - Configure notification services (Slack webhook, email settings, etc.)

## Usage

### One-time processing

Run the application once to process and output the current news:

```bash
python src/main.py --output console
```

You can specify different output methods:
- `--output console` - Display output in terminal
- `--output slack` - Send to configured Slack channel
- `--output email` - Send as an email
- `--output web` - Save for web dashboard

### Running the web dashboard

Start the web dashboard server:

```bash
python src/main.py --web-server --port 5001
```

Then access the dashboard at `http://localhost:5001`

### Scheduled processing

To run the application as a scheduler that periodically checks for new content:

```bash
python src/scheduler.py --output slack --interval 120
```

This will run the process every 120 minutes and send updates to Slack.

### Command-line options

```
--output {console,slack,email,web}  Output method (default: console)
--web-server                        Run the web dashboard server
--port PORT                         Port for web dashboard (default: 5001)
--history-retention DAYS            Number of days to retain article history (default: 30)
--ignore-history                    Ignore article history (process all articles)
--interval MINUTES                  Interval in minutes between scheduled runs
```

## Configuration

The application is configured through the `.env` file:

```
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# RSS Feed URLs (one per line)
RSS_FEEDS=https://techcrunch.com/category/artificial-intelligence/feed/
https://venturebeat.com/category/ai/feed/
https://www.theverge.com/ai-artificial-intelligence/rss/index.xml
https://www.technologyreview.com/topic/artificial-intelligence/feed
https://www.wired.com/feed/tag/artificial-intelligence/latest/rss
https://news.google.com/rss/search?q=generative+ai&hl=en-US&gl=US&ceid=US:en
https://huggingface.co/blog/feed.xml
https://openai.com/blog/rss/
https://ai.meta.com/blog/rss/
https://blog.google/technology/ai/rss/

# Filtering Configuration
FILTER_PROMPT="Only include stories directly related to generative AI, such as significant advancements, breakthroughs, and applications. Exclude stories without direct information (what, where, when) about the generative AI."

# Model Selection (adjust based on your performance needs)
FILTER_MODEL=gpt-4o
GROUP_MODEL=gpt-4o
SUMMARIZE_MODEL=gpt-4o

# Process Interval (in minutes)
PROCESS_INTERVAL=120

# History Retention (in days)
HISTORY_RETENTION_DAYS=30

# Output Configuration
# For Slack output
SLACK_WEBHOOK_URL=your_slack_webhook_url_here

# For Email output
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_email_password
SMTP_USE_TLS=True
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

## LLM Provider Configuration

The application supports multiple LLM providers, allowing you to mix and match models for different tasks.

### Supported Providers

| Provider | Models | Status |
|----------|--------|--------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-5, gpt-5-mini | Available |
| **xAI** | grok-3, grok-3-mini | Available |
| **Anthropic** | claude-sonnet-4-20250514, claude-haiku | Available |
| **Google** | gemini-2.0-flash, gemini-pro | Coming Soon |

### Configuration Format

Models can be specified in two formats:

```bash
# Old format (defaults to OpenAI)
FILTER_MODEL=gpt-4o-mini

# New format (explicit provider)
FILTER_MODEL=openai:gpt-4o-mini
FILTER_MODEL=xai:grok-3-mini
```

### Mix and Match Providers

You can use different providers for different tasks to optimize cost and quality:

```bash
# Fast, cheap filtering with xAI
FILTER_MODEL=xai:grok-3-mini

# Quality grouping with OpenAI
GROUP_MODEL=openai:gpt-4o-mini

# High-quality summaries with GPT-5
SUMMARIZE_MODEL=openai:gpt-5-mini

# Cost-effective queries
QUERY_MODEL=openai:gpt-4o-mini
```

### API Keys

Set the API keys for the providers you use:

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# xAI Grok
XAI_API_KEY=xai-...

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
```

## Historical Database & Query System

The application maintains a SQLite database of all summaries, topics, and articles for trend analysis and historical queries.

### History CLI Commands

```bash
# Initialize the database
python src/history_cli.py init

# Import existing JSON summary files
python src/history_cli.py import data/*.json

# Natural language query (requires OpenAI API key)
python src/history_cli.py query "What were the top AI themes last month?"

# Trend analysis
python src/history_cli.py trends --start 2024-06-01 --end 2024-12-01 --period month

# Compare two time periods
python src/history_cli.py compare --period1 2024-01-01 2024-03-31 \
                                  --period2 2024-04-01 2024-06-30

# Search for topics
python src/history_cli.py search "OpenAI" --start 2024-01-01 --end 2024-12-31

# View recent summaries
python src/history_cli.py recent --limit 5

# Database statistics
python src/history_cli.py stats
```

### Topic Alias Management

Normalize topic name variations across summaries:

```bash
# Add an alias (maps "OpenAI News" → "OpenAI")
python src/history_cli.py alias add "OpenAI News" "OpenAI"

# List all aliases
python src/history_cli.py alias list

# View unique topics in database
python src/history_cli.py alias topics

# Remove an alias
python src/history_cli.py alias remove "OpenAI News"
```

### Data Export

Export historical data for external analysis or backup:

```bash
# Export topics to CSV
python src/history_cli.py export topics --output topics.csv

# Export articles to CSV with date filter
python src/history_cli.py export articles --start 2024-01-01 --end 2024-06-30 --output articles.csv

# Export all data to JSON
python src/history_cli.py export json --output backup.json
```

### Web API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/history` | GET | Interactive query interface page |
| `/api/history/stats` | GET | Database statistics |
| `/api/trends` | GET | Topic trends over time |
| `/api/compare` | GET | Compare top topics between periods |
| `/api/topics` | GET | Search topics by name |
| `/api/query` | POST | Natural language query |

Example API usage:

```bash
# Get database statistics
curl http://localhost:5002/api/history/stats

# Get topic trends
curl "http://localhost:5002/api/trends?start=2024-01-01&end=2024-12-31&period=month"

# Compare two periods
curl "http://localhost:5002/api/compare?p1_start=2024-01-01&p1_end=2024-03-31&p2_start=2024-04-01&p2_end=2024-06-30"

# Search topics
curl "http://localhost:5002/api/topics?search=OpenAI&limit=10"

# Natural language query
curl -X POST http://localhost:5002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What were the top topics last month?"}'
```

## Docker Deployment

### Build the Image

```bash
docker build -t rss-news-ai .
```

### Run with Volume Mounts

For production, mount the data and logs directories as volumes to persist the database outside the container:

```bash
# Create host directories
mkdir -p /var/lib/rss-news-ai/data
mkdir -p /var/lib/rss-news-ai/logs

# Run container with volumes
docker run -d \
  --name rss-news-ai \
  -v /var/lib/rss-news-ai/data:/app/data \
  -v /var/lib/rss-news-ai/logs:/app/logs \
  -p 5002:5002 \
  --env-file .env \
  rss-news-ai --output slack web
```

### Access Database from Host

```bash
# View database
sqlite3 /var/lib/rss-news-ai/data/history.db

# Backup database
cp /var/lib/rss-news-ai/data/history.db /backup/history_$(date +%Y%m%d).db

# Monitor size
ls -lh /var/lib/rss-news-ai/data/history.db
```

## 📁 Architecture

The application consists of several modules:

- `main.py` - Main application logic and command-line interface
- `rss_reader.py` - Handles fetching and parsing RSS feeds
- `llm_filter.py` - Uses LLM to filter relevant articles
- `summarizer.py` - Groups and summarizes articles by topic
- `article_history.py` - Manages the history of processed articles
- `history_db.py` - SQLite database for historical storage and queries
- `query_engine.py` - LLM-powered natural language query processing
- `history_cli.py` - Command-line interface for historical queries
- `web_dashboard.py` - Web interface for viewing results and history
- `slack_publisher.py` - Publishes results to Slack
- `email_reporter.py` - Sends results via email
- `scheduler.py` - Runs the application at scheduled intervals
- `utils.py` - Utility functions shared across modules

## 🔄 Customization

### Filtering Criteria

The filtering uses OpenAI's API with a prompt that you can customize in the `.env` file:

```
FILTER_PROMPT="Only include stories directly related to generative AI, such as significant advancements, breakthroughs, and applications. Exclude stories without direct information (what, where, when) about the generative AI."
```

You can adjust this prompt to focus on different aspects of generative AI or broaden/narrow the criteria.

### Adding More RSS Feeds

Add more RSS feeds to the `.env` file, one per line:

```
RSS_FEEDS=https://feed1.com/rss
https://feed2.com/rss
https://feed3.com/rss
```

### Changing the Output Format

You can customize the output formats by modifying:
- `templates/dashboard.html` - Web dashboard template
- `slack_publisher.py` - Slack message format
- `email_reporter.py` - Email template

## 🛠 Troubleshooting

### Common Issues

1. **JSON Parsing Errors**: If you see JSON parsing errors in the logs, try:
   - Increasing the max_output_tokens for the LLM calls
   - Using a more powerful model (e.g., gpt-4o instead of gpt-4o-mini)

2. **No Articles Found**: Check:
   - RSS feed URLs are valid and accessible
   - Filter prompt isn't too restrictive
   - History retention to ensure old articles are being removed

3. **Web Dashboard Not Loading**: Verify:
   - Flask server is running
   - Port is not in use by another application
   - Data directory exists and has write permissions

## 📜 License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). Copyright (c) 2025 AI for Altruism Inc.

When using or distributing this software, please attribute as follows:

```
RSS AI News Feed Monitor
Copyright (c) 2025 AI for Altruism Inc
License: GNU GPL v3.0
```

## Acknowledgements

- Uses OpenAI, xAI, and Anthropic APIs for content filtering and summarization
- Built with Flask for the web interface
- Uses feedparser for RSS processing
- Slack and email integrations for notifications

## 🎯 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📩 Contact

For issues or questions, please open a GitHub issue or contact:

- **Email**: team@ai4altruism.org