"""
Provides the data merger, performance analytics, storage management,
and the main coordinator responsible for building the unified space-weather dataset.
"""

from dependency_injector import containers, providers

from src.domain.weather.feature_synthesis.multi_source_merger import EnvironmentDataMerger
from src.domain.weather.feature_synthesis.repository.env_synthesis_repository import EnvSynthesisRepository

from src.pipeline.monitoring.performance_monitor import PerformanceMonitor
from ..coordinators.phase6_environment_synthesis.env_feature_synthesis import EnvSynthesisCoordinator

from ..coordinators.phase6_environment_synthesis.components.request_builder import SynthesisRequestBuilder
from ..coordinators.phase6_environment_synthesis.components.executor import SynthesisExecutor
from ..coordinators.phase6_environment_synthesis.components.checkpoint_handler import P6CheckPointHandler

class EnvironmentSynthesisContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()


    performance_monitor = providers.Singleton(
        PerformanceMonitor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logging_config=config.logging,
        logger=core.logger.provided.bind.call(module="performance"),
        quota_manager=core.quota_manager,
        storage_adapter=core.storage_adapter)

    # Unified repository
    repository = providers.Singleton(
        EnvSynthesisRepository,
        pipeline_config=config.pipeline,
        storage_adapter=core.storage_adapter,
        logger=core.logger.provided.bind.call(module="synth.repository"))

    # Data merger
    data_merger = providers.Singleton(
        EnvironmentDataMerger,
        repository=repository,
        logger=core.logger.provided.bind.call(module="env.merger"))

    # Synthesis components
    request_builder = providers.Singleton(
        SynthesisRequestBuilder,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.bind.call(module="synth.req_builder"))

    executor = providers.Singleton(
        SynthesisExecutor,
        environment_merger=data_merger,
        logger=core.logger.provided.bind.call(module="synth.executor"))

    checkpoint_handler = providers.Singleton(
        P6CheckPointHandler,
        checkpoint_guard=core.checkpoint_guard,
        logger=core.logger.provided.bind.call(module="synth.cache"))

    # Phase coordinator
    coordinator = providers.Singleton(
        EnvSynthesisCoordinator,
        logger=core.logger.provided.bind.call(module="env.synthesis"),
        request_builder=request_builder,
        executor=executor,
        checkpoint_handler=checkpoint_handler,
        repository=repository,
        metadata_service=core.metadata_service)
