from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin, require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import (
    Branch, ConsentRecord, DecisionRecord, LoanApplication, Organization,
    OrganizationMembership, WorkflowHistory, utc_now,
)
from backend.app.database import get_db
from backend.app.workflow_schemas import (
    ApplicationCreate, BranchCreate, ConsentCreate, DecisionCreate, MembershipCreate,
    OrganizationCreate, PredictionReference, TransitionRequest,
)


router = APIRouter(prefix="/api/v1", tags=["enterprise workflow"])
VALID_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"PREDICTION_PENDING", "NEEDS_ADDITIONAL_INFORMATION", "CANCELLED"},
    "PREDICTION_PENDING": {"PREDICTED", "CANCELLED"},
    "PREDICTED": {"UNDER_REVIEW", "CANCELLED"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED", "NEEDS_ADDITIONAL_INFORMATION", "CANCELLED"},
    "NEEDS_ADDITIONAL_INFORMATION": {"SUBMITTED", "CANCELLED"},
    "APPROVED": set(), "REJECTED": set(), "CANCELLED": set(),
}


def serialize_application(row: LoanApplication) -> dict[str, object]:
    return {
        "id": row.id, "application_number": row.application_number,
        "organization_id": row.organization_id, "branch_id": row.branch_id,
        "status": row.status, "model_recommendation": row.model_recommendation,
        "risk_score_band": row.risk_score_band, "prediction_id": row.prediction_id,
        "version": row.version, "created_at": row.created_at, "updated_at": row.updated_at,
    }


def ensure_scope(session: Session, admin: AuthenticatedAdmin, organization_id: str, branch_id: str | None = None) -> None:
    if "super_admin" in admin.roles:
        return
    query = select(OrganizationMembership).where(
        OrganizationMembership.user_id == admin.user.id,
        OrganizationMembership.organization_id == organization_id,
    )
    memberships = session.scalars(query).all()
    allowed = any(item.scope == "organization" or (branch_id is not None and item.branch_id == branch_id) for item in memberships)
    if not allowed:
        raise AdminAPIError(403, "SCOPE_DENIED", "The resource is outside your authorized organization or branch scope")


def application_or_404(session: Session, application_id: str) -> LoanApplication:
    row = session.get(LoanApplication, application_id)
    if row is None:
        raise AdminAPIError(404, "APPLICATION_NOT_FOUND", "Credit application was not found")
    return row


@router.post("/organizations", status_code=201)
def create_organization(payload: OrganizationCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("organizations.write"))], session: Annotated[Session, Depends(get_db)]):
    row = Organization(**payload.model_dump(), enabled_features={}, security_policy={}, reporting_configuration={})
    session.add(row)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback(); raise AdminAPIError(409, "ORGANIZATION_EXISTS", "Organization code or name already exists") from error
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="organization.created", resource_type="organization", resource_id=row.id, result="success")
    session.commit(); return {"id": row.id, "code": row.code, "name": row.name, "status": row.status}


@router.get("/organizations")
def list_organizations(admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("organizations.read"))], session: Annotated[Session, Depends(get_db)]):
    query = select(Organization)
    if "super_admin" not in admin.roles:
        ids = session.scalars(select(OrganizationMembership.organization_id).where(OrganizationMembership.user_id == admin.user.id)).all()
        query = query.where(Organization.id.in_(ids))
    rows = session.scalars(query.order_by(Organization.name)).all()
    return {"items": [{"id": row.id, "code": row.code, "name": row.name, "status": row.status, "risk_threshold": row.risk_threshold, "model_version": row.model_version, "openfhe_profile": row.openfhe_profile} for row in rows]}


@router.get("/organizations/{organization_id}/branches")
def list_branches(organization_id: str, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("organizations.read"))], session: Annotated[Session, Depends(get_db)]):
    ensure_scope(session, admin, organization_id)
    rows = session.scalars(select(Branch).where(Branch.organization_id == organization_id).order_by(Branch.name)).all()
    return {"items": [{"id": row.id, "organization_id": row.organization_id, "code": row.code, "name": row.name, "status": row.status, "manager_user_id": row.manager_user_id} for row in rows]}


@router.post("/organizations/{organization_id}/branches", status_code=201)
def create_branch(organization_id: str, payload: BranchCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("organizations.write"))], session: Annotated[Session, Depends(get_db)]):
    ensure_scope(session, admin, organization_id)
    if session.get(Organization, organization_id) is None: raise AdminAPIError(404, "ORGANIZATION_NOT_FOUND", "Organization was not found")
    row = Branch(organization_id=organization_id, **payload.model_dump()); session.add(row)
    try: session.flush()
    except IntegrityError as error: session.rollback(); raise AdminAPIError(409, "BRANCH_EXISTS", "Branch code already exists in this organization") from error
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="branch.created", resource_type="branch", resource_id=row.id, result="success", safe_metadata={"organization_id": organization_id})
    session.commit(); return {"id": row.id, "organization_id": row.organization_id, "code": row.code, "name": row.name, "status": row.status}


@router.post("/organizations/{organization_id}/memberships", status_code=201)
def create_membership(organization_id: str, payload: MembershipCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("organizations.write"))], session: Annotated[Session, Depends(get_db)]):
    ensure_scope(session, admin, organization_id)
    if payload.scope == "branch" and payload.branch_id is None: raise AdminAPIError(422, "BRANCH_REQUIRED", "Branch scope requires a branch")
    if payload.branch_id:
        branch = session.get(Branch, payload.branch_id)
        if branch is None or branch.organization_id != organization_id: raise AdminAPIError(422, "INVALID_BRANCH", "Branch does not belong to the organization")
    row = OrganizationMembership(organization_id=organization_id, **payload.model_dump()); session.add(row)
    try: session.flush()
    except IntegrityError as error: session.rollback(); raise AdminAPIError(409, "MEMBERSHIP_EXISTS", "This organization scope is already assigned") from error
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="membership.created", resource_type="organization_membership", resource_id=row.id, result="success", safe_metadata={"organization_id": organization_id, "scope": row.scope})
    session.commit(); return {"id": row.id, "organization_id": row.organization_id, "branch_id": row.branch_id, "scope": row.scope}


@router.post("/organizations/{organization_id}/consents", status_code=201)
def create_consent(organization_id: str, payload: ConsentCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.write"))], session: Annotated[Session, Depends(get_db)]):
    ensure_scope(session, admin, organization_id)
    row = ConsentRecord(organization_id=organization_id, **payload.model_dump()); session.add(row); session.flush()
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="consent.recorded", resource_type="consent_record", resource_id=row.id, result="success", safe_metadata={"organization_id": organization_id, "lawful_basis": row.lawful_basis})
    session.commit(); return {"id": row.id, "status": row.status, "purpose": row.purpose, "granted_at": row.granted_at}


@router.post("/applications", status_code=201)
def create_application(payload: ApplicationCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.write"))], session: Annotated[Session, Depends(get_db)]):
    ensure_scope(session, admin, payload.organization_id, payload.branch_id)
    branch, consent = session.get(Branch, payload.branch_id), session.get(ConsentRecord, payload.consent_record_id)
    if branch is None or branch.organization_id != payload.organization_id: raise AdminAPIError(422, "INVALID_BRANCH", "Branch does not belong to the organization")
    if consent is None or consent.organization_id != payload.organization_id or consent.status != "active": raise AdminAPIError(422, "ACTIVE_CONSENT_REQUIRED", "An active organization consent record is required")
    row = LoanApplication(**payload.model_dump(), created_by=admin.user.id, retention_expires_at=utc_now() + timedelta(days=365)); session.add(row); session.flush()
    session.add(WorkflowHistory(application_id=row.id, from_status=None, to_status="DRAFT", changed_by=admin.user.id, reason_code="created"))
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="application.created", resource_type="loan_application", resource_id=row.id, result="success", safe_metadata={"organization_id": row.organization_id, "branch_id": row.branch_id})
    session.commit(); return serialize_application(row)


@router.get("/applications")
def list_applications(admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.read"))], session: Annotated[Session, Depends(get_db)], organization_id: str | None = None, branch_id: str | None = None, status: str | None = Query(default=None, max_length=40)):
    query = select(LoanApplication)
    if "super_admin" not in admin.roles:
        memberships = session.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == admin.user.id)).all()
        organization_scopes = [item.organization_id for item in memberships if item.scope == "organization"]
        branch_scopes = [item.branch_id for item in memberships if item.branch_id]
        if not organization_scopes and not branch_scopes: return {"items": [], "count": 0}
        query = query.where(or_(LoanApplication.organization_id.in_(organization_scopes), LoanApplication.branch_id.in_(branch_scopes)))
    if organization_id: query = query.where(LoanApplication.organization_id == organization_id)
    if branch_id: query = query.where(LoanApplication.branch_id == branch_id)
    if status: query = query.where(LoanApplication.status == status.upper())
    rows = session.scalars(query.order_by(LoanApplication.created_at.desc()).limit(200)).all()
    return {"items": [serialize_application(row) for row in rows], "count": len(rows)}


@router.get("/applications/{application_id}")
def get_application(application_id: str, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.read"))], session: Annotated[Session, Depends(get_db)]):
    row = application_or_404(session, application_id); ensure_scope(session, admin, row.organization_id, row.branch_id); return serialize_application(row)


@router.get("/applications/{application_id}/history")
def application_history(application_id: str, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.read"))], session: Annotated[Session, Depends(get_db)]):
    row = application_or_404(session, application_id); ensure_scope(session, admin, row.organization_id, row.branch_id)
    history = session.scalars(select(WorkflowHistory).where(WorkflowHistory.application_id == row.id).order_by(WorkflowHistory.changed_at)).all()
    return {"items": [{"id": item.id, "from_status": item.from_status, "to_status": item.to_status, "reason_code": item.reason_code, "safe_note": item.safe_note, "changed_by": item.changed_by, "changed_at": item.changed_at} for item in history]}


@router.post("/applications/{application_id}/transitions")
def transition_application(application_id: str, payload: TransitionRequest, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.review"))], session: Annotated[Session, Depends(get_db)]):
    row = application_or_404(session, application_id); ensure_scope(session, admin, row.organization_id, row.branch_id)
    if row.version != payload.expected_version: raise AdminAPIError(409, "APPLICATION_VERSION_CONFLICT", "Application was updated by another user")
    if payload.to_status not in VALID_TRANSITIONS.get(row.status, set()): raise AdminAPIError(409, "INVALID_WORKFLOW_TRANSITION", "The requested workflow transition is not allowed")
    if payload.to_status in {"APPROVED", "REJECTED"}: raise AdminAPIError(409, "DECISION_ENDPOINT_REQUIRED", "Final decisions must use the governed decision endpoint")
    previous = row.status; row.status = payload.to_status; row.version += 1
    if row.status == "SUBMITTED": row.submitted_at = utc_now()
    if row.status == "CANCELLED": row.completed_at = utc_now()
    session.add(WorkflowHistory(application_id=row.id, from_status=previous, to_status=row.status, changed_by=admin.user.id, reason_code=payload.reason_code, safe_note=payload.safe_note))
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="application.transitioned", resource_type="loan_application", resource_id=row.id, result="success", safe_metadata={"from": previous, "to": row.status})
    session.commit(); return serialize_application(row)


@router.post("/applications/{application_id}/prediction-reference")
def record_prediction(application_id: str, payload: PredictionReference, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.write"))], session: Annotated[Session, Depends(get_db)]):
    row = application_or_404(session, application_id); ensure_scope(session, admin, row.organization_id, row.branch_id)
    if row.version != payload.expected_version or row.status != "PREDICTION_PENDING": raise AdminAPIError(409, "PREDICTION_STATE_CONFLICT", "Application is not ready for a prediction result")
    previous = row.status; row.status = "PREDICTED"; row.prediction_id = payload.prediction_id; row.model_recommendation = payload.model_recommendation; row.risk_score_band = payload.risk_score_band; row.version += 1
    session.add(WorkflowHistory(application_id=row.id, from_status=previous, to_status=row.status, changed_by=admin.user.id, reason_code="encrypted_prediction_completed"))
    append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="application.prediction_linked", resource_type="loan_application", resource_id=row.id, result="success", safe_metadata={"prediction_id": row.prediction_id})
    session.commit(); return serialize_application(row)


@router.post("/applications/{application_id}/decision")
def record_decision(application_id: str, payload: DecisionCreate, admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.approve"))], session: Annotated[Session, Depends(get_db)]):
    row = application_or_404(session, application_id); ensure_scope(session, admin, row.organization_id, row.branch_id)
    if row.version != payload.expected_version or row.status != "UNDER_REVIEW": raise AdminAPIError(409, "DECISION_STATE_CONFLICT", "Application is not ready for a final decision")
    is_override = (row.model_recommendation == "HIGH RISK" and payload.decision == "APPROVED") or (row.model_recommendation == "LOW RISK" and payload.decision == "REJECTED")
    if is_override and not payload.override_reason: raise AdminAPIError(422, "OVERRIDE_REASON_REQUIRED", "A model override requires an authorized reason")
    row.status = payload.decision; row.version += 1; row.completed_at = utc_now()
    decision = DecisionRecord(application_id=row.id, officer_id=admin.user.id, decision=payload.decision, model_recommendation=row.model_recommendation, is_override=is_override, override_reason=payload.override_reason, note=payload.note)
    session.add_all([decision, WorkflowHistory(application_id=row.id, from_status="UNDER_REVIEW", to_status=row.status, changed_by=admin.user.id, reason_code="human_decision")])
    session.flush(); append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0], action="application.decision_recorded", resource_type="loan_application", resource_id=row.id, result="success", safe_metadata={"decision": row.status, "model_override": is_override})
    session.commit(); return {**serialize_application(row), "decision_id": decision.id, "model_override": is_override}
