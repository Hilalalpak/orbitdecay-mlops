from typing import Optional
from src.pipeline.policies.checkpoint_guard import CheckpointGuard
from src.shared import ExecutionRequest
from src.domain.contracts.timeseries_schema import TimeSeriesCheckpointResult
from structlog.stdlib import BoundLogger
from src.shared.config.config_models import PipelineConfigModel
from src.pipeline.contracts import ExecutionMode
from src.pipeline.metadata.contracts.run_history import RunHistory

class TimeseriesCheckpointHandler:
    """
    Responsible for 'Read' operations: Creating requests and checking cache status.
    """
    def __init__(self,
                 checkpoint_guard: CheckpointGuard,
                 pipeline_config: PipelineConfigModel,
                 logger: BoundLogger,
                 execution_mode: str) -> None:

        self.check = checkpoint_guard
        self.execution_mode = execution_mode
        self.config = pipeline_config
        self.logger = logger

    def create_request(self) -> ExecutionRequest:
        """Creates the standard request object for Phase 7."""
        return ExecutionRequest.from_config(
            pipeline_config=self.config,
            input_data_type='orbital_features',
            source="ml_preprocessor",
            processing_stage="timeseries_integration")

    def check_and_maybe_skip(self, request: ExecutionRequest) -> Optional[TimeSeriesCheckpointResult]:

        result = self.check.evaluate(request)

        if result.mode == ExecutionMode.REUSE:
            history = self.check.metadata_service.get_history_by_hash(
                param_hash=request.hash,
                phase=request.processing_stage,
                source_id=request.source)
            past_stats = history.get("execution_details", {})
            age = history.get('age_days', 0)
            processed = past_stats.get('satellites_processed', 0)

            self.logger.info(f"Timeseries Phase SKIPPED using checkpoint (Hash: {request.hash[:8]}, Age: {age} days)")

            return TimeSeriesCheckpointResult(
                should_run=False,
                satellites_processed=processed,
                checkpoint_age_days=age,
                meta_data=past_stats)

        self.logger.debug("No valid checkpoint found. Integration will run.")
        return None


    def persist_execution_lineage(self,
                                  request: ExecutionRequest,
                                  satellites_processed: int,
                                  produced_files,
                                  execution_mode: ExecutionMode,
                                  metadata_service) -> None:
        """Persists execution metadata directly to metadata service for Phase 7."""
        try:
            record = RunHistory(
                phase="timeseries_integration",
                source_id=request.source,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=produced_files,
                extra_metadata={
                    "satellites_processed": satellites_processed,
                    "batch_files_created": len(produced_files),
                    "execution_mode": execution_mode.value,
                    "processing_stage": "timeseries_integration"
                })

            metadata_service.record_collection_execution(record)

            self.logger.debug(
                "metadata_persisted",
                context="phase7_timeseries_integration",
                satellites_processed=satellites_processed)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="timeseries_integration",
                error=str(meta_error))
