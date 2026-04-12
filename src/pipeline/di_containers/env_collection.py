"""
Phase 4 container. Wires three collectors (solar flux, Kp index, sunspot)
and the coordinator that runs them, checks cache, and validates results.
"""

from dependency_injector import containers, providers

from src.domains.space_weather.collection.collect_flux import FluxCollector
from src.domains.space_weather.collection.collect_kp_ap import KpCollector
from src.domains.space_weather.collection.collect_sunspot import SunspotCollector

from ..coordinators.phase3_environment_collection.components.data_quality_validator import DataQualityValidator
from ..coordinators.phase3_environment_collection.components.request_builder import RequestBuilder
from ..coordinators.phase3_environment_collection.components.cache_handler import CacheHandler
from ..coordinators.phase3_environment_collection.components.collector_runner import CollectorRunner

from src.pipeline.coordinators.phase3_environment_collection.coordinator import EnvCollectionCoordinator
from src.pipeline.management.performance_monitor import PerformanceMonitor


class EnvironmentCollectionContainer(containers.DeclarativeContainer):

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

    flux_collector = providers.Singleton(
        FluxCollector,
        pipeline_config=config.pipeline,
        processing_config=config.processing,
        logger=core.logger.provided.getChild.call("env.flux"))

    kp_collector = providers.Singleton(
        KpCollector,
        pipeline_config=config.pipeline,
        processing_config=config.processing,
        logger=core.logger.provided.getChild.call("env.kp"))

    sunspot_collector = providers.Singleton(
        SunspotCollector,
        pipeline_config=config.pipeline,
        processing_config=config.processing,
        logger=core.logger.provided.getChild.call("env.sunspot"))

    collectors_dict = providers.Dict({
        "solar_flux": flux_collector,
        "geomagnetic": kp_collector,
        "solar_activity": sunspot_collector})

    validator = providers.Singleton(
        DataQualityValidator,
        logger=core.logger.provided.getChild.call("env.validator"))

    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_config=config.pipeline,
        execution_mode=config.pipeline.provided.execution_mode,
        logger=core.logger.provided.getChild.call("env.req_builder"))

    cache_handler = providers.Singleton(
        CacheHandler,
        prefix=config.pipeline.provided.get_s3_prefix.call('env_cache'),
        cache_manager=core.cache_manager,
        metadata_tracker=core.metadata_tracker,
        logger=core.logger.provided.getChild.call("env.checkpoint_handler"),
        validator=validator)

    collector_runner = providers.Singleton(
        CollectorRunner,
        quota_manager=core.quota_manager,
        cache_handler=cache_handler,
        validator=validator,
        logger=core.logger.provided.getChild.call("env.runner"))

    coordinator = providers.Singleton(
        EnvCollectionCoordinator,
        logger=core.logger.provided.getChild.call("env.collect"),
        performance_monitor=performance_monitor,
        request_builder=request_builder,
        cache_handler=cache_handler,
        runner=collector_runner,
        collectors=collectors_dict)
