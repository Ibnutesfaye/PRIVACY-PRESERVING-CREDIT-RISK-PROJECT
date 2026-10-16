from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin,request_context,require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import ModelVersion
from backend.app.database import get_db
from ml.config import ARTIFACTS_DIR,PROJECT_ROOT

router=APIRouter(prefix="/api/admin/models",tags=["Admin models"])
def ensure_baseline(session:Session)->ModelVersion:
    row=session.scalar(select(ModelVersion).where(ModelVersion.version=="logistic-regression-baseline-v1"))
    if row:return row
    metrics=json.loads((PROJECT_ROOT/"docs/reports/baseline_metrics.json").read_text(encoding="utf-8"))
    digest=hashlib.sha256((ARTIFACTS_DIR/"model.pkl").read_bytes()).hexdigest()
    row=ModelVersion(version="logistic-regression-baseline-v1",model_name="Credit Risk Logistic Regression",model_type="Logistic Regression",dataset_version="credit-risk-deduplicated-v1",polynomial_version="sigmoid-degree7-v1",status="active",fhe_compatible=True,validation_passed=True,metrics=metrics,artifact_hash=digest,notes="Measured seven-feature public-dataset baseline; institutional validation required",approved_by="system",approved_at=datetime.now(timezone.utc),activated_at=datetime.now(timezone.utc))
    session.add(row);session.commit();return row
def serialize(row):return {c.name:getattr(row,c.name) for c in ModelVersion.__table__.columns}
@router.get("")
def models(_admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("model.read"))],session:Annotated[Session,Depends(get_db)]):ensure_baseline(session);return {"items":[serialize(r) for r in session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()]}
@router.get("/metrics")
def model_metrics(_admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("model.read"))],session:Annotated[Session,Depends(get_db)]):
    row=ensure_baseline(session);params=json.loads((ARTIFACTS_DIR/"model_parameters.json").read_text(encoding="utf-8"));pre=json.loads((ARTIFACTS_DIR/"preprocessing_metadata.json").read_text(encoding="utf-8"));poly=json.loads((PROJECT_ROOT/"docs/reports/polynomial_analysis.json").read_text(encoding="utf-8"));return {"model":serialize(row),"parameters":params,"preprocessing":pre,"polynomial":next(c for c in poly["candidates"] if c["degree"]==7),"causality_note":"Coefficient magnitude describes this fitted model on scaled features; it does not establish causal importance."}
def transition(request:Request,row:ModelVersion,admin:AuthenticatedAdmin,session:Session,action:str):
    before=row.status;now=datetime.now(timezone.utc)
    if action=="approve":
        if row.status not in {"testing","draft"} or not row.validation_passed or not row.fhe_compatible:raise AdminAPIError(409,"MODEL_NOT_VALIDATED","Only validated FHE-compatible draft/testing models can be approved")
        row.status="approved";row.approved_by=admin.user.id;row.approved_at=now
    elif action=="activate":
        if row.status!="approved":raise AdminAPIError(409,"MODEL_NOT_APPROVED","Only approved models can be activated")
        for active in session.scalars(select(ModelVersion).where(ModelVersion.status=="active")):active.status="archived"
        row.status="active";row.activated_at=now
    elif action=="archive":
        if row.status=="active":raise AdminAPIError(409,"ACTIVE_MODEL_ARCHIVE_DENIED","Activate another approved model before archiving the active model")
        row.status="archived"
    ip,agent=request_context(request);append_audit_event(session,actor_id=admin.user.id,actor_role=admin.roles[0] if admin.roles else None,action=f"model.{action}",resource_type="model_version",resource_id=row.id,result="success",ip_address=ip,user_agent=agent,safe_metadata={"from_status":before,"to_status":row.status,"version":row.version});session.commit();return serialize(row)
def find(session,id):
    ensure_baseline(session);row=session.get(ModelVersion,id)
    if not row:raise AdminAPIError(404,"MODEL_NOT_FOUND","Model version was not found")
    return row
@router.post("/{model_id}/approve")
def approve(model_id:str,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("model.approve"))],session:Annotated[Session,Depends(get_db)]):return transition(request,find(session,model_id),admin,session,"approve")
@router.post("/{model_id}/activate")
def activate(model_id:str,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("model.activate"))],session:Annotated[Session,Depends(get_db)]):return transition(request,find(session,model_id),admin,session,"activate")
@router.post("/{model_id}/archive")
def archive(model_id:str,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("model.activate"))],session:Annotated[Session,Depends(get_db)]):return transition(request,find(session,model_id),admin,session,"archive")
