"""
Feature engineering pipeline for orbital data.
Applies physics-based calculations to orbital history via parallel processing.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from structlog.stdlib import BoundLogger
from typing import List, Tuple
from src.domain.orbital.features.feature_validator import FeatureRecordValidator
from src.domain.orbital.features.orbital_repository import OrbitalDataRepository

from src.domain.orbital.features.generators.physics_features import PhysicsDerivedGenerator
from src.domain.orbital.features.generators.angular_features import CyclicOrbitalFeatureGenerator
from src.domain.orbital.features.generators.spatiotemporal_features import SpatioTemporalFeatureGenerator
from src.domain.orbital.features.generators.targets import TargetLabelGenerator
from src.domain.orbital.features.generators.state_vector_features import StateVectorFeatureGenerator
from src.domain.orbital.features.metrics.phase3_telemetry import FeatureGenerationStats

from enum import Enum

class DatasetRole(str, Enum):
    ACTIVE = "active"
    DECAYED = "decayed"

class OrbitalFeatureGenerator:
    """
    Enriches orbital history with physics-based features.
    Processes satellites in parallel and persists results to S3.
    """

    def __init__(self,
                 max_workers: int,
                 logger: BoundLogger,
                 state_vector_generator: StateVectorFeatureGenerator,
                 feature_validator: FeatureRecordValidator,
                 physics_generator: PhysicsDerivedGenerator,
                 cyclic_generator: CyclicOrbitalFeatureGenerator,
                 spatiotemporal_generator: SpatioTemporalFeatureGenerator,
                 target_generator: TargetLabelGenerator,
                 data_repository: OrbitalDataRepository) -> None:

        self.logger = logger
        self.max_workers = max_workers

        self.validator = feature_validator
        self.data_repository = data_repository

        self.physics_generator = physics_generator
        self.cyclic_generator = cyclic_generator
        self.spatiotemporal_generator = spatiotemporal_generator
        self.target_generator = target_generator
        self.state_vector_generator = state_vector_generator

    def process_all_satellites(self,
                               manifest: List[str],
                               is_incremental: bool = False) -> Tuple[FeatureGenerationStats, List[str]]:
        """
        Processes satellite history files in parallel.
        Returns (FeatureGenerationStats, manifest of generated S3 keys).
        """
        start_time = time.time()
        if is_incremental:
            target_keys = [path for path in manifest if '/updates/delta_' in path and path.endswith('.parquet')]
        else:
            target_keys = [path for path in manifest if 'orbital_history_latest.parquet' in path]

        if not target_keys:
            self.logger.warning("no_processable_files_found_in_manifest")
            return FeatureGenerationStats(
                satellites_total=0,
                successfully_processed=0,
                processing_failures=0,
                execution_time=0.0,
                workers_utilized=self.max_workers), []

        self.logger.debug("feature_generation_started", target_count=len(target_keys), max_workers=self.max_workers)

        total_manifest: List[str] = []
        failures = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_key = {executor.submit(self._process_satellite, key, is_incremental): key
                             for key in target_keys}

            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    produced_paths = future.result()
                    if produced_paths:
                        total_manifest.extend(produced_paths)
                    else:
                        failures += 1
                except Exception as e:
                    self.logger.error("satellite_feature_processing_failed",
                                      source_key=key,
                                      error=str(e))
                    failures += 1

        self.logger.debug("feature_generation_completed", generated_files=len(total_manifest))

        stats = FeatureGenerationStats(
            satellites_total=len(target_keys),
            successfully_processed=len(target_keys) - failures,
            processing_failures=failures,
            execution_time=time.time() - start_time,
            workers_utilized=self.max_workers)

        return stats, total_manifest

    def _process_satellite(self, s3_key: str, is_incremental: bool = False) -> List[str]:
        """Loads, enriches, and saves features for a single satellite."""
        if "/active/" in s3_key:
            dataset_role = DatasetRole.ACTIVE
        elif "/decayed/" in s3_key:
            dataset_role = DatasetRole.DECAYED
        else:
            raise ValueError(f"Cannot infer dataset role from path: {s3_key}")

        sat_id = s3_key.split('/')[3]

        df = self.data_repository.load_data_by_key(s3_key)
        if df.is_empty():
            return []

        df = self.physics_generator.apply(df)
        df = self.state_vector_generator.apply(df)
        df = self.cyclic_generator.apply(df)
        df = self.spatiotemporal_generator.apply(df)
        df = self.target_generator.apply(df)

        df = self.validator.validate(df)
        if df.is_empty():
            self.logger.warning("all_features_invalidated", sat_id=sat_id)
            return []

        return self.data_repository.save_enhanced_data(sat_id, df, dataset_role, is_incremental)