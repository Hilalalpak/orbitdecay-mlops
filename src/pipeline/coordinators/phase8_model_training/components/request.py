from src.shared import ExecutionRequest
from src.shared.config import PipelineConfigInterface


class TrainingRequestBuilder:

    def __init__(self, pipeline_config: PipelineConfigInterface) -> None:
        self.pipeline_config = pipeline_config

    def build(self) -> ExecutionRequest:
        return ExecutionRequest.from_config(
            pipeline_config=self.pipeline_config,
            input_data_type='timeseries',
            source='model_trainer',
            processing_stage='model_training')
