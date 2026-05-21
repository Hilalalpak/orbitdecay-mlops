from src.domain.weather.feature_synthesis.metrics.phase6_telemetry import SynthesisMergeResult
from structlog.stdlib import BoundLogger
from src.domain.weather.feature_synthesis.multi_source_merger import EnvironmentDataMerger

class SynthesisExecutor:
    def __init__(self, environment_merger: EnvironmentDataMerger, logger: BoundLogger) -> None:
        self.merger = environment_merger
        self.logger = logger

    def is_ready(self) -> bool:
        if not self.merger:
            self.logger.warning("merger_missing", component="EnvironmentDataMerger")
            return False
        return True

    def execute_merge(self) -> SynthesisMergeResult:
        """Executes the merge process using the injected merger."""
        self.logger.info("synthesis_started", reason="cache_miss_or_stale")
        return self.merger.merge_all_datasets()