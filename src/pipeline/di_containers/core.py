"""
Core infrastructure dependency injection container.

This container manages the lifecycle of foundational singleton services that form
the backbone of the entire pipeline. It provides centralized access to storage,
logging, compliance, caching, and metadata tracking infrastructure.

Key services:
- Storage adapter for S3/MinIO operations
- Centralized logging infrastructure
- API compliance and rate limiting
- Pipeline caching system
- Metadata and lineage tracking
- Checkpoint management for idempotent operations
"""

from dependency_injector import containers, providers
import structlog
import os
import psycopg2
from src.pipeline.metadata.repository import MetadataRepository
from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.execution.repository import PipelineExecutionRepository
from src.pipeline.metadata.execution.service import PipelineExecutionService
from src.pipeline.metadata.data_lineage.repository import DataLineageRepository
from src.pipeline.metadata.data_lineage.service import DataLineageService
from src.pipeline.metadata.model_registry.repository import ModelRegistryRepository
from src.pipeline.metadata.model_registry.service import ModelRegistryService
from src.shared.quota.repository import QuotaRepository
from src.shared.quota.service import QuotaService
from src.shared.storage.s3_adapter import S3StorageAdapter

from src.shared.quota.quota_manager  import ApiQuotaManager
from src.shared.quota.quota_policy import QuotaPolicy
from src.shared.quota.state_store import QuotaStateStore

from src.pipeline.policies.checkpoint_guard import CheckpointGuard

from src.pipeline.policies.collection_freshness_policy import CollectionFreshnessPolicy


class CoreContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Root logger for entire pipeline
    logger = providers.Factory(
        structlog.get_logger,
        system="orbit_decay_pipeline")

    # S3/MinIO storage interface
    storage_adapter = providers.Singleton(
        S3StorageAdapter,
        storage_config=config.storage,
        logger=logger.provided.bind.call(module="storage"))

    # Shared DB connection
    db_connection = providers.Singleton(
        psycopg2.connect,
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"))

    # --- Focused repositories ---
    execution_repository = providers.Singleton(
        PipelineExecutionRepository, connection=db_connection)
    data_lineage_repository = providers.Singleton(
        DataLineageRepository, connection=db_connection)
    model_registry_repository = providers.Singleton(
        ModelRegistryRepository, connection=db_connection)
    quota_repository = providers.Singleton(
        QuotaRepository, connection=db_connection)

    # --- Focused services ---
    execution_service = providers.Singleton(
        PipelineExecutionService, repository=execution_repository)
    data_lineage_service = providers.Singleton(
        DataLineageService, repository=data_lineage_repository)
    model_registry_service = providers.Singleton(
        ModelRegistryService, repository=model_registry_repository)
    quota_service = providers.Singleton(
        QuotaService, repository=quota_repository)

    # --- Composition facades (backward-compatible public API) ---
    metadata_repository = providers.Singleton(
        MetadataRepository,
        execution_repo=execution_repository,
        data_lineage_repo=data_lineage_repository,
        model_registry_repo=model_registry_repository,
        quota_repo=quota_repository)

    metadata_service = providers.Singleton(
        MetadataService,
        execution_service=execution_service,
        data_lineage_service=data_lineage_service,
        model_registry_service=model_registry_service,
        quota_service=quota_service)

    # API rate limiting and compliance enforcement
    state_store = providers.Singleton(
        QuotaStateStore,
        quota_service=quota_service,
        max_daily_requests=config.pipeline.provided.get_space_track_daily_limit.call(),
        logger=logger.provided.bind.call(module="api.state_store"))

    quota_policy = providers.Singleton(
        QuotaPolicy,
        pipeline_config=config.pipeline,
        logger=logger.provided.bind.call(module="api.policy"))

    quota_manager = providers.Singleton(
        ApiQuotaManager,
        max_daily_request=config.pipeline.provided.get_space_track_daily_limit.call(),
        batch_size=config.pipeline.provided.get_full_batch_size.call(),
        monitoring_config=config.monitoring,
        logger=logger.provided.bind.call(module="api.quota"),
        quota_state_store=state_store,
        quota_policy=quota_policy)

    # Cache system components
    collection_freshness_policy = providers.Singleton(
        CollectionFreshnessPolicy,
        pipeline_config=config.pipeline,
        logger=logger.provided.bind.call(module="cache.policy"),
        metadata_service=metadata_service)

    # Checkpoint manager for idempotent operations
    checkpoint_guard = providers.Singleton(
        CheckpointGuard,
        metadata_service=metadata_service,
        logger=logger.provided.bind.call(module="checkpoint"))