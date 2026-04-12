from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.domain.orbital.processing.metrics.processing_telemetry import ProcessingExecutionStats
from enum import Enum


class Phase2FailureReason(str, Enum):
    """Known failure reasons for Phase 2 processing."""
    NO_INPUT_DATA = "no_input_data"
    HASH_CREATION_FAILED = "hash_creation_failed"
    PROCESSING_FAILED = "processing_failed"
    UNKNOWN_ERROR = "unknown_error"


class Phase2Result(BaseModel):
    """Phase 2 output contract for pipeline executor."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    success: bool
    execution_status: ExecutionStatus
    request_hash: str

    produced_manifest: List[str] = Field(default_factory=list)
    is_incremental: bool = Field(default=False)

    reason: Optional[Phase2FailureReason] = Field(default=None)


class CheckpointHitResult(BaseModel):
    """Returned when Phase 2 checkpoint exists and processing is skipped."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    execution_status: ExecutionStatus = ExecutionStatus.SKIPPED
    produced_manifest: List[str] = Field(default_factory=list)
    successfully_processed: int = 0


class ProcessingStrategyResult(BaseModel):
    """Phase 2 execution result returned after active processing."""
    model_config = ConfigDict(frozen=True)

    execution_status: ExecutionStatus
    stats: ProcessingExecutionStats
    produced_manifest: List[str] = Field(default_factory=list)
    checkpoint_used: bool = False
    checkpoint_age_days: Optional[float] = None