
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.shared.enums.failure_enums import Phase3FailureReason


class Phase3Result(BaseModel):
    """Phase 3 output contract for pipeline executor."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    success: bool
    execution_status: ExecutionStatus

    request_hash: str
    produced_manifest: List[str] = Field(default_factory=list)
    is_incremental: bool = Field(default=False)

    reason: Optional[Phase3FailureReason] = None

