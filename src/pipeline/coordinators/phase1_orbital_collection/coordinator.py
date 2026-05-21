"""
Phase 1 coordinator - entry point for orbital data collection.

Orchestrates catalog lookup, request creation, strategy resolution
(full vs incremental) and delegates execution to strategy runner.
"""

import time
from datetime import datetime
from structlog.stdlib import BoundLogger
from typing import Optional
from uuid import UUID

from src.domain.orbital.collection.contracts.phase1_result import Phase1Result
from src.shared.enums.failure_enums import Phase1FailureReason

from src.pipeline.coordinators.phase1_orbital_collection.strategy_runner import StrategyRunner
from src.pipeline.coordinators.phase1_orbital_collection.components.cache_handler import CollectionCacheHandler
from src.pipeline.coordinators.phase1_orbital_collection.components.errors import Phase1ErrorHandler
from src.pipeline.coordinators.phase1_orbital_collection.components.request import RequestBuilder
from src.domain.orbital.collection.catalog.catalog_service import SatCatalogService

from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus, ExecutionMode

class OrbitCollectionCoordinator:
    """
    Phase 1 orchestrator for orbital data acquisition.
    Handles catalog lookup, strategy selection, and execution delegation.
    """

    def __init__(self,
                 logger: BoundLogger,
                 catalog_service: SatCatalogService,
                 request_builder: RequestBuilder,
                 error_handler: Phase1ErrorHandler,
                 strategy_runner: StrategyRunner,
                 cache_handler: CollectionCacheHandler,
                 metadata_service: Optional[MetadataService] = None) -> None:

        self.logger = logger

        self.catalog_service = catalog_service
        self.request_builder = request_builder
        self.error_handler = error_handler
        self.strategy_runner = strategy_runner
        self.cache_handler = cache_handler
        self.metadata_service = metadata_service

    def run_collection(self, run_id: Optional[UUID] = None) -> Phase1Result:
        """
        Executes Phase 1 orbital data collection pipeline.
        Returns Phase1Result with success/failure status and metadata.
        """
        phase_start = time.time()

        try:
            self.logger.info("phase1_collection_started")

            decayed_ids, active_ids = self.catalog_service.get_satellites()

            if not decayed_ids and not active_ids:
                raise RuntimeError("catalog returned empty satellite sets")

            self.logger.info("catalog_resolved", decayed=len(decayed_ids), active=len(active_ids))

            collection_req = self.request_builder.build(decayed_ids, active_ids)
            execution_decision = self.cache_handler.resolve_strategy(collection_req)

            strategy_result = self.strategy_runner.run_strategy(execution_decision, collection_req)

            self.cache_handler.record_lineage(strategy_result,
                                                         execution_decision,
                                                         collection_req)

            manifest = strategy_result.manifest_files
            is_incremental = execution_decision.mode == ExecutionMode.INCREMENTAL
            phase_duration = time.time() - phase_start
            satellites = active_ids + decayed_ids
            total_processed = len(satellites)

            if execution_decision.mode == ExecutionMode.REUSE:
                execution_status = ExecutionStatus.SKIPPED
            elif manifest:
                execution_status = ExecutionStatus.COMPLETED
            else:
                self.logger.error("batch_completed_without_manifest")
                execution_status = ExecutionStatus.FAILED

            self.logger.info(
                "phase1_collection_completed",
                duration=f"{phase_duration:.2f}",
                artifacts=len(manifest),
                mode=execution_decision.mode.value,
                status=execution_status.value)

            result = Phase1Result(
                success=execution_status in [ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED],
                is_incremental=is_incremental,
                satellites_processed=total_processed,
                processing_manifest=manifest,
                collection_hash=collection_req.hash,
                execution_time=phase_duration,
                reason=Phase1FailureReason.NO_DATA_RETRIEVED if execution_status == ExecutionStatus.FAILED else None,
                error_message="Batch mode completed but produced no manifest files." if execution_status == ExecutionStatus.FAILED else None)

            if self.metadata_service and run_id:
                self.metadata_service.record_dataset(DatasetMetadata(
                    pipeline_run_id=run_id,
                    phase_id="phase1",
                    output_data_type="orbital_raw",
                    artifact_name="tle_elements",
                    manifest_files=result.processing_manifest,
                    record_count=result.satellites_processed,
                    execution_mode=execution_decision.mode,
                    decision_reason=execution_decision.reason,
                    status=execution_status))

                if execution_decision.mode != ExecutionMode.REUSE:
                    try:
                        self.metadata_service.record_source_fetch(
                            source_id="space_track",
                            fetched_at=datetime.utcnow(),
                            run_id=run_id,
                            record_count=result.satellites_processed,
                            success=execution_status != ExecutionStatus.FAILED,
                        )
                    except Exception:
                        pass

            return result

        except Exception as exc:
            return self.error_handler.handle(exc, time.time() - phase_start)