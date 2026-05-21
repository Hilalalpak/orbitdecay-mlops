from typing import Optional, List
from datetime import datetime
import polars as pl
from structlog.stdlib import BoundLogger

from src.shared.storage.s3_adapter import S3StorageAdapter
from src.shared.config.config_interfaces import PipelineConfigInterface


class EnvSynthesisRepository:
    """
    Unified S3 repository for Phase 6 Environment Synthesis.
    Handles loading processed environment data and saving synthesized features.
    Replaces EnvironmentDataLoader and SynthesisPersistence.
    """

    def __init__(self,
                 pipeline_config: PipelineConfigInterface,
                 storage_adapter: S3StorageAdapter,
                 logger: BoundLogger) -> None:

        self.pipeline_cfg = pipeline_config
        self.storage = storage_adapter
        self.logger = logger

        self.env_bucket = self.pipeline_cfg.get_s3_bucket('env_data')
        self.processed_prefix = self.pipeline_cfg.get_s3_prefix('env_processed')

        self._last_saved_files: List[str] = []

    def find_latest_processed_file(self, data_type: str) -> Optional[str]:
        """Finds the most recent processed file for a given data type."""
        try:
            search_prefix = f"{data_type}/{self.processed_prefix}/"
            response = self.storage.list_objects(self.env_bucket, search_prefix)

            if 'Contents' not in response or not response['Contents']:
                return None

            latest_file = max(response['Contents'], key=lambda x: x['LastModified'])['Key']
            return latest_file

        except Exception as e:
            self.logger.error(f"Error finding latest {data_type} file: {e}")
            return None

    def load_dataframe(self, key: str) -> pl.DataFrame:
        """Loads Parquet file from S3 directly into Polars DataFrame."""
        try:
            buffer = self.storage.load_parquet(self.env_bucket, key)

            if buffer:
                return pl.read_parquet(buffer)

            return pl.DataFrame()

        except Exception as e:
            self.logger.error(f"Failed to load s3://{self.env_bucket}/{key}: {str(e)}")
            return pl.DataFrame()

    def save_synthesis(self, data_category: str, dataset: pl.DataFrame, prefix_key: str) -> List[str]:
        """Saves synthesized data as Polars Parquet with versioning and latest snapshot."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        storage_prefix = self.pipeline_cfg.get_s3_prefix(prefix_key)

        versioned_file = f'{storage_prefix}/{data_category}_data_{timestamp}.parquet'
        latest_file = f'{storage_prefix}/{data_category}_data_latest.parquet'

        saved_files = []

        for file_key in [versioned_file, latest_file]:
            success = self.storage.save_polars_parquet(self.env_bucket, file_key, dataset)

            if success:
                saved_files.append(file_key)
            else:
                self.logger.error(f'Failed to save environment data ({data_category}) to {file_key}')

        if saved_files:
            self.logger.info(f'Saved environment data: {data_category} ({dataset.height} records)')
            self._last_saved_files = saved_files

        return saved_files

    def get_last_saved_files(self) -> List[str]:
        """Returns the list of files saved in the last save_synthesis operation."""
        return self._last_saved_files.copy()
