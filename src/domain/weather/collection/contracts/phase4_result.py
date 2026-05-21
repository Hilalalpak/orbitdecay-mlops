"""Public contract for Phase 4 (Environmental Data Collection)."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.shared.enums.failure_enums import Phase4FailureReason


class Phase4Result(BaseModel):
    """Public contract returned by Phase 4 to the Pipeline Executor."""
    model_config = ConfigDict(frozen=True)

    success: bool
    execution_status: ExecutionStatus

    execution_time: float = Field(default=0.0)

    produced_manifest: List[str] = Field(default_factory=list)
    reason: Optional[Phase4FailureReason] = None
