from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class BatchCollectionStats(BaseModel):
    """Batch collection execution stats."""
    model_config = ConfigDict(frozen=False)

    batch_count: int = Field(..., ge=0)
    total_records: int = Field(..., ge=0)

    success_rate: float = Field(..., ge=0.0, le=100.0)
    failed_batches: List[Dict[str, Any]] = Field(default_factory=list)
    api_calls_made: int = Field(default=0, ge=0)
    collection_duration: float = Field(default=0.0, ge=0)