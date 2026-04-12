"""
This script decides exactly which satellites make the cut for processing, choosing
between a dynamic list from the catalog or a static fallback list if things go wrong.
"""

from typing import List
from structlog.stdlib import BoundLogger
from src.domains.orbital_data.collection.orbital_data_fetcher import OrbitalDataFetcher

class SatelliteSelector:
    def __init__(self, dynamic_selection: bool, fallback_list: List[int], collector: OrbitalDataFetcher, logger: BoundLogger) -> None:
        self.dynamic_selection = dynamic_selection
        self.fallback_list = fallback_list
        self.collector = collector
        self.logger = logger

    def resolve(self) -> List[int]:
        """Figures out the final list of satellite IDs to use, prioritizing dynamic selection over the fallback."""
        if self.dynamic_selection:
            try:
                self.logger.info("Attempting to load dynamic satellite list...")
                dynamic_ids = self.collector.list_satellites()
                self.logger.info(f"Successfully loaded a dynamic list with {len(dynamic_ids)} satellites.")
                return [int(sat_id) for sat_id in dynamic_ids]

            except Exception as e:
                self.logger.error(f"Failed to load dynamic satellite list: {e}. Falling back to static configuration.")
                return self.fallback_list
        else:
            self.logger.info("Dynamic selection disabled. Using fallback.")
            return self.fallback_list