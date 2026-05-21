"""
Shared utilities and infrastructure components.
Re-exports commonly used classes for cleaner imports.

Note: CheckpointGuard and CollectionFreshnessPolicy are intentionally
NOT re-exported here — they depend on src.pipeline.contracts and
src.pipeline.metadata, which would create a circular import chain.
Import them directly from their modules when needed:
  from src.pipeline.policies.checkpoint_guard import CheckpointGuard
  from src.pipeline.policies.collection_freshness_policy import CollectionFreshnessPolicy
"""

from src.shared.utils.execution_request import ExecutionRequest
from src.shared.storage.s3_adapter import S3StorageAdapter
from src.shared.quota.quota_manager import ApiQuotaManager
from src.shared.utils.hashing_service import HashingService

__all__ = [
    "ExecutionRequest",
    "S3StorageAdapter",
    "ApiQuotaManager",
    "HashingService",
]
