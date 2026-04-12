"""
Pipeline metadata module. Provides database-backed tracking of pipeline runs,
phase outputs, and run history for duplicate detection and caching.
"""

from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.metadata.repository import MetadataRepository

__all__ = [
    "MetadataService",
    "DatasetMetadata",
    "RunHistory",
    "MetadataRepository",
]
