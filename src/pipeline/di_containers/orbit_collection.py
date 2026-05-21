"""
This container wires all components required for collecting TLE (Two-Line Element)
data from Space-Track API. It manages API clients, rate limiting, satellite catalog
services, and collection strategies (batch vs incremental).
"""

from dependency_injector import containers, providers

from src.domain.orbital.collection import (
    SpaceTrackClient,
    SatCatalogService,
    OrbitalDataFetcher,
    BatchCollector,
    IncrementalCollector,
    OrbitalCollectionRepository,
)
from src.domain.orbital.collection.catalog.catalog_repository import SatCatalogRepository
from src.domain.orbital.collection.validation.telemetry_validator import TelemetryValidator

from ..coordinators.phase1_orbital_collection.components.request import RequestBuilder
from ..coordinators.phase1_orbital_collection.components.errors import Phase1ErrorHandler
from ..coordinators.phase1_orbital_collection.components.cache_handler import CollectionCacheHandler

from src.pipeline.coordinators.phase1_orbital_collection.strategy_runner import StrategyRunner
from ..coordinators.phase1_orbital_collection.coordinator import OrbitCollectionCoordinator


class OrbitCollectionContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # Infra. Services
    api_client = providers.Singleton(
        SpaceTrackClient,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="space_track"))

    # Satellite catalog repository for persistent storage
    catalog_repository = providers.Singleton(
        SatCatalogRepository,
        logger=core.logger.provided.bind.call(module="sat_repo"),
        orbit_data_bucket=config.pipeline.provided.get_s3_bucket.call('satellite_data'),
        satcat_prefix=config.pipeline.provided.get_s3_prefix.call('satcat'),
        storage_adapter=core.storage_adapter)

    # Satellite catalog service managing target selection
    catalog_service = providers.Singleton(
        SatCatalogService,
        catalog_config=config.catalog,
        logger=core.logger.provided.bind.call(module="sat_registry"),
        repository=catalog_repository,
        quota_manager=core.quota_manager,
        api_client=api_client)

    collection_repo = providers.Singleton(
        OrbitalCollectionRepository,
        logger=core.logger.provided.bind.call(module="orbit.repo"),
        cache_bucket=config.pipeline.provided.get_s3_bucket.call('pipeline_cache'),
        data_prefix=config.pipeline.provided.get_s3_prefix.call("orbit_cache"),
        storage_adapter=core.storage_adapter)

    telemetry_validator=providers.Singleton(
        TelemetryValidator,
        logger=core.logger.provided.bind.call(module="telemetry_validator"))

    # Orbital data fetcher handling API requests
    orbital_data_collector = providers.Singleton(
        OrbitalDataFetcher,
        logger=core.logger.provided.bind.call(),
        api_client=api_client,
        quota_manager=core.quota_manager,
        telemetry_validator=telemetry_validator)


    # Request builder creating execution requests
    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="req_builder"))

    # Error policy for handling API failures
    error_policy = providers.Singleton(
        Phase1ErrorHandler,
        logger=core.logger.provided.bind.call(module="err_policy"))

    # Fetch mode cache (batch vs incremental)
    cache_handler = providers.Singleton(
        CollectionCacheHandler,
        collection_freshness_policy=core.collection_freshness_policy,
        logger=core.logger.provided.bind.call(module="cache"),
        metadata_service=core.metadata_service)

    # Collection strategies
    batch_strategy = providers.Singleton(
        BatchCollector,
        logger=core.logger.provided.bind.call(module="strategy.batch"),
        batch_size=config.pipeline.provided.get_full_batch_size.call(),
        orbital_collection_repository=collection_repo,
        orbital_data_collector=orbital_data_collector)

    incremental_strategy = providers.Singleton(
        IncrementalCollector,
        logger=core.logger.provided.bind.call(module="strategy.inc"),
        batch_size=config.pipeline.provided.get_inc_batch_size.call(),
        buffer_size=config.pipeline.provided.get_incremental_buffer_size.call(),
        overlap_hours=config.pipeline.provided.get_incremental_overlap_hours.call(),
        orbital_collection_repository=collection_repo,
        orbital_data_collector=orbital_data_collector)

    # Strategy runner executing selected collection mode
    strategy_runner = providers.Singleton(
        StrategyRunner,
        logger=core.logger.provided.bind.call(module="collect.runner"),
        batch_strategy=batch_strategy,
        incremental_strategy=incremental_strategy)

    # Phase coordinator orchestrating collection workflow
    coordinator = providers.Singleton(
        OrbitCollectionCoordinator,
        logger=core.logger.provided.bind.call(module="collect"),
        catalog_service=catalog_service,
        request_builder=request_builder,
        error_handler=error_policy,
        strategy_runner=strategy_runner,
        cache_handler=cache_handler,
        metadata_service=core.metadata_service)