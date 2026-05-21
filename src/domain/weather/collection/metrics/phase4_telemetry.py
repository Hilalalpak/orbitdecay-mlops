"""Internal telemetry models for Phase 4 (Environmental Data Collection)."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus, ExecutionMode


class BaseSourceResult(BaseModel):
    """Base contract for all per-source collection outcomes in Phase 4."""
    model_config = ConfigDict(frozen=True)

    source_id: str
    success: bool
    mode: ExecutionMode
    file_path: Optional[str] = None
    api_call_made: bool = False


class SourceCollectionResult(BaseSourceResult):
    """Returned when fresh data is fetched from the API."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    mode: ExecutionMode = ExecutionMode.RUN
    data_hash: Optional[str] = None


class CachedSourceResult(BaseSourceResult):
    """Returned when source is served from checkpoint (REUSE mode)."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    mode: ExecutionMode = ExecutionMode.REUSE
    success: bool = True


class Phase4ExecutionStats(BaseModel):
    """Internal execution statistics (NOT returned directly)."""
    model_config = ConfigDict(frozen=True)

    execution_status: ExecutionStatus
    execution_time: float = Field(..., ge=0.0)

    sources_total: int
    sources_successful: int
    sources_failed: int

    produced_manifest: List[str] = Field(default_factory=list)

    cached_sources: int = 0
    fresh_sources: int = 0

    api_calls_made: int = 0
    quota_exceeded: bool = False
