from typing import Dict, Any

from src.shared import ExecutionRequest
from structlog.stdlib import BoundLogger

from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.contracts import ExecutionDecision, ExecutionMode, DecisionReason


class CheckpointGuard:
    """
    Prevents redundant processing by tracking completed executions.
    Enables pipeline restart capability without reprocessing completed phases.
    """

    def __init__(self,
                 metadata_service,
                 logger: BoundLogger) -> None:

        self.logger = logger
        self.metadata_service = metadata_service

    def evaluate(self, request: ExecutionRequest) -> ExecutionDecision:
        """Verifies if valid checkpoint exists for execution parameters."""

        param_hash = request.hash
        phase = request.processing_stage
        source_id = request.source

        try:

            history = self.metadata_service.get_history_by_hash(param_hash=param_hash,
                                                                phase=phase,
                                                                source_id=source_id)

            if not history["found_duplicate"]:
                self.logger.debug(f"No checkpoint for hash {param_hash[:8]}. Processing required.")
                return ExecutionDecision(
                    mode=ExecutionMode.RUN,
                    reason=DecisionReason.INITIAL_RUN,
                    param_hash=param_hash,
                    produced_manifest=None)

            manifest_files = history.get("manifest_files", [])

            self.logger.info(f"Checkpoint found for hash {param_hash[:8]}. Skipping.")

            return ExecutionDecision(
                mode=ExecutionMode.REUSE,
                reason=DecisionReason.CHECKPOINT_EXISTS,
                param_hash=param_hash,
                produced_manifest=manifest_files)

        except Exception as e:
            self.logger.warning(f"Checkpoint check failed for hash {param_hash[:8]}: {e}. Defaulting to run.",
                                exc_info=True)

            return ExecutionDecision(
                mode=ExecutionMode.FORCED,
                reason=DecisionReason.FORCE_REFRESH,
                param_hash=param_hash,
                produced_manifest=None)