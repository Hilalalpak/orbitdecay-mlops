from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class PhaseExecution(BaseModel):
    run_id: UUID
    phase_name: str
    phase_index: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_sec: Optional[float] = None
    status: Optional[str] = None
    is_incremental: bool = False
    records_in: Optional[int] = None
    records_out: Optional[int] = None
    records_failed: Optional[int] = None
    skip_reason: Optional[str] = None
    error_message: Optional[str] = None
