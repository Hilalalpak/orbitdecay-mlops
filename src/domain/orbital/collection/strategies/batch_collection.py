"""Batch collection strategy - fetches full orbital history and writes chunked Parquet files."""

from typing import List, Dict, Any
from structlog.stdlib import BoundLogger

from src.domain.orbital.collection.orbital_data_fetcher import OrbitalDataFetcher
from src.domain.orbital.collection.models.satellite_record import SatelliteRecord
from src.shared import ExecutionRequest
from src.domain.orbital.collection.contracts.strategy_result import BatchStrategyResult

from src.domain.orbital.collection.repository.orbital_collection_repository import OrbitalCollectionRepository

class BatchCollector:
    """
    Fetches complete orbital history for satellite sets.
    Writes data in batched Parquet files to S3.
    """

    def __init__(self,
                 logger: BoundLogger,
                 batch_size: int,
                 orbital_collection_repository: OrbitalCollectionRepository,
                 orbital_data_collector: OrbitalDataFetcher) -> None:
        self.batch_size = batch_size
        self.logger = logger
        self.repository = orbital_collection_repository
        self.data_collector = orbital_data_collector

    def execute(self, request: ExecutionRequest) -> BatchStrategyResult:
        """Executes full-history collection, returns stats and file manifest."""
        decayed_ids = request.satellite_ids
        active_ids = request.active_ids

        manifest_accumulator: List[str] = []

        self.logger.info(
            "batch_strategy_started",
            decayed=len(decayed_ids),
            active=len(active_ids),
            batch_size=self.batch_size)

        def _callback(batch_data: List[SatelliteRecord],
                      batch_num: int,
                      group: str) -> Dict[str, Any]:

            return self._persist_batch(
                batch_data=batch_data,
                batch_num=batch_num,
                request=request,
                group=group,
                manifest_list=manifest_accumulator)

        stats = self.data_collector.fetch_full_history(
            decayed_satellites=decayed_ids,
            active_satellites=active_ids,
            batch_size=self.batch_size,
            on_batch_callback=_callback)

        self.logger.info(
            "batch_strategy_completed",
            total_records=stats.total_records,
            manifest_count=len(manifest_accumulator),
            success_rate=f"{stats.success_rate:.2f}%")

        return BatchStrategyResult(
            param_hash=request.hash,
            stats=stats,
            manifest_files=manifest_accumulator,
            total_records=stats.total_records)

    def _persist_batch(self,
                       batch_data: List[SatelliteRecord],
                       batch_num: int,
                       request: ExecutionRequest,
                       group: str,
                       manifest_list: List[str]) -> Dict[str, Any]:
        """Serializes and saves single batch to S3."""
        self.logger.debug("persisting_batch", batch=batch_num, record_count=len(batch_data))

        try:
            save_result = self.repository.save_batch(group, request, batch_data, batch_num)

            if not save_result.get('success'):
                self.logger.error("batch_persistence_failed",
                                  batch=batch_num,
                                  error=save_result.get('error', 'unknown'))
                return save_result

            filename = save_result.get("filename")
            manifest_list.append(filename)
            return save_result

        except Exception as e:
            self.logger.error(
                "batch_persistence_exception",
                batch=batch_num,
                error=str(e),
                exc_info=True)

            return {'success': False, 'error': str(e)}