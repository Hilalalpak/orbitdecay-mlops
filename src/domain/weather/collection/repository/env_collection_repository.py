from typing import Dict, Any

from src.shared.storage.s3_adapter import S3StorageAdapter
from structlog.stdlib import BoundLogger
from src.shared import ExecutionRequest


class EnvCollectionRepository:
    """
    Handles S3 persistence strictly for Phase 3 (Environmental Data Collection).
    Manages raw text storage for space weather indices (Flux, Kp, Sunspot).
    """

    def __init__(self,
                 logger: BoundLogger,
                 data_prefix: str,
                 cache_bucket: str,
                 storage_adapter: S3StorageAdapter) -> None:

        self.bucket = cache_bucket
        self.logger = logger
        self.storage = storage_adapter
        self.prefix = data_prefix

    def save_env_data(self,
                       source_id: str,
                       execution_request: ExecutionRequest,
                       data: str) -> Dict[str, Any]:
        """
        Handles normalization, metadata wrapping, and persistence for raw data.
        Replaces logic previously in CollectionFreshnessPolicy.
        """
        try:
            structured_data = [{"raw_content": data}]

            param_hash = execution_request.hash
            key = f'{self.prefix}/{source_id}/data_{param_hash[:16]}.parquet'

            success = self.storage.save_list_dict_as_parquet(self.bucket, key, structured_data)

            return {
                'success': success,
                'filename': key,
                'error': None if success else "S3_write_failed"}

        except Exception as e:
            self.logger.error(f'Critical failure in save_env_cache for {source_id}: {str(e)}', exc_info=True)
            return {'success': False, 'error': str(e)}
