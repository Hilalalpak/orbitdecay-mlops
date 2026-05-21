from src.pipeline.metadata.execution.repository import PipelineExecutionRepository
from src.pipeline.metadata.data_lineage.repository import DataLineageRepository
from src.pipeline.metadata.model_registry.repository import ModelRegistryRepository
from src.shared.quota.repository import QuotaRepository


class MetadataRepository:

    def __init__(self,
                 execution_repo: PipelineExecutionRepository,
                 data_lineage_repo: DataLineageRepository,
                 model_registry_repo: ModelRegistryRepository,
                 quota_repo: QuotaRepository):
        self._execution = execution_repo
        self._data_lineage = data_lineage_repo
        self._model_registry = model_registry_repo
        self._quota = quota_repo

    # --- execution ---
    def insert_pipeline_run(self, run): return self._execution.insert_pipeline_run(run)
    def finish_pipeline_run(self, run_id, status, end_time, error=None): return self._execution.finish_pipeline_run(run_id, status, end_time, error)
    def insert_phase_execution(self, record): return self._execution.insert_phase_execution(record)
    def get_phase_executions_for_run(self, run_id): return self._execution.get_phase_executions_for_run(run_id)

    # --- data lineage ---
    def insert_dataset_metadata(self, meta): return self._data_lineage.insert_dataset_metadata(meta)
    def insert_run_history(self, record): return self._data_lineage.insert_run_history(record)
    def get_run_history(self, param_hash): return self._data_lineage.get_run_history(param_hash)
    def get_latest_run_history(self, param_hash, phase, source_id=None): return self._data_lineage.get_latest_run_history(param_hash, phase, source_id)
    def insert_data_source_freshness(self, record): return self._data_lineage.insert_data_source_freshness(record)
    def get_latest_source_freshness(self, source_id): return self._data_lineage.get_latest_source_freshness(source_id)

    # --- model registry ---
    def insert_model_training_run(self, record): return self._model_registry.insert_model_training_run(record)
    def get_latest_model_training_run(self, model_type): return self._model_registry.get_latest_model_training_run(model_type)
    def insert_model_deployment(self, record): return self._model_registry.insert_model_deployment(record)
    def retire_previous_deployments(self, model_type, environment, replaced_by): return self._model_registry.retire_previous_deployments(model_type, environment, replaced_by)
    def get_active_deployment(self, model_type, environment): return self._model_registry.get_active_deployment(model_type, environment)

    # --- quota ---
    def upsert_quota_daily_snapshot(self, record): return self._quota.upsert_quota_daily_snapshot(record)
    def load_quota_counter(self, snapshot_date): return self._quota.load_quota_counter(snapshot_date)
