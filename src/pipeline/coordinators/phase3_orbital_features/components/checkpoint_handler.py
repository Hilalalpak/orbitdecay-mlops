"""
Checkpoint handler for Phase 3 feature engineering.
Ensures idempotency by skipping redundant processing.
"""

from typing import Optional, List, Any, Union
from src.domain.orbital.features.metrics.phase3_telemetry import FeatureStrategyResult, CheckpointHitResult
from structlog.stdlib import BoundLogger

from src.pipeline.policies.checkpoint_guard import CheckpointGuard
from src.shared import ExecutionRequest

from src.shared.config.config_models import PipelineConfigModel
from src.pipeline.contracts import ExecutionDecision
from src.pipeline.metadata import MetadataService
from src.pipeline.metadata.contracts.run_history import RunHistory

class FeatureCheckpointHandler:
    """
    Manages checkpoints and execution state for Phase 3.
    Handles request creation, checkpoint validation, and lineage recording.
    """

    def __init__(self,
                 checkpoint_guard: CheckpointGuard,
                 pipeline_config: PipelineConfigModel,
                 logger: BoundLogger,
                 metadata_service: MetadataService) -> None:

        self.checkpoint_guard = checkpoint_guard
        self.pipeline_config = pipeline_config
        self.logger = logger
        self.metadata_service = metadata_service

    def create_request(self, manifest_files: List[str]) -> Optional[Any]:
        """
        Creates ExecutionRequest for Phase 3 with feature version suffix.
        Returns None if creation fails.
        """
        try:
            request = ExecutionRequest.from_config(
                pipeline_config=self.pipeline_config,
                input_data_type='orbital_cleaned',
                source="feature_generator",
                processing_stage="orbital_features",
                manifest=manifest_files)

            request.hash = f"{request.hash}_features_v1"
            return request

        except Exception as e:
            self.logger.error("phase3_request_creation_failed", error=str(e))
            return None

    def check_and_maybe_skip(self, request: ExecutionRequest) -> ExecutionDecision:
        """Checks for existing checkpoint, returns decision to skip or execute."""
        return self.checkpoint_guard.evaluate(request)

    def persist_execution_lineage(
            self,
            stats: Union[FeatureStrategyResult, CheckpointHitResult],
            decision: ExecutionDecision,
            request: ExecutionRequest) -> None:
        """
        Persists execution metadata for checkpoint/lineage tracking.
        Fail-safe - metadata errors won't break the pipeline.
        """
        try:
            records_processed = (stats.stats.successfully_processed
                                 if hasattr(stats, 'stats')
                                 else stats.successfully_processed)

            record = RunHistory(
                phase=request.processing_stage,
                source_id=request.source,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=stats.produced_manifest,
                extra_metadata={
                    "records_processed": records_processed,
                    "batch_files_created": len(stats.produced_manifest),
                    "collection_strategy": decision.mode.value,
                    "collection_mode": decision.mode.value,
                })

            self.metadata_service.record_collection_execution(record)
            self.logger.debug(
                "metadata_persisted",
                context="phase3_features",
                records=records_processed)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="orbital_features",
                error=str(meta_error))
