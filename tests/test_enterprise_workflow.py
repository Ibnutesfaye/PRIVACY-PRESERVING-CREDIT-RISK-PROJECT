from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.admin.auth import login_rate_limiter
from backend.app.admin.models import AdminUser, AuditLog, DecisionRecord, LoanApplication, Role, UserRole, WorkflowHistory
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.admin.security import hash_password
from backend.app.database import Base, get_db
from backend.app.main import app


PASSWORD = "Strong-Workflow-Password-2026!"


def test_governed_application_workflow_requires_human_override_reason(monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "test-only-secret-at-least-thirty-two-characters")
    database = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(database)
    factory = sessionmaker(database, expire_on_commit=False)
    with factory.begin() as session:
        seed_roles_and_permissions(session)
        role = session.scalar(select(Role).where(Role.name == "super_admin"))
        user = AdminUser(email="workflow@example.com", full_name="Workflow Administrator", password_hash=hash_password(PASSWORD))
        session.add(user); session.flush(); session.add(UserRole(user_id=user.id, role_id=role.id))

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    login_rate_limiter._events.clear()
    try:
        with TestClient(app) as client:
            login = client.post("/api/admin/auth/login", json={"email": "workflow@example.com", "password": PASSWORD})
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            organization = client.post("/api/v1/organizations", headers=headers, json={"code": "BANK01", "name": "Pilot Bank"})
            assert organization.status_code == 201
            organization_id = organization.json()["id"]
            branch = client.post(f"/api/v1/organizations/{organization_id}/branches", headers=headers, json={"code": "HQ01", "name": "Head Office"})
            assert branch.status_code == 201
            branch_id = branch.json()["id"]
            customer_hash = "a" * 64
            consent = client.post(f"/api/v1/organizations/{organization_id}/consents", headers=headers, json={"subject_reference_hash": customer_hash, "purpose": "Encrypted credit risk assessment", "lawful_basis": "customer consent"})
            assert consent.status_code == 201
            application = client.post("/api/v1/applications", headers=headers, json={"application_number": "APP-0001", "organization_id": organization_id, "branch_id": branch_id, "consent_record_id": consent.json()["id"], "customer_reference_hash": customer_hash, "loan_product_code": "PERSONAL"})
            assert application.status_code == 201
            state = application.json()

            invalid_skip = client.post(f"/api/v1/applications/{state['id']}/transitions", headers=headers, json={"to_status": "APPROVED", "expected_version": state["version"]})
            assert invalid_skip.status_code == 409
            for target in ("SUBMITTED", "PREDICTION_PENDING"):
                response = client.post(f"/api/v1/applications/{state['id']}/transitions", headers=headers, json={"to_status": target, "expected_version": state["version"]})
                assert response.status_code == 200; state = response.json()
            predicted = client.post(f"/api/v1/applications/{state['id']}/prediction-reference", headers=headers, json={"prediction_id": "PRD-ENCRYPTED-001", "model_recommendation": "HIGH RISK", "risk_score_band": "HIGH", "expected_version": state["version"]})
            assert predicted.status_code == 200; state = predicted.json()
            review = client.post(f"/api/v1/applications/{state['id']}/transitions", headers=headers, json={"to_status": "UNDER_REVIEW", "expected_version": state["version"]})
            assert review.status_code == 200; state = review.json()
            missing_reason = client.post(f"/api/v1/applications/{state['id']}/decision", headers=headers, json={"decision": "APPROVED", "expected_version": state["version"]})
            assert missing_reason.status_code == 422
            decision = client.post(f"/api/v1/applications/{state['id']}/decision", headers=headers, json={"decision": "APPROVED", "expected_version": state["version"], "override_reason": "Verified compensating collateral under delegated policy"})
            assert decision.status_code == 200
            assert decision.json()["model_override"] is True
            assert decision.json()["status"] == "APPROVED"

        with factory() as session:
            saved = session.get(LoanApplication, state["id"])
            assert saved.status == "APPROVED"
            assert saved.customer_reference_hash == customer_hash
            assert session.scalar(select(DecisionRecord).where(DecisionRecord.application_id == saved.id)).is_override is True
            assert len(session.scalars(select(WorkflowHistory).where(WorkflowHistory.application_id == saved.id)).all()) == 6
            actions = set(session.scalars(select(AuditLog.action)).all())
            assert {"application.created", "application.prediction_linked", "application.decision_recorded"} <= actions
    finally:
        app.dependency_overrides.pop(get_db, None)
        database.dispose()
