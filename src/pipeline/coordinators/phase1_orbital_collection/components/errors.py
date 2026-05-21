"""Error handler for Phase 1 failures."""

from structlog.stdlib import BoundLogger
from src.domain.orbital.collection.contracts.phase1_result import Phase1Result
from src.shared.enums.failure_enums import Phase1FailureReason

class Phase1ErrorHandler:
    """Converts Phase 1 exceptions into structured Phase1Result objects."""

    def __init__(self, logger: BoundLogger) -> None:
        self.logger = logger

    def handle(self, error: Exception, phase_duration: float) -> Phase1Result:
        """Converts exception to Phase1Result with categorized failure reason."""
        self.logger.error("phase1_failed",
                          duration_sec=round(phase_duration, 2),
                          error=str(error),
                          exc_info=True)

        reason = self._determine_reason(error)

        return Phase1Result(
            success=False,
            execution_time=phase_duration,
            satellites_processed=0,
            processing_failures=0,
            reason=reason,
            error_message=str(error))

    def _determine_reason(self, error: Exception) -> Phase1FailureReason:
        from src.shared.quota.quota_manager import QuotaExceededError

        if isinstance(error, QuotaExceededError):
            return Phase1FailureReason.API_QUOTA_EXCEEDED

        if isinstance(error, RuntimeError) and "satellite" in str(error).lower():
            return Phase1FailureReason.NO_SATELLITES

        return Phase1FailureReason.UNKNOWN_ERROR