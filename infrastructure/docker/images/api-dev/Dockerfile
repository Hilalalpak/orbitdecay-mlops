FROM orbitdec-foundation:latest

WORKDIR /app

# Install development dependencies
USER root
COPY infrastructure/docker/images/api-dev/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create config directory for matplotlib cache
RUN mkdir -p /home/appuser/.config/matplotlib && \
    chown -R appuser:appuser /home/appuser/.config

ARG API_PORT=8000
EXPOSE ${API_PORT}

# Health check for development server
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER appuser

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]