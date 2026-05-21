from typing import Dict
from datetime import datetime, timedelta
from structlog.stdlib import BoundLogger
from src.shared.config.config_models import PipelineConfigModel

class QuotaPolicy:
    """
    Responsible for business rules: Checking config, calculating delays, and assessing status.
    Pure logic, no storage I/O.
    """
    def __init__(self, pipeline_config: PipelineConfigModel, logger: BoundLogger) -> None:
        self.logger = logger
        self.limits = self._load_limits(pipeline_config)

    def _count_recent(self, daily_counter: Dict, minutes: int = 5) -> int:
        """Calculates request count within last N minutes for burst detection."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return sum((1 for req in daily_counter.get('request_history', []) if
                    datetime.fromisoformat(req.get('timestamp', '')) >= cutoff_time))
    def _load_limits(self, config: PipelineConfigModel) -> Dict:
        """Extracts API limit configuration from pipeline config."""
        return {'max_daily_requests': config.get_space_track_daily_limit(),
                'api_delay': config.get_space_track_api_delay(),
                'hourly_limit': config.get_space_track_hourly_limit(),
                'burst_limit': config.get_space_track_burst_limit()}

    def check_availability(self, daily_counter: Dict) -> Dict:
        """Validates request against all configured config before allowing execution."""
        total = daily_counter['total_requests']
        max_daily = self.limits['max_daily_requests']

        # 1. Daily Limit Check
        if total >= max_daily:
            self.logger.warning("Request blocked: Daily API quota exhausted.")
            return {'allowed': False,
                    'reason': 'daily_limit_exceeded',
                    'current_count': total,
                    'limit': max_daily}

        # 2. Hourly Limit Check
        current_hour = datetime.now().strftime('%H')
        hourly_count = daily_counter['hourly_requests'].get(current_hour, 0)
        hourly_limit = self.limits['hourly_limit']

        if hourly_count >= hourly_limit:
            self.logger.warning(f"Hourly quota exceeded ({hourly_count}/{hourly_limit})")
            return {'allowed': False,
                    'reason': 'hourly_limit_exceeded',
                    'current_count': hourly_count,
                    'limit': hourly_limit}

        # 3. Burst Limit Check
        recent_req = self._count_recent(daily_counter, minutes=5)
        if recent_req >= self.limits['burst_limit']:
            return {'allowed': False,
                    'reason': 'burst_limit_exceeded',
                    'recent_req': recent_req,
                    'burst_limit': self.limits['burst_limit']}

        # 4. Status Calculation
        usage_pct = total / self.limits['max_daily_requests'] * 100
        hourly_usage = hourly_count / self.limits['hourly_limit'] * 100

        if usage_pct > 90 or hourly_usage > 80:
            status = 'critical'
        elif usage_pct > 75 or hourly_usage > 60:
            status = 'warning'
        else:
            status = 'good'

        return {'allowed': True,
                'total': total,
                'remaining_requests': self.limits['max_daily_requests'] - total,
                'usage_percentage': round(usage_pct, 1),
                'hourly_count': hourly_count,
                'status': status}
    def calc_delay(self, status: str) -> float:
        """Calculates adaptive delay based on current system load status."""
        base_delay = self.limits['api_delay']
        if status == 'critical':
            return base_delay * 2.0
        elif status == 'warning':
            return base_delay * 1.5
        return base_delay * 1.0
    def get_status(self, daily_counter: Dict) -> Dict:
        """Generates comprehensive quota usage snapshot for monitoring dashboards."""
        total = daily_counter['total_requests']
        max_daily = self.limits['max_daily_requests']

        usage_pct = total / max_daily * 100
        current_hour = datetime.now().strftime('%H')
        hourly_count = daily_counter['hourly_requests'].get(current_hour, 0)
        hourly_usage = hourly_count / self.limits['hourly_limit'] * 100
        recent_reqs = self._count_recent(daily_counter, minutes=5)

        if usage_pct > 90 or hourly_usage > 80:
            status = 'critical'
        elif usage_pct > 75 or hourly_usage > 60:
            status = 'warning'
        elif usage_pct > 50 or hourly_usage > 40:
            status = 'caution'
        else:
            status = 'good'

        return {'status': status,
                'requests_today': total,
                'daily_limit': max_daily,
                'usage_percentage': round(usage_pct, 1),
                'remaining_requests': max_daily - total,
                'hourly_stats': {'current_hour': current_hour,
                                 'hourly_count': hourly_count,
                                 'hourly_limit': self.limits['hourly_limit'],
                                 'hourly_usage_percentage': round(hourly_usage, 1)},
                'recent_activity': {'last_5_minutes': recent_reqs,
                                    'burst_limit': self.limits['burst_limit']}}

