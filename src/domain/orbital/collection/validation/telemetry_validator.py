"""
Validates and filters satellite telemetry data.
Enforces schema compliance and business rules (epoch filtering, etc).
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from dateutil import parser
from structlog.stdlib import BoundLogger

from src.domain.orbital.collection.models.satellite_record import SatelliteRecord

class TelemetryValidator:
    """
    Validates raw API data against schema and applies epoch filtering.
    
    Fail-fast on config errors (bad last_epoch), fault-tolerant on data errors.
    """

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger

    def validate_and_filter(self,
                            raw_data: List[Dict[str, Any]],
                            last_epoch: Optional[Union[datetime, str]] = None) -> Tuple[List[SatelliteRecord], int, int]:
        """
        Validates raw API batch and filters by epoch.
        
        Returns: (valid_records, filtered_count, invalid_count)
        """
        valid_records: List[SatelliteRecord] = []
        filtered_count = 0
        invalid_count = 0

        cutoff_dt = self._parse_cutoff_epoch(last_epoch)

        for item in raw_data:
            try:
                record = SatelliteRecord.model_validate(item)

                if cutoff_dt:
                    if not self._is_record_new(record, cutoff_dt):
                        filtered_count += 1
                        continue

                valid_records.append(record)

            except ValueError:
                # skip bad records but keep processing batch
                invalid_count += 1

        return valid_records, filtered_count, invalid_count

    def _parse_cutoff_epoch(self, raw_epoch: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """
        Parses cutoff epoch from config.
        Raises ValueError if format is invalid (fail-fast on config errors).
        """
        if raw_epoch is None:
            return None

        if isinstance(raw_epoch, datetime):
            return raw_epoch

        try:
            return parser.parse(str(raw_epoch))
        except (ValueError, TypeError) as e:
            self.logger.critical("validator_config_error", raw_value=str(raw_epoch), error=str(e))
            raise ValueError(f"Critical: Invalid last_epoch format: {raw_epoch}") from e

    def _is_record_new(self, record: SatelliteRecord, cutoff_dt: datetime) -> bool:
        try:
            record_dt = parser.parse(record.epoch)

            if record_dt.tzinfo is not None:
                record_dt = record_dt.replace(tzinfo=None)
            if cutoff_dt.tzinfo is not None:
                cutoff_dt = cutoff_dt.replace(tzinfo=None)

            return record_dt > cutoff_dt

        except (ValueError, TypeError):
            raise ValueError(f"Malformed epoch in record: {record.epoch}")
