FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
#COPY .env.example ./.env.example

# Create necessary directories with proper permissions
RUN mkdir -p logs data
RUN chmod -R 777 logs data

# Create templates directory for Flask
RUN mkdir -p src/templates
COPY src/templates/ ./src/templates/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

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