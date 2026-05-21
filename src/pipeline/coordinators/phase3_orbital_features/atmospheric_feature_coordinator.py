"""
Phase 3 coordinator for orbital feature engineering.
Orchestrates physics-based feature calculation workflow.
"""

from structlog.stdlib import BoundLogger

from src.pipeline.contracts.execution_lifecycle import ExecutionStatus, ExecutionMode
from src.domain.orbital.features.contracts.phase3_result import Phase3Result
from src.shared.enums.failure_enums import Phase3FailureReason
from src.pipeline.coordinators.phase3_orbital_features.components.checkpoint_handler import FeatureCheckpointHandler
from src.domain.orbital.features.core.orbital_feature_generator import OrbitalFeatureGenerator
from src.domain.orbital.features.metrics.phase3_telemetry import FeatureStrategyResult, CheckpointHitResult
from typing import List, Optional
from uuid import UUID
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata


class FeatureEngineeringCoordinator:
    """
    Phase 3 coordinator for feature engineering.
    Handles checkpoint validation, execution delegation, and state persistence.
    """

    def __init__(self,
                 logger: BoundLogger,
                 orbital_feature_engineer: OrbitalFeatureGenerator,
                 checkpoint_handler: FeatureCheckpointHandler,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger
        self.feature_extractor = orbital_feature_engineer
        self.checkpoint_handler = checkpoint_handler
        self.metadata_service = metadata_service

    def run_feature_engineering(self,
                                processing_manifest: List[str],
                                is_incremental: bool = False,
                                run_id: Optional[UUID] = None) -> Phase3Result:
        """
        Executes feature engineering workflow with checkpoint validation.
        Returns Phase3Result with execution status and produced manifest.
        """
        decayed_manifest = [p for p in processing_manifest if "/decayed/" in p]
        if not decayed_manifest:
            return Phase3Result(
                success=False,
                execution_status=ExecutionStatus.FAILED,
                request_hash="unknown",
                reason=Phase3FailureReason.NO_INPUT_DATA)

        request = self.checkpoint_handler.create_request(processing_manifest)
        if not request:
            return Phase3Result(
                success=False,
                execution_status=ExecutionStatus.FAILED,
                request_hash="unknown",
                reason=Phase3FailureReason.HASH_CREATION_FAILED)

        execution_decision = self.checkpoint_handler.check_and_maybe_skip(request)

        if execution_decision.mode == ExecutionMode.REUSE:
            self.logger.debug("phase3_skipped_cached", hash=request.hash[:8])
            strategy_result = CheckpointHitResult(produced_manifest=execution_decision.produced_manifest or [])
            execution_status = ExecutionStatus.SKIPPED

        else:
            self.logger.debug("phase3_execution_started", hash=request.hash[:8])

            exec_stats, produced_manifest = self.feature_extractor.process_all_satellites(
                processing_manifest, is_incremental=is_incremental)

            is_success = exec_stats.successfully_processed > 0
            execution_status = ExecutionStatus.COMPLETED if is_success else ExecutionStatus.FAILED

            strategy_result = FeatureStrategyResult(
                execution_status=execution_status,
                stats=exec_stats,
                produced_manifest=produced_manifest)

        self.checkpoint_handler.persist_execution_lineage(strategy_result, execution_decision, request)

        result = Phase3Result(
            success=execution_status in [ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED],
            execution_status=execution_status,
            request_hash=request.hash,
            is_incremental=is_incremental,
            produced_manifest=strategy_result.produced_manifest,
            reason=None if execution_status == ExecutionStatus.COMPLETED else Phase3FailureReason.PROCESSING_FAILED)

        if self.metadata_service and run_id:
            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase3",
                execution_mode=execution_decision.mode,
                decision_reason=execution_decision.reason,
                status=execution_status,
                output_data_type="orbital_features",
                artifact_name="atmospheric_drag_features",
                manifest_files=result.produced_manifest,
                record_count=(strategy_result.stats.successfully_processed
                              if isinstance(strategy_result, FeatureStrategyResult)
                              else strategy_result.successfully_processed)))

        return result