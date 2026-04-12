"""
Represents a simple, structured description of a processing job. Downstream
components use this to understand what work needs to be done.
"""

from typing import Any, Optional
from structlog.stdlib import BoundLogger
from src.pipeline.utilities.execution_request import ExecutionRequest
from src.configuration.config_models import PipelineConfigModel


class RequestBuilder:

    def __init__(self, pipeline_config: PipelineConfigModel, logger: BoundLogger, execution_mode: str) -> None:
        self.cfg = pipeline_config
        self.execution_mode = execution_mode
        self.logger = logger

    def build_request(self, collection_hash: str) -> Optional[Any]:
        """Build and return a request object."""

        try:
            request = ExecutionRequest.from_config(
                pipeline_config=self.cfg,
                satellite_ids=[],
                execution_mode=self.execution_mode,
                data_type='orbital_processing',
                source=collection_hash)

            request.hash = f"{request.hash}_process_v1"
            return request

        except Exception as e:
            self.logger.error(f"Failed to create Phase 2 request: {e}")
            return None