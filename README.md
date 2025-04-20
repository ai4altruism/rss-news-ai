# Generative AI News Tracker

A Python-based application that monitors RSS feeds for generative AI news, filters relevant stories using OpenAI's API, groups them by topic, and presents summaries through multiple output formats including web dashboard, Slack, and email.

![Generative AI News Tracker Dashboard](https://raw.githubusercontent.com/yourusername/genai-news-tracker/main/docs/images/dashboard_preview.png)

## Features

- **RSS Feed Monitoring**: Tracks multiple AI-focused RSS feeds for the latest news
- **Smart Filtering**: Uses OpenAI's API to identify relevant generative AI stories
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

## 📁 Architecture

The application consists of several modules:

- `main.py` - Main application logic and command-line interface
- `rss_reader.py` - Handles fetching and parsing RSS feeds
- `llm_filter.py` - Uses LLM to filter relevant articles
- `summarizer.py` - Groups and summarizes articles by topic
- `article_history.py` - Manages the history of processed articles
- `web_dashboard.py` - Web interface for viewing results
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

- Uses OpenAI's API for content filtering and summarization
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