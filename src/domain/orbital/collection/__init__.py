"""
Phase 1 orchestration layer for orbital data collection.

This package provides a higher-level, SRP-friendly wrapper around:
- OrbitDataCollectionCoordinator
- StrategyRunner
- StrategyEngine

Existing method bodies in those classes are NOT modified. These classes
simply delegate to them to keep behavior identical while improving structure.
"""

from src.domain.orbital.collection.repository.orbital_collection_repository import OrbitalCollectionRepository
from src.domain.orbital.collection.api_clients.spacetrack_client import SpaceTrackClient
from src.domain.orbital.collection.orbital_data_fetcher import OrbitalDataFetcher
from src.domain.orbital.collection.catalog.catalog_service import SatCatalogService

__all__ = [
    "OrbitalCollectionRepository",
    "SpaceTrackClient",
    "OrbitalDataFetcher",
    "SatCatalogService",
]