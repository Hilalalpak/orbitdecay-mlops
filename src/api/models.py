"""
Pydantic models for API request/response validation.

These schemas define the contract between API clients and the OrbitDecay service,
ensuring type safety and automatic validation for all endpoints. They provide
clear documentation of expected data structures and enable OpenAPI generation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class TrainRequest(BaseModel):

    X: List[Dict[str, Any]]
    y: List[float]
    groups: Optional[List[Any]] = None

class TrainResponse(BaseModel):
    """Model training response schema."""
    run_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class HealthResponse(BaseModel):
    """Comprehensive health checkpoint response schema."""
    status: str
    timestamp: str
    service_status: str
    components: Dict[str, Any]
    configuration: Dict[str, Any]
    monitoring: Dict[str, Any]
    alerts: Dict[str, Any]

class MonitoringStatusResponse(BaseModel):
    """Monitoring system status response schema."""
    monitoring_system: Dict[str, Any]
    compliance: Dict[str, Any]
    config_performance: Dict[str, Any]
    alerts: Dict[str, Any]
    configuration: Dict[str, Any]