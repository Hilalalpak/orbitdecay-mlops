"""
Merges multiple environment data sources into one unified dataset.
Loads data from S3, runs feature engineering, and combines everything using Polars.
Basically the glue that turns separate weather streams into one coherent dataset.
"""
import polars as pl
from structlog.stdlib import BoundLogger

from src.domain.weather.feature_synthesis.repository.env_synthesis_repository import EnvSynthesisRepository
from .feature_engineering_rules import EnvironmentFeatureEngineer
from src.domain.weather.feature_synthesis.metrics.phase6_telemetry import SynthesisMergeResult


class EnvironmentDataMerger:
    """
    Combines multiple environment data sources into a single dataset.
    Loads from S3, applies feature engineering, and merges everything together.
    The final step before data goes to the time series integration phase.
    """

    def __init__(self,
                 repository: EnvSynthesisRepository,
                 logger: BoundLogger) -> None:

        self.logger = logger
        self.repository = repository
        self.engineer = EnvironmentFeatureEngineer(logger)

    def _load_source(self, source_name: str) -> pl.DataFrame:
        """Loads processed data from S3 and makes sure we have proper DateTime types.
        Finds the latest file for each source and returns it as a DataFrame."""
        latest_file = self.repository.find_latest_processed_file(source_name)

        if not latest_file:
            self.logger.warning(f"No processed data found for source: {source_name}")
            return pl.DataFrame()

        df = self.repository.load_dataframe(latest_file)

        if not df.is_empty():
            # Ensure the 'date' column is cast to strict Datetime for Asof Joining
            if "date" in df.columns and df.schema["date"] != pl.Datetime:
                df = df.with_columns(pl.col("date").str.to_datetime(strict=False))

        return df

    def merge_all_datasets(self) -> SynthesisMergeResult:
        """
        Execute full synthesis pipeline.
        Loads sources, delegates to ASOF Join feature engineering.
        """
        self.logger.info("Starting environment data synthesis (Polars Vectorized)")

        try:
            # Load individual sources as Polars DataFrames
            flux_df = self._load_source('solar_flux')
            kp_df = self._load_source('kp_indices')
            sunspot_df = self._load_source('sunspot')

            if flux_df.is_empty() and kp_df.is_empty() and sunspot_df.is_empty():
                self.logger.error("All input sources empty - cannot synthesize")
                return SynthesisMergeResult(
                    success=False,
                    message="All input datasets were empty")

            self.logger.info("Merging datasets and engineering features (backward matching)...")

            # Execute Core Physics Rules & Merge
            space_weather = self.engineer.apply_features(flux_df, kp_df, sunspot_df)

            rows = space_weather.height
            cols = len(space_weather.columns)

            self.logger.info(f"Synthesis complete. Generated {rows} records with {cols} features.")

            return SynthesisMergeResult(
                success=True,
                data=space_weather,
                record_count=rows,
                feature_count=cols)

        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}", exc_info=True)
            return SynthesisMergeResult(
                success=False,
                message=str(e))