import polars as pl
import os
from sqlalchemy import create_engine, text
from typing import List

class TimeSeriesStorage:
    def __init__(self, pipeline_config, storage_adapter, logger) -> None:
        self.pipeline_config = pipeline_config
        self.storage = storage_adapter
        self.logger = logger
        self.feature_store_table = "ml_training_data"
        self.db_engine = self._init_db_engine()

    def _init_db_engine(self):
        db_url = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:5432/{os.getenv('POSTGRES_DB')}"
        return create_engine(
            db_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_timeout=60)

    def load_space_weather_data(self) -> pl.DataFrame:
        bucket = self.pipeline_config.get_s3_bucket("env_data")
        key = "featured/unified_synthesis_data_latest.parquet"
        buffer = self.storage.load_parquet(bucket, key)
        return pl.read_parquet(buffer) if buffer else pl.DataFrame()

    def list_active_latest_paths(self):
        bucket = self.pipeline_config.get_s3_bucket("orbit-data")
        prefix = f"{self.pipeline_config.get_s3_prefix('omm_leo')}/active/"
        response = self.storage.list_objects(bucket, prefix)
        return [obj["Key"] for obj in response.get("Contents", []) if "orbital_history_latest.parquet" in obj["Key"]]

    def list_decayed_latest_paths(self):
        bucket = self.pipeline_config.get_s3_bucket("orbit-data")
        prefix = f"{self.pipeline_config.get_s3_prefix('omm_leo')}/decayed/"
        response = self.storage.list_objects(bucket, prefix)
        return [obj["Key"] for obj in response.get("Contents", []) if "enhanced_latest.parquet" in obj["Key"]]


    def get_satellite_list(self) -> List[str]:
        """Scans all recursive paths in S3."""
        bucket = self.pipeline_config.get_s3_bucket("orbit-data")
        prefix = f"{self.pipeline_config.get_s3_prefix('omm_leo')}/"
        response = self.storage.list_objects(bucket, prefix)
        return [obj["Key"] for obj in response.get("Contents", []) if "enhanced_latest.parquet" in obj["Key"]]

    def load_satellite_orbital_data(self, key: str) -> pl.DataFrame:
        bucket = self.pipeline_config.get_s3_bucket("orbit-data")
        buffer = self.storage.load_parquet(bucket, key)
        return pl.read_parquet(buffer) if buffer else pl.DataFrame()

    def get_max_epoch(self, norad_cat_id: str):
        """Returns the max epoch stored in DB for this satellite, or None if not present."""
        if self.db_engine is None:
            return None
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT MAX(epoch) FROM {self.feature_store_table} WHERE norad_cat_id = :nid"),
                    {"nid": norad_cat_id}
                ).scalar()
            return result
        except Exception:
            return None

    def save_satellite_timeseries(self, df: pl.DataFrame) -> bool:
        if self.db_engine is None or df.is_empty(): return False
        try:
            pdf = df.to_pandas()
            with self.db_engine.begin() as conn:
                tmp_table = f"{self.feature_store_table}_tmp"
                pdf.to_sql(tmp_table, con=conn, if_exists="replace", index=False, method="multi", chunksize=500)
                cols = ", ".join(pdf.columns.tolist())
                conn.execute(text(
                    f"INSERT INTO {self.feature_store_table} ({cols}) "
                    f"SELECT {cols} FROM {tmp_table} "
                    f"ON CONFLICT (norad_cat_id, epoch) DO NOTHING"
                ))
                conn.execute(text(f"DROP TABLE IF EXISTS {tmp_table}"))
            return True
        except Exception as e:
            self.logger.error(f"DB Error: {e}")
            return False

    def verify_integrity(self, expected_count: int) -> bool:
        """
        Checkpoint validation step:
        Verifies that the expected number of satellites has been processed in the database.
        """
        if self.db_engine is None:
            return False

        try:
            from sqlalchemy import text

            # Count unique satellites (satellites_processed) in the table
            query = text(f"SELECT COUNT(DISTINCT norad_cat_id) FROM {self.feature_store_table}")

            with self.db_engine.connect() as conn:
                actual_count = conn.execute(query).scalar()

            # Check if data exists in DB and the expected count has been reached
            if actual_count and actual_count >= expected_count:
                self.logger.info(
                    f"Integrity Check OK: {actual_count} satellites in database (Expected: {expected_count}).")
                return True
            else:
                self.logger.warning(
                    f"Integrity Check FAILED: {actual_count} satellites in DB, but checkpoint expected {expected_count}.")
                return False

        except Exception as e:
            self.logger.error(f"Error during database integrity check: {e}")
            # Return False to reprocess data if table is missing or an error occurs
            return False