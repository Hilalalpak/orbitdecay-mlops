from typing import Dict
from datetime import datetime
from structlog.stdlib import BoundLogger
from src.shared.quota.service import QuotaService


class QuotaStateStore:
    """
    Handles persistence of API usage counters.
    Pure storage operations without business logic.
    """

    def __init__(self, quota_service: QuotaService, max_daily_requests: int, logger: BoundLogger) -> None:
        self.quota_service = quota_service
        self.max_daily_requests = max_daily_requests
        self.logger = logger

    def _create_empty_counter(self) -> Dict:
        """Creates fresh daily counter structure."""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_requests': 0,
            'hourly_requests': {},
            'request_history': [],
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'storage_backend': 'postgres',
        }

    def load_counter(self) -> Dict:
        """Loads today's counter from PostgreSQL or creates a new one."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            stored = self.quota_service.load_quota_counter()

            if not stored:
                self.logger.info("Starting new daily counter")
                return self._create_empty_counter()

            if stored.get('date') != today:
                self.logger.warning(f"Resetting stale counter from {stored.get('date')}")
                return self._create_empty_counter()

            total = stored['total_requests']
            self.logger.info(f"Daily counter restored: {total} requests used today")
            return stored

        except Exception as e:
            self.logger.error(f"Counter load failed, creating new: {e}")
            return self._create_empty_counter()

    def save_counter(self, daily_counter: Dict) -> bool:
        """Persists counter to PostgreSQL."""
        try:
            daily_counter['last_updated'] = datetime.now().isoformat()

            total = daily_counter.get('total_requests', 0)
            remaining = max(0, self.max_daily_requests - total)
            usage_pct = (total / self.max_daily_requests * 100) if self.max_daily_requests else 0.0

            hourly = daily_counter.get('hourly_requests', {})
            peak_hour = max(hourly, key=lambda h: hourly[h], default=None)
            if peak_hour is not None:
                peak_hour = int(peak_hour)

            self.quota_service.snapshot_quota(
                total_requests=total,
                remaining=remaining,
                usage_pct=round(usage_pct, 2),
                peak_hour=peak_hour,
                hourly_requests=hourly,
                request_history=daily_counter.get('request_history', []),
            )

            self.logger.debug(f"Counter saved to PostgreSQL: {total} requests")
            return True

        except Exception as e:
            self.logger.error(f"Exception during counter save: {e}")
            return False
