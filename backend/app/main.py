import os
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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
from app.services.auth import JWT_SECRET_KEY, is_jwt_secret_secure


def _ensure_secure_config() -> None:
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in {"prod", "production"} and not is_jwt_secret_secure(JWT_SECRET_KEY):
        raise RuntimeError(
            "In production APP_ENV, JWT_SECRET_KEY must be set to a secure value (>=32 chars, non-default)."
        )


_ensure_secure_config()

app = FastAPI(
    title="cycle-aware-load-monitoring API",
    description="Cycle-aware load monitoring backend.",
    version="0.1.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
allowed_hosts = [
    host.strip()
    for host in os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if os.getenv("SECURE_TRANSPORT_ONLY", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


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
