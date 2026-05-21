import os
import httpx
from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime
from prometheus_client import CONTENT_TYPE_LATEST

from src.api.models import HealthResponse
import src.api.state_manager as sm

router = APIRouter()


async def _check_postgres() -> str:
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "orbitdecay_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connect_timeout=3)
        conn.close()
        return "healthy"
    except Exception:
        return "unreachable"


async def _check_mlflow() -> str:
    try:
        mlflow_url = os.getenv("MLFLOW_TRACKING_URI_CONTAINER", "http://mlflow:5000")
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{mlflow_url}/health")
            return "healthy" if resp.status_code == 200 else "degraded"
    except Exception:
        return "unreachable"


async def _check_minio() -> str:
    try:
        minio_url = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{minio_url}/minio/health/live")
            return "healthy" if resp.status_code == 200 else "degraded"
    except Exception:
        return "unreachable"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Service health check endpoint.

    Returns comprehensive health status including component availability,
    configuration state, and active alerts. Used by orchestration systems
    for service discovery and load balancing decisions.

    Returns:
        HealthResponse with service status and component states
    """
    postgres_status = await _check_postgres()
    mlflow_status = await _check_mlflow()
    minio_status = await _check_minio()

    all_healthy = all(s == "healthy" for s in [postgres_status, mlflow_status, minio_status])
    overall = "healthy" if (sm.SERVICE_STATUS == "active" and all_healthy) else "degraded"

    if sm.monitoring_system is not None:
        sm.monitoring_system.update_infra_health(
            db=postgres_status == "healthy",
            minio=minio_status == "healthy",
            mlflow=mlflow_status == "healthy")

    return HealthResponse(
        status=overall,
        timestamp=datetime.now().isoformat(),
        service_status=sm.SERVICE_STATUS,
        components={
            "predictor": sm.PREDICTOR_STATUS,
            "postgres": postgres_status,
            "mlflow": mlflow_status,
            "minio": minio_status,
        },
        configuration={
            "config_loader": "available" if sm.config_loader is not None else "unavailable",
        },
        monitoring={
            "status": sm.MONITORING_STATUS,
        },
        alerts={})

@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics export endpoint.

    Exports metrics in Prometheus text format for scraping by monitoring systems.
    Includes API usage, processing times, risk assessments, and system health.

    Returns:
        Response with Prometheus-formatted metrics or disabled message
    """

    if sm.MONITORING_STATUS == "active":
        return Response(content=sm.export_prometheus_metrics(), media_type=CONTENT_TYPE_LATEST)
    return Response(content="# Monitoring disabled", media_type=CONTENT_TYPE_LATEST)
