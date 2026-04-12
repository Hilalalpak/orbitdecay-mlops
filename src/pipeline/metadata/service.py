"""
Business logic layer for pipeline metadata. Builds the right contracts
and delegates persistence to MetadataRepository. Callers should use this
instead of touching the repository directly.
"""

from uuid import uuid4
from datetime import datetime
from typing import Dict, Optional, Any
from .contracts.pipeline_runs import PipelineRunMetadata
from .contracts.dataset_metadata import DatasetMetadata
from .contracts.run_history import RunHistory


class MetadataService:

    def __init__(self, repository):
        self.repository = repository

    def start_pipeline_run(
            self,
            pipeline_name: str,
            execution_mode: str,
            target_date: str,
            parameters: Dict[str, Any]):
        """Creates a pipeline_runs row and returns the new run_id."""
        run = PipelineRunMetadata(
            run_id=uuid4(),
            pipeline_name=pipeline_name,
            execution_mode=execution_mode,
            target_date=target_date,
            parameters=parameters,
            start_time=datetime.utcnow(),
            status="running")
        self.repository.insert_pipeline_run(run)
        return run.run_id

    def finish_pipeline_run(self, run_id, status: str, error=None) -> None:
        """Marks the run as finished with a final status and optional error message."""
        self.repository.finish_pipeline_run(
            run_id,
            status,
            datetime.utcnow(),
            error)

    def record_dataset(self, meta: DatasetMetadata) -> None:
        """Persists phase output metadata to dataset_metadata."""
        self.repository.insert_dataset_metadata(meta)

    def record_collection_execution(self, record: RunHistory) -> None:
        """Saves a run history entry for duplicate/cache detection in future runs."""
        self.repository.insert_run_history(record)

    def get_history_by_hash(
            self,
            param_hash: str,
            phase: str,
            source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Looks up the most recent run matching hash + phase. Returns
        found_duplicate=False if nothing found or timestamp is missing.
        """
        row = self.repository.get_latest_run_history(
            param_hash=param_hash,
            phase=phase,
            source_id=source_id)

        if not row:
            return {"found_duplicate": False}

        timestamp_str = row.get("timestamp")
        if not timestamp_str:
            return {"found_duplicate": False}

        try:
            last_collected = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            age_days = (datetime.now() - last_collected).days
        except (ValueError, AttributeError):
            return {"found_duplicate": False}

        return {
            "found_duplicate": True,
            "last_collected": timestamp_str,
            "age_days": age_days,
            "filter_params": row.get("filter_params", {}),
            "manifest_files": row.get("manifest_files", []),
            "execution_details": row.get("execution_details", {})}
