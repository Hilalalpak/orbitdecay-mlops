"""
Phase 1 container. Wires everything needed to pull TLE data from Space-Track:
API client, rate limiter, satellite catalog, collection strategies (batch and
incremental), and the coordinator that drives the whole flow.
"""

from dependency_injector import containers, providers

from src.domains.orbital_data.collection.api_clients.spacetrack_client import SpaceTrackClient
from src.domains.orbital_data.collection.api_clients.spacetrack_rate_limiter import ApiRateLimiter
from src.domains.orbital_data.collection.catalog_service import SatCatalogRepository, SatCatalogService
from src.domains.orbital_data.collection.orbital_data_fetcher import OrbitalDataFetcher

from ..coordinators.phase1_orbital_collection.components.selector import SatelliteSelector
from ..coordinators.phase1_orbital_collection.components.request import RequestBuilder
from ..coordinators.phase1_orbital_collection.components.errors import ErrorPolicy
from ..coordinators.phase1_orbital_collection.components.cache_handler import CacheHandler

from src.domains.orbital_data.collection.strategies.batch_collection import BatchFetch
from src.domains.orbital_data.collection.strategies.incremental_collection import IncrementalFetch

from src.domains.orbital_data.collection.strategy_runner import StrategyRunner
from ..coordinators.phase1_orbital_collection.coordinator import OrbitCollectionCoordinator


class OrbitCollectionContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    api_client = providers.Singleton(
        SpaceTrackClient,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("space_track"))

    rate_monitor = providers.Singleton(
        ApiRateLimiter,
        quota_manager=core.quota_manager,
        logger=core.logger.provided.getChild.call("rate_limiter"))

    catalog_repository = providers.Singleton(
        SatCatalogRepository,
        logger=core.logger.provided.getChild.call("sat_repo"),
        bucket=config.pipeline.provided.get_s3_bucket.call('orbit-data'),
        prefix=config.pipeline.provided.get_s3_prefix.call('satcat'),
        storage_adapter=core.storage_adapter)

    catalog_service = providers.Singleton(
        SatCatalogService,
        catalog_config=config.catalog,
        logger=core.logger.provided.getChild.call("sat_registry"),
        repository=catalog_repository,
        quota_manager=core.quota_manager,
        api_client=api_client)

    data_fetcher = providers.Singleton(
        OrbitalDataFetcher,
        logger=core.logger.provided.getChild.call("orbit_fetcher"),
        api_delay=config.pipeline.provided.get_space_track_api_delay.call(),
        api_client=api_client,
        catalog=catalog_service,
        quota_manager=core.quota_manager)

    satellite_selector = providers.Singleton(
        SatelliteSelector,
        dynamic_selection=config.catalog.provided.use_dynamic_selection.call(),
        fallback_list=config.catalog.provided.get_fallback_satellites.call(),
        collector=data_fetcher,
        logger=core.logger.provided.getChild.call("selector"))

    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_cfg=config.pipeline,
        execution_mode=config.pipeline.provided.execution_mode,
        logger=core.logger.provided.getChild.call("req_builder"))

    error_policy = providers.Singleton(
        ErrorPolicy,
        logger=core.logger.provided.getChild.call("err_policy"),
        execution_mode=config.pipeline.provided.execution_mode)

    cache_handler = providers.Singleton(
        CacheHandler,
        cache_manager=core.cache_manager,
        metadata_tracker=core.metadata_tracker,
        logger=core.logger.provided.getChild.call("cache"))

    batch_strategy = providers.Singleton(
        BatchFetch,
        logger=core.logger.provided.getChild.call("strategy.batch"),
        batch_size=config.pipeline.provided.get_space_track_batch_size.call(),
        cache_manager=core.cache_manager,
        collector=data_fetcher)

    incremental_strategy = providers.Singleton(
        IncrementalFetch,
        logger=core.logger.provided.getChild.call("strategy.inc"),
        quota_manager=core.quota_manager,
        cache_manager=core.cache_manager,
        collector=data_fetcher)

    strategy_runner = providers.Singleton(
        StrategyRunner,
        logger=core.logger.provided.getChild.call("collect.runner"),
        prefix=config.pipeline.provided.get_s3_prefix.call('orbit_cache'),
        cache_manager=core.cache_manager,
        quota_manager=core.quota_manager,
        batch_strategy=batch_strategy,
        incremental_strategy=incremental_strategy)

    coordinator = providers.Singleton(
        OrbitCollectionCoordinator,
        logger=core.logger.provided.getChild.call("collect"),
        execution_mode=config.pipeline.execution_mode,
        target_date=config.pipeline.date,
        selector=satellite_selector,
        request_builder=request_builder,
        error_handler=error_policy,
        runner=strategy_runner,
        cache_handler=cache_handler)