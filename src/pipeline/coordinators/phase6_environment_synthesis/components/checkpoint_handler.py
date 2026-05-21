from typing import Optional
from src.pipeline.policies.checkpoint_guard import CheckpointGuard
from src.domain.weather.feature_synthesis.metrics.phase6_telemetry import SynthesisCheckpointResult
from structlog.stdlib import BoundLogger
from src.shared import ExecutionRequest
from src.pipeline.contracts import ExecutionDecision, ExecutionMode
from src.pipeline.metadata.contracts.run_history import RunHistory  # Import ekle


class P6CheckPointHandler:
    def __init__(self,
                 checkpoint_guard: CheckpointGuard,
                 logger: BoundLogger) -> None:

        self.checkpoint_guard = checkpoint_guard
        self.logger = logger

    def check_and_maybe_skip(self, request: ExecutionRequest) -> ExecutionDecision:
        """Returns ExecutionDecision for standardized pipeline flow."""
        return self.checkpoint_guard.evaluate(request)

    def build_skip_result(self, execution_decision: ExecutionDecision, request: ExecutionRequest) -> Optional[
        SynthesisCheckpointResult]:
        """Builds skip result from ExecutionDecision."""
        if execution_decision.mode == ExecutionMode.RUN:
            return None

        if execution_decision.mode == ExecutionMode.REUSE:
            self.logger.info("synthesis_skipped", hash_prefix=request.hash[:8], reason="checkpoint_reuse")
            return SynthesisCheckpointResult(
                unified_records=0,
                checkpoint_age_days=0.0,
                meta_data=None)

        return None

    def persist_execution_lineage(self,
                                  request: ExecutionRequest,
                                  record_count: int,
                                  source_count: int,
                                  produced_files,
                                  decision: ExecutionDecision,
                                  metadata_service) -> None:
        """Persists execution metadata directly to metadata service for Phase 6."""
        try:
            record = RunHistory(
                phase="environmental_synthesis",
                source_id=request.source,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=produced_files,
                extra_metadata={
                    "unified_records": record_count,
                    "sources_merged": source_count,
                    "batch_files_created": len(produced_files),
                    "execution_mode": decision.mode.value,
                })

            metadata_service.record_collection_execution(record)

            self.logger.debug(
                "metadata_persisted",
                context="phase6_environmental_synthesis",
                unified_records=record_count)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="environmental_synthesis",
                error=str(meta_error))