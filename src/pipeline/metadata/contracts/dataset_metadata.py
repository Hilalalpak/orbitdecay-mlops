"""
Pydantic model for a phase output record written to dataset_metadata.
Captures both the pre-execution decision (mode + reason) and the
post-execution outcome (status, artifact path, record count).
"""

from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional
from src.pipeline.contracts.execution_lifecycle import ExecutionMode, DecisionReason, ExecutionStatus


class DatasetMetadata(BaseModel):
    pipeline_run_id: UUID
    phase_id: str

    # Decided before execution
    execution_mode: ExecutionMode
    decision_reason: DecisionReason

    # Filled in after execution
    status: ExecutionStatus

    output_data_type: str
    artifact_name: str
    version: Optional[str] = None
    base_path: Optional[str] = None
    manifest_files: List[str] = Field(default_factory=list)
    record_count: Optional[int] = None
