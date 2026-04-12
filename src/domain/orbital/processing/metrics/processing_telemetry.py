"""Phase 2 execution statistics."""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class ProcessingExecutionStats(BaseModel):
    """Execution statistics from the orbital processor."""
    model_config = ConfigDict(frozen=True)

    records_total: int = Field(default=0, ge=0)
    successfully_processed: int = Field(default=0, ge=0)
    processing_failures: int = Field(default=0, ge=0)

    batches_total: int = Field(default=0, ge=0)
    batches_processed: int = Field(default=0, ge=0)

    execution_time: float = Field(default=0.0, ge=0.0)
    workers_utilized: int = Field(default=0, ge=0)

