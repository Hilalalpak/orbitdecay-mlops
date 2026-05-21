from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID
from src.pipeline.metadata.contracts.model_training import ModelTrainingRun, ModelDeployment
from src.pipeline.metadata.model_registry.repository import ModelRegistryRepository


class ModelRegistryService:

    def __init__(self, repository: ModelRegistryRepository):
        self.repository = repository

    def record_model_training(
            self,
            model_type: str,
            run_id: Optional[UUID] = None,
            mlflow_run_id: Optional[str] = None,
            experiment_name: Optional[str] = None,
            training_samples: Optional[int] = None,
            validation_samples: Optional[int] = None,
            validation_metrics: Optional[Dict[str, Any]] = None,
            risk_thresholds: Optional[Dict[str, float]] = None,
            status: Optional[str] = None) -> str:

        record = ModelTrainingRun(
            run_id=run_id,
            model_type=model_type,
            mlflow_run_id=mlflow_run_id,
            experiment_name=experiment_name,
            training_samples=training_samples,
            validation_samples=validation_samples,
            validation_metrics=validation_metrics,
            risk_thresholds=risk_thresholds,
            status=status,
            trained_at=datetime.utcnow(),
        )
        return self.repository.insert_model_training_run(record)

    def record_model_deployment(
            self,
            model_type: str,
            version: str,
            environment: str,
            training_run_id: Optional[UUID] = None) -> str:

        record = ModelDeployment(
            training_run_id=training_run_id,
            model_type=model_type,
            version=version,
            environment=environment,
            status="active",
        )
        deployment_id = self.repository.insert_model_deployment(record)
        self.repository.retire_previous_deployments(model_type, environment, deployment_id)
        return deployment_id

    def get_active_model(self, model_type: str, environment: str) -> Dict[str, Any]:
        return self.repository.get_active_deployment(model_type, environment) or {}
