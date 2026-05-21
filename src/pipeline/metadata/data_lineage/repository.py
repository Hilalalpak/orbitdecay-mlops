import json
from typing import Dict, Optional
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.metadata.contracts.data_freshness import DataSourceFreshness


class DataLineageRepository:

    def __init__(self, connection):
        self.connection = connection

    def insert_dataset_metadata(self, meta: DatasetMetadata) -> None:
        query = """
        INSERT INTO dataset_metadata
        (pipeline_run_id, phase_id, output_data_type, artifact_name, version,
         base_path, manifest_files, record_count, status, execution_mode, decision_reason)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(meta.pipeline_run_id),
                meta.phase_id,
                meta.output_data_type,
                meta.artifact_name,
                meta.version,
                meta.base_path,
                meta.manifest_files,
                meta.record_count,
                meta.status.value,
                meta.execution_mode.value,
                meta.decision_reason.value,
            ))
        self.connection.commit()

    def insert_run_history(self, record: RunHistory) -> None:
        query = """
        INSERT INTO run_history
        (phase, source_id, param_hash, filter_params, manifest_files, extra_metadata)
        VALUES (%s,%s,%s,%s,%s,%s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                record.phase,
                record.source_id,
                record.param_hash,
                json.dumps(record.filter_params),
                record.manifest_files,
                json.dumps(record.extra_metadata)))
        self.connection.commit()

    def get_run_history(self, param_hash: str) -> Optional[Dict]:
        query = """
        SELECT param_hash, filter_params, manifest_files, created_at
        FROM run_history
        WHERE param_hash=%s
        ORDER BY created_at DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (param_hash,))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "param_hash": row[0],
            "filter_params": row[1],
            "manifest_files": row[2],
            "timestamp": row[3],
        }

    def get_latest_run_history(self, param_hash: str, phase: str,
                                source_id: Optional[str] = None) -> Optional[Dict]:
        query = """
        SELECT param_hash, filter_params, manifest_files,
               created_at, extra_metadata
        FROM run_history
        WHERE param_hash = %s
          AND phase = %s
          AND (%s IS NULL OR source_id = %s)
        ORDER BY created_at DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (param_hash, phase, source_id, source_id))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "param_hash": row[0],
            "filter_params": row[1],
            "manifest_files": row[2],
            "timestamp": row[3].isoformat() if row[3] else None,
            "execution_details": row[4] or {},
        }

    def insert_data_source_freshness(self, record: DataSourceFreshness) -> None:
        query = """
        INSERT INTO data_source_freshness
        (run_id, source_id, fetched_at, record_count, success, age_before_sec, error)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(record.run_id) if record.run_id else None,
                record.source_id,
                record.fetched_at,
                record.record_count,
                record.success,
                record.age_before_sec,
                record.error,
            ))
        self.connection.commit()

    def get_latest_source_freshness(self, source_id: str) -> Optional[Dict]:
        query = """
        SELECT source_id, fetched_at, record_count, success, age_before_sec
        FROM data_source_freshness
        WHERE source_id = %s
        ORDER BY fetched_at DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (source_id,))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "source_id": row[0],
            "fetched_at": row[1].isoformat() if row[1] else None,
            "record_count": row[2],
            "success": row[3],
            "age_before_sec": row[4],
        }
