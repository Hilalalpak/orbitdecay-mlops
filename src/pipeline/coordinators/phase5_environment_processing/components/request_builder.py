from typing import Optional
from src.shared import ExecutionRequest
from src.shared.config import PipelineConfigInterface
from structlog.stdlib import BoundLogger


class RequestBuilder:
    def __init__(self, pipeline_config: PipelineConfigInterface, logger: BoundLogger, execution_mode: str) -> None:
        self.exec_mode = execution_mode
        self.cfg = pipeline_config
        self.logger = logger

    def create_request(self, source_id: str) -> Optional[ExecutionRequest]:
        """Creates a ExecutionRequest for a given source."""
        try:
            request = ExecutionRequest.from_config(
                pipeline_config=self.cfg,
                input_data_type='weather_raw',
                source=source_id,
                processing_stage='environmental_processing')
            return request
        except Exception as e:
            self.logger.error("env_processing_request_failed", source=source_id, error=str(e))
            return None