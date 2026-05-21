import json
import boto3
from typing import Dict, Optional, Any, cast, List
from botocore.exceptions import ClientError
import io
import pandas as pd
import polars as pl
import pyarrow as pa

from src.shared.config.config_interfaces import StorageConfigInterface
from structlog.stdlib import BoundLogger
import pyarrow.parquet as pq

class S3StorageAdapter:
    """
    Manages all S3/MinIO interactions with connection handling and error recovery.
    Provides unified interface for JSON operations across the pipeline.
    """

    def __init__(self, storage_config: StorageConfigInterface, logger: BoundLogger) -> None:
        self.config = storage_config
        self.logger = logger

        self.s3_client = self._init_client()

    def _init_client(self):
        """Creates and configures the S3 client with credentials."""
        try:
            client = boto3.client(
                's3',
                endpoint_url=self.config.get_s3_endpoint(),
                aws_access_key_id=self.config.get_s3_access_key(),
                aws_secret_access_key=self.config.get_s3_secret_key())

            self.logger.info(f"S3 client initialized successfully")
            self.logger.debug("Connected to S3 endpoint", endpoint=self.config.get_s3_endpoint())
            return client
        except Exception as e:
            self.logger.critical("Failed to initialize S3 client", error=str(e))
            raise


    def load_parquet_as_json(self, bucket: str, key: str) -> Optional[List[Dict[str, Any]]]:
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            buffer = io.BytesIO(response['Body'].read())

            table = pq.read_table(buffer)
            data = table.to_pylist()

            self.logger.debug(f"Loaded Parquet s3://{bucket}/{key} as JSON list.")
            return data

        except self.s3_client.exceptions.NoSuchKey:
            self.logger.warning(f"Key not found: {key}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading Parquet as JSON: {e}")
            return None

    def save_parquet_data(self, bucket: str, key: str, df: pd.DataFrame) -> bool:
        try:
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False, engine='pyarrow', compression='snappy') # type: ignore
            buffer.seek(0)

            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/vnd.apache.parquet')

            self.logger.debug(f"Saved (Parquet) to s3://{bucket}/{key}")
            return True

        except Exception as e:
            self.logger.error(f"S3 Parquet write failed for s3://{bucket}/{key}: {e}")
            return False


    def save_polars_parquet(
            self,
            bucket: str,
            key: str,
            df: pl.DataFrame) -> bool:
        """
        Saves a Polars DataFrame to Parquet using the native Polars writer.

        This method guarantees:
        - column name preservation
        - schema stability
        - optimal write performance

        Use this method for all Polars-based pipeline outputs.
        """
        try:
            buffer = io.BytesIO()
            df.write_parquet(buffer, compression='snappy')
            buffer.seek(0)

            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/vnd.apache.parquet')

            self.logger.debug(
                "saved_polars_parquet",
                bucket=bucket,
                key=key,
                rows=df.height)
            return True

        except Exception as e:
            self.logger.error(
                "polars_parquet_write_failed",
                bucket=bucket,
                key=key,
                error=str(e))
            return False

    def save_list_dict_as_parquet(self, bucket: str, key: str, data: List[Dict[str, Any]]) -> bool:
        """
        Saves a List[Dict] directly to S3 as Parquet using PyArrow.
        Bypasses Pandas DataFrame creation for maximum performance and lower RAM usage.
        """
        try:
            if not data:
                self.logger.warning(f"Attempted to save empty list to {key}")
                return False

            table = pa.Table.from_pylist(data)  # type: ignore

            buffer = io.BytesIO()
            pq.write_table(table, buffer, compression='snappy')
            buffer.seek(0)

            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType='application/vnd.apache.parquet')

            self.logger.debug(f"Direct List[Dict] save success: s3://{bucket}/{key}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save List[Dict] parquet to s3://{bucket}/{key}: {e}")
            return False


    def load_parquet(self, bucket: str, key: str) -> Optional[io.BytesIO]:
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return io.BytesIO(response['Body'].read())

        except self.s3_client.exceptions.NoSuchKey:
            self.logger.warning("object_not_found", bucket=bucket, key=key)
            return None

        except Exception as e:
            self.logger.error("failed_fetch_stream", bucket=bucket, key=key, error=str(e))
            return None

    def load_parquet_data(self, bucket: str, key: str) -> Optional[pd.DataFrame]:
        """Loads Parquet file from S3 into a DataFrame."""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            buffer = io.BytesIO(response['Body'].read())

            df = pd.read_parquet(buffer, engine='pyarrow')

            self.logger.debug(f"Loaded Parquet s3://{bucket}/{key} | Shape: {df.shape}")
            return df

        except self.s3_client.exceptions.NoSuchKey:
            self.logger.warning(f"Parquet object not found: s3://{bucket}/{key}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load Parquet s3://{bucket}/{key}: {e}")
            return None

    def save_json_data(self, bucket: str, key: str, data: Any) -> bool:
        """Serializes data to JSON and uploads to S3 bucket."""
        try:
            json_data = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            self.s3_client.put_object(Bucket=bucket,
                                      Key=key,
                                      Body=json_data.encode('utf-8'),
                                      ContentType='application/json')

            self.logger.debug(f"Saved to s3://{bucket}/{key}")
            return True

        except ClientError as e:
            self.logger.error(f"S3 write failed for s3://{bucket}/{key}: {e}")
            return False

    def load_json_data(self, bucket: str, key: str) -> Optional[Dict[Any, Any]]:
        """Loads and parses JSON from S3."""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')

            if response.get('ContentEncoding') == 'gzip':
                import gzip
                content = gzip.decompress(content.encode('utf-8')).decode('utf-8')

            data = json.loads(content)

            self.logger.debug(f"Loaded s3://{bucket}/{key}")
            return cast(Dict[Any, Any], data)

        except self.s3_client.exceptions.NoSuchKey:
            self.logger.debug(f"Object not found: s3://{bucket}/{key}")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to load s3://{bucket}/{key}: {e}")
            return None
    def object_exists(self, bucket: str, key: str) -> bool:
        """Checks if an object exists in S3."""
        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
    def list_objects(self, bucket: str, prefix: str) -> Dict[Any, Any]:
        """Lists all objects under a given prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

            count = len(response.get('Contents', []))
            self.logger.debug(f"Found {count} objects in s3://{bucket}/{prefix}")
            return cast(Dict[Any, Any], response)

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                self.logger.warning(f"Bucket does not exist: s3://{bucket}/")
                return {}
            self.logger.error(f"Failed to list objects in s3://{bucket}/{prefix}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to list objects in s3://{bucket}/{prefix}: {e}")
            return {}
    def delete_object(self, bucket: str, key: str) -> bool:
        """Deletes an object from S3."""
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            self.logger.debug(f"Deleted s3://{bucket}/{key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete s3://{bucket}/{key}: {e}")
            return False