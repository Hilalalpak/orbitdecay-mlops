"""Public contract for Phase 5 (Environmental Data Processing)."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from src.pipeline.contracts.execution_lifecycle import ExecutionStatus
from src.shared.enums.failure_enums import Phase5FailureReason
from src.domain.weather.processing.metrics.phase5_telemetry import Phase5ExecutionStats


class EnvProcessingResult(BaseModel):
    """The official contract returned by Phase 5 to the Pipeline Executor."""
    model_config = ConfigDict(frozen=True)

    success: bool
    execution_status: ExecutionStatus
    execution_time: float = 0.0

    total_requested: int
    processed_count: int
    skipped_count: int
    failure_count: int

    produced_manifest: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    failure_reason: Optional[Phase5FailureReason] = None

    @classmethod
    def from_execution_stats(cls,
                             stats: Phase5ExecutionStats,
                             failure_reason: Optional[Phase5FailureReason] = None) -> "EnvProcessingResult":
        """Factory method to convert internal stats to public result."""
        return cls(
            success=stats.execution_status in (ExecutionStatus.COMPLETED, ExecutionStatus.SKIPPED),
            execution_status=stats.execution_status,
            execution_time=stats.execution_time,
            total_requested=stats.sources_total,
            processed_count=stats.sources_successful - stats.sources_skipped,
            skipped_count=stats.sources_skipped,
            failure_count=stats.sources_failed,
            produced_manifest=stats.produced_manifest,
            failures=stats.failed_sources,
            failure_reason=failure_reason)

    @classmethod
    def failure(cls, reason: Phase5FailureReason, total_sources: int = 0) -> "EnvProcessingResult":
        """Quick failure helper for pre-run errors (like empty manifest)."""
        return cls(
            success=False,
            execution_status=ExecutionStatus.FAILED,
            total_requested=total_sources,
            processed_count=0,
            skipped_count=0,
            failure_count=total_sources,
            failure_reason=reason)
