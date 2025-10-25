# Chess OpenEnv Demo - Dockerfile
# Multi-agent chess environment using OpenEnv 0.1 specification

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application code
COPY src/ ./src/
COPY web/ ./web/
COPY config/ ./config/

# Create directory for logs
RUN mkdir -p /app/logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    MAX_CONCURRENT_GAMES=100 \
    CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Run the application
CMD ["python", "-m", "src.api.main"]
