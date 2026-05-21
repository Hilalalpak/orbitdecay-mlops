"""
S3 repository for orbital feature engineering.
Handles loading Phase 2 outputs and persisting Phase 3 features.
"""

import polars as pl
from datetime import datetime
from typing import List, Optional
from structlog.stdlib import BoundLogger

from src.shared.storage.s3_adapter import S3StorageAdapter


class OrbitalDataRepository:
    """
    Data access layer for Phase 3 feature engineering.
    Loads orbital history and persists generated features to S3.
    """

    def __init__(self,
                 orbit_data_bucket: str,
                 orbit_data_prefix: str,
                 storage_adapter: S3StorageAdapter,
                 logger: BoundLogger) -> None:
        self.storage_adapter = storage_adapter
        self.logger = logger
        self.data_bucket = orbit_data_bucket
        self.data_prefix = orbit_data_prefix

    def load_data_by_key(self, s3_key: str) -> Optional[pl.DataFrame]:
        """Loads Parquet data from S3 key. Returns None on failure."""
        self.logger.debug("loading_manifest_data", key=s3_key, format="parquet")

        stream = self.storage_adapter.load_parquet(self.data_bucket, s3_key)

        if not stream:
            return None

        try:
            return pl.read_parquet(stream)
        except Exception as e:
            self.logger.error("repo_load_failed", key=s3_key, error=str(e))
            return None

    def save_enhanced_data(self,
                           sat_id: str,
                           enhanced_data: pl.DataFrame,
                           dataset_role,
                           is_incremental: bool = False) -> List[str]:
        """
        Persists features to S3.
        Incremental mode saves to updates/, batch mode saves timestamped + latest versions.
        Returns list of S3 keys written.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = f"{self.data_prefix}/{dataset_role.value}/{sat_id}/featured"
        files_to_save: List[str] = []

        if is_incremental:
            delta_key = f"{base_path}/updates/delta_{timestamp}.parquet"
            files_to_save.append(delta_key)
        else:
            history_key = f"{base_path}/enhanced_{timestamp}.parquet"
            latest_key = f"{base_path}/enhanced_latest.parquet"
            files_to_save.extend([history_key, latest_key])

        saved_paths: List[str] = []

        for key in files_to_save:
            try:
                success = self.storage_adapter.save_polars_parquet(self.data_bucket, key, enhanced_data)
                if success:
                    saved_paths.append(key)
                else:
                    self.logger.error("s3_write_failed", key=key, sat_id=sat_id)
            except Exception as e:
                self.logger.error("s3_write_exception", key=key, error=str(e), exc_info=True)

        if saved_paths:
            self.logger.info(
                "enhanced_data_saved",
                sat_id=sat_id,
                files_count=len(saved_paths),
                mode="incremental" if is_incremental else "batch")

        return saved_paths