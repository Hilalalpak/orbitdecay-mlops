"""
Provides the environment data loader, the orbital physics engine, and the main coordinator
responsible for producing ML-ready feature datasets.
"""

from dependency_injector import containers, providers

from src.domain.orbital.features.core.orbital_feature_generator import OrbitalFeatureGenerator
from src.domain.orbital.features.feature_validator import FeatureRecordValidator
from src.pipeline.coordinators.phase3_orbital_features.atmospheric_feature_coordinator import FeatureEngineeringCoordinator
from src.pipeline.monitoring.performance_monitor import PerformanceMonitor
from src.domain.orbital.features.orbital_repository import OrbitalDataRepository
from ..coordinators.phase3_orbital_features.components.checkpoint_handler import FeatureCheckpointHandler

from src.domain.orbital.features.generators.physics_features import PhysicsDerivedGenerator
from src.domain.orbital.features.generators.angular_features import CyclicOrbitalFeatureGenerator
from src.domain.orbital.features.generators.spatiotemporal_features import SpatioTemporalFeatureGenerator
from src.domain.orbital.features.generators.targets import TargetLabelGenerator
from src.domain.orbital.features.generators.state_vector_features import StateVectorFeatureGenerator


class AtmosphericFeaturesContainer(containers.DeclarativeContainer):

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # Performance tracking
    performance_monitor = providers.Singleton(
        PerformanceMonitor,
        processing_config=config.processing,
        pipeline_config=config.pipeline,
        logging_config=config.logging,
        logger=core.logger.provided.bind.call(module="performance"),
        quota_manager=core.quota_manager,
        storage_adapter=core.storage_adapter)

    orbit_data_repository = providers.Singleton(
        OrbitalDataRepository,
        logger=core.logger.provided.bind.call(module="orbit.repository"),
        storage_adapter=core.storage_adapter,
        orbit_data_prefix=config.pipeline.provided.get_s3_prefix.call('omm_leo'),
        orbit_data_bucket=config.pipeline.provided.get_s3_bucket.call('satellite_data'))

    physics_feature_generator = providers.Singleton(
        PhysicsDerivedGenerator,
        earth_equatorial_radius_km=config.domain.provided.get_earth_equatorial_radius_km.call())

    cyclic_feature_generator = providers.Singleton(
        CyclicOrbitalFeatureGenerator)

    spatiotemporal_feature_generator = providers.Singleton(
        SpatioTemporalFeatureGenerator)

    state_vector_generator=providers.Singleton(
        StateVectorFeatureGenerator,
        logger=core.logger.provided.bind.call(module="feat.statevec"),
        earth_equatorial_radius_km=config.domain.provided.get_earth_equatorial_radius_km.call(),
        far_from_tle_minutes=config.processing.provided.get_far_from_tle_minutes.call())


    target_label_generator = providers.Singleton(
        TargetLabelGenerator)

    feature_validator = providers.Singleton(
        FeatureRecordValidator,
        logger=core.logger.provided.bind.call(module="feat.validator"))
    # Feature engineer
    orbital_feature_engineer = providers.Singleton(
        OrbitalFeatureGenerator,
        logger=core.logger.provided.bind.call(module="orbit.features"),
        feature_validator=feature_validator,
        state_vector_generator=state_vector_generator,
        data_repository=orbit_data_repository,
        physics_generator=physics_feature_generator,
        cyclic_generator=cyclic_feature_generator,
        spatiotemporal_generator=spatiotemporal_feature_generator,
        target_generator=target_label_generator,
        max_workers=config.processing.provided.get_max_workers.call())

    checkpoint_handler = providers.Singleton(
        FeatureCheckpointHandler,
        checkpoint_guard=core.checkpoint_guard,
        pipeline_config=config.pipeline,
        metadata_service=core.metadata_service,
        logger=core.logger.provided.bind.call(module="feat.checkpoint"))

    # Phase coordinator
    coordinator = providers.Singleton(
        FeatureEngineeringCoordinator,
        logger=core.logger.provided.bind.call(module="features"),
        orbital_feature_engineer=orbital_feature_engineer,
        checkpoint_handler=checkpoint_handler,
        metadata_service=core.metadata_service)
