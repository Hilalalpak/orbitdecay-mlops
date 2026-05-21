"""
Cache decision manager and metadata persistence for Phase 1.
Mediates between coordinator and core caching/metadata systems.
"""

from structlog.stdlib import BoundLogger

from src.domain.orbital.collection.contracts.strategy_result import BaseStrategyResult
from src.pipeline.policies.collection_freshness_policy import CollectionFreshnessPolicy
from src.shared import ExecutionRequest
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.contracts import ExecutionDecision

class CollectionCacheHandler:
    """Resolves cache vs API strategy and records execution metadata."""

    def __init__(self,
                 collection_freshness_policy: CollectionFreshnessPolicy,
                 logger: BoundLogger,
                 metadata_service) -> None:

        self.freshness_policy = collection_freshness_policy
        self.logger = logger
        self.metadata_service=metadata_service

    def resolve_strategy(self, request: ExecutionRequest) -> ExecutionDecision:
        """
        Determines collection strategy via CollectionFreshnessPolicy.
        Returns decision with mode, param_hash, and manifest if cached.
        """
        decision = self.freshness_policy.evaluate(
            execution_request=request,
            phase="orbital_collection")
        self.logger.debug(
            "strategy_resolved",
            mode=decision.mode.value,
            reason=decision.reason.value)

        return decision

    def record_lineage(
        self,
        result: BaseStrategyResult,
        decision: ExecutionDecision,
        request: ExecutionRequest) -> None:
        """
        Persists execution metadata for cache/incremental logic.
        Fail-safe - metadata errors won't break the pipeline.
        """
        try:
            record = RunHistory(
                phase="orbital_collection",
                source_id="orbital",
                param_hash=result.param_hash,
                filter_params=request.parameters,
                manifest_files=result.manifest_files,
                extra_metadata={
                    "records_processed": result.total_records,
                    "batch_files_created": len(result.manifest_files),
                    "collection_strategy": decision.mode.value,
                    "collection_mode": result.mode.value,
                })

            self.metadata_service.record_collection_execution(record)

            self.logger.debug(
                "metadata_persisted",
                context="phase1_collection",
                records=result.total_records)

        except Exception as meta_error:
            self.logger.warning(
                "metadata_persistence_failed",
                stage="orbital_collection",
                error=str(meta_error))