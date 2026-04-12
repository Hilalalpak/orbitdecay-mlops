"""
Core orbital data processing pipeline.
Cleans, segments, filters, propagates, and validates TLE data.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from structlog.stdlib import BoundLogger
import polars as pl

from src.shared.config.config_interfaces import ProcessingConfigInterface, DomainConfigInterface
from src.domain.orbital.processing.engines.record_validator import OrbitRecordValidator
from src.domain.orbital.processing.engines.cleaner import OrbitalDataCleaner
from src.domain.orbital.processing.engines.propagation import SGP4Propagator
from src.domain.orbital.processing.engines.segment_filtering import SegmentFilter
from src.domain.orbital.processing.engines.segmentation import OrbitalSegmenter

class OrbitProcessor:
    """
    Phase 2 processing pipeline.
    Orchestrates cleaning, segmentation, filtering, propagation, and validation.
    """

    def __init__(self,
                 processing_config: ProcessingConfigInterface,
                 domain_config: DomainConfigInterface,
                 record_validator: OrbitRecordValidator,
                 environment_name: str,
                 logger: BoundLogger) -> None:

        self.processing_config = processing_config
        self.domain_config = domain_config
        self.record_validator = record_validator
        self.env_name = environment_name
        self.logger = logger

        self.cleaner = OrbitalDataCleaner(
            self.processing_config.get_orbital_cleaning_config(),
            self.processing_config)
        self.segmenter = OrbitalSegmenter(
            self.processing_config.get_orbital_segmentation_config(),
            self.domain_config.get_earth_gravitational_parameter())
        self.segment_filter = SegmentFilter(self.processing_config.get_segment_filter_config())
        self.propagator = SGP4Propagator(
            logger,
            self.processing_config.get_orbital_propagation_config(),
            self.processing_config.get_static_columns_to_keep())

        self.metrics: Dict[str, Any] = {}
        self._reset_metrics()

    def _reset_metrics(self) -> None:
        """Resets execution counters for new batch."""
        self.metrics = {
            'total_input': 0,
            'valid_output': 0,
            'invalid_records': 0,
            'tba_filtered': 0,
            'duration_seconds': 0.0,
            'env': self.env_name}

    def process(self, raw_df: pl.DataFrame, dataset_role) -> Optional[pl.DataFrame]:
        """
        Processes satellite records through full pipeline.
        Returns cleaned, segmented, propagated, and validated DataFrame.
        """
        start_time = datetime.now()
        self._reset_metrics()

        self.metrics['total_input'] = raw_df.height

        try:
            df = self.cleaner.process(raw_df, dataset_role)

            self.metrics['tba_filtered'] = (raw_df.height - df.height)

            if df.is_empty():
                return None

            df = self.segmenter.process(df, dataset_role)

            df = self.segment_filter.process(df, dataset_role)

            if df.is_empty():
                return None

            df = self.propagator.process(df, dataset_role)

            df = self.record_validator.validate(df)

            self.metrics['valid_output'] = df.height
            self.metrics['invalid_records'] = (self.metrics['total_input'] - df.height)

            self.metrics['duration_seconds'] = (datetime.now() - start_time).total_seconds()

            self._log_execution_summary()

            return df

        except Exception as e:
            self.logger.error("polars_processing_failed", error=str(e), exc_info=True)
            self.metrics['invalid_records'] = self.metrics['total_input']
            return None

    def _log_execution_summary(self) -> None:
        """Logs execution statistics."""
        self.logger.info(
            "processing_summary",
            valid=self.metrics['valid_output'],
            total=self.metrics['total_input'],
            invalid=self.metrics['invalid_records'],
            tba_filtered=self.metrics['tba_filtered'],
            duration_s=f"{self.metrics['duration_seconds']:.2f}")