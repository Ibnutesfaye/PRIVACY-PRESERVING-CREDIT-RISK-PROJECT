from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from backend.app.config import ApplicationSettings
from backend.app.main import app
from backend.app.middleware import RequestBodyLimitMiddleware
from backend.app.service import service


def test_production_rejects_plaintext_compatibility_endpoint() -> None:
    with pytest.raises(ValidationError, match="MODEL_PLAINTEXT_PREDICTION_ENABLED"):
        ApplicationSettings(
            application_environment="production",
            application_allowed_origins="https://credit.example",
            model_plaintext_prediction_enabled=True,
        )


def test_production_rejects_insecure_cors_origin() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        ApplicationSettings(
            application_environment="production",
            application_allowed_origins="http://credit.example",
            model_plaintext_prediction_enabled=False,
        )


def test_production_requires_protected_metrics_token() -> None:
    with pytest.raises(ValidationError, match="OBSERVABILITY_METRICS_TOKEN"):
        ApplicationSettings(
            application_environment="production",
            application_allowed_origins="https://credit.example",
            model_plaintext_prediction_enabled=False,
            observability_metrics_token=None,
        )


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Wildcard"):
        ApplicationSettings(application_allowed_origins="*")


def test_system_probes_do_not_expose_secrets() -> None:
    client = TestClient(app)
    liveness = client.get("/api/v1/system/liveness")
    readiness = client.get("/api/v1/system/readiness")

    assert liveness.status_code == 200
    assert liveness.json()["status"] == "alive"
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    assert readiness_body["status"] == "ready"
    assert readiness_body["checks"]["database"] is True
    assert readiness_body["checks"]["openfhe_evaluator"] is service.executable.exists()
    assert isinstance(readiness_body["checks"]["encrypted_profile"], bool)
    serialized = readiness.text.lower()
    assert "password" not in serialized
    assert "database_url" not in serialized


def test_database_failure_makes_readiness_fail_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.main as main_module

    monkeypatch.setattr(main_module.engine, "connect", lambda: (_ for _ in ()).throw(ConnectionError("credential-bearing internal detail")))
    response = TestClient(app).get("/api/v1/system/readiness")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] is False
    assert "credential-bearing" not in response.text
    assert response.headers["x-request-id"]


def test_request_body_limit_rejects_content_length_and_streamed_body() -> None:
    limited_app = FastAPI()
    limited_app.add_middleware(RequestBodyLimitMiddleware, max_bytes=16)

    @limited_app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"length": len(await request.body())}

    response = TestClient(limited_app).post("/echo", content=b"x" * 17)
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large"}


def test_invalid_request_id_is_replaced() -> None:
    response = TestClient(app).get(
        "/api/v1/system/liveness",
        headers={"X-Request-ID": "unsafe request id with spaces"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "unsafe request id with spaces"
    assert len(response.headers["X-Request-ID"]) == 36


def test_plaintext_route_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.main as main_module

    monkeypatch.setattr(main_module.settings, "model_plaintext_prediction_enabled", False)
    response = TestClient(app).post(
        "/predict",
        json={
            "person_age": 28,
            "person_income": 45_000,
            "person_emp_length": 5,
            "loan_amnt": 10_000,
            "loan_int_rate": 11.5,
            "loan_percent_income": 0.22,
            "cb_person_cred_hist_length": 4,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "The plaintext compatibility endpoint is disabled"


def test_metrics_endpoint_is_disabled_or_constant_time_token_protected(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.main as main_module

    client = TestClient(app)
    monkeypatch.setattr(main_module.settings, "observability_metrics_token", None)
    assert client.get("/internal/metrics").status_code == 404
    monkeypatch.setattr(main_module.settings, "observability_metrics_token", SecretStr("m" * 40))
    assert client.get("/internal/metrics", headers={"X-Metrics-Token": "wrong"}).status_code == 401
    response = client.get("/internal/metrics", headers={"X-Metrics-Token": "m" * 40})
    assert response.status_code == 200
    assert "cipherscore_http_requests_total" in response.text
    assert "cipherscore_auth_failures_total" in response.text
    assert "cipherscore_database_healthy" in response.text
    assert "cipherscore_application_ready" in response.text
    assert "cipherscore_fhe_worker_ready" in response.text
    assert "m" * 40 not in response.text
    for forbidden in ("income", "loan_amount", "credit_history", "ciphertext_contents", "access_token", "secret_key"):
        assert forbidden not in response.text.lower()
