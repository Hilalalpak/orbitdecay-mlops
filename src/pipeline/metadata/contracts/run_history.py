from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class RunHistory(BaseModel):
    phase: str
    param_hash: str
    source_id: Optional[str] = None

    filter_params: Dict[str, Any]

    manifest_files: List[str] = []

    created_at: Optional[datetime] = None

    extra_metadata: Dict[str, Any] = {}