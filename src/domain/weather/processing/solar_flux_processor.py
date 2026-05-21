
import polars as pl
from typing import List, TypedDict, Optional
from datetime import datetime

from src.domain.weather.processing.base import BaseDataProcessor
from src.shared.config.config_interfaces import (
    ProcessingConfigInterface,
    PipelineConfigInterface,
)
from structlog.stdlib import BoundLogger


class FluxRecord(TypedDict):
    date: datetime
    observed_flux: float
    adjusted_flux: float
    series_d_flux: float


class SolarFluxProcessor(BaseDataProcessor):

    def __init__(
            self,
            processing_config: ProcessingConfigInterface,
            pipeline_config: PipelineConfigInterface,
            logger: BoundLogger) -> None:

        super().__init__()

        self.processing_cfg = processing_config
        self.pipeline_cfg = pipeline_config
        self.logger = logger

        self.validation_cfg = {
            "quality_checks": self.processing_cfg.is_quality_check_enabled(),
            "min_points": self.processing_cfg.get_min_data_points(),
            "max_gap": self.processing_cfg.get_max_gap_days(),
        }

        self.mapping = {
            "date_index": 0,
            "observed_flux_index": 4,
            "adj_flux_index": 5,
            "series_d_flux_index": 6,
            "min_col_required": 7,
        }

    def _prepare_input(self, raw_text: str) -> List[str]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        skip = self.pipeline_cfg.get_flux_header_skip_lines()
        return lines[skip:]

    def _parse_line(self, line: str) -> Optional[FluxRecord]:
        parts = line.split()
        if len(parts) < self.mapping["min_col_required"]:
            return None

        date = datetime.strptime(parts[self.mapping["date_index"]], "%Y%m%d")

        return FluxRecord(
            date=date,
            observed_flux=float(parts[self.mapping["observed_flux_index"]]),
            adjusted_flux=float(parts[self.mapping["adj_flux_index"]]),
            series_d_flux=float(parts[self.mapping["series_d_flux_index"]]),
        )

    def _create_dataframe(self, records: List[FluxRecord]) -> pl.DataFrame:
        schema = {
            "date": pl.Datetime,
            "observed_flux": pl.Float64,
            "adjusted_flux": pl.Float64,
            "series_d_flux": pl.Float64
        }

        if not records:
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(records, schema=schema).sort("date")

    def _validate_output(self, df: pl.DataFrame) -> pl.DataFrame:
        if not self.validation_cfg["quality_checks"]:
            return df

        # Physical sanity filter: flux must be > 0 (filters -999.0 errors)
        df = df.filter(pl.col("observed_flux") > 0)

        if df.height < self.validation_cfg["min_points"]:
            self.logger.warning(
                "Flux dataset small",
                rows=df.height,
                minimum=self.validation_cfg["min_points"])

        if df.height > 1:
            gaps = df.select((pl.col("date").diff().dt.total_days()).alias("gap")).drop_nulls()
            if not gaps.is_empty():
                largest = gaps.max().item()
                if largest > self.validation_cfg["max_gap"]:
                    self.logger.warning(
                        "Large gap detected",
                        days=int(largest),
                        threshold=self.validation_cfg["max_gap"])

        return df