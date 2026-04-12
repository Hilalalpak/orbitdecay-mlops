"""
This module defines how we package and report errors when things go wrong, ensuring
the pipeline fails gracefully with clear diagnostic information.
"""
from structlog.stdlib import BoundLogger
from src.domains.schemas.orbital_collection_schema import Phase1Result

class ErrorPolicy:
    def __init__(self, logger: BoundLogger, execution_mode: str) -> None:
        self.logger = logger
        self.exec_mode = execution_mode

    def format(self, error, phase_duration) -> Phase1Result:
        """Constructs a standardized dictionary containing error details and execution stats to be returned when the pipeline fails."""
        self.logger.error(f"Phase 1 (Collection) FAILED after {phase_duration:.2f}s: {str(error)}",exc_info=True)
        return Phase1Result(
            success=False,
            execution_time=phase_duration,
            exec_mode=self.exec_mode,
            satellites_processed=0,
            processing_failures=0,
            reason=f"exception_{type(error).__name__}",
            error_message=str(error))
