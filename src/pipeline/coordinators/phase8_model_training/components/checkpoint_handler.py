from src.pipeline.policies.checkpoint_guard import CheckpointGuard
from src.shared import ExecutionRequest
from src.pipeline.contracts import ExecutionDecision
from src.pipeline.contracts.execution_lifecycle import ExecutionMode
from src.pipeline.metadata.contracts.run_history import RunHistory


class TrainingCheckpointHandler:

    def __init__(self,
                 checkpoint_guard: CheckpointGuard,
                 logger) -> None:
        self.checkpoint_guard = checkpoint_guard
        self.logger = logger

    def evaluate(self, request: ExecutionRequest) -> ExecutionDecision:
        decision = self.checkpoint_guard.evaluate(request)
        if decision.mode == ExecutionMode.REUSE:
            self.logger.info(f"Phase 8 skipped: RunHistory checkpoint found (Hash: {request.hash[:8]})")
        return decision

    def persist_execution_lineage(self,
                                  request: ExecutionRequest,
                                  satellites_trained: int,
                                  training_samples: int,
                                  mlflow_run_id: str,
                                  decision: ExecutionDecision,
                                  metadata_service) -> None:
        try:
            record = RunHistory(
                phase="model_training",
                source_id=request.source,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=[],
                extra_metadata={
                    "satellites_trained": satellites_trained,
                    "training_samples": training_samples,
                    "mlflow_run_id": mlflow_run_id,
                    "execution_mode": decision.mode.value,
                    "processing_stage": "model_training"
                })

            metadata_service.record_collection_execution(record)

            self.logger.debug(
                "metadata_persisted",
                context="phase8_model_training",
                satellites_trained=satellites_trained,
                training_samples=training_samples)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="model_training",
                error=str(meta_error))
