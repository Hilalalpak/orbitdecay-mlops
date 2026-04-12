"""
Handles orbital data retrieval from Space-Track.

Wraps session management, quota enforcement and validation. Most of the heavy lifting
happens in batch processors, this class mainly coordinates API interaction safely.
"""

import time
from datetime import datetime
from typing import List, Any, Dict, Callable, Iterator, Optional
import ijson
from structlog.stdlib import BoundLogger
from requests import Session

from src.shared.api_compliance.quota_manager import ApiQuotaManager
from src.domain.orbital.collection.api_clients.spacetrack_client import SpaceTrackClient
from src.domain.orbital.collection.validation.telemetry_validator import TelemetryValidator
from src.domain.orbital.collection.metrics.batch_telemetry import BatchCollectionStats
from src.domain.orbital.collection.models.satellite_record import SatelliteRecord


class OrbitalDataFetcher:
    """Controls ingestion lifecycle: auth, rate limits and validation."""

    def __init__(self,
                 logger: BoundLogger,
                 api_client: SpaceTrackClient,
                 telemetry_validator: TelemetryValidator,
                 quota_manager: ApiQuotaManager) -> None:

        self.logger = logger
        self.quota_manager = quota_manager
        self.client = api_client
        self.validator = telemetry_validator

    # -- Incremental --
    def collect_recent_updates(self,
                               satellite_ids: List[str],
                               batch_size: int,
                               start_date: str,
                               last_epoch: Optional[datetime]) -> Iterator[List[SatelliteRecord]]:

        processor = lambda session, batch_ids, batch_num, total_batches: (
            self._process_incremental_batch(session,
                                            batch_ids,
                                            batch_num,
                                            total_batches,
                                            start_date,
                                            last_epoch))

        return self._iter_batches(
            target_ids=satellite_ids,
            batch_size=batch_size,
            log_start_msg="incremental_sync_started",
            log_start_kwargs={"target_count": len(satellite_ids), "start_date": start_date},
            processor_func=processor)

    def _process_incremental_batch(self,
                                   session: Session,
                                   batch_ids: List[str],
                                   batch_num: int,
                                   total_batches: int,
                                   start_date: str,
                                   last_epoch: Optional[datetime]) -> Optional[List[SatelliteRecord]]:

        raw_data = self.client.fetch_updates_since(session,
                                                   batch_ids,
                                                   start_date)

        self.quota_manager.record_request(f"bulk_inc_batch_{len(batch_ids)}")

        self.logger.debug(
            "api_response_received",
            batch=f"{batch_num}/{total_batches}",
            size=len(raw_data) if raw_data else 0)

        if not raw_data:
            return None

        try:
            valid_records, _, invalid_count = self.validator.validate_and_filter(raw_data, last_epoch)
        except ValueError as exc:
            self.logger.error("batch_aborted_config_error", error=str(exc))
            return None

        if invalid_count:
            self.logger.warning(
                "data_quality_issue",
                batch=batch_num,
                invalid_count=invalid_count)

        if not valid_records:
            return None

        self.logger.debug(
            "incremental_batch_success",
            batch=f"{batch_num}/{total_batches}",
            valid_records=len(valid_records))

        return valid_records

    # Shared execution loop
    def _iter_batches(self,
                             target_ids: List[str],
                             batch_size: int,
                             log_start_msg: str,
                             log_start_kwargs: Dict[str, Any],
                             processor_func: Callable[
                                 [Session, List[str], int, int], Optional[List[SatelliteRecord]]]) -> Iterator[
        List[SatelliteRecord]]:

        total_sats = len(target_ids)
        total_batches = (total_sats + batch_size - 1) // batch_size

        self.logger.info(log_start_msg, **log_start_kwargs)

        with self.client.open_session() as session:
            if not self.client.authenticate(session):
                self.logger.error("fetch_cycle_aborted", reason="api_login_failed")
                return

            for i in range(0, total_sats, batch_size):

                if not self.quota_manager.check_availability().get("allowed", False):
                    self.logger.warning("fetch_cycle_paused", reason="quota_exceeded")
                    break

                batch_ids = target_ids[i:i + batch_size]
                batch_num = (i // batch_size) + 1

                result = processor_func(session, batch_ids, batch_num, total_batches)
                if result is not None:
                    yield result

                self._throttle()

    # -- Full history --
    def fetch_full_history(self,
                                        decayed_satellites: List[str],
                                        active_satellites: List[str],
                                        batch_size: int,
                                        on_batch_callback: Callable[
                                            [List[SatelliteRecord], int, str], Dict
                                        ]) -> BatchCollectionStats:

        start_time = time.time()
        global_batch_counter = 0

        total_expected_batches = (
            (len(decayed_satellites) + batch_size - 1) // batch_size +
            (len(active_satellites) + batch_size - 1) // batch_size)

        stats = BatchCollectionStats(
            batch_count=0,
            total_records=0,
            failed_batches=[],
            success_rate=0.0)

        self.logger.info(
            "batch_collection_started",
            decayed=len(decayed_satellites),
            active=len(active_satellites),
            total_batches=total_expected_batches)

        with self.client.open_session() as session:
            if not self.client.authenticate(session):
                stats.failed_batches.append({"batch": "init", "reason": "login_failed"})
                return stats

            def _run_group(group_name: str, satellites: List[str]):
                nonlocal global_batch_counter
                group_batch_num = 0

                for i in range(0, len(satellites), batch_size):

                    if not self.quota_manager.check_availability().get("allowed", False):
                        self.logger.warning(
                            "batch_collection_stopped",
                            group=group_name,
                            global_batch=global_batch_counter,
                            total_batches=total_expected_batches,
                            reason="quota_exceeded")
                        return

                    batch_ids = satellites[i:i + batch_size]
                    group_batch_num += 1
                    global_batch_counter += 1


                    self.logger.debug(
                        "processing_batch",
                        group=group_name,
                        group_batch=group_batch_num,
                        global_batch=global_batch_counter,
                        total_batches=total_expected_batches,
                        progress=f"{global_batch_counter}/{total_expected_batches}")

                    success = self._process_single_batch(
                        session=session,
                        batch_ids=batch_ids,
                        batch_num=group_batch_num,
                        callback=lambda data, num: on_batch_callback(data, num, group_name),
                        stats_accumulator=stats,
                        global_batch_num=global_batch_counter)

                    if success:
                        self._throttle()

            if decayed_satellites:
                self.logger.info(
                    "batch_group_started",
                    group="decayed",
                    satellites=len(decayed_satellites),
                    expected_batches=(len(decayed_satellites) + batch_size - 1) // batch_size)
                _run_group("decayed", decayed_satellites)

            if active_satellites:
                self.logger.info(
                    "batch_group_started",
                    group="active",
                    satellites=len(active_satellites),
                    expected_batches=(len(active_satellites) + batch_size - 1) // batch_size,
                    global_offset=global_batch_counter)
                _run_group("active", active_satellites)

        stats.collection_duration = time.time() - start_time

        if total_expected_batches:
            stats.success_rate = (stats.batch_count / total_expected_batches) * 100

        self.logger.info(
            "batch_collection_completed",
            duration_sec=round(stats.collection_duration, 2),
            records_ingested=stats.total_records,
            batches_processed=f"{stats.batch_count}/{total_expected_batches}",
            failed=len(stats.failed_batches))

        return stats

    # Single batch processor
    def _process_single_batch(self,
                              session: Session,
                              batch_ids: List[str],
                              batch_num: int,
                              callback: Callable[[List[SatelliteRecord], int], Dict[str, Any]],
                              stats_accumulator: BatchCollectionStats,
                              global_batch_num: int) -> bool:

        raw_items = []

        try:
            with self.client.fetch_bulk_history_stream(session, batch_ids) as response:

                if not response:
                    self._record_failure(
                        stats_accumulator, batch_num, "no_data_returned",
                        batch_ids, global_batch=global_batch_num)
                    return False

                stats_accumulator.api_calls_made += 1
                self.quota_manager.record_request("batch_history_fetch")

                try:
                    for item in ijson.items(response.raw, "item"):
                        raw_items.append(item)
                except Exception as e:
                    self._record_failure(
                        stats_accumulator, batch_num, "json_stream_error",
                        batch_ids, str(e), global_batch=global_batch_num)
                    return False

            if not raw_items:
                self.logger.warning(
                    "batch_empty",
                    group_batch=batch_num,
                    global_batch=global_batch_num)
                return True

            valid_records, _, invalid_count = self.validator.validate_and_filter(raw_items, last_epoch=None)

            if invalid_count:
                self.logger.warning(
                    "data_quality_issue",
                    group_batch=batch_num,
                    global_batch=global_batch_num,
                    invalid_records=invalid_count)

            if not valid_records:
                self.logger.warning(
                    "batch_all_records_invalid",
                    group_batch=batch_num,
                    global_batch=global_batch_num)
                return True

            cb_result = callback(valid_records, batch_num)

            if not cb_result.get("success"):
                self._record_failure(
                    stats_accumulator, batch_num, "callback_failed",
                    batch_ids, cb_result.get("error"),
                    global_batch=global_batch_num)
                return False

            stats_accumulator.batch_count += 1
            stats_accumulator.total_records += len(valid_records)

            self.logger.debug(
                "batch_processed",
                group_batch=batch_num,
                global_batch=global_batch_num,
                records=len(valid_records),
                file=cb_result.get("filename", "N/A"))

            return True

        except Exception as e:
            self._record_failure(stats_accumulator,
                                 batch_num,
                                 "unhandled_exception",
                                  batch_ids, str(e),
                                 global_batch=global_batch_num)

            self.logger.error(
                "batch_crash",
                group_batch=batch_num,
                global_batch=global_batch_num,
                error=str(e),
                exc_info=True)

            return False

    # Helpers
    def _throttle(self) -> None:
        status = self.quota_manager.check_availability()
        delay = self.quota_manager.calc_delay(status.get("status", "good"))
        if delay > 0:
            time.sleep(delay)

    def _record_failure(self,
                        stats: BatchCollectionStats,
                        group_batch_num: int,
                        reason: str,
                        ids: List[str],
                        error: str = "",
                        global_batch: Optional[int] = None):

        stats.failed_batches.append({
            "group_batch": group_batch_num,
            "global_batch": global_batch,
            "reason": reason,
            "satellites": ids[:5], # limit log payload
            "error_detail": error})
