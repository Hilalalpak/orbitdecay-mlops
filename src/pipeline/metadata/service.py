from typing import Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from src.pipeline.metadata.execution.service import PipelineExecutionService
from src.pipeline.metadata.data_lineage.service import DataLineageService
from src.pipeline.metadata.model_registry.service import ModelRegistryService
from src.shared.quota.service import QuotaService


class MetadataService:

    def __init__(self,
                 execution_service: PipelineExecutionService,
                 data_lineage_service: DataLineageService,
                 model_registry_service: ModelRegistryService,
                 quota_service: QuotaService):
        self._execution = execution_service
        self._data_lineage = data_lineage_service
        self._model_registry = model_registry_service
        self._quota = quota_service

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def start_pipeline_run(self, pipeline_name, execution_mode,
                            target_date, parameters):
        return self._execution.start_pipeline_run(
            pipeline_name, execution_mode, target_date, parameters)

    def finish_pipeline_run(self, run_id, status, error=None):
        return self._execution.finish_pipeline_run(run_id, status, error)

    def record_phase_execution(
            self,
            run_id: UUID,
            phase_name: str,
            phase_index: int,
            start_time: datetime,
            end_time: Optional[datetime] = None,
            status: Optional[str] = None,
            is_incremental: bool = False,
            records_in: Optional[int] = None,
            records_out: Optional[int] = None,
            records_failed: Optional[int] = None,
            skip_reason: Optional[str] = None,
            error_message: Optional[str] = None) -> None:
        return self._execution.record_phase_execution(
            run_id, phase_name, phase_index, start_time, end_time,
            status, is_incremental, records_in, records_out,
            records_failed, skip_reason, error_message)

    def get_phase_executions(self, run_id: str):
        return self._execution.get_phase_executions(run_id)

    # ------------------------------------------------------------------ #
    # Data lineage
    # ------------------------------------------------------------------ #

    def record_dataset(self, meta) -> None:
        return self._data_lineage.record_dataset(meta)

    def record_collection_execution(self, record) -> None:
        return self._data_lineage.record_collection_execution(record)

    def get_history_by_hash(self, param_hash: str, phase: str,
                             source_id: Optional[str] = None) -> Dict[str, Any]:
        return self._data_lineage.get_history_by_hash(param_hash, phase, source_id)

    def record_source_fetch(self, source_id: str, fetched_at: datetime,
                             run_id: Optional[UUID] = None,
                             record_count: Optional[int] = None,
                             success: bool = True,
                             age_before_sec: Optional[int] = None,
                             error: Optional[str] = None) -> None:
        return self._data_lineage.record_source_fetch(
            source_id, fetched_at, run_id, record_count,
            success, age_before_sec, error)

    def get_source_freshness(self, source_id: str) -> Dict[str, Any]:
        return self._data_lineage.get_source_freshness(source_id)

    # ------------------------------------------------------------------ #
    # Model registry
    # ------------------------------------------------------------------ #

    def record_model_training(self, model_type: str,
                               run_id: Optional[UUID] = None,
                               mlflow_run_id: Optional[str] = None,
                               experiment_name: Optional[str] = None,
                               training_samples: Optional[int] = None,
                               validation_samples: Optional[int] = None,
                               validation_metrics: Optional[Dict[str, Any]] = None,
                               risk_thresholds: Optional[Dict[str, float]] = None,
                               status: Optional[str] = None) -> str:
        return self._model_registry.record_model_training(
            model_type, run_id, mlflow_run_id, experiment_name,
            training_samples, validation_samples,
            validation_metrics, risk_thresholds, status)

    def record_model_deployment(self, model_type: str, version: str,
                                 environment: str,
                                 training_run_id: Optional[UUID] = None) -> str:
        return self._model_registry.record_model_deployment(
            model_type, version, environment, training_run_id)

    def get_active_model(self, model_type: str, environment: str) -> Dict[str, Any]:
        return self._model_registry.get_active_model(model_type, environment)

    # ------------------------------------------------------------------ #
    # Quota
    # ------------------------------------------------------------------ #

    def snapshot_quota(self, total_requests: int, remaining: int,
                        usage_pct: float, peak_hour: Optional[int] = None,
                        warning_fired: bool = False,
                        critical_fired: bool = False,
                        hourly_requests: Optional[dict] = None,
                        request_history: Optional[list] = None) -> None:
        return self._quota.snapshot_quota(
            total_requests, remaining, usage_pct, peak_hour,
            warning_fired, critical_fired, hourly_requests, request_history)

    def load_quota_counter(self) -> Optional[dict]:
        return self._quota.load_quota_counter()
