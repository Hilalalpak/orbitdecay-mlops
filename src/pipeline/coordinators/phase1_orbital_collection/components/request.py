"""
ExecutionRequest factory for Phase 1.
Isolates coordinator from global pipeline config details.
"""

from typing import List
from structlog.stdlib import BoundLogger

from src.shared import ExecutionRequest
from src.shared.config.config_models import PipelineConfigModel


class RequestBuilder:
    """Factory for creating ExecutionRequest objects with config and satellite targets."""

    def __init__(self,
                 pipeline_config: PipelineConfigModel,
                 logger: BoundLogger) -> None:
        self.pipeline_config = pipeline_config
        self.logger = logger

    def build(self,
              target_satellites: List[str],
              active_ids: List[str]) -> ExecutionRequest:
        """
        Creates ExecutionRequest by merging satellite lists with pipeline config.
        Returns immutable request object with traceable hash.
        """
        req = ExecutionRequest.from_config(
            pipeline_config=self.pipeline_config,
            input_data_type="orbital_raw",
            source="space-track",
            processing_stage="orbital_collection",
            satellite_ids=target_satellites,
            active_ids=active_ids)

        self.logger.debug(
            "execution_request_built",
            target_count=len(req.satellite_ids),
            active_count=len(req.active_ids or []),
            param_hash=req.hash[:8])

        return req