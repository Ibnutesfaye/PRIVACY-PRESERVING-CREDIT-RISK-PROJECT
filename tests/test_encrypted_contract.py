from __future__ import annotations

import base64
import hashlib
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.encrypted_schemas import EncryptedEvaluationRequest
from backend.app.main import app
from backend.app.admin.auth import AuthenticatedAdmin, get_current_admin
from backend.app.admin.models import AdminUser, FheMetric, PredictionMetadata
from sqlalchemy import select
from backend.app.encrypted_service import EvaluationArtifact
from backend.app.database import Base, get_db


@pytest.fixture(autouse=True)
def encrypted_operator():
    database = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(database)
    factory = sessionmaker(database, expire_on_commit=False)
    with factory.begin() as session:
        user = AdminUser(id="operator-id", email="operator@example.com", full_name="Encrypted Operator", password_hash="not-used")
        session.add(user)
    operator = AuthenticatedAdmin(
        user=user,
        roles=["loan_officer"], permissions=["applications.write"],
    )
    def override_db():
        with factory() as session:
            yield session
    app.dependency_overrides[get_current_admin] = lambda: operator
    app.dependency_overrides[get_db] = override_db
    yield factory
    app.dependency_overrides.pop(get_current_admin, None)
    app.dependency_overrides.pop(get_db, None)
    database.dispose()


def valid_request() -> dict[str, object]:
    ciphertext = base64.b64encode(b"serialized-openfhe-ciphertext").decode("ascii")
    return {
        "protocol_version": 1,
        "profile_id": "ckks-balanced-degree7-v1",
        "batch_size": 1,
        "context_fingerprint": hashlib.sha256(b"test-context").hexdigest(),
        "feature_ciphertexts": [ciphertext] * 7,
    }


def test_encrypted_contract_requires_exactly_seven_ciphertexts() -> None:
    payload = valid_request()
    payload["feature_ciphertexts"] = payload["feature_ciphertexts"][:6]
    response = TestClient(app).post("/api/v1/fhe/evaluate", json=payload)
    assert response.status_code == 422


def test_encrypted_contract_rejects_invalid_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    request = EncryptedEvaluationRequest(**{**valid_request(), "feature_ciphertexts": ["%%%"] * 7})
    from backend.app.encrypted_service import CiphertextEvaluationService

    monkeypatch.setattr(CiphertextEvaluationService, "ready", property(lambda _self: True))
    monkeypatch.setattr(CiphertextEvaluationService, "context_fingerprint", property(lambda _self: request.context_fingerprint))
    service = CiphertextEvaluationService()
    with pytest.raises(ValueError, match="valid base64"):
        service.evaluate(request)


def test_encrypted_contract_rejects_empty_ciphertext() -> None:
    payload = valid_request()
    payload["feature_ciphertexts"] = [""] * 7
    response = TestClient(app).post("/api/v1/fhe/evaluate", json=payload)
    assert response.status_code == 422


def test_encrypted_contract_rejects_wrong_model_version(monkeypatch: pytest.MonkeyPatch) -> None:
    request = EncryptedEvaluationRequest(**{**valid_request(), "model_version": "unknown-model"})
    from backend.app.encrypted_service import CiphertextEvaluationService

    monkeypatch.setattr(CiphertextEvaluationService, "ready", property(lambda _self: True))
    with pytest.raises(ValueError, match="model version"):
        CiphertextEvaluationService().evaluate(request)


def test_encrypted_contract_rejects_wrong_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    request = EncryptedEvaluationRequest(**{**valid_request(), "profile_id": "wrong-profile"})
    from backend.app.encrypted_service import CiphertextEvaluationService

    monkeypatch.setattr(CiphertextEvaluationService, "ready", property(lambda _self: True))
    with pytest.raises(ValueError, match="profile"):
        CiphertextEvaluationService().evaluate(request)


def test_encrypted_contract_rejects_wrong_context_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    request = EncryptedEvaluationRequest(**valid_request())
    from backend.app.encrypted_service import CiphertextEvaluationService

    monkeypatch.setattr(CiphertextEvaluationService, "ready", property(lambda _self: True))
    monkeypatch.setattr(CiphertextEvaluationService, "context_fingerprint", property(lambda _self: "0" * 64))
    with pytest.raises(ValueError, match="crypto context"):
        CiphertextEvaluationService().evaluate(request)


def test_worker_timeout_is_safely_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    from backend.app.encrypted_service import CiphertextEvaluationService

    request = EncryptedEvaluationRequest(**valid_request())
    temporary_directory = tempfile.TemporaryDirectory
    monkeypatch.setattr(CiphertextEvaluationService, "ready", property(lambda _self: True))
    monkeypatch.setattr(CiphertextEvaluationService, "context_fingerprint", property(lambda _self: request.context_fingerprint))
    monkeypatch.setattr("backend.app.encrypted_service.tempfile.TemporaryDirectory", temporary_directory)
    monkeypatch.setattr(
        "backend.app.encrypted_service.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("contains-secret", 5)),
    )
    with pytest.raises(RuntimeError, match="could not complete") as captured:
        CiphertextEvaluationService().evaluate(request)
    assert "contains-secret" not in str(captured.value)


def test_evaluation_response_remains_encrypted(monkeypatch: pytest.MonkeyPatch, encrypted_operator) -> None:
    import backend.app.encrypted_routes as routes

    monkeypatch.setattr(routes.encrypted_service, "evaluate", lambda _request: EvaluationArtifact(b"encrypted-result", 1234))
    response = TestClient(app).post("/api/v1/fhe/evaluate", json=valid_request())
    assert response.status_code == 200
    body = response.json()
    assert base64.b64decode(body["result_ciphertext"]) == b"encrypted-result"
    assert body["evaluator_decrypted_result"] is False
    assert body["prediction_id"].startswith("PRD-")
    assert body["evaluation_time_ms"] >= 0
    assert "risk_score" not in body
    with encrypted_operator() as session:
        metadata = session.scalar(select(PredictionMetadata).where(PredictionMetadata.prediction_id == body["prediction_id"]))
        assert metadata is not None
        assert metadata.risk_class is None
        metric = session.scalar(select(FheMetric).where(FheMetric.prediction_metadata_id == metadata.id))
        assert metric is not None
        assert metric.encryption_time_ms is None
        assert metric.decryption_time_ms is None
        assert metric.ciphertext_size_bytes == 1234


def test_profile_metadata_never_claims_server_secret_key_distribution() -> None:
    response = TestClient(app).get("/api/v1/fhe/profiles/current")
    assert response.status_code == 200
    body = response.json()
    assert body["secret_key_distributed_by_server"] is False
    assert "secret" not in " ".join(body.keys()).lower().replace("secret_key_distributed_by_server", "")


def test_worker_failure_returns_safe_correlated_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.encrypted_routes as routes

    monkeypatch.setattr(routes.encrypted_service, "evaluate", lambda _request: (_ for _ in ()).throw(RuntimeError("native internal path and secret detail")))
    response = TestClient(app).post("/api/v1/fhe/evaluate", json=valid_request())
    assert response.status_code == 503
    assert response.json()["detail"] == "Encrypted evaluation is temporarily unavailable"
    assert "native internal" not in response.text
    assert response.headers["x-request-id"]


def test_encrypted_api_rejects_unauthenticated_requests() -> None:
    app.dependency_overrides.pop(get_current_admin, None)
    response = TestClient(app).post("/api/v1/fhe/evaluate", json=valid_request())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
