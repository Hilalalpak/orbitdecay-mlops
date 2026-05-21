import time
from src.domain.weather.feature_synthesis.contracts.phase6_result import Phase6Result
from structlog.stdlib import BoundLogger
from src.pipeline.coordinators.phase6_environment_synthesis.components.checkpoint_handler import P6CheckPointHandler
from src.pipeline.coordinators.phase6_environment_synthesis.components.executor import SynthesisExecutor
from src.domain.weather.feature_synthesis.repository.env_synthesis_repository import EnvSynthesisRepository
from src.pipeline.coordinators.phase6_environment_synthesis.components.request_builder import SynthesisRequestBuilder
from typing import Optional, List
from uuid import UUID
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata

from src.pipeline.contracts.execution_lifecycle import ExecutionMode, ExecutionStatus

class EnvSynthesisCoordinator:

    def __init__(self,
                logger: BoundLogger,
                 request_builder: SynthesisRequestBuilder,
                 executor: SynthesisExecutor,
                 checkpoint_handler: P6CheckPointHandler,
                 repository: EnvSynthesisRepository,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger

        self.builder = request_builder
        self.executor = executor
        self.check = checkpoint_handler
        self.repository = repository
        self.metadata_service = metadata_service                                # ← ekle

    def run(self,
            available_sources: List[str],
            run_id: Optional[UUID] = None) -> Phase6Result:
        """Runs the synthesis phase to merge all environmental datasets."""
        t0 = time.time()

        # 1. Validation
        if not self.executor.is_ready():
            return Phase6Result(
                success=False,
                execution_time=0.0,
                action=ExecutionMode.FORCED,
                reason='EnvironmentMerger not available')

        if not available_sources:
            self.logger.warning('No source IDs received from Phase 5. Skipping synthesis phase.')
            return Phase6Result(
                success=False,
                execution_time=0.0,
                action=ExecutionMode.FORCED,
                reason='No sources available')

        self.logger.info('Starting Phase 5 (Environment Synthesis)')

        # 2. Build Request
        req = self.builder.create_request(available_sources)
        if not req:
            return Phase6Result(
                success=False,
                execution_time=time.time() - t0,
                action=ExecutionMode.FORCED,
                reason='Failed to create synthesis request')

        # 3. Checkpoint check
        execution_decision = self.check.check_and_maybe_skip(req)

        if execution_decision.mode == ExecutionMode.REUSE:
            self.logger.info("Phase 5 SKIPPED (Checkpoint Hit).")
            skip_result = self.check.build_skip_result(execution_decision, req)
            rows = skip_result.unified_records if skip_result else 0
            cols = 0
            saved_files = []
            execution_status = ExecutionStatus.SKIPPED
            success = True
            action = ExecutionMode.REUSE
            reason = 'checkpoint_exists'

        else:
            # 4. Execute Merge
            synthesis_result = self.executor.execute_merge()

            if synthesis_result and synthesis_result.success:
                rows = synthesis_result.record_count
                cols = synthesis_result.feature_count

                if rows > 0:
                    saved_files = self.repository.save_synthesis('unified_synthesis', synthesis_result.data, 'env_featured')
                    execution_status = ExecutionStatus.COMPLETED
                    success = True
                    action = ExecutionMode.RUN
                    reason = None
                    self.logger.info(f'Phase 5 complete. {rows} records, {cols} features.')
                else:
                    self.logger.warning('Space weather synthesis successful but resulted in empty data.')
                    saved_files = []
                    execution_status = ExecutionStatus.FAILED
                    success = False
                    action = ExecutionMode.FORCED
                    reason = 'No records produced'
            else:
                self.logger.error(f'Phase 5 merge failed: {synthesis_result.message if synthesis_result else "Unknown error"}')
                rows, cols, saved_files = 0, 0, []
                execution_status = ExecutionStatus.FAILED
                success = False
                action = ExecutionMode.FORCED
                reason = 'Merge operation failed'

        duration = time.time() - t0

        # 5. Persist lineage — always called after REUSE/RUN decision (Phase 2/3 pattern)
        self.check.persist_execution_lineage(
            request=req,
            record_count=rows,
            source_count=len(available_sources),
            produced_files=saved_files,
            decision=execution_decision,
            metadata_service=self.metadata_service)

        result = Phase6Result(
            success=success,
            execution_time=duration,
            action=action,
            unified_records=rows,
            feature_count=cols,
            reason=reason)

        if self.metadata_service and run_id:
            self.metadata_service.record_dataset(DatasetMetadata(
                pipeline_run_id=run_id,
                phase_id="phase6",
                execution_mode=execution_decision.mode,
                decision_reason=execution_decision.reason,
                status=execution_status,
                output_data_type="weather_synthesis",
                artifact_name="unified_spaceweather",
                record_count=rows,
            ))

        return result
