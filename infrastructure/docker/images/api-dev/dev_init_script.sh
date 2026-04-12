#!/bin/bash
# Development API initialization script
# Author: Hilal Alpak

set -e

echo "[dev] OrbitDecay API starting..."

mkdir -p /app/logs /app/reports /app/data

exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level debug
