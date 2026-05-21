
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.shared.enums.failure_enums import Phase1FailureReason


class Phase1Result(BaseModel):
    """Phase 1 execution result contract."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    success: bool
    execution_time: float

    # Success fields
    satellites_processed: int = 0
    processing_manifest: List[str] = Field(default_factory=list)
    collection_hash: Optional[str] = None
    is_incremental: bool = False

    success_rate: float = 0.0

    # Failure fields
    processing_failures: int = 0
    reason: Optional[Phase1FailureReason] = None
    error_message: Optional[str] = None



