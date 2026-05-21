"""Internal telemetry models for Phase 6 (Environmental Data Synthesis)."""

from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class SynthesisCheckpointResult(BaseModel):
    """Returned when Phase 6 checkpoint exists and synthesis is skipped."""
    model_config = ConfigDict(frozen=True)
    unified_records: int = 0
    checkpoint_age_days: float = 0.0
    meta_data: Optional[Any] = None


class SynthesisMergeResult(BaseModel):
    """Result of the active merge operation."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    success: bool
    data: Any = None
    record_count: int = 0
    feature_count: int = 0
    message: Optional[str] = None
