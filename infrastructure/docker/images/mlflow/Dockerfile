FROM orbitdec-foundation:latest

WORKDIR /app

USER root
COPY infrastructure/docker/images/mlflow/requirements.txt ./
RUN pip install -r requirements.txt && rm requirements.txt

RUN mkdir -p orbitdecay_mlruns orbitdecay_artifacts logs && \
    chown -R appuser:appuser /app

ARG MLFLOW_PORT=5000
EXPOSE ${MLFLOW_PORT}
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

USER appuser

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]