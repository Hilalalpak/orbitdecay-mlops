
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.pipeline.contracts.execution_lifecycle import ExecutionStatus


class CheckpointHitResult(BaseModel):
    """Returned when Phase 3 checkpoint exists and processing is skipped."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    execution_status: ExecutionStatus = ExecutionStatus.SKIPPED
    produced_manifest: List[str] = Field(default_factory=list)
    successfully_processed: int = 0


class FeatureGenerationStats(BaseModel):
    """Execution statistics from OrbitalFeatureGenerator domain layer."""
    model_config = ConfigDict(frozen=True)

    satellites_total: int = Field(default=0, ge=0)
    successfully_processed: int = Field(default=0, ge=0)
    processing_failures: int = Field(default=0, ge=0)

    high_risk_satellites: int = Field(default=0, ge=0)

    execution_time: float = Field(default=0.0, ge=0.0)
    workers_utilized: int = Field(default=0, ge=0)


class FeatureStrategyResult(BaseModel):
    """Phase 3 execution result returned after active processing."""
    model_config = ConfigDict(frozen=True)

    execution_status: ExecutionStatus

    stats: FeatureGenerationStats

    produced_manifest: List[str] = Field(default_factory=list)

    checkpoint_used: bool = False
    checkpoint_age_days: Optional[float] = None