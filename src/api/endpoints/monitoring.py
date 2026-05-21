from fastapi import APIRouter, Request
from typing import Any, Dict
import logging

import src.api.state_manager as sm

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/monitoring/webhook")
async def alertmanager_webhook(request: Request) -> Dict[str, Any]:
    """
    Default alertmanager webhook receiver.
    Receives all alert notifications from Alertmanager.
    """
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "unknown")
        status = alert.get("status", "unknown")
        logger.warning(f"[ALERT] {name} | status={status}")
    return {"received": len(alerts), "status": "ok"}


@router.post("/monitoring/webhook/critical")
async def alertmanager_critical_webhook(request: Request) -> Dict[str, Any]:
    """
    Critical alert webhook receiver.
    Receives only critical severity alerts from Alertmanager.
    """
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "unknown")
        status = alert.get("status", "unknown")
        logger.error(f"[CRITICAL ALERT] {name} | status={status} | labels={alert.get('labels', {})}")
    return {"received": len(alerts), "status": "ok"}


@router.post("/monitoring/compliance/webhook")
async def alertmanager_compliance_webhook(request: Request) -> Dict[str, Any]:
    """
    API quota/compliance alert webhook receiver.
    Receives api_usage component alerts from Alertmanager.
    """
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "unknown")
        status = alert.get("status", "unknown")
        annotations = alert.get("annotations", {})
        logger.warning(f"[COMPLIANCE ALERT] {name} | status={status} | {annotations.get('description', '')}")
    return {"received": len(alerts), "status": "ok"}


@router.post("/monitoring/performance/webhook")
async def alertmanager_performance_webhook(request: Request) -> Dict[str, Any]:
    """
    Cache/performance alert webhook receiver.
    Receives cache component alerts from Alertmanager.
    """
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "unknown")
        status = alert.get("status", "unknown")
        annotations = alert.get("annotations", {})
        logger.warning(f"[PERFORMANCE ALERT] {name} | status={status} | {annotations.get('description', '')}")
    return {"received": len(alerts), "status": "ok"}


@router.get("/monitoring/status")
async def monitoring_status() -> Dict[str, Any]:
    """
    Returns current monitoring system status.
    """
    return {
        "monitoring_status": sm.MONITORING_STATUS,
        "service_status": sm.SERVICE_STATUS,
    }
