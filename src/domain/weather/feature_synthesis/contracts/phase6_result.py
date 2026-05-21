"""Public contract for Phase 6 (Environmental Data Synthesis)."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionMode


class Phase6Result(BaseModel):
    """Public contract returned by Phase 6 to the Pipeline Executor."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    success: bool
    processing_stage: Literal['environmental_data_synthesis'] = 'environmental_data_synthesis'
    execution_time: float = Field(ge=0.0, description="Seconds")

    action: ExecutionMode

    unified_records: int = Field(default=0, ge=0)
    feature_count: int = Field(default=0, ge=0)

    reason: Optional[str] = None
