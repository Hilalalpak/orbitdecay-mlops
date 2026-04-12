FROM python:3.9-slim

WORKDIR /app

# Install system packages needed for scientific computing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install Python packages
COPY infrastructure/docker/images/base/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# Setup working directories
RUN mkdir -p logs data config tmp \
    && chown -R appuser:appuser /app

USER appuser