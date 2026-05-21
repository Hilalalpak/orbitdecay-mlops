
"""
This container assembles components for processing raw TLE data into cleaned,
classified, and enriched orbital records. It handles batch processing, grouping
by satellite, and applying orbital mechanics calculations and classifications.
"""

from dependency_injector import containers, providers

from ..coordinators.phase2_orbital_processing.components.executor import Executor
from ..coordinators.phase2_orbital_processing.components.checkpoint_handler import CheckpointHandler
from src.domain.orbital.processing.engines.record_validator import OrbitRecordValidator

from src.domain.orbital.processing.core.tle_data_processor_factory import OrbitProcessorFactory
from src.domain.orbital.processing.repositories.orbital_batch_repository import OrbitalBatchRepository
from ..coordinators.phase2_orbital_processing.orbital_processing_coordinator import OrbitProcessingCoordinator


class OrbitProcessingContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()


    record_validator = providers.Singleton(
        OrbitRecordValidator,
        logger=core.logger.provided.bind.call(module="rec.validator"))

    orbit_processor_factory = providers.Factory(
        OrbitProcessorFactory,
        processing_config=config.processing,
        domain_config=config.domain,
        record_validator=record_validator,
        environment_name=config.logging.provided.get_environment_name.call(),
        logger=core.logger.provided.bind.call(module="orbit.processor"))

    # For persisting processed data
    data_repository = providers.Singleton(
        OrbitalBatchRepository,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="data_repo"),
        storage_adapter=core.storage_adapter)

    # Checkpoint handler for idempotent processing
    checkpoint_handler = providers.Singleton(
        CheckpointHandler,
        checkpoint_guard=core.checkpoint_guard,
        logger=core.logger.provided.bind.call(module="service.checkpoint_handler"),
        pipeline_config=config.pipeline,
        metadata_service=core.metadata_service)

    # Processing executor for parallel satellite processing
    executor = providers.Singleton(
        Executor,
        orbit_processor_factory=orbit_processor_factory,
        data_repository=data_repository,
        logger=core.logger.provided.bind.call(module="engine.runner"),
        max_workers=config.processing.provided.get_max_workers.call())

    # Phase coordinator orchestrating processing workflow
    coordinator = providers.Singleton(
        OrbitProcessingCoordinator,
        logger=core.logger.provided.bind.call(module="process.orbit"),
        checkpoint_handler=checkpoint_handler,
        executor=executor,
        data_repository=data_repository,
        max_workers=config.processing.provided.get_max_workers.call(),
        metadata_service=core.metadata_service)
