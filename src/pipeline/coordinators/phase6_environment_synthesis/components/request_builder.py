from typing import Dict, Any, Optional, List
from src.shared import ExecutionRequest
from src.shared.utils.hashing_service import HashingService
from src.shared.config import PipelineConfigInterface
from structlog.stdlib import BoundLogger

class SynthesisRequestBuilder:
    def __init__(self, pipeline_config: PipelineConfigInterface,logger: BoundLogger) -> None:
        self.pipeline_cfg = pipeline_config
        self.logger = logger

    def create_request(self, available_sources: List[str]) -> Optional[ExecutionRequest]:
        """Creates the ExecutionRequest for synthesis."""
        try:
            req = ExecutionRequest.from_config(
                pipeline_config=self.pipeline_cfg,
                input_data_type='weather_cleaned',
                source='weather_synthesizer',
                processing_stage='environmental_synthesis')

            sorted_sources = sorted(available_sources)
            req.parameters['input_sources'] = sorted_sources
            return req
        except Exception as e:
            self.logger.error("synthesis_request_failed", error=str(e))
            return None

    def _get_data_signature(self, processed_datasets: Dict[str, Any]) -> str:
        """Generates a hash signature for the processed datasets."""
        return HashingService.for_data_signature(processed_datasets)