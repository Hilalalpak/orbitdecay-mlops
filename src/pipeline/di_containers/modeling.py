
"""
Provides data loading, feature engineering, model inference utilities,
and the coordinator responsible for training the ML models.
"""

from dependency_injector import containers, providers

from src.machine_learning.data_loader import DataLoader
from src.machine_learning.feature_engineering.survival_feature_engineer import FeatureEngineer
from src.machine_learning.models.loader import ModelLoader
from src.machine_learning.satellite_risk_predictor import SatelliteSurvivalPredictor

from src.pipeline.coordinators.phase8_model_training.model_training_coordinator import ModelTrainingCoordinator
from src.pipeline.coordinators.phase8_model_training.components.request import TrainingRequestBuilder
from src.pipeline.coordinators.phase8_model_training.components.checkpoint_handler import TrainingCheckpointHandler
from src.pipeline.coordinators.phase8_model_training.components.data_preparation import TrainingDataPreparer
from src.pipeline.coordinators.phase8_model_training.components.reporting import TrainingReporter
from src.pipeline.coordinators.phase8_model_training.training_runner import TrainingRunner
from src.pipeline.monitoring.performance_monitor import PerformanceMonitor


class MLContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # Performance tracking
    performance_monitor = providers.Singleton(
        PerformanceMonitor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logging_config=config.logging,
        logger=core.logger.provided.bind.call(module="performance"),
        quota_manager=core.quota_manager,
        storage_adapter=core.storage_adapter)

    # ML components
    data_loader = providers.Singleton(
        DataLoader,
        logger=core.logger.provided.bind.call(module="ml.loader"))

    feature_engineer = providers.Singleton(
        FeatureEngineer,
        logger=core.logger.provided.bind.call(module="ml.feature_engineer"))

    model_loader = providers.Singleton(
        ModelLoader,
        ml_config=config.ml,
        storage_config=config.storage)

    predictor = providers.Singleton(
        SatelliteSurvivalPredictor,
        loader=data_loader,
        model_loader=model_loader,
        feature_engineer=feature_engineer,
        ml_config=config.ml)

    # Phase 8 components
    request_builder = providers.Singleton(
        TrainingRequestBuilder,
        pipeline_config=config.pipeline)

    checkpoint_handler = providers.Singleton(
        TrainingCheckpointHandler,
        checkpoint_guard=core.checkpoint_guard,
        logger=core.logger.provided.bind.call(module="train.checkpoint"))

    data_preparer = providers.Singleton(
        TrainingDataPreparer,
        data_loader=data_loader,
        feature_engineer=feature_engineer,
        target_date=config.pipeline.date,
        logger=core.logger.provided.bind.call(module="train.data"))

    training_runner = providers.Singleton(
        TrainingRunner,
        ml_config=config.ml,
        logger=core.logger.provided.bind.call(module="train.runner"))

    reporter = providers.Singleton(
        TrainingReporter,
        logger=core.logger.provided.bind.call(module="train.reporter"),
        metadata_service=core.metadata_service)

    # Phase coordinator
    coordinator = providers.Singleton(
        ModelTrainingCoordinator,
        scheduling_config=config.scheduling,
        logger=core.logger.provided.bind.call(module="train"),
        request_builder=request_builder,
        checkpoint_handler=checkpoint_handler,
        data_preparer=data_preparer,
        training_runner=training_runner,
        reporter=reporter)
