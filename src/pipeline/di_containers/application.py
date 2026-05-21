"""
Master dependency injection container for the entire pipeline.

This container orchestrates all phase-specific containers and wires them together
into a cohesive application. It provides the PipelineExecutor with fully configured
coordinators for each phase, ensuring proper dependency injection throughout.

Architecture:
1. Core infrastructure (storage, logging, caching)
2. Phase-specific domain containers (8 phases)
3. Pipeline executor with injected coordinators
"""

from dependency_injector import containers, providers

from .core import CoreContainer
from .orbit_collection import OrbitCollectionContainer
from .orbit_processing import OrbitProcessingContainer
from .env_collection import EnvironmentCollectionContainer
from .env_processing import EnvironmentProcessingContainer
from .env_synthesis import EnvironmentSynthesisContainer
from .atmospheric_features import AtmosphericFeaturesContainer
from .timeseries import TimeSeriesContainer
from .modeling import MLContainer

from src.pipeline.orchestration.pipeline_executor import PipelineExecutor

class ApplicationContainer(containers.DeclarativeContainer):

    config = providers.Configuration()

    # Core infrastructure services (singleton across all phases)
    core = providers.Container(
        CoreContainer,
        config=config)

    # Phase 1: Orbital collection → orbit container
    orbit = providers.Container(
        OrbitCollectionContainer,
        core=core,
        config=config)

    # Phase 2: Orbital processing → orbit_processing container
    orbit_processing = providers.Container(
        OrbitProcessingContainer,
        core=core,
        config=config)

    # Phase 3: Orbital feature engineering → atmospheric_features container
    atmospheric_features = providers.Container(
        AtmosphericFeaturesContainer,
        core=core,
        config=config)

    # Phase 4: Environmental collection → environment container
    environment = providers.Container(
        EnvironmentCollectionContainer,
        core=core,
        config=config)

    # Phase 5: Environmental processing → environment_processing container
    environment_processing = providers.Container(
        EnvironmentProcessingContainer,
        core=core,
        config=config)

    # Phase 6: Environmental synthesis → environment_synthesis container
    environment_synthesis = providers.Container(
        EnvironmentSynthesisContainer,
        core=core,
        config=config)

    # Phase 7: Time series integration → time_series container
    time_series = providers.Container(
        TimeSeriesContainer,
        core=core,
        config=config)

    # Phase 8: Model training → ml container
    ml = providers.Container(
        MLContainer,
        core=core,
        config=config)

    # Pipeline executor with all phase coordinators injected
    pipeline_executor = providers.Singleton(
        PipelineExecutor,
        logger=core.logger,
        orbit_collection_coordinator=orbit.coordinator,
        orbit_processing_coordinator=orbit_processing.coordinator,
        env_collection_coordinator=environment.coordinator,
        env_processing_coordinator=environment_processing.coordinator,
        env_synthesis_coordinator=environment_synthesis.coordinator,
        feature_coordinator=atmospheric_features.coordinator,
        timeseries_coordinator=time_series.coordinator,
        training_coordinator=ml.coordinator)