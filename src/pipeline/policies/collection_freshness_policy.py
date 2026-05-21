from typing import Optional, Dict, Any

from src.shared import ExecutionRequest
from src.shared.config import PipelineConfigInterface
from structlog.stdlib import BoundLogger
from src.pipeline.metadata import MetadataService
from src.pipeline.contracts import ExecutionDecision, ExecutionMode, DecisionReason

class CollectionFreshnessPolicy:
    """
    Determines cache strategy based on data freshness and configuration rules.
    Orchestrates decisions between cache reuse, incremental updates, and full refreshes.
    """

    def __init__(self,
                 pipeline_config: PipelineConfigInterface,
                 logger: BoundLogger,
                 metadata_service: MetadataService) -> None:

        self.config = pipeline_config
        self.logger = logger
        self.metadata_service=metadata_service


    def evaluate(self,
                 execution_request: ExecutionRequest,
                 phase:str,
                 source_id: Optional[str] = None) -> ExecutionDecision:
        """Evaluates whether fresh data collection is needed based on age and policy."""

        param_hash = execution_request.hash

        # 1. Check if duplicate detection is enabled
        if not self.config.is_duplicate_detection_enabled():
            return ExecutionDecision(
                mode=ExecutionMode.FORCED,
                reason=DecisionReason.FORCE_REFRESH,
                param_hash=param_hash,
                produced_manifest=None)

        # 2. Check execution history
        history_check = self.metadata_service.get_history_by_hash(param_hash=param_hash,
                                                                  phase=phase,
                                                                  source_id=source_id)

        if not history_check['found_duplicate']:
            return ExecutionDecision(
                mode=ExecutionMode.RUN,
                reason=DecisionReason.INITIAL_RUN,
                param_hash=param_hash,
                produced_manifest=None)

        # 3. Evaluate data age
        age_days = history_check['age_days']
        force_refresh_thr = self.config.get_smart_collection_force_refresh_days()
        max_inc_thr = self.config.get_incremental_max_days()

        manifest_files = history_check.get('manifest_files', [])

        # 3a. Data is fresh - use cache
        if age_days < force_refresh_thr:
            return ExecutionDecision(
                mode=ExecutionMode.REUSE,
                reason=DecisionReason.CACHE_HIT,
                param_hash=param_hash,
                produced_manifest=manifest_files)

        # 3b. Data is suitable for incremental update
        elif age_days < max_inc_thr and self.config.is_incremental_updates_enabled():
            return ExecutionDecision(
                mode=ExecutionMode.INCREMENTAL,
                reason=DecisionReason.DATA_STALE,
                param_hash=param_hash,
                produced_manifest=None)

        # 3c. Data is too old - force full refresh
        else:
            self.logger.warning("cache_expired",
                                age_days=age_days,
                                threshold_days=force_refresh_thr)
            return ExecutionDecision(
                mode=ExecutionMode.RUN,
                reason=DecisionReason.DATA_STALE,
                param_hash=param_hash,
                produced_manifest=None)
