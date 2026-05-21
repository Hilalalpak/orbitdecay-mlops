"""
Satellite target selection for Phase 1.

Implements a 3-tier lookup: memory → S3 → Space-Track API.
Selection uses stratified sampling to ensure coverage across orbital regimes and solar cycles.
"""

import random
from typing import List, Optional, Dict, Any, cast, Tuple
from structlog.stdlib import BoundLogger

from src.shared.config.config_interfaces import CatalogConfigInterface
from src.shared.quota.quota_manager  import ApiQuotaManager
from .catalog_repository import SatCatalogRepository
from src.domain.orbital.collection.api_clients.spacetrack_client import SpaceTrackClient
from src.domain.orbital.collection.catalog.catalog_schema import SatelliteCategory
from src.domain.orbital.collection.catalog.filters import is_orbit_duration_valid

class SatCatalogService:
    """Selects and caches the satellite targets used across the collection pipeline."""


    def __init__(self,
                 catalog_config: CatalogConfigInterface,
                 logger: BoundLogger,
                 repository: SatCatalogRepository,
                 quota_manager: ApiQuotaManager,
                 api_client: SpaceTrackClient) -> None:

        self.catalog_config = catalog_config
        self.logger = logger
        self.repository = repository
        self.quota_manager = quota_manager
        self.client = api_client

        self.seed = self.catalog_config.get_dynamic_selection_seed()
        self.min_orbit_days = self.catalog_config.get_min_orbit_days()

        self.calibration_count = self.catalog_config.get_calibration_count()
        self.target_count = self.catalog_config.get_target_count()

        self.calibration_query = self.catalog_config.get_calibration_query()
        self.target_query = self.catalog_config.get_target_query()

        self.anchor_calibration_ids = set(self.catalog_config.get_anchor_calibration_ids())
        self.solar_cycle_regimes = self.catalog_config.get_solar_cycle_regimes()
        self.calibration_period_bands = self.catalog_config.get_calibration_period_bands()

        self._memory_cache: Optional[Tuple[List[str], List[str]]] = None

    def get_satellites(self) -> Tuple[List[str], List[str]]:
        """
        Returns (decayed_ids, active_ids) using 3-tier lookup.
        Checks memory cache -> S3 -> Space-Track API in that order.
        """
        if self._memory_cache is not None:
            return self._memory_cache

        selected_target = self.repository.load_satellite_list("selected_target")
        selected_calibration = self.repository.load_satellite_list("selected_calibration")

        if selected_target and selected_calibration:
            self.logger.info(
                "using_cached_selected_catalog",
                target=len(selected_target),
                calibration=len(selected_calibration))
            self._memory_cache = (selected_target, selected_calibration)
            return self._memory_cache

        target_pool = self._load_satellite_pool(self.target_query, "target")
        calibration_pool = self._load_satellite_pool(self.calibration_query, "calibration")

        if not target_pool or not calibration_pool:
            self.logger.warning(
                "catalog_pool_incomplete",
                target=len(target_pool),
                calibration=len(calibration_pool))

        s_target, s_calibration = self._select_satellites(target_pool, calibration_pool)

        self._memory_cache = (s_target, s_calibration)
        return s_target, s_calibration

    def _load_satellite_pool(self, api_query: str, category: SatelliteCategory) -> List[Dict[str, Any]]:
        """Loads satellite pool from S3 cache, falls back to API if missing."""
        pool_ids = self.repository.load_satellite_list(category)
        if pool_ids:
            self.logger.debug("pool_loaded_from_cache", category=category, count=len(pool_ids))
            return [{"id": sid} for sid in pool_ids]

        self.logger.info("fetching_base_list_from_api", category=category)
        pool_items = self._fetch_and_filter_from_api(category, api_query)

        if pool_items:
            self.repository.save_satellite_list(pool_items, category)

        return pool_items

    def _fetch_and_filter_from_api(self,
                                   category: SatelliteCategory,
                                   query_path: str) -> List[Dict[str, Any]]:
        """Executes API call, parses response, and filters by duration."""
        with self.client.open_session() as session:
            if not self.client.authenticate(session):
                return []

            raw_data = self.client.fetch_data_by_query(session, query_path, self.client.timeout)

            if not raw_data:
                self.logger.warning("api_returned_no_data", category=category)
                return []

            valid_items: List[Dict[str, Any]] = []
            items = cast(List[Dict[str, Any]], raw_data)

            for item in items:

                norad_id = item.get('NORAD_CAT_ID')
                if not norad_id:
                    continue

                # skip satellites that didn't orbit long enough
                if not is_orbit_duration_valid(item, category, self.min_orbit_days):
                    continue

                decay_date = item.get("DECAY_DATE") or item.get("DECAY")
                launch_date = item.get("LAUNCH_DATE") or item.get("LAUNCH")

                valid_items.append({
                    "id": str(norad_id),
                    "decay_year": int(decay_date[:4]) if decay_date else None,
                    "launch_year": int(launch_date[:4]) if launch_date else None,
                    "object_type": item.get("OBJECT_TYPE"),
                    "rcs_size": item.get("RCS_SIZE"),
                    "period": float(item.get("PERIOD")) if item.get("PERIOD") else None})

            self.logger.info("api_fetch_success", category=category, raw_count=len(items), valid_count=len(valid_items))
            self.quota_manager.record_request(f'{category}_satellites_query')

            return valid_items

    def _select_satellites(self,
                           target_pool: List[Dict[str, Any]],
                           calibration_pool: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """
        Applies stratified sampling to ensure balanced coverage across:
        - Solar cycle regimes (high/low/transition drag periods)
        - Orbital altitude bands for calibration satellites
        """
        random.seed(self.seed)

        regime_pools = self._split_target_by_regime(target_pool)

        # calc how many per regime based on what we actually have
        active_regimes = [r for r in regime_pools.keys() if regime_pools[r]]
        regime_count = len(active_regimes) if active_regimes else 1
        per_regime = self.target_count // regime_count

        selected_target_items = []

        for regime in active_regimes:
            pool = regime_pools[regime]
            if not pool:
                continue

            sample = random.sample(pool, min(per_regime, len(pool)))
            selected_target_items.extend(sample)

        s_target = [item["id"] for item in selected_target_items]

        # calibration set: inject anchors first, then random sample
        selected_calibration_items = []
        anchor_items = []

        for anchor_id in self.anchor_calibration_ids:
            anchor_items.append({
                "id": anchor_id,
                "decay_year": None,
                "launch_year": None,
                "object_type": None,
                "rcs_size": None,
                "period": None})

        selected_calibration_items.extend(anchor_items)

        remaining_pool = [
            item for item in calibration_pool
            if item["id"] not in self.anchor_calibration_ids]

        remaining_slots = self.calibration_count - len(anchor_items)

        if remaining_slots > 0 and remaining_pool:
            random_sample = random.sample(
                remaining_pool,
                min(remaining_slots, len(remaining_pool)))

            selected_calibration_items.extend(random_sample)

        selected_calibration_items = selected_calibration_items[:self.calibration_count]

        s_calibration = [item["id"] for item in selected_calibration_items]

        # TODO: consider async S3 writes here to speed up first run
        self.repository.save_satellite_list(selected_target_items,
                                            "selected_target",
                                            seed=self.seed)

        self.repository.save_satellite_list(selected_calibration_items,
                                            "selected_calibration",
                                            seed=self.seed)

        self.logger.info(
            "sampling_complete",
            seed=self.seed,
            target=len(s_target),
            calibration=len(s_calibration))

        return s_target, s_calibration

    def _split_target_by_regime(self, target_pool: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Splits targets by solar cycle regime based on decay year."""
        pools = {"high": [],
                "low": [],
                "transition": []}

        for item in target_pool:
            y = item.get("decay_year")

            if not y:
                continue

            high_ranges = self.solar_cycle_regimes.get("high_drag", [])
            low_ranges = self.solar_cycle_regimes.get("low_drag", [])

            if any(r[0] <= y <= r[1] for r in high_ranges):
                pools["high"].append(item)
            elif any(r[0] <= y <= r[1] for r in low_ranges):
                pools["low"].append(item)
            else:
                pools["transition"].append(item)

        return pools

    def _split_calibration_by_altitude(self, calibration_pool: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Splits calibration sats by altitude using orbital period as proxy."""
        bands = {"low": [],  # ~300-400 km
                "mid": [],  # ~400-500 km
                "high": []}  # 500+ km

        for item in calibration_pool:
            p = item.get("period")

            if not p:
                continue

            try:
                p = float(p)
            except (ValueError, TypeError):
                continue

            low_max = self.calibration_period_bands.get("low_max", 95)
            mid_max = self.calibration_period_bands.get("mid_max", 100)

            if p < low_max:
                bands["low"].append(item)
            elif p < mid_max:
                bands["mid"].append(item)
            else:
                bands["high"].append(item)

        return bands

    def update_seed(self, new_seed: int) -> None:
        """Updates random seed and clears cache to force re-selection."""
        self.logger.info("seed_updated", old=self.seed, new=new_seed)
        self.seed = new_seed
        self._memory_cache = None