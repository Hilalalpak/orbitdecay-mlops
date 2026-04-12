"""
Orbit collection phase coordinator.

Orchestrates the complete orbital data collection workflow by coordinating
satellite selection, cache decisions, collection strategy execution, and
metadata tracking. Acts as the central controller for Phase 1.

Workflow:
1. Satellite target selection (dynamic or fallback)
2. Execution request creation with configuration
3. Cache decision (batch vs incremental)
4. Strategy execution (collect or skip)
5. Manifest preparation for Phase 2
6. Metadata persistence
"""

import time
from typing import Optional

from structlog.stdlib import BoundLogger
from src.domains.schemas.orbital_collection_schema import Phase1Result
from src.domains.orbital_data.collection.strategy_runner import StrategyRunner
from src.pipeline.coordinators.phase1_orbital_collection.components.cache_handler import CacheHandler
from src.pipeline.coordinators.phase1_orbital_collection.components.errors import ErrorPolicy
from src.pipeline.coordinators.phase1_orbital_collection.components.request import RequestBuilder
from src.pipeline.coordinators.phase1_orbital_collection.components.selector import SatelliteSelector


class OrbitCollectionCoordinator:

    def __init__(self,
                 logger: BoundLogger,
                 execution_mode: str,
                 target_date: Optional[str],
                 selector: SatelliteSelector,
                 request_builder: RequestBuilder,
                 error_handler: ErrorPolicy,
                 runner: StrategyRunner,
                 cache_handler: CacheHandler) -> None:

        self.logger = logger
        self.exec_mode = execution_mode
        self.date = target_date

        # Core services
        self.selector = selector
        self.request = request_builder
        self.error_handler = error_handler

        # External operators
        self.runner = runner
        self.cache = cache_handler

    def run_phase(self) -> Phase1Result:
        """Runs the complete orbit collection pipeline from start to finish."""
        phase_start = time.time()

        try:
            # 1. Identify targets
            satellites = self.selector.resolve()
            if not satellites:
                self.logger.error("No target satellites found to process. Aborting Phase 1.")
                return Phase1Result(
                    success=False,
                    execution_time=time.time() - phase_start,
                    exec_mode=self.exec_mode,
                    reason="no_satellites_available")

            # 2. Build Request & Strategy
            request = self.request.build(satellites)
            decision = self.cache.choose(request)

            # 3. Execute Strategy
            result = self.runner.run_strategy(decision, request, satellites)
            if not result:
                self.logger.error("Collection strategy failed to return a result.")
                return Phase1Result(
                    success=False,
                    execution_time=time.time() - phase_start,
                    exec_mode=self.exec_mode,
                    reason="no_data_retrieved")

            # 4. Prepare Manifest
            manifest = self.runner.prepare_output_manifest(result, request)
            if not manifest:
                self.logger.error("Data was retrieved but no data/manifest was created. No data to process.")
                return Phase1Result(
                    success=False,
                    execution_time=time.time() - phase_start,
                    exec_mode=self.exec_mode,
                    reason="manifest_creation_failed")

            # 5. Metadata & Completion
            self.cache.store_execution_metadata(result, decision, request, manifest)

            self.logger.info("Phase 1 complete. Passing processing manifest to Phase 2.")
            return Phase1Result(
                success=True,
                satellites_processed=len(satellites),
                processing_failures=0,
                execution_time=time.time() - phase_start,
                exec_mode=self.exec_mode,
                processing_manifest=manifest,
                collection_hash=request.hash)

        except Exception as e:
            return self.error_handler.format(e, time.time() - phase_start)