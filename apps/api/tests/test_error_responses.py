from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.auth.dependencies import CurrentUserContext, require_current_user
from app.auth.session import MctaiSessionClaims
from app.db.session import get_session
from app.main import app
from fastapi.testclient import TestClient

OWNER_ID = uuid.UUID("77777777-7777-4777-8777-777777777777")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeSession:
    def commit(self) -> None:
        return None

    def refresh(self, _: object) -> None:
        return None

    def rollback(self) -> None:
        return None


def _current_user() -> CurrentUserContext:
    user = SimpleNamespace(
        id=OWNER_ID,
        sub="auth-sub-errors",
        email="errors@example.test",
        name="Error Tester",
        picture_url=None,
        created_at=NOW,
        last_seen_at=NOW,
    )
    claims = MctaiSessionClaims(
        sub="auth-sub-errors",
        email="errors@example.test",
        email_verified=True,
        name="Error Tester",
        picture=None,
        raw={"sub": "auth-sub-errors", "email": "errors@example.test"},
    )
    return CurrentUserContext(user=user, claims=claims, created=False)


def test_validation_errors_use_consistent_error_envelope() -> None:
    app.dependency_overrides[require_current_user] = _current_user
    app.dependency_overrides[get_session] = lambda: FakeSession()

    try:
        response = TestClient(app).post(
            "/api/papers",
            json={"title": "   ", "latex_source": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"]
    assert body["error"]["details"][0]["location"].startswith("body.")
    assert "Title must not be blank" in body["error"]["details"][0]["message"]


def test_http_errors_use_consistent_error_envelope() -> None:
    app.dependency_overrides[get_session] = lambda: FakeSession()

    try:
        response = TestClient(app).get("/api/papers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Not signed in",
        }
    }
