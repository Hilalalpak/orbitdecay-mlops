"""
Phase 5 container. Normalizes the three environmental sources collected
in Phase 4 (flux, Kp, sunspot). Checkpoint-aware.
"""

from dependency_injector import containers, providers

from ..coordinators.phase4_environment_processing.components.validation import Validator
from ..coordinators.phase4_environment_processing.components.checkpoint_handler import P4CheckPointHandler

from src.domains.space_weather.processing.process_flux import FluxProcessor
from src.domains.space_weather.processing.process_kp_ap import KpProcessor
from src.domains.space_weather.processing.process_sunspot import SunspotProcessor

from ..management.storage_manager import StorageManager
from ..coordinators.phase4_environment_processing.coordinator import EnvProcessingCoordinator


class EnvironmentProcessingContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    storage_manager = providers.Singleton(
        StorageManager,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("storage.manager"),
        storage_adapter=core.storage_adapter)

    flux_processor = providers.Singleton(
        FluxProcessor,
        processing_config=config.processing,
        logging_config=config.logging,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("proc.flux"))

    kp_processor = providers.Singleton(
        KpProcessor,
        processing_config=config.processing,
        logging_config=config.logging,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("proc.kp"))

    sunspot_processor = providers.Singleton(
        SunspotProcessor,
        processing_config=config.processing,
        logging_config=config.logging,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("proc.sunspot"))

    processors_dict = providers.Dict({
        "solar_flux": flux_processor,
        "geomagnetic": kp_processor,
        "solar_activity": sunspot_processor})

    validator = providers.Singleton(
        Validator,
        logger=core.logger.provided.getChild.call("proc.validator"))

    checkpoint_handler = providers.Singleton(
        P4CheckPointHandler,
        checkpoint_manager=core.checkpoint_manager,
        storage_manager=storage_manager,
        cache_manager=core.cache_manager,
        logger=core.logger.provided.getChild.call("proc.checkpoint_handler"),
        cache_prefix=config.pipeline.provided.get_s3_prefix.call('env_cache'))

    coordinator = providers.Singleton(
        EnvProcessingCoordinator,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("env.process"),
        validator=validator,
        checkpoint_handler=checkpoint_handler,
        environment_data_processors=processors_dict,
        execution_mode=config.pipeline.execution_mode)
