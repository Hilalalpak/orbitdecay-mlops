from datetime import datetime
from typing import Dict, List, Optional, Any
import polars as pl

from src.shared.config.config_interfaces import PipelineConfigInterface
from src.shared.storage.s3_adapter import S3StorageAdapter
from structlog.stdlib import BoundLogger

class EnvProcessingStorage:
    def __init__(self,
                 pipeline_config: PipelineConfigInterface,
                 logger: BoundLogger,
                 storage_adapter: S3StorageAdapter) -> None:

        self.pipeline_config = pipeline_config
        self.logger = logger
        self.storage_adapter = storage_adapter
        self.prefix = self.pipeline_config.get_s3_prefix("env_processed")
        self.bucket = self.pipeline_config.get_s3_bucket('env_data')
        self.cache_bucket = self.pipeline_config.get_s3_bucket('pipeline_cache')

    def load_data(self, key: str) -> str:
        data = self.storage_adapter.load_parquet_as_json(self.cache_bucket, key)
        return self._extract_raw_content(data)

    def _extract_raw_content(self, cached_data: Optional[List[Dict[str, Any]]]) -> str:
        if cached_data:
            return "\n".join([
                str(item['raw_content'])
                for item in cached_data
                if isinstance(item, dict) and 'raw_content' in item])
        return ""

    def save_env_data(self, source_id: str, df: pl.DataFrame) -> List[str]:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = f"{source_id}/{self.prefix}"

        files_to_write = [
            f"{base_path}/data_{timestamp}.parquet",
            f"{base_path}/data_latest.parquet"]

        saved_keys = []

        for key in files_to_write:
            if self.storage_adapter.save_polars_parquet(self.bucket, key, df):
                saved_keys.append(key)
            else:
                self.logger.error(f"Failed to save environment data ({source_id}) to {key}")

        if saved_keys:
            self.logger.info(
                "env_data_saved",
                source=source_id,
                records=df.height,  # Polars native
                files=len(saved_keys))

        return saved_keys