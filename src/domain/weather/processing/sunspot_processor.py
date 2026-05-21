
import polars as pl
from typing import List, TypedDict, Optional
from datetime import datetime

from src.domain.weather.processing.base import BaseDataProcessor
from structlog.stdlib import BoundLogger


class SunspotRecord(TypedDict):
    date: datetime
    sunspot_number: float
    std_dev: float
    nb_observations: float
    definitive: str


class SunspotProcessor(BaseDataProcessor):

    def __init__(
        self,
        logger: BoundLogger) -> None:

        super().__init__()
        self.logger = logger

    def _prepare_input(self, raw_text: str) -> List[str]:
        return [
            line.strip()
            for line in raw_text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def _parse_line(self, line: str) -> Optional[SunspotRecord]:
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 8:
            return None

        year, month, day = map(int, parts[:3])
        date = datetime(year=year, month=month, day=day)

        return SunspotRecord(
            date=date,
            sunspot_number=float(parts[4]),
            std_dev=float(parts[5]),
            nb_observations=float(parts[6]),
            definitive=parts[7],
        )

    def _create_dataframe(self, records: List[SunspotRecord]) -> pl.DataFrame:
        schema = {
            "date": pl.Datetime,
            "sunspot_number": pl.Float64,
            "std_dev": pl.Float64,
            "nb_observations": pl.Float64,
            "definitive": pl.Utf8
        }

        if not records:
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(records, schema=schema).sort("date")

    def _validate_output(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty():
            return df

        # Sanity check: Sunspot cannot be negative
        return df.filter((pl.col("sunspot_number") >= 0) & pl.col("date").is_not_null())