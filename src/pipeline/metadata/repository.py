"""
Raw database access for pipeline metadata. Executes INSERT/UPDATE/SELECT
queries against the three metadata tables. No business logic here — all
decisions live in MetadataService.
"""

import psycopg2
import json
from typing import Dict, Optional
from .contracts.pipeline_runs import PipelineRunMetadata
from .contracts.dataset_metadata import DatasetMetadata
from .contracts.run_history import RunHistory


class MetadataRepository:

    def __init__(self, connection):
        self.connection = connection

    def insert_pipeline_run(self, run: PipelineRunMetadata) -> None:
        """Inserts a new pipeline run row with status 'running'."""
        query = """
        INSERT INTO pipeline_runs
            (run_id, pipeline_name, execution_mode, target_date,
             parameters, start_time, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(run.run_id),
                run.pipeline_name,
                run.execution_mode,
                run.target_date,
                json.dumps(run.parameters),
                run.start_time,
                run.status))
        self.connection.commit()

    def finish_pipeline_run(self, run_id, status: str, end_time, error=None) -> None:
        """Updates the run row with final status, end time, and optional error."""
        query = """
        UPDATE pipeline_runs
        SET status = %s, end_time = %s, error_message = %s
        WHERE run_id = %s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (status, end_time, error, str(run_id)))
        self.connection.commit()

    def insert_dataset_metadata(self, meta: DatasetMetadata) -> None:
        """Records phase output metadata after a phase completes."""
        query = """
        INSERT INTO dataset_metadata
            (pipeline_run_id, phase_id, output_data_type, artifact_name,
             version, base_path, manifest_files, record_count,
             status, execution_mode, decision_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                meta.decision_reason.value))
        self.connection.commit()

    def insert_run_history(self, record: RunHistory) -> None:
        """Saves a run history entry used for duplicate/cache detection."""
        query = """
        INSERT INTO run_history
            (phase, source_id, param_hash, filter_params, manifest_files, extra_metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
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
        """Returns the most recent run history row matching param_hash."""
        query = """
        SELECT param_hash, filter_params, manifest_files, created_at
        FROM run_history
        WHERE param_hash = %s
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
                "timestamp": row[3]}

    def get_latest_run_history(
            self,
            param_hash: str,
            phase: str,
            source_id: Optional[str] = None) -> Optional[Dict]:
        """Returns the most recent run history row matching hash, phase, and optional source."""
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
                "execution_details": row[4] or {}}
