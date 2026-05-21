from datetime import datetime, date as _date
from typing import Dict, Optional
from src.shared.quota.quota_snapshot import QuotaDailySnapshot
from src.shared.quota.repository import QuotaRepository


class QuotaService:

    def __init__(self, repository: QuotaRepository):
        self.repository = repository

    def snapshot_quota(
            self,
            total_requests: int,
            remaining: int,
            usage_pct: float,
            peak_hour: Optional[int] = None,
            warning_fired: bool = False,
            critical_fired: bool = False,
            hourly_requests: Optional[dict] = None,
            request_history: Optional[list] = None) -> None:

        record = QuotaDailySnapshot(
            snapshot_date=_date.today(),
            total_requests=total_requests,
            remaining=remaining,
            usage_pct=usage_pct,
            peak_hour=peak_hour,
            warning_fired=warning_fired,
            critical_fired=critical_fired,
            hourly_requests=hourly_requests,
            request_history=request_history,
            last_updated=datetime.utcnow(),
        )
        self.repository.upsert_quota_daily_snapshot(record)

    def load_quota_counter(self) -> Optional[Dict]:
        return self.repository.load_quota_counter(_date.today())
