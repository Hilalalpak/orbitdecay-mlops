from typing import Dict, Optional, List, Any
from datetime import datetime

from src.shared.config.config_interfaces import MonitoringConfigInterface
from structlog.stdlib import BoundLogger
from src.shared.quota.quota_policy import QuotaPolicy
from src.shared.quota.state_store import QuotaStateStore

class ApiQuotaManager:
    """
    Manages Space-Track API daily/hourly limits to avoid getting banned.
    We have a 1000 request/day limit - exceed it and we're locked out.
    Tracks every API call, monitors hourly/daily limits, and warns when we're getting close.
    Stops everything if we hit critical levels.
    """

    def __init__(self,
                 max_daily_request: int,
                 batch_size: int,
                 monitoring_config: MonitoringConfigInterface,
                 logger: BoundLogger,
                 quota_state_store: QuotaStateStore,
                 quota_policy: QuotaPolicy) -> None:

        self.monitoring_cfg = monitoring_config
        self.logger = logger

        self.state_store = quota_state_store
        self.policy = quota_policy

        # Configuration
        self.max_req = max_daily_request
        self.batch_size = batch_size

        # State
        self.daily_counter = self.state_store.load_counter()
        self.pending_requests: List[Dict[str, Any]] = []
        self.last_save_time = datetime.now()

    def _save_state(self):
        """Saves quota state to S3. Persists every 5 requests or 5 minutes.
        Alerts if usage exceeds 80% (warning) or 95% (critical)."""
        if not self.pending_requests:
            return

        # Save to storage
        success = self.state_store.save_counter(self.daily_counter)

        if success:
            # Monitoring alerts
            current_count = self.daily_counter['total_requests']
            usage_pct = (current_count / self.max_req) * 100

            if usage_pct > self.monitoring_cfg.get_compliance_daily_critical() * 100:
                self.logger.critical("quota_critical", usage_pct=round(usage_pct, 1), requests=current_count)
            elif usage_pct > self.monitoring_cfg.get_compliance_daily_warning() * 100:
                self.logger.warning("quota_warning", usage_pct=round(usage_pct, 1))
            else:
                self.logger.debug("quota_synced", usage_pct=round(usage_pct, 1))

        # Clear pending
        self.pending_requests = []
        self.last_save_time = datetime.now()

    def record_request(self, request_type: str = 'api_call', resource_id: Optional[str] = None) -> None:
        """Call this for every API request. Increments daily/hourly counters.
        Keeps last 100 requests in history to detect burst patterns.
        Auto-saves to S3 every 5 requests or 5 minutes."""
        current_hour = datetime.now().strftime('%H')

        self.daily_counter['total_requests'] += 1
        self.daily_counter['hourly_requests'][current_hour] = self.daily_counter['hourly_requests'].get(current_hour, 0) + 1

        record = {'timestamp': datetime.now().isoformat(),
                  'request_type': request_type,
                  'resource_id': resource_id,
                  'hour': current_hour}

        self.daily_counter['request_history'].append(record)
        self.daily_counter['request_history'] = self.daily_counter['request_history'][-100:]

        self.pending_requests.append(record)

        if len(self.pending_requests) == 1:
            self.logger.debug("request_recorded", type=request_type)

        time_since_save = (datetime.now() - self.last_save_time).total_seconds()

        # TODO: Hardcoded to 5 for small batches - prevents data loss on shutdown.
        # Should be configurable when we have time to refactor this.
        if len(self.pending_requests) >= 5 or time_since_save > 300:
            self._save_state()

    def __del__(self):
        """Emergency flush on shutdown. Saves any pending requests so we don't lose count."""
        if hasattr(self, 'pending_requests') and self.pending_requests:
            self.logger.warning("shutdown_flush", pending=len(self.pending_requests))
            self._save_state()

    def check_availability(self) -> Dict:
        """Check if we can make another API request.
        Validates against daily, hourly, and burst limits all at once."""
        return self.policy.check_availability(self.daily_counter)
    def get_status(self) -> Dict:
        """Current quota usage snapshot. Shows percentage used, remaining quota, hourly status.
        Used for dashboards and monitoring."""
        return self.policy.get_status(self.daily_counter)
    def calc_delay(self, status: str) -> float:
        """Calculates delay between requests when quota is getting full.
        Slows down for 'warning', even slower for 'critical' status."""
        return self.policy.calc_delay(status)

