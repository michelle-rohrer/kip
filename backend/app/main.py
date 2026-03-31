from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers import (
    auth_router,
    cycle_router,
    injury_router,
    predictions_router,
    privacy_router,
    training_router,
    wellness_router,
)


app = FastAPI(
    title="cycle-aware-load-monitoring API",
    description="Cycle-aware load monitoring backend.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(wellness_router)
app.include_router(cycle_router)
app.include_router(training_router)
app.include_router(injury_router)
app.include_router(privacy_router)
app.include_router(predictions_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["system"])
def health_check_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
