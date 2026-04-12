# src/pipeline/coordinators/phase2_orbital_processing/components/checkpoint_handler.py

"""
Handles checkpoint validation and batch loading for Phase 2 orbital processing.
"""

from typing import Dict, Any, Optional, List

from src.core.checkpoint_manager import ComputationCheckpointManager

from structlog.stdlib import BoundLogger
from src.domains.schemas.orbital_processing_schema import Phase2Result
from src.pipeline.coordinators.phase2_orbital_processing.components.batch_data_loader import BatchDataLoader
from src.pipeline.utilities.execution_request import ExecutionRequest

class CheckpointHandler:
    """
    Manages checkpoint checks and batch data loading for orbital processing phase.
    """

    def __init__(self,
                 checkpoint_manager: ComputationCheckpointManager,
                 batch_data_loader: BatchDataLoader,
                 logger: BoundLogger) -> None:

        self.checkpoint = checkpoint_manager
        self.batch_loader = batch_data_loader
        self.logger = logger

    def load_batch_data(self, batch_file: str) -> Optional[List[Dict]]:
        """Load batch file from Phase 1 cache."""
        try:
            return self.batch_loader.load_batch_file(batch_file)

        except Exception as e:
            self.logger.error(f"Error loading batch '{batch_file}': {e}")
            return None

    def check_and_maybe_skip(self, request: ExecutionRequest) -> Optional[Phase2Result]:
        """Check if checkpoint exists and return cached stats if processing can be skipped."""
        result = self.checkpoint.check_checkpoint(request)

        if not result.should_run:
            self.logger.info(f"Phase 2 skipped using checkpoint (hash={request.hash[:8]})")

            checkpoint_data = result.checkpoint_data
            age_days = 0
            if checkpoint_data is not None:
                age_days = checkpoint_data.get('age_days', 0)

            return Phase2Result(
                successfully_processed=-1,
                processing_failures=0,
                checkpoint_used=True,
                checkpoint_age_days=age_days,
                execution_time=0.0)

        self.logger.debug("No checkpoint found. Processing will run.")
        return None

    def save_checkpoint(self, request, stats: Dict[str, Any]) -> None:
        """Save checkpoint after successful phase execution."""
        try:
            self.checkpoint.mark_completed(request, stats)
            self.logger.debug(f"Checkpoint recorded for hash {request.hash[:8]}")

        except Exception as e:
            self.logger.error(f"Failed to record checkpoint: {e}")
            self.logger.warning("Pipeline continues but checkpoint may be missing.")