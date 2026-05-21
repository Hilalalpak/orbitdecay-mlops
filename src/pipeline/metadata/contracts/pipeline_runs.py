from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any


class PipelineRunMetadata(BaseModel):
    run_id: UUID
    pipeline_name: str
    execution_mode: str
    target_date: str
    parameters: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None