FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root --only main

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Install the application
RUN poetry install --only-root

# Create necessary directories
RUN mkdir -p /app/data /app/secrets /app/logs

# Development stage
FROM base as development
RUN poetry install --with dev
CMD ["python", "-m", "starke.cli"]

# Production stage
FROM base as production
# Run as non-root user
RUN useradd -m -u 1000 starke && \
    chown -R starke:starke /app
USER starke

CMD ["python", "-m", "starke.cli", "run", "--production"]

# Portainer stage - for deployment via Portainer with API
FROM base as portainer
# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# Copy config files (essential!)
COPY config/ ./config/

# Set Python path
ENV PYTHONPATH=/app/src

# Expose API port
EXPOSE 8000

# Healthcheck - verificação rápida para Traefik
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1

# Start API with migrations
CMD ["sh", "-c", "\
    echo '⏳ Waiting for database...' && \
    sleep 5 && \
    echo '🔄 Running migrations...' && \
    alembic upgrade head && \
    echo '🚀 Starting API...' && \
    python -m uvicorn starke.api.main:app --host 0.0.0.0 --port 8000\
"]
