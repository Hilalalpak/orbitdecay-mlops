"""
Executes the requested processing steps in order. Ensures each stage runs with
the right inputs and handles basic workflow housekeeping.
"""

from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from structlog.stdlib import BoundLogger
from src.domains.orbital_data.processing.tle_data_processor import OrbitProcessor
from src.pipeline.management.storage_manager import StorageManager


class Executor:

    def __init__(self, orbital_data_processor: OrbitProcessor, storage_manager: StorageManager, logger: BoundLogger) -> None:
        self.processor = orbital_data_processor
        self.storage = storage_manager
        self.logger = logger

    def _process_and_save(self, item: tuple) -> tuple:
        """Processes a single satellite's data and saves the output."""
        sat_id, raw_data = item

        try:
            if not isinstance(raw_data, list) or not raw_data:
                self.logger.warning(f"No data found for satellite {sat_id} after grouping (empty list).")
                return sat_id, 'failure'

            self.logger.debug(f"Processing SAT-{sat_id} ({len(raw_data)} records)...")

            processed = self.processor.process(raw_data)

            if processed and self.storage.save_orbit_data(sat_id, processed):
                return sat_id, "success"

            return sat_id, "failure"

        except Exception as e:
            self.logger.error(f"Unexpected error while processing SAT-{sat_id}: {e}", exc_info=True)
            return sat_id, 'failure'

    def process_grouped_data(self,
                             grouped: Dict[str, List[Dict]],
                             max_workers: int) -> Tuple[int, int]:
        """Executes per-satellite work in parallel."""
        success = 0
        fail = 0
        total = len(grouped)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_and_save, item): item[0]
                       for item in grouped.items()}

            for future in as_completed(futures):
                sat_id, status = future.result()

                if status == 'success':
                    success += 1
                else:
                    fail += 1

                processed = success + fail
                if processed % 50 == 0 or processed == total:
                    self.logger.info(f"Progress: {processed}/{total} satellites processed.")

        return success, fail