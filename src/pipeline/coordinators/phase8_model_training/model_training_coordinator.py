import time
from typing import Optional
from uuid import UUID

from src.shared.config import SchedulingConfigInterface
from src.pipeline.contracts.execution_lifecycle import ExecutionMode
from src.pipeline.coordinators.phase8_model_training.components.request import TrainingRequestBuilder
from src.pipeline.coordinators.phase8_model_training.components.checkpoint_handler import TrainingCheckpointHandler
from src.pipeline.coordinators.phase8_model_training.components.data_preparation import TrainingDataPreparer
from src.pipeline.coordinators.phase8_model_training.components.reporting import TrainingReporter
from src.pipeline.coordinators.phase8_model_training.training_runner import TrainingRunner


class ModelTrainingCoordinator:

    def __init__(self,
                 scheduling_config: SchedulingConfigInterface,
                 logger,
                 request_builder: TrainingRequestBuilder,
                 checkpoint_handler: TrainingCheckpointHandler,
                 data_preparer: TrainingDataPreparer,
                 training_runner: TrainingRunner,
                 reporter: TrainingReporter) -> None:

        self.scheduling_config = scheduling_config
        self.logger = logger
        self.request_builder = request_builder
        self.checkpoint_handler = checkpoint_handler
        self.data_preparer = data_preparer
        self.training_runner = training_runner
        self.reporter = reporter

    def run_model_training_phase(self, run_id: Optional[UUID] = None):
        self.logger.info('--- Starting Phase 8 (Model Training) ---')
        phase_timer = time.time()

        if not self.scheduling_config.is_model_training_enabled():
            self.logger.info('Model training disabled. Skipping.')
            return {'success': True, 'skipped': True}

        request = self.request_builder.build()
        decision = self.checkpoint_handler.evaluate(request)
        if decision.mode == ExecutionMode.REUSE:
            return {'success': True, 'skipped': True, 'reason': 'checkpoint_hit'}

        satellite_data_list = self.data_preparer.load_satellite_data()
        if not satellite_data_list:
            return {'success': False, 'error': 'No valid satellite data loaded'}

        X, y, groups = self.data_preparer.prepare_features(satellite_data_list)
        training_results = self.training_runner.run(X, y, groups)

        if training_results.get("success"):
            self.checkpoint_handler.persist_execution_lineage(
                request=request,
                satellites_trained=len(satellite_data_list),
                training_samples=len(X),
                mlflow_run_id=training_results["run_id"],
                decision=decision,
                metadata_service=self.reporter.metadata_service)

            self.reporter.record_dataset(run_id, len(satellite_data_list))

            training_db_id = self.reporter.record_model_training_run(
                run_id=run_id,
                training_results=training_results,
                training_samples=len(X))

            self.reporter.record_model_deployment_entry(
                model_type="lstm_survival",
                mlflow_run_id=training_results.get("run_id"),
                training_run_id=training_db_id)

        phase_duration = time.time() - phase_timer
        self.logger.info(f"Phase 8 finished in {phase_duration:.2f}s.")
        return {'success': True, 'training_results': training_results}