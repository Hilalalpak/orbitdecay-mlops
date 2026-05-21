"""
Provides processors for solar flux, geomagnetic indices, and sunspot activity,
and wires them into the main coordinator responsible for normalizing data.
"""

from dependency_injector import containers, providers

from ..coordinators.phase5_environment_processing.components.checkpoint_handler import P5CheckPointHandler

from src.domain.weather.processing.solar_flux_processor import SolarFluxProcessor
from src.domain.weather.processing.geomagnetic_index_processor import GeomagneticIndexProcessor
from src.domain.weather.processing.sunspot_processor import SunspotProcessor
from src.domain.weather.processing.repository import EnvProcessingStorage

from ..coordinators.phase5_environment_processing.coordinator import EnvProcessingCoordinator
from src.pipeline.coordinators.phase5_environment_processing.components.request_builder import RequestBuilder
from src.pipeline.coordinators.phase5_environment_processing.components.processing_runner import ProcessingRunner


class EnvironmentProcessingContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # Storage manager
    storage = providers.Singleton(
        EnvProcessingStorage,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="storage"),
        storage_adapter=core.storage_adapter)

    request_builder = providers.Singleton(
        RequestBuilder,
        pipeline_config=config.pipeline,
        execution_mode=config.pipeline.provided.execution_mode,
        logger=core.logger.provided.bind.call(module="env.req_builder"))

    # Data processors


    flux_processor = providers.Singleton(
        SolarFluxProcessor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="proc.flux"))

    kp_processor = providers.Singleton(
        GeomagneticIndexProcessor,
        logger=core.logger.provided.bind.call(module="proc.kp"))

    sunspot_processor = providers.Singleton(
        SunspotProcessor,
        logger=core.logger.provided.bind.call(module="proc.sunspot"))

    # Processor registry
    processors_dict = providers.Dict({
        "solar_flux": flux_processor,
        "kp_indices": kp_processor,
        "sunspot": sunspot_processor
    })


    checkpoint_handler = providers.Singleton(
        P5CheckPointHandler,
        checkpoint_guard=core.checkpoint_guard,
        logger=core.logger.provided.bind.call(module="proc.checkpoint_handler"),
        metadata_service=core.metadata_service)

    processor = providers.Singleton(
        ProcessingRunner,
        logger=core.logger.provided.bind.call(module="env.runner"),
        storage=storage,
        checkpoint_handler=checkpoint_handler,
        environment_data_processors=processors_dict)

    # Phase coordinator
    coordinator = providers.Singleton(
        EnvProcessingCoordinator,
        logger=core.logger.provided.bind.call(module="env.process"),
        request=request_builder,
        runner=processor,
        metadata_service=core.metadata_service)
