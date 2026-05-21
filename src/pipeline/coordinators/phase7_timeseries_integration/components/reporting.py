
from structlog.stdlib import BoundLogger
from src.pipeline.monitoring.performance_monitor import PerformanceMonitor
from typing import Dict, Union

class TimeseriesReportingHandler:
    def __init__(self, performance_monitor: PerformanceMonitor, logger: BoundLogger) -> None:

        self.performance_monitor = performance_monitor
        self.logger = logger

    def update_metrics(self, phase_duration: float) -> Dict[str, Union[bool, str]]:
        self.performance_monitor.performance_metrics['processing_time_saved'] += max(0.0, 120.0 - phase_duration)

        current_metrics = self.performance_monitor.get_current_metrics()
        self.logger.debug("metrics_updated", time_saved=round(current_metrics['processing_time_saved'], 1), efficiency_ratio=round(current_metrics['data_efficiency_ratio'], 3))

        return self.performance_monitor.get_timeseries_metrics()