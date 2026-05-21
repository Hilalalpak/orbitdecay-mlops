from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.metadata.contracts.data_freshness import DataSourceFreshness
from src.pipeline.metadata.data_lineage.repository import DataLineageRepository


class DataLineageService:

    def __init__(self, repository: DataLineageRepository):
        self.repository = repository

    def record_dataset(self, meta: DatasetMetadata) -> None:
        self.repository.insert_dataset_metadata(meta)

    def record_collection_execution(self, record: RunHistory) -> None:
        self.repository.insert_run_history(record)

    def get_history_by_hash(self, param_hash: str, phase: str,
                             source_id: Optional[str] = None) -> Dict[str, Any]:
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
            last_collected = datetime.fromisoformat(
                timestamp_str.replace("Z", "+00:00"))
            age_days = (datetime.now() - last_collected).days
        except (ValueError, AttributeError):
            return {"found_duplicate": False}

        return {
            "found_duplicate": True,
            "last_collected": timestamp_str,
            "age_days": age_days,
            "filter_params": row.get("filter_params", {}),
            "manifest_files": row.get("manifest_files", []),
            "execution_details": row.get("execution_details", {}),
        }

    def record_source_fetch(self, source_id: str, fetched_at: datetime,
                             run_id: Optional[UUID] = None,
                             record_count: Optional[int] = None,
                             success: bool = True,
                             age_before_sec: Optional[int] = None,
                             error: Optional[str] = None) -> None:
        record = DataSourceFreshness(
            run_id=run_id,
            source_id=source_id,
            fetched_at=fetched_at,
            record_count=record_count,
            success=success,
            age_before_sec=age_before_sec,
            error=error,
        )
        self.repository.insert_data_source_freshness(record)

    def get_source_freshness(self, source_id: str) -> Dict[str, Any]:
        return self.repository.get_latest_source_freshness(source_id) or {}
