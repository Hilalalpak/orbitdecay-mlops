"""
Top-level DI container. Wires one sub-container per phase and hands all
8 coordinators to PhaseExecutor. Everything here is a singleton.
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

from src.pipeline.orchestration.phase_executor import PhaseExecutor

class ApplicationContainer(containers.DeclarativeContainer):

    config = providers.Configuration()

    # shared infra: storage, logger, cache, quota, metadata
    core = providers.Container(
        CoreContainer,
        config=config)

    # Phase 1 — orbital collection
    orbit = providers.Container(
        OrbitCollectionContainer,
        core=core,
        config=config)

    # Phase 2 — orbital processing
    orbit_processing = providers.Container(
        OrbitProcessingContainer,
        core=core,
        config=config)

    # Phase 4 — environmental collection
    environment = providers.Container(
        EnvironmentCollectionContainer,
        core=core,
        config=config)

    # Phase 5 — environmental processing
    environment_processing = providers.Container(
        EnvironmentProcessingContainer,
        core=core,
        config=config)

    # Phase 6 — environmental synthesis
    environment_synthesis = providers.Container(
        EnvironmentSynthesisContainer,
        core=core,
        config=config)

    # Phase 3 — orbital feature engineering
    atmospheric_features = providers.Container(
        AtmosphericFeaturesContainer,
        core=core,
        config=config)

    # Phase 7 — time series integration
    time_series = providers.Container(
        TimeSeriesContainer,
        core=core,
        config=config)

    # Phase 8 — model training
    ml = providers.Container(
        MLContainer,
        core=core,
        config=config)

    pipeline_executor = providers.Singleton(
        PhaseExecutor,
        logger=core.logger,
        orbit_collection_coordinator=orbit.coordinator,
        orbit_processing_coordinator=orbit_processing.coordinator,
        env_collection_coordinator=environment.coordinator,
        env_processing_coordinator=environment_processing.coordinator,
        env_synthesis_coordinator=environment_synthesis.coordinator,
        feature_coordinator=atmospheric_features.coordinator,
        timeseries_coordinator=time_series.coordinator,
        training_coordinator=ml.coordinator)