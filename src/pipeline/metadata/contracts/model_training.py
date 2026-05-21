from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime


class ModelTrainingRun(BaseModel):
    run_id: Optional[UUID] = None
    model_type: str
    mlflow_run_id: Optional[str] = None
    experiment_name: Optional[str] = None
    training_samples: Optional[int] = None
    validation_samples: Optional[int] = None
    validation_metrics: Optional[Dict[str, Any]] = None
    risk_thresholds: Optional[Dict[str, float]] = None
    status: Optional[str] = None
    trained_at: Optional[datetime] = None


class ModelDeployment(BaseModel):
    training_run_id: Optional[UUID] = None
    model_type: str
    version: str
    environment: str
    status: str = "active"
