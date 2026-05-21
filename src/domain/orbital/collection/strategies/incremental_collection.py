"""
Incremental sync strategy - fetches only recent updates to minimize API usage.
Queries telemetry after last sync timestamp for active satellites only.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List
from structlog.stdlib import BoundLogger
from dateutil import parser

from src.domain.orbital.collection.contracts.strategy_result import IncrementalStrategyResult
from src.domain.orbital.collection.models.satellite_record import SatelliteRecord
from src.domain.orbital.collection.orbital_data_fetcher import OrbitalDataFetcher
from src.shared import ExecutionRequest
from src.domain.orbital.collection.repository.orbital_collection_repository import OrbitalCollectionRepository

class IncrementalCollector:
    """
    Delta collection handler with smart buffering.
    Fetches recent telemetry updates and buffers writes to reduce S3 I/O.
    """

    def __init__(self,
                 logger: BoundLogger,
                 batch_size: int,
                 buffer_size: int,
                 overlap_hours: int,
                 orbital_collection_repository: OrbitalCollectionRepository,
                 orbital_data_collector: OrbitalDataFetcher) -> None:

        self.logger = logger
        self.batch_size = batch_size
        self.overlap_hours = overlap_hours
        self.repository = orbital_collection_repository

        self.buffer_size = buffer_size
        self.data_collector = orbital_data_collector

    def execute(self,
                request: ExecutionRequest) -> IncrementalStrategyResult:
        """
        Fetches recent updates and writes delta files to S3.
        Uses smart buffering to batch writes efficiently.
        """
        param_hash = request.hash

        # only active sats produce new TLEs
        target_ids = [str(sat_id) for sat_id in request.active_ids]

        # TODO: last_epoch should come from ExecutionRequest instead of hardcoded default
        # right now we always use 24hr overlap which wastes API quota
        raw_epoch = None
        last_epoch_dt = self._parse_epoch(raw_epoch)

        start_date_str = self._calculate_start_date(self.overlap_hours)

        self.logger.info("incremental_strategy_started",
                         target_count=len(target_ids),
                         start_date=start_date_str,
                         mode="bulk_smart_buffer")

        record_buffer: List[SatelliteRecord] = []
        delta_manifest: List[str] = []
        total_fetched_count = 0

        try:
            fetcher_gen = self.data_collector.collect_recent_updates(
                satellite_ids=target_ids,
                batch_size=self.batch_size,
                start_date=start_date_str,
                last_epoch=last_epoch_dt)

            for batch_records in fetcher_gen:
                record_buffer.extend(batch_records)

                if len(record_buffer) >= self.buffer_size:
                    self._flush_buffer(record_buffer, delta_manifest)
                    total_fetched_count += len(record_buffer)
                    record_buffer.clear()

            # flush remaining
            if record_buffer:
                self._flush_buffer(record_buffer, delta_manifest)
                total_fetched_count += len(record_buffer)
                record_buffer.clear()

        except Exception as e:
            self.logger.error("incremental_execution_failed", error=str(e), exc_info=True)
            if record_buffer:
                self._flush_buffer(record_buffer, delta_manifest)
            raise

        if total_fetched_count > 0:
            self.logger.info(
                    "incremental_sync_completed",
                    total_records=total_fetched_count,
                    delta_files=len(delta_manifest))

        else:
            self.logger.info("incremental_sync_no_updates_found")

        return IncrementalStrategyResult(
                param_hash=param_hash,
                manifest_files=delta_manifest,
                total_records=total_fetched_count)

    def _flush_buffer(self,
                      data: List[SatelliteRecord],
                      manifest: List[str]) -> None:
        """Writes buffered records to S3."""
        if not data:
            self.logger.warning("flush_called_with_empty_buffer")
            return

        count = len(data)
        self.logger.debug("flushing_incremental_buffer", record_count=count)

        save_res = self.repository.save_delta(data)

        if save_res.get('success'):
            filename = save_res.get("filename")
            manifest.append(filename)
            self.logger.debug("buffer_flushed", file=filename, records=count)
        else:
            self.logger.error("smart_buffer_flush_failed", error=save_res.get('error'))

    def _calculate_start_date(self, hours_overlap: int) -> str:
        """Calculates API query start date with overlap buffer."""
        overlap_dt = datetime.now(timezone.utc) - timedelta(hours=hours_overlap)
        return overlap_dt.strftime('%Y-%m-%d')

    def _parse_epoch(self, raw_epoch: Any) -> Optional[datetime]:
        """Parses last sync timestamp, returns None if invalid."""
        if not raw_epoch:
            return None
        try:
            return parser.parse(str(raw_epoch))
        except (ValueError, TypeError):
            self.logger.warning("epoch_parse_failed", raw_value=str(raw_epoch))
            return None