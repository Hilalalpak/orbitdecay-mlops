"""
Strategy router for orbital collection.
Dispatches to batch, incremental, or cache-reuse based on execution decision.
"""

from structlog.stdlib import BoundLogger

from src.domain.orbital.collection.contracts.strategy_result import (
    BaseStrategyResult,
    CachedStrategyResult,
    IncrementalStrategyResult,
    BatchStrategyResult
)
from src.domain.orbital.collection.strategies.batch_collection import BatchCollector
from src.domain.orbital.collection.strategies.incremental_collection import IncrementalCollector
from src.shared import ExecutionRequest
from src.pipeline.contracts import ExecutionDecision, ExecutionMode

class StrategyRunner:
    """Dispatches to the appropriate collection strategy based on execution mode."""

    def __init__(self,
                 logger: BoundLogger,
                 batch_strategy: BatchCollector,
                 incremental_strategy: IncrementalCollector) -> None:

        self.logger = logger
        self.batch_strategy = batch_strategy
        self.incr_strategy = incremental_strategy

    def run_strategy(self, decision: ExecutionDecision, request: ExecutionRequest) -> BaseStrategyResult:
        self.logger.debug("strategy_dispatching", mode=decision.mode.value)

        if decision.mode == ExecutionMode.REUSE:
            return self._return_cached_result(decision)
        if decision.mode == ExecutionMode.INCREMENTAL:
            return self._run_incremental(request)
        if decision.mode in (ExecutionMode.RUN, ExecutionMode.FORCED):
            return self._run_batch(request)

        raise ValueError(f"Unhandled execution mode: {decision.mode}")

    def _return_cached_result(self, decision: ExecutionDecision) -> CachedStrategyResult:
        return CachedStrategyResult(
            param_hash=decision.param_hash,
            manifest_files=decision.produced_manifest)

    def _run_incremental(self, request: ExecutionRequest) -> IncrementalStrategyResult:
        result = self.incr_strategy.execute(request)
        return result

    def _run_batch(self, request: ExecutionRequest) -> BatchStrategyResult:
        return self.batch_strategy.execute(request)
