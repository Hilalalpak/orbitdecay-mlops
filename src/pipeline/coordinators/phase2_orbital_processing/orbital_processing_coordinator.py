"""
Phase 2 coordinator for orbital data processing.
Orchestrates batch loading, parallel processing, and checkpoint persistence.
"""

from uuid import UUID

from typing import List, Optional
from structlog.stdlib import BoundLogger

from src.domain.orbital.processing.contracts.phase2_result import Phase2Result
from src.shared.enums.failure_enums import Phase2FailureReason
from src.domain.orbital.processing.metrics.phase2_telemetry import ProcessingStrategyResult, CheckpointHitResult

from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.pipeline.coordinators.phase2_orbital_processing.components.checkpoint_handler import CheckpointHandler
from src.pipeline.coordinators.phase2_orbital_processing.components.executor import Executor
from src.domain.orbital.processing.repositories.orbital_batch_repository import OrbitalBatchRepository
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.contracts.execution_lifecycle import ExecutionMode

class OrbitProcessingCoordinator:
    """
    Phase 2 coordinator for orbital data processing.
    Handles checkpoint validation, execution delegation, and metadata persistence.
    """

    def __init__(self,
                 logger: BoundLogger,
                 checkpoint_handler: CheckpointHandler,
                 executor: Executor,
                 data_repository: OrbitalBatchRepository,
                 max_workers: int,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger
        self.max_workers = max_workers

        self.checkpoint_handler = checkpoint_handler
        self.executor = executor
        self.data_repository = data_repository
        self.metadata_service = metadata_service

    def run(self,
            processing_manifest: List[str],
            is_incremental: bool = False,
            run_id: Optional[UUID] = None) -> Phase2Result:
        """
        Executes Phase 2 orbital processing pipeline.
        Returns Phase2Result with success status and metadata.
        """
        if not processing_manifest:
            self.logger.error("phase2_aborted_no_input")
            return Phase2Result(
                success=False,
                execution_status=ExecutionStatus.FAILED,
                request_hash="unknown",
                reason=Phase2FailureReason.NO_INPUT_DATA)

        request = self.checkpoint_handler.create_request(processing_manifest)
        if not request:
            return Phase2Result(
                success=False,
                execution_status=ExecutionStatus.FAILED,
                request_hash="unknown",
                reason=Phase2FailureReason.HASH_CREATION_FAILED)

        execution_decision = self.checkpoint_handler.check_and_maybe_skip(request)

        if execution_decision.mode == ExecutionMode.REUSE:
            self.logger.debug("phase2_skipped_cached", hash=request.hash[:8])
            strategy_result = CheckpointHitResult(produced_manifest=execution_decision.produced_manifest)
            execution_status = ExecutionStatus.SKIPPED


        else:
            self.logger.debug("phase2_started", batch_count=len(processing_manifest))

            exec_stats, produced_manifest = self.executor.execute_manifest(
                processing_manifest, is_incremental)

            is_success = exec_stats.successfully_processed > 0 and exec_stats.processing_failures < 10000
            execution_status = ExecutionStatus.COMPLETED if is_success else ExecutionStatus.FAILED

            strategy_result = ProcessingStrategyResult(
                execution_status=execution_status,
                stats=exec_stats,
                produced_manifest=produced_manifest)

        self.checkpoint_handler.persist_execution_lineage(strategy_result,
                                                          execution_decision,
                                                          request)

        result = Phase2Result(
            success=execution_status in [ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED],
            execution_status=execution_status,
            request_hash=request.hash,
            is_incremental=is_incremental,
            produced_manifest=strategy_result.produced_manifest,
            reason=None if execution_status == ExecutionStatus.COMPLETED else Phase2FailureReason.PROCESSING_FAILED)

        if self.metadata_service and run_id:
            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase2",
                execution_mode=execution_decision.mode,
                decision_reason=execution_decision.reason,
                status=execution_status,
                output_data_type="orbital_cleaned",
                artifact_name="normalized_orbits",
                manifest_files=result.produced_manifest,
                record_count=(strategy_result.stats.successfully_processed
                              if isinstance(strategy_result, ProcessingStrategyResult)
                              else strategy_result.successfully_processed)))

        return result