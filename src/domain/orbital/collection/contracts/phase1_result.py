
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class Phase1FailureReason(str, Enum):
    """Enum of failure reasons for Phase 1 diagnostics."""
    NO_SATELLITES = "no_satellites_available"
    NO_DATA_RETRIEVED = "no_data_retrieved"
    MANIFEST_CREATION_FAILED = "manifest_creation_failed"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    STRATEGY_EXECUTION_FAILED = "strategy_execution_failed"
    CACHE_ERROR = "cache_error"
    UNKNOWN_ERROR = "unknown_error"


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



