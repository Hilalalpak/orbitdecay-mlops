from typing import Any
from structlog.stdlib import BoundLogger
import polars as pl
from src.domain.weather.processing.metrics.phase5_telemetry import SourceProcessingResult
from src.shared.enums.failure_enums import Phase5FailureReason
from src.pipeline.coordinators.phase5_environment_processing.components.checkpoint_handler import P5CheckPointHandler
from src.domain.weather.processing.repository import EnvProcessingStorage
from src.pipeline.contracts.execution_lifecycle import ExecutionMode

class ProcessingRunner:
    def __init__(self,
                 logger: BoundLogger,
                 storage: EnvProcessingStorage,
                 checkpoint_handler: P5CheckPointHandler,
                 environment_data_processors) -> None:

        self.processors = environment_data_processors
        self.storage = storage
        self.checkpoint = checkpoint_handler
        self.logger = logger

    def execute(self,
                source_id: str,
                file_ref: str,
                request: Any) -> SourceProcessingResult:
        try:
            # 1. Checkpoint (Skip case)
            execution_decision = self.checkpoint.check_and_maybe_skip(request)

            if execution_decision.mode == ExecutionMode.REUSE:
                manifest = self.checkpoint.build_skip_result(execution_decision, request)
                self.logger.info(f"Checkpoint hit for {source_id}, using cached files: {manifest}")

                return SourceProcessingResult(
                    source_id=source_id,
                    success=True,
                    mode=ExecutionMode.REUSE,
                    produced_files=manifest,
                    record_count=0)

            # 2. Data Loading
            raw_data = self.storage.load_data(file_ref)
            if not raw_data:
                return SourceProcessingResult(source_id=source_id,
                                              success=False,
                                              failure_reason=Phase5FailureReason.SOURCE_LOAD_FAILED)

            # 3. Processing (Now returns pl.DataFrame)
            processor = self.processors.get(source_id)
            processed_data: pl.DataFrame = processor.process(raw_data)

            # 5. Save and Final (Using Polars 'height')
            record_count = processed_data.height
            produced_files = self.storage.save_env_data(source_id, processed_data)

            return SourceProcessingResult(
                source_id=source_id,
                success=True,
                mode=ExecutionMode.RUN,
                produced_files=produced_files,
                record_count=record_count)

        except Exception as e:
            self.logger.error(f"Processing failed for {source_id}: {e}")
            return SourceProcessingResult(source_id=source_id,
                                          success=False,
                                          failure_reason=Phase5FailureReason.PROCESSING_FAILED)

    def persist_execution_lineage(self,
                                  request: Any,
                                  result: SourceProcessingResult) -> None:
        """Delegates lineage persistence to checkpoint handler. Called by coordinator."""
        self.checkpoint.persist_execution_lineage(
            request=request,
            source_id=result.source_id,
            produced_files=result.produced_files or [],
            record_count=result.record_count or 0,
            execution_mode=result.mode or ExecutionMode.RUN)