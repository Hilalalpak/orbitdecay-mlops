"""
Coordinates the environmental data collection step.
Acts as the "Phase 1 orchestrator" for all space-weather sources.
Updated to use ThreadPoolExecutor for concurrent I/O operations.
"""
import time
import concurrent.futures
from datetime import datetime
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Any
from uuid import UUID
from collections import Counter

from src.domain.weather.collection.contracts.phase4_result import Phase4Result
from src.domain.weather.collection.metrics.phase4_telemetry import Phase4ExecutionStats, BaseSourceResult
from src.shared.enums.failure_enums import Phase4FailureReason
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus, ExecutionMode, DecisionReason
from structlog.stdlib import BoundLogger
from src.shared.config.config_interfaces import PipelineConfigInterface

from src.pipeline.coordinators.phase4_environment_collection.components.cache_handler import CacheHandler
from src.pipeline.coordinators.phase4_environment_collection.components.collector_runner import CollectorRunner
from src.pipeline.coordinators.phase4_environment_collection.components.request_builder import RequestBuilder
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata


@dataclass
class _AccumulationState:
    """Thread-local aggregation state for coordinator metrics."""
    sources_successful: int = 0
    sources_failed: int = 0
    produced_manifest: List[str] = field(default_factory=list)
    cached_sources: int = 0
    fresh_sources: int = 0
    api_calls_made: int = 0
    quota_exceeded: bool = False
    decision_reasons: List[DecisionReason] = field(default_factory=list)

    def add_success(self, file_path: Optional[str], mode: ExecutionMode,
                    api_call: bool, decision_reason: DecisionReason) -> None:
        self.sources_successful += 1
        self.decision_reasons.append(decision_reason)
        if file_path:
            self.produced_manifest.append(file_path)
        if mode == ExecutionMode.REUSE:
            self.cached_sources += 1
        elif mode == ExecutionMode.RUN:
            self.fresh_sources += 1
        if api_call:
            self.api_calls_made += 1

    def add_failure(self, reason: Optional[Phase4FailureReason] = None) -> None:
        self.sources_failed += 1
        if reason == Phase4FailureReason.QUOTA_EXCEEDED:
            self.quota_exceeded = True

    def dominant_reason(self) -> DecisionReason:
        if not self.decision_reasons:
            return DecisionReason.FORCE_REFRESH
        return Counter(self.decision_reasons).most_common(1)[0][0]


class EnvCollectionCoordinator:
    def __init__(self,
                 logger: BoundLogger,
                 request_builder: RequestBuilder,
                 cache_handler: CacheHandler,
                 runner: CollectorRunner,
                 pipeline_config: PipelineConfigInterface,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger
        self.pipeline_config = pipeline_config

        self.request = request_builder
        self.cache_handler = cache_handler
        self.runner = runner
        self.metadata_service = metadata_service

    def _process_single_source(self, source_id: str) -> Tuple[str, Optional[BaseSourceResult], Optional[Any]]:
        try:
            request = self.request.create_request(source_id)
            execution_decision = self.cache_handler.resolve_strategy(request, phase="environmental_collection")
            result = self.runner.execute_collection(source_id, execution_decision, request)

            self.cache_handler.persist_execution_lineage(result=result,
                                                        decision=execution_decision,
                                                        request=request)

            return source_id, result, execution_decision

        except Exception as e:
            self.logger.error(f"[{source_id}] Unexpected error: {str(e)}")
            return source_id, None, None

    def run(self, run_id: Optional[UUID] = None) -> Phase4Result:
        start_time = time.time()

        sources = self.pipeline_config.get_env_sources()
        if not sources:
            return Phase4Result(success=False,
                                execution_status=ExecutionStatus.FAILED,
                                execution_time=0.0,
                                reason=Phase4FailureReason.NO_SOURCES)

        sources_total = len(sources)
        state = _AccumulationState()

        with concurrent.futures.ThreadPoolExecutor(max_workers=sources_total) as executor:
            future_to_source = {
                executor.submit(self._process_single_source, source_id): source_id
                for source_id in sources.keys()}

            for future in concurrent.futures.as_completed(future_to_source):
                source_id = future_to_source[future]

                try:
                    _, result, execution_decision = future.result()

                    if result and result.success and execution_decision:
                        state.add_success(result.file_path, result.mode,
                                        result.api_call_made, execution_decision.reason)
                        if result.mode == ExecutionMode.RUN and self.metadata_service and run_id:
                            try:
                                self.metadata_service.record_source_fetch(
                                    source_id=source_id,
                                    fetched_at=datetime.utcnow(),
                                    run_id=run_id,
                                    record_count=1,
                                    success=True,
                                )
                            except Exception:
                                pass
                    else:
                        state.add_failure(result.reason if result else None)
                        if self.metadata_service and run_id:
                            try:
                                self.metadata_service.record_source_fetch(
                                    source_id=source_id,
                                    fetched_at=datetime.utcnow(),
                                    run_id=run_id,
                                    success=False,
                                    error=str(result.reason) if result else "unknown",
                                )
                            except Exception:
                                pass

                except Exception as exc:
                    self.logger.error(f"[{source_id}] Thread execution failed: {exc}")
                    state.add_failure()

        # Determine execution status and dominant mode
        if state.sources_successful == sources_total:
            if state.fresh_sources == 0 and state.cached_sources > 0:
                execution_status = ExecutionStatus.SKIPPED
                reason = None
                dominant_mode = ExecutionMode.REUSE
            else:
                execution_status = ExecutionStatus.COMPLETED
                reason = None
                dominant_mode = ExecutionMode.REUSE if state.cached_sources > state.fresh_sources else ExecutionMode.RUN
        elif state.sources_successful == 0:
            execution_status = ExecutionStatus.FAILED
            reason = Phase4FailureReason.NO_DATA_RETRIEVED
            dominant_mode = ExecutionMode.FORCED
        else:
            execution_status = ExecutionStatus.FAILED
            reason = Phase4FailureReason.STRICT_MODE_FAILED
            dominant_mode = ExecutionMode.FORCED

        execution_time = time.time() - start_time

        stats = Phase4ExecutionStats(
            execution_status=execution_status,
            execution_time=execution_time,
            sources_total=sources_total,
            sources_successful=state.sources_successful,
            sources_failed=state.sources_failed,
            produced_manifest=state.produced_manifest,
            cached_sources=state.cached_sources,
            fresh_sources=state.fresh_sources,
            api_calls_made=state.api_calls_made,
            quota_exceeded=state.quota_exceeded)

        result = Phase4Result(
            success=execution_status in (ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED),
            execution_status=execution_status,
            execution_time=execution_time,
            produced_manifest=state.produced_manifest,
            reason=reason)

        # TODO: Refactor metadata persistence to record per-source granularity.
        # Currently, a single aggregated metadata record is written per phase.
        # Future enhancement: Each source (flux, kp, sunspot) should have its own
        # DatasetMetadata entry for finer lineage tracking and debugging.
        # This applies to all phases (1-6) for consistency across the pipeline.
        if self.metadata_service and run_id:
            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase4",
                execution_mode=dominant_mode,
                decision_reason=state.dominant_reason(),
                status=execution_status,
                output_data_type="weather_raw",
                artifact_name="f107_ap_indices",
                manifest_files=state.produced_manifest,
                record_count=state.sources_successful))

        return result