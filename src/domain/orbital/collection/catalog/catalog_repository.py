from structlog.stdlib import BoundLogger
from typing import List, Optional, cast, Dict, Any

from src.shared.storage.s3_adapter import S3StorageAdapter
from src.domain.orbital.collection.catalog.catalog_schema import SatelliteCatalog, SatelliteCategory


class SatCatalogRepository:
    """
    S3 persistence layer for satellite catalog lists.
    Abstracts the S3 key paths and serialization logic.
    """

    def __init__(self,
                 logger: BoundLogger,
                 orbit_data_bucket: str,
                 satcat_prefix: str,
                 storage_adapter: S3StorageAdapter) -> None:

        self.logger = logger
        self.orbit_data_bucket = orbit_data_bucket
        self.storage_adapter = storage_adapter
        self.satcat_prefix = satcat_prefix

    def save_satellite_list(self,
                            satellite_items: List[Dict[str, Any]],
                            category: SatelliteCategory,
                            seed: Optional[int] = None) -> bool:
        """Saves the satellite list for the given category to S3."""
        key = self._get_s3_key(category)
        ids = [item["id"] for item in satellite_items]

        catalog = SatelliteCatalog(
            category=category,
            satellite_ids=ids,
            satellite_metadata=satellite_items,
            seed=seed)

        data = catalog.model_dump(mode='json', exclude_none=True)
        success = self.storage_adapter.save_json_data(self.orbit_data_bucket, key, data)

        if success:
            self.logger.info("catalog_saved_to_s3", category=category, count=len(ids), key=key)
        else:
            self.logger.error("catalog_save_failed", category=category, key=key)

        return success

    def load_satellite_list(self, category: SatelliteCategory) -> Optional[List[str]]:
        key = self._get_s3_key(category)
        try:
            data = self.storage_adapter.load_json_data(self.orbit_data_bucket, key)
            if not data:
                self.logger.debug("catalog_cache_miss", category=category, key=key)
                return None

            ids = cast(List[str], data['satellite_ids'])
            self.logger.debug("catalog_cache_hit", category=category, count=len(ids))
            return ids

        except Exception as e:
            self.logger.error("catalog_load_error", category=category, error=str(e))
            return None

    def _get_s3_key(self, category: SatelliteCategory) -> str:
        """Returns the S3 key for the given catalog category."""
        return f"{self.satcat_prefix}/{category}_satellites.json"
