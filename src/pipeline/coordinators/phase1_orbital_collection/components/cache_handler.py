"""
This module acts as the brain of the operation, checking the cache to see if we
really need to go out and fetch fresh data or if we can skip it.
"""
from structlog.stdlib import BoundLogger
from src.domains.schemas.orbital_collection_schema import StrategyResult
from src.core.caching.cache_manager import CacheManager
from src.core.metadata_tracker import PipelineMetadataTracker
from src.pipeline.utilities.execution_request import ExecutionRequest
from typing import Dict, List, Union

class CacheHandler:

    def __init__(self, cache_manager: CacheManager, metadata_tracker: PipelineMetadataTracker, logger: BoundLogger) -> None:
        self.cache = cache_manager
        self.logger = logger
        self.metadata = metadata_tracker

    def choose(self, execution_request: ExecutionRequest) -> Dict[str, Union[bool, str]]:
        """Consults the cache manager to determine the best strategy for handling this specific request."""
        return self.cache.should_collect_data(execution_request)


    def store_execution_metadata(self, collection_result: StrategyResult, decision: Dict[str, Union[bool, str]], execution_request: ExecutionRequest, data_to_process: List[str]) -> None:
        """Records metadata about how this collection was performed for tracking and audit purposes."""
        if decision.get('collection_mode') == 'use_cached':
            return

        try:
            total_records = collection_result.total_records

            execution_details = {'processing_stage': 'orbital_collection',
                                'records_processed': total_records,
                                'batch_files_created': len(data_to_process) if collection_result.mode != 'incremental' else 0,
                                'collection_strategy': decision.get('collection_mode'),
                                'collection_mode': collection_result.mode}

            self.metadata.record_collection_execution(execution_request, execution_details)

        except Exception as meta_error:
            self.logger.error(f"Metadata recording failed: {meta_error}", exc_info=True)
            self.logger.warning("Execution continues, but lineage information may be incomplete.")