FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
#COPY .env.example ./.env.example

# Create necessary directories with proper permissions
# NOTE: In production, mount these as volumes from the host for:
#   - Data persistence across container rebuilds
#   - Easy backup and monitoring
#   - Direct access for maintenance
#
# Example docker run with volume mounts:
#   docker run -d \
#     -v /var/lib/rss-news-ai/data:/app/data \
#     -v /var/lib/rss-news-ai/logs:/app/logs \
#     -p 5002:5002 \
#     --env-file .env \
#     rss-news-ai
#
RUN mkdir -p logs data
RUN chmod -R 777 logs data

# Create templates directory for Flask
RUN mkdir -p src/templates
COPY src/templates/ ./src/templates/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Historical database path (can be overridden via environment)
# Mount /app/data as a volume to persist database outside container
ENV HISTORY_DB_PATH=/app/data/history.db

# Expose port for web dashboard
EXPOSE 5002

# Create a non-root user to run the application
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Entry point
ENTRYPOINT ["python", "src/main.py"]

# Default command
CMD ["--output", "console"]