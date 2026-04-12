"""
Phase 6 container. Merges the normalized environmental sources into a
single unified dataset and saves it. Checkpoint-aware.
"""

from dependency_injector import containers, providers

from src.domains.space_weather.feature_synthesis.multi_source_merger import EnvironmentDataMerger

from src.pipeline.management.storage_manager import StorageManager
from src.pipeline.management.performance_monitor import PerformanceMonitor
from ..coordinators.phase5_environment_synthesis.env_feature_synthesis import EnvSynthesisCoordinator

from ..coordinators.phase5_environment_synthesis.components.request_builder import SynthesisRequestBuilder
from ..coordinators.phase5_environment_synthesis.components.executor import SynthesisExecutor
from ..coordinators.phase5_environment_synthesis.components.checkpoint_handler import P5CheckpointHandler
from ..coordinators.phase5_environment_synthesis.components.persistence import SynthesisPersistence

class EnvironmentSynthesisContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    storage_manager = providers.Singleton(
        StorageManager,
        pipeline_config=config.pipeline,
        logger=core.logger.provided.getChild.call("storage.manager"),
        storage_adapter=core.storage_adapter)

    performance_monitor = providers.Singleton(
        PerformanceMonitor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logging_config=config.logging,
        logger=core.logger.provided.getChild.call("performance"),
        quota_manager=core.quota_manager,
        storage_adapter=core.storage_adapter)

    data_merger = providers.Singleton(
        EnvironmentDataMerger,
        pipeline_config=config.pipeline,
        processing_config=config.processing,
        logger=core.logger.provided.getChild.call("env.merger"),
        storage_adapter=core.storage_adapter)

    request_builder = providers.Singleton(
        SynthesisRequestBuilder,
        pipeline_config=config.pipeline,
        execution_mode=config.pipeline.execution_mode,
        logger=core.logger.provided.getChild.call("synth.req_builder"))

    executor = providers.Singleton(
        SynthesisExecutor,
        environment_merger=data_merger,
        logger=core.logger.provided.getChild.call("synth.executor"))

    checkpoint_handler = providers.Singleton(
        P5CheckpointHandler,
        checkpoint_manager=core.checkpoint_manager,
        logger=core.logger.provided.getChild.call("synth.cache"))

    persistence = providers.Singleton(
        SynthesisPersistence,
        storage_manager=storage_manager,
        logger=core.logger.provided.getChild.call("synth.checkpoint_handler"))

    coordinator = providers.Singleton(
        EnvSynthesisCoordinator,
        logger=core.logger.provided.getChild.call("env.synthesis"),
        request_builder=request_builder,
        executor=executor,
        checkpoint_handler=checkpoint_handler,
        persistence=persistence,
        execution_mode=config.pipeline.execution_mode)
