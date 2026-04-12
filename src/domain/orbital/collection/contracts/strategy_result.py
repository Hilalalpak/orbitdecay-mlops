from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from src.domain.orbital.collection.metrics.batch_telemetry import BatchCollectionStats

class CollectionStrategy(str, Enum):
    """Phase 1 collection strategy types."""
    BATCH = "batch_collection"
    INCREMENTAL_SYNC = "incremental_sync"
    CACHE_REUSE = "cache_reuse"


class BaseStrategyResult(BaseModel):
    """Base result schema for all collection strategies."""
    model_config = ConfigDict(frozen=True, extra='forbid')

    mode: CollectionStrategy
    param_hash: str = Field(..., min_length=8, max_length=64)
    manifest_files: List[str] = Field(default_factory=list)
    total_records: int = Field(default=0, ge=0)

class BatchStrategyResult(BaseStrategyResult):
    mode: Literal[CollectionStrategy.BATCH] = CollectionStrategy.BATCH
    stats: BatchCollectionStats

class IncrementalStrategyResult(BaseStrategyResult):
    mode: Literal[CollectionStrategy.INCREMENTAL_SYNC] = CollectionStrategy.INCREMENTAL_SYNC
    api_calls_count: int = Field(default=0, ge=0)

class CachedStrategyResult(BaseStrategyResult):
    mode: Literal[CollectionStrategy.CACHE_REUSE] = CollectionStrategy.CACHE_REUSE
