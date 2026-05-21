import json
from src.pipeline.metadata.contracts.pipeline_runs import PipelineRunMetadata
from src.pipeline.metadata.contracts.phase_execution import PhaseExecution


class PipelineExecutionRepository:

    def __init__(self, connection):
        self.connection = connection

    def insert_pipeline_run(self, run: PipelineRunMetadata) -> None:
        query = """
        INSERT INTO pipeline_runs
        (run_id, pipeline_name, execution_mode, target_date,
         parameters, start_time, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(run.run_id),
                run.pipeline_name,
                run.execution_mode,
                run.target_date,
                json.dumps(run.parameters),
                run.start_time,
                run.status))
        self.connection.commit()

    def finish_pipeline_run(self, run_id, status, end_time, error=None) -> None:
        query = """
        UPDATE pipeline_runs
        SET status=%s, end_time=%s, error_message=%s
        WHERE run_id=%s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (status, end_time, error, str(run_id)))
        self.connection.commit()

    def insert_phase_execution(self, record: PhaseExecution) -> None:
        query = """
        INSERT INTO phase_executions
        (run_id, phase_name, phase_index, start_time, end_time,
         duration_sec, status, is_incremental,
         records_in, records_out, records_failed, skip_reason, error_message)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(record.run_id),
                record.phase_name,
                record.phase_index,
                record.start_time,
                record.end_time,
                record.duration_sec,
                record.status,
                record.is_incremental,
                record.records_in,
                record.records_out,
                record.records_failed,
                record.skip_reason,
                record.error_message,
            ))
        self.connection.commit()

    def get_phase_executions_for_run(self, run_id: str):
        query = """
        SELECT phase_name, phase_index, start_time, end_time,
               duration_sec, status, is_incremental,
               records_in, records_out, records_failed, skip_reason, error_message
        FROM phase_executions
        WHERE run_id = %s
        ORDER BY phase_index ASC
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (run_id,))
            return cursor.fetchall()
