import mlflow

from src.machine_learning.models.lstm_neural_network.lstm_survival_model import LSTMSurvivalModel
from src.shared.config import MLConfigInterface


class TrainingRunner:

    def __init__(self,
                 ml_config: MLConfigInterface,
                 logger) -> None:
        self.ml_config = ml_config
        self.logger = logger

    def run(self, X, y, groups) -> dict:
        lstm_params = self.ml_config.get_lstm_params() if hasattr(self.ml_config, 'get_lstm_params') else {}
        model_trainer = LSTMSurvivalModel(
            mlflow_config=self.ml_config,
            model_params=lstm_params or None,
            sequence_length=lstm_params.get("sequence_length", 30))

        self.logger.info(f'Training ready. Samples: {len(X)}, Features: {X.shape[1]}')
        training_results = model_trainer.train(X, y, groups)

        if training_results.get("success"):
            self._log_mlflow_metrics(training_results)

        return training_results

    def _log_mlflow_metrics(self, training_results: dict) -> None:
        mlflow_run_id = training_results["run_id"]
        metrics = training_results["metrics"]
        model_name = self.ml_config.get_default_model_registry_name()

        metric_map = {
            "sota_rul_smape_percent": metrics.get("rul_smape"),
            "sota_weighted_mae_days": metrics.get("weighted_mae"),
            "sota_critical_window_f1": metrics.get("critical_window_f1"),
            "val_mae_log_scale": metrics.get("test_mae_log"),
        }

        with mlflow.start_run(run_id=mlflow_run_id):
            for key, value in metric_map.items():
                if value is not None:
                    mlflow.log_metric(key, value)

        mlflow.register_model(
            model_uri=f"runs:/{mlflow_run_id}/lstm_model",
            name=model_name)
