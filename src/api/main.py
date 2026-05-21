"""
Main entry point leveraging modular routers and centralized state management.
"""

from fastapi import FastAPI
import src.api.state_manager as sm
from src.api.endpoints import health, training, prediction, monitoring


app = FastAPI(
    title="🛰 OrbitDecay Risk Prediction API",
    description="Satellite risk assessment and lifetime prediction system.",
    version="1.0.0")

app.include_router(health.router, tags=["health"])
app.include_router(training.router, tags=["training"])
app.include_router(prediction.router, tags=["predictions"])
app.include_router(monitoring.router, tags=["monitoring"])


sm.init_services()
sm.initialize_monitoring_system()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)