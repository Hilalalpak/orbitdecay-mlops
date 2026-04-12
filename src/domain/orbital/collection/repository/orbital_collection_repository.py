from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, TypeAdapter
import uuid

from src.shared.storage.s3_adapter import S3StorageAdapter
from structlog.stdlib import BoundLogger
from src.shared import ExecutionRequest


class OrbitalCollectionRepository:
    """
    S3 persistence layer for Phase 1 orbital data.
    Serializes Pydantic models to Parquet for storage efficiency.
    """

    def __init__(self,
                 logger: BoundLogger,
                 cache_bucket: str,
                 data_prefix: str,
                 storage_adapter: S3StorageAdapter) -> None:

        self.bucket = cache_bucket
        self.prefix = data_prefix
        self.logger = logger
        self.storage = storage_adapter

    def _serialize_models(self, models: List[BaseModel]) -> List[Dict[str, Any]]:
        if not models:
            return []
        model_type = type(models[0])
        adapter = TypeAdapter(list[model_type])  # type: ignore
        return adapter.dump_python(models, by_alias=True)

    def save_batch(self,
                                 group: str,
                                 execution_request: ExecutionRequest,
                                 batch_data: List[BaseModel],
                                 batch_num: int) -> Dict[str, Any]:
        """Writes batch to S3 as Parquet file."""
        try:
            if not batch_data:
                return {'success': False, 'reason': 'empty_batch'}

            param_hash = execution_request.hash
            filename = f'{self.prefix}/{group}/data_{param_hash[:16]}_batch_{batch_num:03d}.parquet'

            serialized_data = self._serialize_models(batch_data)

            success = self.storage.save_list_dict_as_parquet(
                bucket=self.bucket,
                key=filename,
                data=serialized_data)

            if not success:
                return {'success': False, 'error': 'parquet_write_failed'}

            self.logger.info("batch_saved", batch=batch_num, records=len(batch_data), file=filename)
            return {
                'success': True,
                'filename': filename,
                'record_count': len(batch_data),
                'batch_number': batch_num}

        except Exception as e:
            self.logger.error("batch_save_failed", batch=batch_num, error=str(e))
            return {'success': False, 'error': str(e)}

    def save_delta(self, data: List[BaseModel]) -> Dict[str, Any]:
        """Writes incremental updates to S3 as Parquet."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            short_uuid = uuid.uuid4().hex[:4]

            # only active sats get new TLEs, decayed ones are static
            filename = f"{self.prefix}/active/updates/delta_{timestamp}_{short_uuid}.parquet"

            normalized_data = self._serialize_models(data)

            success = self.storage.save_list_dict_as_parquet(
                bucket=self.bucket,
                key=filename,
                data=normalized_data)

            if not success:
                return {'success': False, 'error': 'parquet_write_failed'}

            self.logger.info("incremental_saved", records=len(normalized_data), file=filename)
            return {
                'success': True,
                'filename': filename,
                'record_count': len(normalized_data),
                'compressed': True}

        except Exception as e:
            self.logger.error("incremental_save_failed", error=str(e))
            return {'success': False, 'error': str(e)}

