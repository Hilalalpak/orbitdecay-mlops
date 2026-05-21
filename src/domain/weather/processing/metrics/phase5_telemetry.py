"""Internal telemetry models for Phase 5 (Environmental Data Processing)."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus, ExecutionMode
from src.shared.enums.failure_enums import Phase5FailureReason


class SourceProcessingResult(BaseModel):
    """Result of processing a single source (e.g., solar_flux)."""
    model_config = ConfigDict(frozen=True)

    source_id: str
    success: bool
    mode: Optional[ExecutionMode] = None

    produced_files: List[str] = Field(default_factory=list)
    record_count: int = 0

    failure_reason: Optional[Phase5FailureReason] = None
    error_detail: Optional[str] = None


class Phase5ExecutionStats(BaseModel):
    """Aggregated stats collected during the Coordinator run."""
    model_config = ConfigDict(frozen=True)

    execution_status: ExecutionStatus
    execution_time: float = Field(..., ge=0.0)

    sources_total: int
    sources_successful: int
    sources_skipped: int
    sources_failed: int

    produced_manifest: List[str] = Field(default_factory=list)
    failed_sources: List[str] = Field(default_factory=list)
