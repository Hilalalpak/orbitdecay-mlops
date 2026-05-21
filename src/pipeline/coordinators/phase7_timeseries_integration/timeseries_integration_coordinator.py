import time
from typing import Optional
from uuid import UUID
from structlog.stdlib import BoundLogger
from src.domain.contracts.timeseries_schema import Phase7Result, TimeSeriesAction
from src.domain.timeseries.timeseries_generator import TimeSeriesGenerator
from src.pipeline.coordinators.phase7_timeseries_integration.components.checkpoint_handler import \
    TimeseriesCheckpointHandler
from src.pipeline.coordinators.phase7_timeseries_integration.components.reporting import TimeseriesReportingHandler
from src.pipeline.coordinators.phase7_timeseries_integration.components.resource_manager import \
    TimeseriesResourceManager
from src.pipeline.contracts.execution_lifecycle import ExecutionMode, DecisionReason, ExecutionStatus
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.metadata.service import MetadataService


class TimeSeriesIntegrationCoordinator:

    def __init__(self,
                 features_enabled: None,
                 logger: BoundLogger,
                 timeseries_creator: TimeSeriesGenerator,
                 reporting_handler: TimeseriesReportingHandler,
                 resource_manager: TimeseriesResourceManager,
                 checkpoint_handler: TimeseriesCheckpointHandler,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.features_enabled = features_enabled
        self.logger = logger
        self.timeseries_creator = timeseries_creator
        self.checkpoint = checkpoint_handler
        self.resource_manager = resource_manager
        self.reporting_handler = reporting_handler
        self.metadata_service = metadata_service

    def run_timeseries_integration(self, run_id: Optional[UUID] = None) -> Phase7Result:
        """Executes Phase 7 with strict schema validation and DB integrity checks."""

        # 1. Checkpoint & Integrity Check
        request = self.checkpoint.create_request()
        skip_result = self.checkpoint.check_and_maybe_skip(request)

        if skip_result:
            expected_count = skip_result.satellites_processed

            if self.timeseries_creator.storage.verify_integrity(expected_count):
                self.logger.info("Checkpoint validated: Feature Store contains data. Skipping Phase 7.")

                self.checkpoint.persist_execution_lineage(
                    request=request,
                    satellites_processed=expected_count,
                    produced_files=[],
                    execution_mode=ExecutionMode.REUSE,
                    metadata_service=self.metadata_service)

                if self.metadata_service and run_id:
                    try:
                        self.metadata_service.record_dataset(DatasetMetadata(
                            pipeline_run_id=run_id,
                            phase_id="phase7",
                            execution_mode=ExecutionMode.REUSE,
                            decision_reason=DecisionReason.CACHE_HIT,
                            status=ExecutionStatus.SKIPPED,
                            output_data_type="timeseries",
                            artifact_name="ml_training_data",
                            manifest_files=[],
                            record_count=expected_count))
                    except Exception as meta_error:
                        self.logger.warning("phase7_metadata_persistence_failed", error=str(meta_error))

                return Phase7Result(
                    success=True,
                    action=TimeSeriesAction.USE_CHECKPOINT,
                    execution_time=0.0,
                    satellites_processed=expected_count,
                    cache_used=True,
                    reason="checkpoint_verified_complete")
            else:
                self.logger.warning(
                    f"Checkpoint hit but Feature Store is EMPTY or MISSING. "
                    "Overriding skip and forcing re-run.")

        phase_start = time.time()
        self.logger.info(f'--- Starting Phase 7 (Time Series Integration) - Hash: {request.hash[:8]} ---')

        try:
            # 2. Resource Calculation
            optimized_workers = self.resource_manager.calculate_workers()

            # 3. Execution
            integration_results = self.timeseries_creator.create_all_timeseries(max_workers=optimized_workers)

            phase_duration = time.time() - phase_start
            self.logger.info(f'Phase 7 finished in {phase_duration:.2f} seconds.')

            successful_count = sum(1 for success in integration_results.values() if success)
            total_attempted = len(integration_results)

            # 4. Determine execution status
            if successful_count == 0:
                self.logger.error("Phase 7 produced 0 successful satellites. Marking as FAILED.")
                execution_status = ExecutionStatus.FAILED
                success = False
                reason = "No data produced in integration"
                efficiency_metrics = None
            elif successful_count == total_attempted:
                execution_status = ExecutionStatus.COMPLETED
                success = True
                reason = None
                efficiency_metrics = self.reporting_handler.update_metrics(phase_duration)
                # run_history only on full success — preserves checkpoint integrity
                self.checkpoint.persist_execution_lineage(
                    request=request,
                    satellites_processed=successful_count,
                    produced_files=[],
                    execution_mode=ExecutionMode.RUN,
                    metadata_service=self.metadata_service)
                self.logger.info(
                    f"Checkpoint saved: All {successful_count}/{total_attempted} satellites processed successfully.")
            else:
                self.logger.warning(
                    f"Checkpoint SKIPPED: Partial success ({successful_count}/{total_attempted}). "
                    "Data was written to DB, but phase marked INCOMPLETE to force retry of failed items next run.")
                execution_status = ExecutionStatus.PARTIAL_SUCCESS
                success = True
                reason = f"Partial: {successful_count}/{total_attempted} satellites processed"
                efficiency_metrics = self.reporting_handler.update_metrics(phase_duration)

            # 5. dataset_metadata — always recorded for all outcomes (observability)
            if self.metadata_service and run_id:
                try:
                    self.metadata_service.record_dataset(DatasetMetadata(
                        pipeline_run_id=run_id,
                        phase_id="phase7",
                        execution_mode=ExecutionMode.RUN,
                        decision_reason=DecisionReason.INITIAL_RUN,
                        status=execution_status,
                        output_data_type="timeseries",
                        artifact_name="ml_training_data",
                        manifest_files=[],
                        record_count=successful_count))
                except Exception as meta_error:
                    self.logger.warning("phase7_metadata_persistence_failed", error=str(meta_error))

            return Phase7Result(
                success=success,
                action=TimeSeriesAction.PROCESS_FRESH,
                execution_time=phase_duration,
                satellites_processed=successful_count,
                cache_used=False,
                reason=reason,
                efficiency_metrics=efficiency_metrics)

        except Exception as e:
            self.logger.error(f"Phase 7 Failed: {str(e)}", exc_info=True)
            return Phase7Result(
                success=False,
                action=TimeSeriesAction.SKIP_ERROR,
                execution_time=time.time() - phase_start,
                reason=str(e))