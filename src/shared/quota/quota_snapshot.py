from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class QuotaDailySnapshot(BaseModel):
    snapshot_date: date
    total_requests: Optional[int] = None
    remaining: Optional[int] = None
    usage_pct: Optional[float] = None
    peak_hour: Optional[int] = None
    warning_fired: bool = False
    critical_fired: bool = False
    hourly_requests: Optional[dict] = None
    request_history: Optional[list] = None
    last_updated: Optional[datetime] = None
