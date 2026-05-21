from typing import Any
from structlog.stdlib import BoundLogger

from src.pipeline.policies.collection_freshness_policy import CollectionFreshnessPolicy
from src.shared import ExecutionRequest
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.contracts import ExecutionDecision, ExecutionMode

class CacheHandler:
    def __init__(self,
                 metadata_service,
                 collection_freshness_policy: CollectionFreshnessPolicy,
                 logger: BoundLogger) -> None:

        self.freshness_policy = collection_freshness_policy
        self.logger = logger
        self.metadata_service=metadata_service


    def resolve_strategy(self,
                         request: ExecutionRequest,
                         phase: str) -> ExecutionDecision:
        """Determines if fresh collection is needed."""

        decision = self.freshness_policy.evaluate(request, phase, request.source)

        self.logger.info(
            "strategy_resolved",
            stage="environmental_collection",
            mode=decision.mode.value,
            reason=decision.reason.value,
            cache_hit=decision.mode == ExecutionMode.REUSE)

        return decision


    def persist_execution_lineage(self,
                                 result: Any,
                                 decision: ExecutionDecision,
                                 request: ExecutionRequest) -> None:
        """
        Records the outcome of the environmental collection phase
        into the Metadata Store.

        Signature aligned with Orbital phase for future standardization.
        Fail-safe by design.
        """
        try:
            record = RunHistory(
                phase="environmental_collection",
                source_id=request.source,
                param_hash=request.hash,
                filter_params=request.parameters,
                manifest_files=[result.file_path],
                extra_metadata={
                    "collection_strategy": decision.mode.value,
                    "collection_mode": result.mode,
                    "decision_reason": decision.reason.value,
                    "execution_mode": decision.mode.value,
                })

            self.metadata_service.record_collection_execution(record)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="environmental_collection",
                error=str(meta_error))