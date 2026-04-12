"""
Shared infrastructure singletons used by every phase container:
S3 storage, logger, API quota management, cache, metadata tracker,
and checkpoint manager.
"""

import logging
from dependency_injector import containers, providers

from src.core.s3_storage import S3StorageAdapter

from src.core.api_compliance.quota_manager  import ApiQuotaManager
from src.core.api_compliance.quota_policy import QuotaPolicyRules
from src.core.api_compliance.state_store import QuotaStateStore

from src.core.metadata_tracker import PipelineMetadataTracker
from src.core.checkpoint_manager import ComputationCheckpointManager

from src.core.caching.cache_manager import CacheManager
from src.core.caching.cache_storage import CacheStorage
from src.core.caching.cache_policy import CachePolicyEngine
from src.core.caching.data_transformer import DataTransformer


class CoreContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    logger = providers.Singleton(
        logging.getLogger,
        name="od.pipeline")

    storage_adapter = providers.Singleton(
        S3StorageAdapter,
        storage_config=config.storage,
        logger=logger.provided.getChild.call("storage"))

    metadata_tracker = providers.Singleton(
        PipelineMetadataTracker,
        pipeline_config=config.pipeline,
        environment_name=config.logging.provided.get_environment_name.call(),
        logger=logger.provided.getChild.call("metadata"),
        storage_adapter=storage_adapter)

    # Space-Track API quota: tracks daily request counts + enforces limits
    state_store = providers.Singleton(
        QuotaStateStore,
        storage_adapter=storage_adapter,
        compliance_bucket=config.pipeline.provided.get_s3_bucket.call('pipeline_state'),
        prefix=config.pipeline.provided.get_s3_prefix.call('api_compliance'),
        logger=logger.provided.getChild.call("api.state_store"))

    quota_policy = providers.Singleton(
        QuotaPolicyRules,
        pipeline_config=config.pipeline,
        logger=logger.provided.getChild.call("api.policy"))

    quota_manager = providers.Singleton(
        ApiQuotaManager,
        max_daily_request=config.pipeline.provided.get_space_track_daily_limit.call(),
        batch_size=config.pipeline.provided.get_space_track_batch_size.call(),
        monitoring_config=config.monitoring,
        logger=logger.provided.getChild.call("api.quota"),
        quota_state_store=state_store,
        quota_policy=quota_policy)

    # Cache: transformer → storage → policy → manager
    transformer = providers.Singleton(
        DataTransformer,
        logger=logger.provided.getChild.call("cache.transform"))

    storage_service = providers.Singleton(
        CacheStorage,
        logger=logger.provided.getChild.call("cache.storage"),
        cache_bucket=config.pipeline.provided.get_s3_bucket.call('pipeline_cache'),
        storage_adapter=storage_adapter,
        data_transformer=transformer)

    policy = providers.Singleton(
        CachePolicyEngine,
        pipeline_config=config.pipeline,
        logger=logger.provided.getChild.call("cache.policy"),
        storage_service=storage_service,
        metadata_tracker=metadata_tracker)

    cache_manager = providers.Singleton(
        CacheManager,
        logger=logger.provided.getChild.call("cache"),
        data_transformer=transformer,
        cache_storage=storage_service,
        cache_policy=policy)

    checkpoint_manager = providers.Singleton(
        ComputationCheckpointManager,
        metadata_tracker=metadata_tracker,
        logger=logger.provided.getChild.call("checkpoint"))