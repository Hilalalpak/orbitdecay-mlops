from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class DataSourceFreshness(BaseModel):
    run_id: Optional[UUID] = None
    source_id: str
    fetched_at: datetime
    record_count: Optional[int] = None
    success: bool = True
    age_before_sec: Optional[int] = None
    error: Optional[str] = None
