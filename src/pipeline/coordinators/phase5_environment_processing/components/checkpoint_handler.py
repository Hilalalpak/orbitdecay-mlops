from src.pipeline.policies.checkpoint_guard import CheckpointGuard
from structlog.stdlib import BoundLogger
from src.shared import ExecutionRequest
from src.pipeline.contracts import ExecutionMode, ExecutionDecision
from src.pipeline.metadata.contracts.run_history import RunHistory  # Import ekle

class P5CheckPointHandler:
    def __init__(self,
                 checkpoint_guard: CheckpointGuard,
                 logger: BoundLogger,
                 metadata_service=None) -> None:

        self.checkpoint_guard = checkpoint_guard
        self.logger = logger
        self.metadata_service = metadata_service

    def check_and_maybe_skip(self, request: ExecutionRequest) -> ExecutionDecision:
        return self.checkpoint_guard.evaluate(request)

    def build_skip_result(self, execution_decision: ExecutionDecision, request: ExecutionRequest) -> list:
        """Builds skip result from ExecutionDecision."""
        if execution_decision.mode == ExecutionMode.RUN:
            return []

        # ExecutionDecision'da produced_manifest var, direkt kullan
        manifest_files = execution_decision.produced_manifest
        self.logger.info(f"Checkpoint hit for {request.source}, using cached files: {manifest_files}")
        return manifest_files


    def persist_execution_lineage(self,
                                  request: ExecutionRequest,
                                  source_id: str,
                                  produced_files,
                                  record_count: int,
                                  execution_mode: ExecutionMode) -> None:
        """Persists execution metadata directly to metadata service for Phase 5."""
        try:
            record = RunHistory(
                phase="environmental_processing",
                source_id=source_id,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=produced_files,
                extra_metadata={
                    "records_processed": record_count,
                    "batch_files_created": len(produced_files),
                    "execution_mode": execution_mode.value,
                })

            self.metadata_service.record_collection_execution(record)

            self.logger.debug(
                "metadata_persisted",
                context="phase5_environmental_processing",
                records=record_count)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="environmental_processing",
                error=str(meta_error))




