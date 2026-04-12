# src/pipeline/coordinators/phase2_orbital_processing/components/batch_data_loader.py

"""
Loads batch files from S3 storage for pipeline processing.
"""

from typing import List, Dict, Optional, Any

from src.core.s3_storage import S3StorageAdapter
from structlog.stdlib import BoundLogger
from src.configuration.config_interfaces import PipelineConfigInterface


class BatchDataLoader:
    """
    Reads and parses batch files stored in S3 pipeline cache.
    """

    def __init__(self,
                 pipeline_config: PipelineConfigInterface,
                 storage_adapter: S3StorageAdapter,
                 logger: BoundLogger) -> None:

        self.config = pipeline_config
        self.storage = storage_adapter
        self.logger = logger
        self.cache_bucket = self.config.get_s3_bucket('pipeline_cache')

    def load_batch_file(self, batch_file_path: str) -> Optional[List[Dict]]:
        """Load single batch file from S3 and extract records."""
        try:
            self.logger.debug(f"Loading batch: {batch_file_path}")

            batch_cache = self.storage.load_json_data(bucket=self.cache_bucket, key=batch_file_path)

            if batch_cache is None:
                self.logger.error(f"Batch file not found: s3://{self.cache_bucket}/{batch_file_path}")
                return None

            records = self._extract_records(batch_cache, batch_file_path)

            if records:
                self.logger.debug(f"Loaded {len(records)} records from batch")
            else:
                self.logger.warning(f"No records in batch file: {batch_file_path}")

            return records

        except Exception as e:
            self.logger.error(f"Failed to load batch {batch_file_path}: {e}",exc_info=True)
            return None

    def _extract_records(self, batch_cache: Any, file_path: str) -> Optional[List[Dict]]:
        """Extract records from batch cache supporting multiple formats."""
        if isinstance(batch_cache, dict) and 'data' in batch_cache:
            records = batch_cache['data']

            if isinstance(records, list):
                return records
            else:
                self.logger.error(f"Invalid data field type in {file_path}: {type(records)}")
                return None

        elif isinstance(batch_cache, list):
            self.logger.debug(f"Legacy list format detected in {file_path}")
            return batch_cache

        else:
            self.logger.error(f"Unknown batch format in {file_path}: {type(batch_cache)}")
            return None