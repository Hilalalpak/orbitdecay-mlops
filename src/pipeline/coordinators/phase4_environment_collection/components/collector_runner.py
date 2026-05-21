
from structlog.stdlib import BoundLogger

from src.domain.weather.collection.metrics.phase4_telemetry import BaseSourceResult, SourceCollectionResult, CachedSourceResult
from src.shared.quota.quota_manager import ApiQuotaManager
from src.shared import ExecutionRequest
from src.domain.weather.collection.raw_fetcher import RawFetcher
from src.domain.weather.collection.repository.env_collection_repository import EnvCollectionRepository
from src.shared.config import PipelineConfigInterface
from src.pipeline.contracts import ExecutionDecision, ExecutionMode


class CollectorRunner:
    def __init__(self,
                 quota_manager: ApiQuotaManager,
                 env_collection_repository: EnvCollectionRepository,
                 pipeline_config: PipelineConfigInterface,
                 logger: BoundLogger) -> None:

        self.quota_manager = quota_manager
        self.repository = env_collection_repository
        self.logger = logger
        self.pipeline_config = pipeline_config

    def execute_collection(self,
                           source_id: str,
                           decision: ExecutionDecision,
                           request: ExecutionRequest) -> BaseSourceResult:

        if decision.mode == ExecutionMode.REUSE:
            return self._handle_cached(source_id, decision)

        return self._handle_fetch(decision, request, source_id)

    def _handle_fetch(self,
                      decision: ExecutionDecision,
                      request: ExecutionRequest,
                      source_id: str) -> SourceCollectionResult:

        self.logger.info(
            "strategy_selected",
            type="fetch",
            reason=decision.reason.value)

        compliance = self.quota_manager.check_availability()
        if not compliance["allowed"]:
            return SourceCollectionResult(
                source_id=source_id,
                success=False)

        url = self.pipeline_config.get_env_source_url(source_id)
        timeout = self.pipeline_config.get_space_track_session_timeout()

        raw_data = RawFetcher.fetch(url, timeout)

        self.quota_manager.record_request(f"env_{source_id}")
        save_result = self.repository.save_env_data(source_id, request, raw_data)
        if not save_result.get('success'):
            return SourceCollectionResult(
                source_id=source_id,
                success=False)

        return SourceCollectionResult(
            source_id=source_id,
            success=True,
            data_hash=request.hash,
            api_call_made=True,
            file_path=save_result.get('filename'))

    def _handle_cached(self,
                       source_id: str,
                       decision: ExecutionDecision) -> CachedSourceResult:

        self.logger.info("strategy_selected", type="cached", reason="data_freshness_verified")

        return CachedSourceResult(
            source_id=source_id,
            file_path=decision.produced_manifest[0] if decision.produced_manifest else None)