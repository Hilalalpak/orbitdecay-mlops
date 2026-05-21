import json
from typing import Dict, Optional
from src.pipeline.metadata.contracts.model_training import ModelTrainingRun, ModelDeployment


class ModelRegistryRepository:

    def __init__(self, connection):
        self.connection = connection

    def insert_model_training_run(self, record: ModelTrainingRun) -> str:
        query = """
        INSERT INTO model_training_runs
        (run_id, model_type, mlflow_run_id, experiment_name,
         training_samples, validation_samples,
         validation_metrics, risk_thresholds, status, trained_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(record.run_id) if record.run_id else None,
                record.model_type,
                record.mlflow_run_id,
                record.experiment_name,
                record.training_samples,
                record.validation_samples,
                json.dumps(record.validation_metrics) if record.validation_metrics else None,
                json.dumps(record.risk_thresholds) if record.risk_thresholds else None,
                record.status,
                record.trained_at,
            ))
            training_id = cursor.fetchone()[0]
        self.connection.commit()
        return str(training_id)

    def get_latest_model_training_run(self, model_type: str) -> Optional[Dict]:
        query = """
        SELECT id, model_type, mlflow_run_id, validation_metrics, status, trained_at
        FROM model_training_runs
        WHERE model_type = %s
        ORDER BY trained_at DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (model_type,))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "model_type": row[1],
            "mlflow_run_id": row[2],
            "validation_metrics": row[3],
            "status": row[4],
            "trained_at": row[5].isoformat() if row[5] else None,
        }

    def insert_model_deployment(self, record: ModelDeployment) -> str:
        query = """
        INSERT INTO model_deployments
        (training_run_id, model_type, version, environment, status)
        VALUES (%s,%s,%s,%s,%s)
        RETURNING id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                str(record.training_run_id) if record.training_run_id else None,
                record.model_type,
                record.version,
                record.environment,
                record.status,
            ))
            deployment_id = cursor.fetchone()[0]
        self.connection.commit()
        return str(deployment_id)

    def retire_previous_deployments(self, model_type: str, environment: str,
                                     replaced_by: str) -> None:
        query = """
        UPDATE model_deployments
        SET status = 'retired', replaced_by = %s
        WHERE model_type = %s AND environment = %s AND status = 'active'
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (replaced_by, model_type, environment))
        self.connection.commit()

    def get_active_deployment(self, model_type: str, environment: str) -> Optional[Dict]:
        query = """
        SELECT id, model_type, version, environment, deployed_at, status
        FROM model_deployments
        WHERE model_type = %s AND environment = %s AND status = 'active'
        ORDER BY deployed_at DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (model_type, environment))
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "model_type": row[1],
            "version": row[2],
            "environment": row[3],
            "deployed_at": row[4].isoformat() if row[4] else None,
            "status": row[5],
        }
