from typing import List, Optional
from datetime import datetime
import polars as pl
from structlog.stdlib import BoundLogger

from src.shared.storage.s3_adapter import S3StorageAdapter
from src.shared.config.config_interfaces import PipelineConfigInterface
from src.shared.enums.dataset_enums import DatasetRole


class OrbitalBatchRepository:
    """
    S3 repository for Phase 2 orbital processing.
    Handles loading raw batches and persisting processed outputs.
    """

    def __init__(self,
                 storage_adapter: S3StorageAdapter,
                 pipeline_config: PipelineConfigInterface,
                 logger: BoundLogger):
        self.adapter = storage_adapter
        self.config = pipeline_config
        self.logger = logger

        self.bucket = self.config.get_s3_bucket('satellite_data')
        self.cache_bucket = self.config.get_s3_bucket('pipeline_cache')
        self.prefix = self.config.get_s3_prefix('omm_leo')

    def load_batch(self, file_key: str) -> Optional[pl.DataFrame]:
        """Loads raw batch from S3. Returns None on failure."""
        stream = self.adapter.load_parquet(bucket=self.cache_bucket, key=file_key)

        if not stream:
            return None

        try:
            return pl.read_parquet(stream)
        except Exception as e:
            self.logger.error("repo_load_failed", key=file_key, error=str(e))
            return None


    def save_processed_satellite(self,
                                 sat_id: str,
                                 df: pl.DataFrame,
                                 is_incremental: bool,
                                 dataset_role: DatasetRole) -> List[str]:
        """Saves processed data to S3. Returns list of saved keys."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = f"{self.prefix}/{dataset_role.value}/{sat_id}/processed"

        saved_keys = []
        files_to_write = []

        if is_incremental:
            files_to_write.append(f'{base_path}/updates/delta_{timestamp}.parquet')
        else:
            files_to_write.append(f'{base_path}/orbital_history_{timestamp}.parquet')
            files_to_write.append(f'{base_path}/orbital_history_latest.parquet')

        for key in files_to_write:
            if self.adapter.save_polars_parquet(self.bucket, key, df):
                saved_keys.append(key)

        return saved_keys
