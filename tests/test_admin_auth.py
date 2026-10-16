from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.admin.auth import AuthenticatedAdmin, login_rate_limiter, require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import AdminUser, AuditLog, ModelVersion, PredictionMetadata, RefreshToken, Role, SecurityEvent, UserRole
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.admin.security import hash_password
from backend.app.database import Base, get_db
from backend.app.main import app


PASSWORD = "Strong-Admin-Password-2026!"


@pytest.fixture()
def admin_context(monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "test-only-secret-at-least-thirty-two-characters")
    monkeypatch.setenv("ADMIN_MAX_FAILED_LOGINS", "3")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        seed_roles_and_permissions(session)
        role = session.scalar(select(Role).where(Role.name == "super_admin"))
        user = AdminUser(
            email="admin@example.com",
            full_name="Test Administrator",
            password_hash=hash_password(PASSWORD),
        )
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    login_rate_limiter._events.clear()
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def login(client: TestClient, password: str = PASSWORD):
    return client.post(
        "/api/admin/auth/login",
        json={"email": "admin@example.com", "password": password},
    )


def test_login_me_refresh_rotation_and_logout(admin_context):
    client, factory = admin_context
    response = login(client)
    assert response.status_code == 200
    payload = response.json()
    assert payload["admin"]["roles"] == ["super_admin"]
    assert "users.write" in payload["admin"]["permissions"]
    assert PASSWORD not in response.text

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    me = client.get("/api/admin/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"

    refreshed = client.post(
        "/api/admin/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert refreshed.status_code == 200
    rotated = refreshed.json()
    assert rotated["refresh_token"] != payload["refresh_token"]
    replay = client.post(
        "/api/admin/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert replay.status_code == 401

    logout = client.post(
        "/api/admin/auth/logout",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert logout.status_code == 200
    assert client.post(
        "/api/admin/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    ).status_code == 401

    with factory() as session:
        actions = session.scalars(select(AuditLog.action)).all()
        assert {"admin.login.succeeded", "admin.token.refreshed", "admin.logout"} <= set(actions)
        assert all(token.token_hash not in {payload["refresh_token"], rotated["refresh_token"]} for token in session.scalars(select(RefreshToken)))


def test_invalid_credentials_and_lockout_create_security_event(admin_context):
    client, factory = admin_context
    first = login(client, "wrong")
    second = login(client, "wrong")
    third = login(client, "wrong")
    assert first.status_code == second.status_code == 401
    assert first.json()["error"]["message"] == "Invalid email or password"
    assert third.status_code == 423
    assert login(client).status_code == 423
    with factory() as session:
        user = session.scalar(select(AdminUser).where(AdminUser.email == "admin@example.com"))
        assert user.failed_login_count == 3
        assert session.scalar(select(SecurityEvent)) is not None


def test_missing_invalid_and_expired_access_tokens(admin_context, monkeypatch):
    client, _ = admin_context
    assert client.get("/api/admin/auth/me").status_code == 401
    assert client.get("/api/admin/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    expired = jwt.encode(
        {
            "sub": "nobody",
            "type": "access",
            "jti": "expired-token-test",
            "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "test-only-secret-at-least-thirty-two-characters",
        algorithm="HS256",
    )
    response = client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_permission_dependency_denies_missing_permission():
    dependency = require_permissions("model.activate")
    principal = AuthenticatedAdmin(
        user=AdminUser(email="support@example.com", full_name="Support", password_hash="unused"),
        roles=["support_admin"],
        permissions=["dashboard.view"],
    )
    with pytest.raises(AdminAPIError) as caught:
        dependency(principal)
    assert caught.value.status_code == 403


def test_admin_tables_do_not_store_customer_financial_fields():
    prohibited = {"person_income", "loan_amnt", "loan_int_rate", "raw_features", "secret_key"}
    for table in Base.metadata.sorted_tables:
        if table.name in {"admin_users", "roles", "permissions", "role_permissions", "user_roles", "refresh_tokens", "audit_logs", "security_events"}:
            assert prohibited.isdisjoint(table.columns.keys())


def test_dashboard_returns_measured_privacy_safe_results(admin_context):
    client, _ = admin_context
    auth = login(client).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    summary = client.get("/api/admin/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["operational_predictions"]["source"] == "privacy_safe_prediction_metadata"
    assert body["measured_research"]["evaluated_samples"] == 6484
    assert body["measured_research"]["accuracy"] == pytest.approx(0.8320481184)

    risk = client.get("/api/admin/dashboard/risk-distribution", headers=headers)
    fhe = client.get("/api/admin/dashboard/fhe-performance", headers=headers)
    privacy = client.get("/api/admin/dashboard/privacy", headers=headers)
    assert risk.status_code == fhe.status_code == privacy.status_code == 200
    combined = summary.text + risk.text + fhe.text + privacy.text
    for prohibited in ("person_income", "loan_amnt", "secret_key_material", "raw_features"):
        assert prohibited not in combined


def test_prediction_metadata_pagination_filters_detail_timeline_and_export(admin_context):
    client, factory = admin_context
    with factory.begin() as session:
        session.add_all([
            PredictionMetadata(prediction_id="PRD-TEST-001", anonymous_user_id="USR-AAA111", risk_class="LOW RISK", risk_score_band="0.00-0.24", encryption_status="successful", evaluation_status="successful", model_version="logistic-regression-baseline-v1", fhe_profile="ckks-balanced-degree7-v1", encryption_time_ms=10, evaluation_time_ms=20, decryption_time_ms=5, total_latency_ms=40, request_status="completed"),
            PredictionMetadata(prediction_id="PRD-TEST-002", anonymous_user_id="USR-BBB222", risk_class="HIGH RISK", risk_score_band="0.75-1.00", encryption_status="successful", evaluation_status="successful", model_version="logistic-regression-baseline-v1", fhe_profile="ckks-balanced-degree7-v1", encryption_time_ms=11, evaluation_time_ms=21, decryption_time_ms=6, total_latency_ms=45, request_status="completed"),
        ])
    auth = login(client).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    listing = client.get("/api/admin/predictions?page=1&page_size=1&risk_class=HIGH%20RISK", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["prediction_id"] == "PRD-TEST-002"
    detail = client.get("/api/admin/predictions/PRD-TEST-001", headers=headers)
    timeline = client.get("/api/admin/predictions/PRD-TEST-001/timeline", headers=headers)
    exported = client.get("/api/admin/predictions/export", headers=headers)
    assert detail.status_code == timeline.status_code == exported.status_code == 200
    assert len(timeline.json()["items"]) == 7
    assert "person_income" not in detail.text + exported.text
    assert "PRD-TEST-001" in exported.text


def test_fhe_monitor_reports_only_measured_profile_and_honest_boundary(admin_context):
    client, _ = admin_context
    auth = login(client).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    metrics = client.get("/api/admin/fhe/metrics", headers=headers)
    profiles = client.get("/api/admin/fhe/profiles", headers=headers)
    assert metrics.status_code == profiles.status_code == 200
    assert metrics.json()["multiplicative_depth"] == 6
    assert metrics.json()["boundary"] == "trusted-client and evaluator responsibilities are separated; the evaluator has no client secret key"
    assert len(profiles.json()["items"]) == 1
    assert profiles.json()["items"][0]["measured"] is True


def test_model_activation_requires_validation_and_approval(admin_context):
    client, factory = admin_context
    with factory.begin() as session:
        candidate = ModelVersion(version="candidate-v2", model_name="Candidate", model_type="Logistic Regression", dataset_version="v1", polynomial_version="degree7", status="testing", fhe_compatible=True, validation_passed=True, metrics={"accuracy": .8}, artifact_hash="a" * 64)
        session.add(candidate); session.flush(); candidate_id = candidate.id
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/api/admin/models/{candidate_id}/activate", headers=headers).status_code == 409
    assert client.post(f"/api/admin/models/{candidate_id}/approve", headers=headers).status_code == 200
    activated = client.post(f"/api/admin/models/{candidate_id}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    with factory() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "model.activate")) is not None


def test_admin_management_health_reports_and_non_secret_settings(admin_context):
    client, _ = admin_context
    auth = login(client).json(); headers = {"Authorization": f"Bearer {auth['access_token']}"}
    roles = client.get("/api/admin/roles", headers=headers).json()
    support = next(role for role in roles["items"] if role["name"] == "support_admin")
    created = client.post("/api/admin/users", headers=headers, json={"email":"new.admin@example.com","full_name":"New Administrator","password":"Another-Strong-Password-2026!","role_ids":[support["id"]]})
    assert created.status_code == 201
    assert created.json()["roles"] == ["support_admin"]
    assert client.post(f"/api/admin/users/{created.json()['id']}/revoke-sessions", headers=headers).status_code == 200
    health = client.get("/api/admin/system-health", headers=headers)
    settings = client.get("/api/admin/settings", headers=headers)
    report = client.post("/api/admin/reports/generate", headers=headers, json={"report_type":"privacy_compliance","format":"json"})
    assert health.status_code == settings.status_code == report.status_code == 200
    assert report.json()["privacy"] == "Contains aggregate and privacy-safe metadata only"
    combined = health.text + settings.text + report.text
    assert "ADMIN_JWT_SECRET" not in combined
    assert "person_income" not in combined
