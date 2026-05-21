from typing import Optional
from uuid import UUID

from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.contracts.execution_lifecycle import ExecutionMode, DecisionReason, ExecutionStatus


class TrainingReporter:

    def __init__(self,
                 logger,
                 metadata_service: Optional[MetadataService] = None) -> None:
        self.logger = logger
        self.metadata_service = metadata_service

    def record_dataset(self, run_id: Optional[UUID], satellite_count: int) -> None:
        if not self.metadata_service or not run_id:
            return
        try:
            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase8",
                execution_mode=ExecutionMode.RUN,
                decision_reason=DecisionReason.INITIAL_RUN,
                status=ExecutionStatus.COMPLETED,
                output_data_type="ml_model",
                artifact_name="lstm_survival_model",
                manifest_files=[],
                record_count=satellite_count))
        except Exception as meta_error:
            self.logger.warning("phase8_metadata_persistence_failed", error=str(meta_error))

    def record_model_training_run(
            self,
            run_id: Optional[UUID],
            training_results: dict,
            training_samples: int) -> Optional[str]:
        if not self.metadata_service:
            return None
        try:
            training_id = self.metadata_service.record_model_training(
                model_type="lstm_survival",
                run_id=run_id,
                mlflow_run_id=training_results.get("run_id"),
                experiment_name=training_results.get("experiment_name"),
                training_samples=training_samples,
                validation_metrics=training_results.get("metrics"),
                status="completed",
            )
            return training_id
        except Exception as e:
            self.logger.warning(f"model_training_run metadata persistence failed: {e}")
            return None

    def record_model_deployment_entry(
            self,
            model_type: str,
            mlflow_run_id: Optional[str],
            training_run_id: Optional[str],
            environment: str = "prod") -> None:
        if not self.metadata_service:
            return
        try:
            from uuid import UUID as _UUID
            tid = _UUID(training_run_id) if training_run_id else None
            self.metadata_service.record_model_deployment(
                model_type=model_type,
                version=mlflow_run_id or "unknown",
                environment=environment,
                training_run_id=tid,
            )
        except Exception as e:
            self.logger.warning(f"model_deployment metadata persistence failed: {e}")
