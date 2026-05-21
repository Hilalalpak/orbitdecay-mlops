
import polars as pl
from typing import List, TypedDict, Optional
from datetime import datetime

from src.domain.weather.processing.base import BaseDataProcessor
from structlog.stdlib import BoundLogger


class KpRecord(TypedDict):
    year: int
    month: int
    day: int
    start_time: str
    mid_time: str
    days_elapsed: float
    modified_days: float
    kp_value: float
    ap_value: float
    data_type: str
    date: datetime


class GeomagneticIndexProcessor(BaseDataProcessor):

    def __init__(
        self,
        logger: BoundLogger) -> None:

        super().__init__()
        self.expected_fields = 10
        self.logger = logger

    def _prepare_input(self, raw_text: str) -> List[str]:
        return [
            line.strip()
            for line in raw_text.splitlines()
            if line.strip() and not line.strip().startswith(("#", ":"))
        ]

    def _parse_line(self, line: str) -> Optional[KpRecord]:
        parts = line.split()
        if len(parts) != self.expected_fields:
            return None

        year, month, day = map(int, parts[:3])
        date = datetime(year=year, month=month, day=day)

        return KpRecord(
            year=year,
            month=month,
            day=day,
            start_time=parts[3],
            mid_time=parts[4],
            days_elapsed=float(parts[5]),
            modified_days=float(parts[6]),
            kp_value=float(parts[7]),
            ap_value=float(parts[8]),
            data_type=parts[9],
            date=date,
        )

    def _create_dataframe(self, records: List[KpRecord]) -> pl.DataFrame:
        schema = {
            "year": pl.Int32, "month": pl.Int32, "day": pl.Int32,
            "start_time": pl.Utf8, "mid_time": pl.Utf8,
            "days_elapsed": pl.Float64, "modified_days": pl.Float64,
            "kp_value": pl.Float64, "ap_value": pl.Float64,
            "data_type": pl.Utf8, "date": pl.Datetime
        }

        if not records:
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(records, schema=schema).sort("date")

    def _validate_output(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty():
            return df

        return df.drop_nulls(subset=["date", "kp_value", "ap_value"])