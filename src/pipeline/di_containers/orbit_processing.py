"""
Phase 2 container. Takes batch files from Phase 1 and runs them through
the orbital processor (propagation + classification) per satellite in
parallel. Checkpoint-aware — skips if results already exist.
"""

from dependency_injector import containers, providers

from ..coordinators.phase2_orbital_processing.components.grouper import GroupResolver
from ..coordinators.phase2_orbital_processing.components.executor import Executor
from ..coordinators.phase2_orbital_processing.components.request import RequestBuilder
from ..coordinators.phase2_orbital_processing.components.checkpoint_handler import CheckpointHandler
from ..coordinators.phase2_orbital_processing.components.batch_data_loader import BatchDataLoader

from src.domains.orbital_data.processing.orbital_classifier import OrbitalClassifier
from src.domains.orbital_data.processing.tle_data_processor import OrbitProcessor
from ..management.storage_manager import StorageManager
from ..coordinators.phase2_orbital_processing.orbital_processing_coordinator import OrbitProcessingCoordinator


class OrbitProcessingContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    classifier = providers.Singleton(
        OrbitalClassifier,
        domain_config=config.domain)

    orbital_processor = providers.Singleton(
        OrbitProcessor,
        processing_config=config.processing,
        environment_name=config.logging.provided.get_environment_name.call(),
        logger=core.logger.provided.getChild.call("orbit.processor"),
        classifier=classifier)

    grouper = providers.Singleton(
        GroupResolver,
        logger=core.logger.provided.getChild.call("orbit.grouper"))

    storage_manager = providers.Singleton(
        StorageManager,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("storage.manager"),
        storage_adapter=core.storage_adapter)

    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("service.request"),
        execution_mode=config.pipeline.execution_mode)

    batch_data_loader = providers.Singleton(
        BatchDataLoader,
        pipeline_config=config.pipeline,
        storage_adapter=core.storage_adapter,
        logger=core.logger.provided.getChild.call("orbit.batch_loader"))

    checkpoint_handler = providers.Singleton(
        CheckpointHandler,
        checkpoint_manager=core.checkpoint_manager,
        batch_data_loader=batch_data_loader,
        logger=core.logger.provided.getChild.call("service.checkpoint_handler"))

    executor = providers.Singleton(
        Executor,
        orbital_data_processor=orbital_processor,
        storage_manager=storage_manager,
        logger=core.logger.provided.getChild.call("engine.runner"))

    coordinator = providers.Singleton(
        OrbitProcessingCoordinator,
        logger=core.logger.provided.getChild.call("process.orbit"),
        request_builder=request_builder,
        checkpoint_handler=checkpoint_handler,
        grouper=grouper,
        executor=executor,
        max_workers=config.processing.provided.get_max_workers.call(),
        target_date=config.pipeline.date)
