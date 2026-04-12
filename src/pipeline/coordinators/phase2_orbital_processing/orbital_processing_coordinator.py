"""
Coordinates the end-to-end orbit processing workflow. It prepares inputs, selects
the right components, and keeps the pipeline moving in the correct order.
"""
import time
from typing import Dict, Any, Optional, List

from structlog.stdlib import BoundLogger
from src.domains.schemas.orbital_processing_schema import Phase2Result
from src.pipeline.coordinators.phase2_orbital_processing.components.checkpoint_handler import CheckpointHandler
from src.pipeline.coordinators.phase2_orbital_processing.components.executor import Executor
from src.pipeline.coordinators.phase2_orbital_processing.components.grouper import GroupResolver
from src.pipeline.coordinators.phase2_orbital_processing.components.request import RequestBuilder

class OrbitProcessingCoordinator:

    def __init__(self,
                 logger: BoundLogger,
                 request_builder: RequestBuilder,
                 checkpoint_handler: CheckpointHandler,
                 grouper: GroupResolver,
                 executor: Executor,
                 max_workers: int,
                 target_date: Optional[str] = None) -> None:

        self.logger = logger
        self.date = target_date
        self.max_workers = max_workers

        self.request = request_builder
        self.checkpoint = checkpoint_handler
        self.grouper = grouper
        self.executor = executor

    def run(self,
            collection_hash: str,
            batch_files_manifest: Optional[List[str]] = None,
            data: Optional[List[Dict]] = None) -> Phase2Result:
        """Main entry point for Phase 2 orbital processing (behavior unchanged)."""
        start_time = time.time()

        # Build phase request object
        request = self.request.build_request(collection_hash)

        if request is None:
            return Phase2Result(
                successfully_processed=0,
                processing_failures=0,
                reason='hash_creation_failed',
                execution_time=time.time() - start_time)

        # Cache lookup
        cached_stats = self.checkpoint.check_and_maybe_skip(request)
        if cached_stats is not None:
            return cached_stats

        max_workers = self.max_workers
        self.logger.info(f"Using {max_workers} parallel workers for processing satellite groups.")

        success_count = 0
        fail_count = 0

        # Incremental mode (data provided directly)
        if data:
            self.logger.info(f"Processing {len(data)} records from RAM (Incremental Mode)...")

            grouped = self.grouper.group_by_sat(data)
            s, f = self.executor.process_grouped_data(grouped, max_workers)
            success_count += s
            fail_count += f

        # Batch Mode (files from Phase 1)
        elif batch_files_manifest:
            self.logger.info(f"Starting Phase 2 (Orbit Process) for {len(batch_files_manifest)} batch files...")

            for i, batch_file in enumerate(batch_files_manifest):
                self.logger.info(f"Processing batch file {i + 1}/{len(batch_files_manifest)}: {batch_file}...")

                try:
                    batch_data = self.checkpoint.load_batch_data(batch_file)

                    if not batch_data:
                        self.logger.warning(f"Batch file {batch_file} was empty or failed to load. Skipping.")
                        continue

                    grouped = self.grouper.group_by_sat(batch_data)
                    if not grouped:
                        self.logger.warning(f"Batch file {batch_file} contained no groupable data. Skipping.")
                        continue

                    s, f = self.executor.process_grouped_data(grouped, max_workers)
                    success_count += s
                    fail_count += f

                except Exception as e:
                    self.logger.error(f"Failed to load or process batch file {batch_file}: {e}", exc_info=True)
                    fail_count += 1

                self.logger.info(f"Batch file {i + 1} complete.")

        # No input
        else:
            self.logger.error("Phase 2 'run' was called without 'data' or 'batch_files_manifest'. Aborting.")
            return Phase2Result(
                successfully_processed=0,
                processing_failures=1,
                reason='no_input_data',
                execution_time=time.time() - start_time)

        self.logger.info(f"Orbital processing complete. {success_count} satellites succeeded, {fail_count} failed.")

        # Build final result
        stats: Dict[str, Any] = {
            'successfully_processed': success_count,
            'processing_failures': fail_count,
            'processing_stage': 'orbital_data_processing',
            'batches_processed': len(batch_files_manifest) if batch_files_manifest else 0
        }

        # Cache + metadata save
        self.checkpoint.save_checkpoint(request, stats)
        return Phase2Result(
            **stats,
            execution_time=time.time() - start_time)