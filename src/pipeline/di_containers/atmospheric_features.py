"""
Phase 3 container. Runs orbital feature engineering — loads processed
orbital + environmental data and computes ML-ready feature vectors.
Checkpoint-aware, parallel execution.
"""

from dependency_injector import containers, providers

from src.domains.orbital_data.feature_engineering.environment_data_loader import EnvironmentDataLoader
from src.domains.orbital_data.feature_engineering.orbital_feature_generator import OrbitalFeatureGenerator

from src.pipeline.coordinators.phase6_orbital_features.atmospheric_feature_coordinator import FeatureEngineeringCoordinator
from src.pipeline.management.performance_monitor import PerformanceMonitor
from ..coordinators.phase6_orbital_features.components.runner import FeatureExtractionRunner
from ..coordinators.phase6_orbital_features.components.checkpoint_handler import FeatureCheckpointHandler
from ..coordinators.phase6_orbital_features.components.resource_manager import FeatureResourceManager
from ..coordinators.phase6_orbital_features.components.reporting import FeatureReportingHandler

class AtmosphericFeaturesContainer(containers.DeclarativeContainer):

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

    weather_loader = providers.Singleton(
        EnvironmentDataLoader,
        pipeline_config=config.pipeline,
        domain_config=config.domain,
        logger=core.logger.provided.getChild.call("env.loader"),
        storage_adapter=core.storage_adapter)

    feature_engineer = providers.Singleton(
        OrbitalFeatureGenerator,
        processing_config=config.processing,
        domain_config=config.domain,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("orbit.features"),
        storage_adapter=core.storage_adapter,
        weather_loader=weather_loader)

    resource_manager = providers.Singleton(
        FeatureResourceManager,
        max_workers=config.processing.provided.get_max_workers.call(),
        execution_mode=config.pipeline.execution_mode,
        logger=core.logger.provided.getChild.call("feat.resources"))

    runner = providers.Singleton(
        FeatureExtractionRunner,
        orbital_feature_engineer=feature_engineer,
        resource_manager=resource_manager,
        logger=core.logger.provided.getChild.call("feat.runner"))

    checkpoint_handler = providers.Singleton(
        FeatureCheckpointHandler,
        checkpoint_manager=core.checkpoint_manager,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("feat.checkpoint"))

    reporting_handler = providers.Singleton(
        FeatureReportingHandler,
        performance_monitor=performance_monitor,
        logger=core.logger.provided.getChild.call("feat.reporter"))

    coordinator = providers.Singleton(
        FeatureEngineeringCoordinator,
        features_enabled=config.ml.is_atmospheric_features_enabled(),
        logger=core.logger.provided.getChild.call("features"),
        runner=runner,
        checkpoint_handler=checkpoint_handler,
        reporter=reporting_handler,
        execution_mode=config.pipeline.execution_mode)
