import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException

import src.api.state_manager as sm
import src.monitoring.prometheus_metrics as metrics

router = APIRouter()

_ENDPOINT = "/satellite/{satellite_id}/risk"

@router.get("/satellite/{satellite_id}/risk")
async def get_satellite_risk(satellite_id: str, date: Optional[str] = None):
    """
    Satellite risk prediction endpoint.

    Predicts orbital decay risk and estimated lifetime for a specified satellite.
    Uses trained LSTM model to analyze time-series telemetry and space weather data.

    Args:
        satellite_id: Unique satellite identifier (e.g., "25544" for ISS)
        date: Optional analysis date (YYYYMMDD format), defaults to current date

    Returns:
        Risk assessment with score, level, and estimated survival days

    Raises:
        HTTPException: If predictor unavailable or prediction fails
    """
    metrics.track_active_request(_ENDPOINT, 1)
    start_time = time.time()

    try:
        if not sm.predictor:
            metrics.record_api_response(_ENDPOINT, "GET", 503, time.time() - start_time)
            raise HTTPException(status_code=503, detail="Predictor unavailable")

        inference_start = time.time()
        result = sm.predictor.predict_satellite_risk(satellite_id, date)
        metrics.record_model_inference(time.time() - inference_start)

        if "error" not in result:
            metrics.record_risk_assessment(satellite_id, result.get("risk_level", "UNKNOWN"))
            metrics.record_model_prediction(float(result.get("risk_score", 0.0)))

        if "error" in result:
            if "Insufficient data" in result["error"]:
                metrics.record_api_response(_ENDPOINT, "GET", 400, time.time() - start_time)
                raise HTTPException(status_code=400, detail=result["error"])

        duration = time.time() - start_time
        metrics.record_api_response(_ENDPOINT, "GET", 200, duration)

        return {
            "satellite_id": satellite_id,
            "analysis_date": date or datetime.now().strftime("%Y%m%d"),
            "risk_assessment": result,
            "execution_time": duration}

    except HTTPException:
        raise
    except Exception as e:
        metrics.record_api_response(_ENDPOINT, "GET", 500, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        metrics.track_active_request(_ENDPOINT, -1)