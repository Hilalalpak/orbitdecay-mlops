FROM python:3.9-slim as builder

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install maturin

WORKDIR /build

COPY src/domain/orbital/processing/rust_plugin ./plugin_src

WORKDIR /build/plugin_src
RUN maturin build --release --interpreter python3 --out /build/dist

FROM orbitdec-foundation:latest

WORKDIR /app

USER root

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm -rf /tmp/*.whl

COPY infrastructure/docker/images/pipeline/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN mkdir -p reports data logs checkpoints output models && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /app/reports/pipeline_status.json || exit 1

USER appuser

CMD ["python", "-m", "src.pipeline.orchestration.pipeline_orchestrator"]