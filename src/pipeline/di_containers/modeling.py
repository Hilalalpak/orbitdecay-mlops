"""
Phase 8 container. Loads the time series dataset, runs feature engineering,
and trains the satellite survival prediction model.
"""

from dependency_injector import containers, providers

from src.machine_learning.data_loader import DataLoader
from src.machine_learning.feature_engineering.survival_feature_engineer import FeatureEngineer
from src.machine_learning.satellite_risk_predictor import SatelliteSurvivalPredictor

from src.pipeline.coordinators.phase8_model_training.model_training_coordinator import ModelTrainingCoordinator
from src.pipeline.management.performance_monitor import PerformanceMonitor


class MLContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    performance_monitor = providers.Singleton(
        PerformanceMonitor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logging_config=config.logging,
        logger=core.logger.provided.getChild.call("performance"),
        quota_manager=core.quota_manager,
        storage_adapter=core.storage_adapter)

    data_loader = providers.Singleton(
        DataLoader,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("ml.loader"))

    feature_engineer = providers.Singleton(
        FeatureEngineer)

    predictor = providers.Singleton(
        SatelliteSurvivalPredictor,
        loader=data_loader,
        ml_config=config.ml,
        domain_config=config.domain,
        storage_config=config.storage)

    coordinator = providers.Singleton(
        ModelTrainingCoordinator,
        storage_config=config.storage,
        ml_config=config.ml,
        scheduling_config=config.scheduling,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("train"),
        cache_manager=core.cache_manager,
        metadata_tracker=core.metadata_tracker,
        performance_monitor=performance_monitor,
        target_date=config.pipeline.date,
        execution_mode=config.pipeline.execution_mode)
