"""
Executor for Phase 2 orbital processing.
Manages parallel batch processing and result aggregation.
"""

from typing import Dict, List, Tuple
import time
import polars as pl
from concurrent.futures import ThreadPoolExecutor, as_completed
from structlog.stdlib import BoundLogger
from src.domain.orbital.processing.metrics.phase2_telemetry import ProcessingExecutionStats
from src.domain.orbital.processing.core.tle_data_processor_factory import OrbitProcessorFactory
from src.domain.orbital.processing.repositories.orbital_batch_repository import OrbitalBatchRepository
from src.pipeline.coordinators.phase2_orbital_processing.utils.grouping import group_by_satellite
from src.shared.enums.dataset_enums import DatasetRole

class Executor:
    """Manages parallel execution of orbital data processing tasks."""
    def __init__(self,
                 orbit_processor_factory: OrbitProcessorFactory,
                 data_repository: OrbitalBatchRepository,
                 logger: BoundLogger,
                 max_workers: int) -> None:
        self.processor_factory = orbit_processor_factory
        self.data_repository = data_repository
        self.logger = logger
        self.max_workers = max_workers

    def execute_manifest(self,
                             manifest_files: List[str],
                         is_incremental: bool) -> Tuple[ProcessingExecutionStats, List[str]]:
        """
        Processes all batch files and aggregates results.
        Returns (ProcessingExecutionStats, manifest of produced files).
        """
        start_time = time.time()

        success_total = 0
        fail_total = 0
        manifest_aggregate: List[str] = []


        for idx, batch_key in enumerate(manifest_files, start=1):

            if "/active/" in batch_key:
                dataset_role = DatasetRole.ACTIVE
            elif "/decayed/" in batch_key:
                dataset_role = DatasetRole.DECAYED
            else:
                raise ValueError(f"Cannot infer dataset role from path: {batch_key}")


            self.logger.info("processing_batch",
                             batch_num=idx,
                             total_batches=len(manifest_files),
                             key=batch_key)

            try:
                batch_data = self.data_repository.load_batch(batch_key)

                if batch_data is None or batch_data.is_empty():
                    self.logger.warning("batch_empty_or_failed", key=batch_key)
                    continue

                grouped = group_by_satellite(batch_data, self.logger)

                if not grouped:
                    self.logger.warning("batch_no_groupable_data", key=batch_key)
                    continue

                success, fail, manifest = self._dispatch_satellite_batch(
                    grouped,
                    dataset_role,
                    self.max_workers,
                    is_incremental=is_incremental)

                success_total += success
                fail_total += fail
                manifest_aggregate.extend(manifest)

            except Exception as e:
                self.logger.error("batch_processing_exception",
                                  batch_key=batch_key,
                                  error=str(e),
                                  exc_info=True)
                fail_total += 1

            self.logger.debug("batch_complete", batch_num=idx)

        self.logger.info("phase2_complete",
                         success=success_total,
                         failures=fail_total)

        stats = ProcessingExecutionStats(
            records_total=success_total + fail_total,
            successfully_processed=success_total,
            processing_failures=fail_total,
            batches_total=len(manifest_files),
            batches_processed=len(manifest_files),
            execution_time=time.time() - start_time,
            workers_utilized=self.max_workers)

        return stats, manifest_aggregate

    def _dispatch_satellite_batch(self,
                             grouped_data: Dict[str, pl.DataFrame],
                             dataset_role: DatasetRole,
                             max_workers: int,
                             is_incremental: bool = False) -> Tuple[int, int, List[str]]:
        """
        Processes satellites in parallel.
        Returns (success_count, failure_count, output_manifest).
        """
        batch_start = time.time()
        success_count = 0
        fail_count = 0
        batch_manifest: List[str] = []
        total_groups = len(grouped_data)

        aggregate_metrics = {
            'total_input': 0,
            'valid_output': 0,
            'invalid_records': 0,
            'tba_filtered': 0}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._transform_and_persist_satellite, item[0], item[1], dataset_role, is_incremental): item[0]
                for item in grouped_data.items()}


            for future in as_completed(futures):
                sat_id, status, paths, metrics = future.result()

                if status == 'success':
                    success_count += 1
                    batch_manifest.extend(paths)

                    for key, value in metrics.items():
                        if key in aggregate_metrics:
                            aggregate_metrics[key] += value
                else:
                    fail_count += 1

                processed = success_count + fail_count
                if processed % 50 == 0 or processed == total_groups:
                    self.logger.info(
                        "processing_progress",
                        current=processed,
                        total=total_groups,
                        success=success_count,
                        failures=fail_count)

        batch_duration = time.time() - batch_start
        self.logger.info(
            "batch_complete",
            batch_duration_s=f"{batch_duration:.2f}",
            total_satellites=total_groups,
            success=success_count,
            fail=fail_count,
            metrics=aggregate_metrics)

        return success_count, fail_count, batch_manifest

    def _transform_and_persist_satellite(self,
                          sat_id: str,
                          raw_data: pl.DataFrame,
                          dataset_role: DatasetRole,
                          is_incremental: bool = False) -> Tuple[str, str, List[str], Dict]:
        """Processes and persists a single satellite's data."""
        processor = self.processor_factory.create()

        try:
            processed_data = processor.process(raw_data, dataset_role)
            if processed_data is None or processed_data.is_empty():
                return sat_id, 'failure', [], {}

            produced_paths = self.data_repository.save_processed_satellite(sat_id, processed_data, is_incremental, dataset_role)

            if produced_paths:
                return sat_id, "success", produced_paths, processor.metrics

            return sat_id, "failure", [], {}

        except Exception as e:
            self.logger.error(
                "satellite_processing_error",
                sat_id=sat_id,
                error=str(e),
                exc_info=True)
            return sat_id, 'failure', [], {}

