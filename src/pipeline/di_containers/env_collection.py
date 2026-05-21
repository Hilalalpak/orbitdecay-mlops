"""
Phase 3 DI container: Environmental raw snapshot collection.
Fully config-driven. No domain-specific collectors.
"""

from dependency_injector import containers, providers

from src.pipeline.coordinators.phase4_environment_collection.components.request_builder import RequestBuilder
from src.pipeline.coordinators.phase4_environment_collection.components.cache_handler import CacheHandler
from src.pipeline.coordinators.phase4_environment_collection.components.collector_runner import CollectorRunner
from src.pipeline.coordinators.phase4_environment_collection.coordinator import EnvCollectionCoordinator
from src.domain.weather.collection.repository.env_collection_repository import EnvCollectionRepository


class EnvironmentCollectionContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # ---------------------------------------------------------
    # Request Builder
    # ---------------------------------------------------------

    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_config=config.pipeline,
        execution_mode=config.pipeline.provided.execution_mode,
        logger=core.logger.provided.bind.call(module="env.req_builder"))

    # ---------------------------------------------------------
    # Cache Handler
    # ---------------------------------------------------------

    collection_repo = providers.Singleton(
        EnvCollectionRepository,
        logger=core.logger.provided.bind.call(module="env.repo"),
        data_prefix=config.pipeline.provided.get_s3_prefix.call("env_cache"),
        cache_bucket=config.pipeline.provided.get_s3_bucket.call('pipeline_cache'),
        storage_adapter=core.storage_adapter)

    cache_handler = providers.Singleton(
        CacheHandler,
        metadata_service=core.metadata_service,
        collection_freshness_policy=core.collection_freshness_policy,
        logger=core.logger.provided.bind.call(module="env.cache"))

    # ---------------------------------------------------------
    # Runner (Raw Fetch Engine)
    # ---------------------------------------------------------

    collector_runner = providers.Singleton(
        CollectorRunner,
        quota_manager=core.quota_manager,
        env_collection_repository=collection_repo,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="env.runner"))

    # ---------------------------------------------------------
    # Phase 3 Coordinator
    # ---------------------------------------------------------

    coordinator = providers.Singleton(
        EnvCollectionCoordinator,
        logger=core.logger.provided.bind.call(module="env.collect"),
        request_builder=request_builder,
        cache_handler=cache_handler,
        runner=collector_runner,
        pipeline_config=config.pipeline,
        metadata_service=core.metadata_service)
