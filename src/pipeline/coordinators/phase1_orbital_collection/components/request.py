"""
This script is responsible for assembling the formal request object, combining
configuration settings with the list of target satellites so the coordinator has everything it needs.
"""

from structlog.stdlib import BoundLogger
from src.pipeline.utilities.execution_request import ExecutionRequest
from src.configuration.config_models import PipelineConfigModel
from typing import List


class RequestBuilder:
    def __init__(self, pipeline_cfg: PipelineConfigModel, execution_mode: str, logger: BoundLogger) -> None:
        self.pipeline_cfg = pipeline_cfg
        self.exec_mode = execution_mode
        self.logger = logger

    def build(self, target_satellites: List[int]) -> ExecutionRequest:
        """Creates and configures a new ExecutionRequest instance based on the current pipeline settings and target list."""
        self.logger.info(f"Building collection request for {len(target_satellites)} satellites...")

        req = ExecutionRequest.from_config(
            pipeline_config=self.pipeline_cfg,
            satellite_ids=target_satellites,
            execution_mode=self.exec_mode)

        self.logger.debug(f"Request details: {req.get_summary()}")
        return req