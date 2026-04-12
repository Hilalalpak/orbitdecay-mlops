"""
Phase 7 container. Aligns orbital and environmental feature data on a
shared time axis and writes the final ML-ready time series dataset.
Checkpoint-aware.
"""

from dependency_injector import containers, providers

from src.domains.time_series_integration.timeseries_generator import TimeSeriesGenerator

from src.pipeline.coordinators.phase7_timeseries_integration.timeseries_integration_coordinator import TimeSeriesIntegrationCoordinator
from src.pipeline.management.performance_monitor import PerformanceMonitor
from ..coordinators.phase7_timeseries_integration.components.resource_manager import TimeseriesResourceManager
from ..coordinators.phase7_timeseries_integration.components.reporting import TimeseriesReportingHandler

from ..coordinators.phase7_timeseries_integration.components.checkpoint_handler import TimeseriesCheckpointHandler

class TimeSeriesContainer(containers.DeclarativeContainer):

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

    timeseries_creator = providers.Singleton(
        TimeSeriesGenerator,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("timeseries.creator"),
        storage_adapter=core.storage_adapter)

    resource_manager = providers.Singleton(
        TimeseriesResourceManager,
        processing_config=config.processing,
        execution_mode=config.pipeline.execution_mode)

    checkpoint_handler = providers.Singleton(
        TimeseriesCheckpointHandler,
        checkpoint_manager=core.checkpoint_manager,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("timeseries.cache"),
        execution_mode=config.pipeline.execution_mode)

    reporting_handler = providers.Singleton(
        TimeseriesReportingHandler,
        performance_monitor=performance_monitor,
        logger=core.logger.provided.getChild.call("timeseries.reporter"))

    coordinator = providers.Singleton(
        TimeSeriesIntegrationCoordinator,
        features_enabled=config.ml.is_orbital_features_enabled(),
        logger=core.logger.provided.getChild.call("timeseries"),
        timeseries_creator=timeseries_creator,
        reporting_handler=reporting_handler,
        resource_manager=resource_manager,
        checkpoint_handler=checkpoint_handler)
