from enum import Enum
from pydantic import BaseModel
from typing import Optional

#######
# BEFORE
#######
class ExecutionMode(str, Enum):
    """
    BEFORE execution: Intent/Strategy for how the phase will run.

    This represents the PLAN - what we intend to do before starting.
    """
    RUN = "run"  # Normal execution
    REUSE = "reuse_artifact"  # Use cached result, skip processing
    INCREMENTAL = "incremental"  # Process only new/delta data
    FORCED = "forced_run"  # Override cache, force execution


class DecisionReason(str, Enum):
    """
    BEFORE execution: Why this ExecutionMode was chosen.

    This explains the RATIONALE behind the mode selection.
    """
    CACHE_HIT = "cache_hit"  # Valid cache exists, can reuse
    CHECKPOINT_EXISTS = "checkpoint_exists"  # Previous checkpoint found
    DATA_FRESH = "data_fresh"  # Existing data is fresh enough
    FORCE_REFRESH = "force_refresh"  # User/API forced reprocessing
    INITIAL_RUN = "initial_run"  # First time, no previous state
    DATA_STALE = "data_stale"


class ExecutionDecision(BaseModel):
    """
    BEFORE execution: Container for the execution decision.

    Combines Mode (what we'll do) + Reason (why) + Input metadata.
    This is immutable once created - it records the intent.
    """
    mode: ExecutionMode  # How we plan to execute
    reason: DecisionReason  # Why we chose this mode

    param_hash: str  # Input parameters fingerprint
    produced_manifest: Optional[list[str]] = None  # Expected/actual outputs


#######
# AFTER
#######
class ExecutionStatus(str, Enum):
    """
    AFTER execution: The actual outcome/result of the phase.

    This represents the REALITY - what actually happened after running.
    This is the only model that changes based on execution result.
    """
    COMPLETED = "completed"  # Successfully finished all work
    SKIPPED = "skipped"  # No work done (cache/checkpoint hit)
    FAILED = "failed"  # Total failure, no usable output
    PARTIAL_SUCCESS = "partial_success"  # Some items succeeded, some failed
    CANCELLED = "cancelled"  # Externally interrupted (quota/user)


