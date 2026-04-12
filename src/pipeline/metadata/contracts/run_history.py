"""
Pydantic model for a run_history row. Used to detect duplicate runs
and serve cached results when the same parameters are re-submitted.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class RunHistory(BaseModel):
    phase: str
    param_hash: str
    source_id: Optional[str] = None
    filter_params: Dict[str, Any]
    manifest_files: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
