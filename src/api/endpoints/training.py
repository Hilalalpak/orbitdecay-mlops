import time
import structlog
from structlog.stdlib import BoundLogger
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.api.models import TrainRequest, TrainResponse
import src.api.state_manager as sm

router = APIRouter()
logger: BoundLogger = structlog.get_logger(__name__)

@router.post("/train/{model_type}", response_model=TrainResponse)
async def train_model(model_type: str, request: TrainRequest):
    """
    Model training endpoint.

    Trains a specified model type using provided features and targets.
    Supports LSTM models with automatic MLflow tracking.

    Args:
        model_type: Model identifier (e.g., "lstm", "deep_learning")
        request: Training data including features, targets, and optional groups

    Returns:
        TrainResponse with MLflow run ID, metrics, and status message

    Raises:
        HTTPException: If training service unavailable or training fails
    """

    if not sm.trainer_factory:
        raise HTTPException(status_code=503, detail="Training service unavailable")

    start_time = time.time()

    try:
        # Get configured trainer
        trainer = sm.trainer_factory.get_trainer(model_type)

        # Convert request data to appropriate formats
        X_df = pd.DataFrame(request.X)
        y_series = pd.Series(request.y)
        groups_series = pd.Series(request.groups) if request.groups else None

        logger.info("training_started", model_type=model_type)

        # Execute training
        training_result = trainer.train(X_df, y_series, groups_series)

        execution_time = time.time() - start_time

        logger.info("training_completed", model_type=model_type, execution_time_seconds=round(execution_time, 2))

        return TrainResponse(
            run_id=training_result.get("run_id"),
            metrics=training_result.get("metrics"),
            message=f"Training completed successfully in {execution_time:.2f}s")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("training_failed", model_type=model_type, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))