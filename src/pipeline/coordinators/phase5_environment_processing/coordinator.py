import time
from structlog.stdlib import BoundLogger
from src.pipeline.coordinators.phase5_environment_processing.components.processing_runner import ProcessingRunner
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.domain.weather.processing.contracts.phase5_result import EnvProcessingResult
from src.domain.weather.processing.metrics.phase5_telemetry import Phase5ExecutionStats, SourceProcessingResult
from src.pipeline.coordinators.phase5_environment_processing.components.request_builder import RequestBuilder
from typing import Optional, List
from uuid import UUID
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.contracts.execution_lifecycle import DecisionReason, ExecutionMode

class EnvProcessingCoordinator:

    def __init__(self,
                 logger: BoundLogger,
                 request: RequestBuilder,
                 runner: ProcessingRunner,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger
        self.runner = runner
        self.request = request
        self.metadata_service = metadata_service

    def run(self,
            processing_manifest: List[str],
            run_id: Optional[UUID] = None) -> EnvProcessingResult:
        """Runs processing for each environmental dataset received from Phase 3."""
        phase_start = time.time()

        self.logger.info(f"Phase 4 received {len(processing_manifest)} files: {processing_manifest}")

        results = []
        for file_ref in processing_manifest:
            source_id = file_ref.split('/')[-2]
            request = self.request.create_request(source_id)
            result = self.runner.execute(source_id=source_id, file_ref=file_ref, request=request)
            self.runner.persist_execution_lineage(request, result)
            results.append(result)

        stats = self._build_stats(results, time.time() - phase_start)
        result = EnvProcessingResult.from_execution_stats(stats)
        self.logger.info(f"Phase 4 produced {len(stats.produced_manifest)} files: {stats.produced_manifest}")

        # Write its own metadata
        if self.metadata_service and run_id:

            processed_sources = [r for r in results if r.success and r.mode == ExecutionMode.RUN]
            skipped_sources = [r for r in results if r.success and r.mode == ExecutionMode.REUSE]

            if len(skipped_sources) > len(processed_sources):
                dominant_mode = ExecutionMode.REUSE
                dominant_reason = DecisionReason.CHECKPOINT_EXISTS
            else:
                dominant_mode = ExecutionMode.RUN
                dominant_reason = DecisionReason.INITIAL_RUN

            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase5",
                output_data_type="weather_cleaned",
                artifact_name="interpolated_weather",
                manifest_files=stats.produced_manifest,
                record_count=stats.sources_successful,
                execution_mode=dominant_mode,
                decision_reason=dominant_reason,
                status=stats.execution_status,
            ))

        return result

    def _build_stats(self, results: List[SourceProcessingResult], duration: float) -> Phase5ExecutionStats:
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        sources_skipped = [r for r in successful if r.mode == ExecutionMode.REUSE]  # <-- YENİ
        sources_processed = [r for r in successful if r.mode == ExecutionMode.RUN]  # <-- YENİ

        if sources_skipped and not sources_processed and not failed:
            execution_status = ExecutionStatus.SKIPPED
        elif not failed:
            execution_status = ExecutionStatus.COMPLETED
        else:
            execution_status = ExecutionStatus.PARTIAL_SUCCESS

        return Phase5ExecutionStats(
            execution_status=execution_status,
            execution_time=duration,
            sources_total=len(results),
            sources_successful=len(sources_processed) + len(sources_skipped),
            sources_skipped=len(sources_skipped),
            sources_failed=len(failed),
            produced_manifest=[f for r in successful for f in r.produced_files],
            failed_sources=[r.source_id for r in failed])