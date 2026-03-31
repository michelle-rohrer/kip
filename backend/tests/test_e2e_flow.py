from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
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
from app.services.auth import reset_auth_state


def _build_app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(wellness_router)
    app.include_router(cycle_router)
    app.include_router(training_router)
    app.include_router(injury_router)
    app.include_router(privacy_router)
    app.include_router(predictions_router)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


def test_e2e_register_login_submit_wellness_and_get_prediction(db_session: Session) -> None:
    app = _build_app(db_session)
    reset_auth_state()

    with TestClient(app) as client:
        register_res = client.post(
            "/api/auth/register",
            json={
                "email": "e2e.player@example.com",
                "password": "SuperSecret123",
                "role": "player",
                "name": "E2E Player",
            },
        )
        assert register_res.status_code == 201, register_res.text
        player_id = register_res.json()["id"]

        login_res = client.post(
            "/api/auth/login",
            json={"email": "e2e.player@example.com", "password": "SuperSecret123"},
        )
        assert login_res.status_code == 200, login_res.text
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        wellness_res = client.post(
            "/api/wellness/",
            headers=headers,
            json={
                "date": "2026-05-20",
                "sleep_hours": 7.0,
                "sleep_quality": 6,
                "muscle_soreness": 5,
                "mental_energy": 6,
                "stress_level": 4,
                "motivation": 7,
                "rpe_previous_day": 6,
            },
        )
        assert wellness_res.status_code == 201, wellness_res.text

        training_res = client.post(
            "/api/training/",
            headers=headers,
            json={
                "date": "2026-05-20",
                "duration_min": 85,
                "intensity": 7,
                "jump_count": 110,
            },
        )
        assert training_res.status_code == 201, training_res.text

        prediction_res = client.get(f"/api/predictions/{player_id}", headers=headers)
        assert prediction_res.status_code == 200, prediction_res.text

        prediction_payload = prediction_res.json()
        assert prediction_payload["player_id"] == player_id
        assert 0.0 <= prediction_payload["risk_score"] <= 1.0
        assert prediction_payload["risk_level"] in {"green", "yellow", "red"}

    app.dependency_overrides.clear()
    reset_auth_state()
