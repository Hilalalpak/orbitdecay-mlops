import json
from typing import Dict, Optional
from src.shared.quota.quota_snapshot import QuotaDailySnapshot


class QuotaRepository:

    def __init__(self, connection):
        self.connection = connection

    def upsert_quota_daily_snapshot(self, record: QuotaDailySnapshot) -> None:
        query = """
        INSERT INTO quota_daily_snapshots
        (snapshot_date, total_requests, remaining, usage_pct,
         peak_hour, warning_fired, critical_fired,
         hourly_requests, request_history, last_updated)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (snapshot_date) DO UPDATE SET
            total_requests  = EXCLUDED.total_requests,
            remaining       = EXCLUDED.remaining,
            usage_pct       = EXCLUDED.usage_pct,
            peak_hour       = COALESCE(EXCLUDED.peak_hour, quota_daily_snapshots.peak_hour),
            warning_fired   = quota_daily_snapshots.warning_fired OR EXCLUDED.warning_fired,
            critical_fired  = quota_daily_snapshots.critical_fired OR EXCLUDED.critical_fired,
            hourly_requests = EXCLUDED.hourly_requests,
            request_history = EXCLUDED.request_history,
            last_updated    = EXCLUDED.last_updated
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                record.snapshot_date,
                record.total_requests,
                record.remaining,
                record.usage_pct,
                record.peak_hour,
                record.warning_fired,
                record.critical_fired,
                json.dumps(record.hourly_requests or {}),
                json.dumps(record.request_history or []),
                record.last_updated,
            ))
        self.connection.commit()

    def load_quota_counter(self, snapshot_date) -> Optional[Dict]:
        query = """
        SELECT snapshot_date, total_requests, remaining, usage_pct,
               peak_hour, warning_fired, critical_fired,
               hourly_requests, request_history, last_updated
        FROM quota_daily_snapshots
        WHERE snapshot_date = %s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (snapshot_date,))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "date": row[0].isoformat(),
            "total_requests": row[1] or 0,
            "remaining": row[2],
            "usage_pct": row[3],
            "peak_hour": row[4],
            "warning_fired": row[5] or False,
            "critical_fired": row[6] or False,
            "hourly_requests": row[7] or {},
            "request_history": row[8] or [],
            "last_updated": row[9].isoformat() if row[9] else None,
        }
