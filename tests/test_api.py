from fastapi.testclient import TestClient

from backend.app.main import app, health
from backend.app.service import service
import pytest


client = TestClient(app)


def test_health_reports_compiled_openfhe() -> None:
    response = health()
    assert response["status"] == "healthy"
    assert response["connected"] is True
    assert response["openfhe"] == ("ready" if service.executable.exists() else "not-built")


def valid_payload() -> dict[str, float]:
    return {
        "person_age": 28,
        "person_income": 45000,
        "person_emp_length": 5,
        "loan_amnt": 10000,
        "loan_int_rate": 11.5,
        "loan_percent_income": 0.22,
        "cb_person_cred_hist_length": 4,
    }


def test_predict_runs_complete_openfhe_pipeline() -> None:
    if not service.executable.exists():
        pytest.skip("Native OpenFHE integration executable is not built in this environment")
    response = client.post("/predict", json=valid_payload())
    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["risk_score"] <= 1
    assert result["prediction"] in {"LOW RISK", "HIGH RISK"}
    assert result["privacy"]["encrypted_inference"] is True
    assert result["privacy"]["evaluator_received_plaintext_features"] is False
    assert result["privacy"]["secret_key_available_to_evaluator"] is False
    assert result["timing"]["encryption_ms"] > 0
    assert result["timing"]["evaluation_ms"] > 0
    assert result["timing"]["decryption_ms"] > 0


def test_negative_income_is_rejected() -> None:
    payload = valid_payload()
    payload["person_income"] = -1
    assert client.post("/predict", json=payload).status_code == 422


def test_negative_loan_is_rejected() -> None:
    payload = valid_payload()
    payload["loan_amnt"] = -100
    assert client.post("/predict", json=payload).status_code == 422


def test_zero_age_is_rejected() -> None:
    payload = valid_payload()
    payload["person_age"] = 0
    assert client.post("/predict", json=payload).status_code == 422


def test_missing_required_income_is_rejected() -> None:
    payload = valid_payload()
    del payload["person_income"]
    assert client.post("/predict", json=payload).status_code == 422


def test_missing_nullable_values_use_training_medians() -> None:
    if not service.executable.exists():
        pytest.skip("Native OpenFHE integration executable is not built in this environment")
    payload = valid_payload()
    payload["person_emp_length"] = None
    payload["loan_int_rate"] = None
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert 0 <= response.json()["risk_score"] <= 1


def test_extreme_values_are_rejected() -> None:
    payload = valid_payload()
    payload["person_age"] = 144
    payload["person_income"] = 1_000_000_000
    payload["loan_amnt"] = 10_000_000
    assert client.post("/predict", json=payload).status_code == 422
