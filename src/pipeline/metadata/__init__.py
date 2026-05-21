"""
Pipeline metadata module.
Handles metadata persistence and run history tracking.
"""

from src.pipeline.metadata.service import MetadataService
from src.pipeline.metadata.contracts.dataset_metadata import DatasetMetadata
from src.pipeline.metadata.contracts.run_history import RunHistory
from src.pipeline.metadata.contracts.phase_execution import PhaseExecution
from src.pipeline.metadata.contracts.model_training import ModelTrainingRun, ModelDeployment
from src.pipeline.metadata.contracts.data_freshness import DataSourceFreshness
from src.shared.quota.quota_snapshot import QuotaDailySnapshot
from src.pipeline.metadata.repository import MetadataRepository

__all__ = [
    "MetadataService",
    "DatasetMetadata",
    "RunHistory",
    "PhaseExecution",
    "ModelTrainingRun",
    "ModelDeployment",
    "DataSourceFreshness",
    "QuotaDailySnapshot",
    "MetadataRepository",
]
