from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional
from src.pipeline.metadata.contracts.pipeline_runs import PipelineRunMetadata
from src.pipeline.metadata.contracts.phase_execution import PhaseExecution
from src.pipeline.metadata.execution.repository import PipelineExecutionRepository


class PipelineExecutionService:

    def __init__(self, repository: PipelineExecutionRepository):
        self.repository = repository

    def start_pipeline_run(self, pipeline_name: str, execution_mode: str,
                            target_date: str, parameters: dict) -> UUID:
        run = PipelineRunMetadata(
            run_id=uuid4(),
            pipeline_name=pipeline_name,
            execution_mode=execution_mode,
            target_date=target_date,
            parameters=parameters,
            start_time=datetime.utcnow(),
            status="running")
        self.repository.insert_pipeline_run(run)
        return run.run_id

    def finish_pipeline_run(self, run_id: UUID, status: str,
                             error: Optional[str] = None) -> None:
        self.repository.finish_pipeline_run(
            run_id, status, datetime.utcnow(), error)

    def record_phase_execution(
            self,
            run_id: UUID,
            phase_name: str,
            phase_index: int,
            start_time: datetime,
            end_time: Optional[datetime] = None,
            status: Optional[str] = None,
            is_incremental: bool = False,
            records_in: Optional[int] = None,
            records_out: Optional[int] = None,
            records_failed: Optional[int] = None,
            skip_reason: Optional[str] = None,
            error_message: Optional[str] = None) -> None:

        duration_sec = (
            (end_time - start_time).total_seconds()
            if end_time and start_time else None
        )
        record = PhaseExecution(
            run_id=run_id,
            phase_name=phase_name,
            phase_index=phase_index,
            start_time=start_time,
            end_time=end_time,
            duration_sec=duration_sec,
            status=status,
            is_incremental=is_incremental,
            records_in=records_in,
            records_out=records_out,
            records_failed=records_failed,
            skip_reason=skip_reason,
            error_message=error_message,
        )
        self.repository.insert_phase_execution(record)

    def get_phase_executions(self, run_id: str):
        return self.repository.get_phase_executions_for_run(run_id)
