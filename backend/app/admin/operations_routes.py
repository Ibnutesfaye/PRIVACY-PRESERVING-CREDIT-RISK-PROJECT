from __future__ import annotations
import json,time
from datetime import datetime,timezone
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Query,Request
from pydantic import BaseModel,Field
from sqlalchemy import func,select,text
from sqlalchemy.orm import Session
from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin,request_context,require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import AdminSetting,AuditLog,ModelVersion,Notification,PredictionMetadata,ReportRecord,SecurityEvent
from backend.app.admin.model_routes import ensure_baseline
from backend.app.database import get_db
from backend.app.service import service

router=APIRouter(prefix="/api/admin",tags=["Admin operations"]);START=time.monotonic()
def page(session,model,page,size,order):
 total=session.scalar(select(func.count()).select_from(model))or 0;rows=session.scalars(select(model).order_by(order).offset((page-1)*size).limit(size)).all();return{"items":[{c.name:getattr(r,c.name) for c in model.__table__.columns}for r in rows],"total":total,"page":page,"pages":max(1,(total+size-1)//size)}
@router.get("/audit-logs")
def audits(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("audit.read"))],s:Annotated[Session,Depends(get_db)],page_number:int=Query(1,alias="page",ge=1),page_size:int=Query(25,ge=1,le=100)):return page(s,AuditLog,page_number,page_size,AuditLog.timestamp.desc())
@router.get("/security-events")
def events(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("security.read"))],s:Annotated[Session,Depends(get_db)],page_number:int=Query(1,alias="page",ge=1),page_size:int=Query(25,ge=1,le=100)):return page(s,SecurityEvent,page_number,page_size,SecurityEvent.created_at.desc())
class EventUpdate(BaseModel):status:Literal["open","investigating","resolved","false_positive"]
@router.patch("/security-events/{event_id}")
def event_update(event_id:str,p:EventUpdate,r:Request,a:Annotated[AuthenticatedAdmin,Depends(require_permissions("security.read"))],s:Annotated[Session,Depends(get_db)]):
 e=s.get(SecurityEvent,event_id)
 if not e:raise AdminAPIError(404,"SECURITY_EVENT_NOT_FOUND","Security event was not found")
 e.status=p.status;e.resolved_at=datetime.now(timezone.utc) if p.status in{"resolved","false_positive"}else None;ip,ua=request_context(r);append_audit_event(s,actor_id=a.user.id,actor_role=a.roles[0]if a.roles else None,action="security.event.updated",resource_type="security_event",resource_id=e.id,result="success",ip_address=ip,user_agent=ua,safe_metadata={"status":p.status});s.commit();return{"success":True}
@router.get("/system-health")
def health(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("dashboard.read"))],s:Annotated[Session,Depends(get_db)]):
 db="healthy"
 try:s.execute(text("SELECT 1"))
 except Exception:db="down"
 model=ensure_baseline(s)
 last=s.scalar(select(PredictionMetadata).where(PredictionMetadata.request_status=="completed").order_by(PredictionMetadata.created_at.desc()))
 return{"polled_at":datetime.now(timezone.utc),"polling_interval_seconds":20,"uptime_seconds":round(time.monotonic()-START),"services":[{"name":"FastAPI","status":"healthy"},{"name":"Database","status":db},{"name":"OpenFHE executable","status":"healthy"if service.executable.exists()else"down"},{"name":"ML model","status":"healthy"if model.status=="active"else"degraded"}],"last_successful_fhe_evaluation":last.completed_at if last else None,"note":"Pilot service polling; centralized production telemetry and alerting require institutional infrastructure approval."}
@router.get("/notifications")
def notifications(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("dashboard.read"))],s:Annotated[Session,Depends(get_db)]):return page(s,Notification,1,50,Notification.created_at.desc())
DEFAULTS={"general.application_name":("Privacy-Preserving Credit Risk","Displayed application name"),"general.time_zone":("Africa/Nairobi","Display time zone"),"prediction.risk_threshold":(0.5,"Model assessment classification threshold"),"prediction.request_timeout_seconds":(120,"FHE request timeout"),"fhe.active_profile":("ckks-balanced-degree7-v1","Non-secret CKKS profile identifier"),"security.session_timeout_minutes":(15,"Access-token lifetime guidance"),"security.audit_retention_days":(365,"Audit retention policy")}
def ensure_settings(s):
 existing={x.key for x in s.scalars(select(AdminSetting))}
 for key,(value,description)in DEFAULTS.items():
  if key not in existing:s.add(AdminSetting(key=key,value=value,description=description))
 s.commit()
@router.get("/settings")
def settings(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("settings.read"))],s:Annotated[Session,Depends(get_db)]):ensure_settings(s);return{"items":[{"key":x.key,"value":x.value,"description":x.description,"updated_at":x.updated_at}for x in s.scalars(select(AdminSetting).order_by(AdminSetting.key))]}
class SettingUpdate(BaseModel):value:str|int|float|bool
@router.patch("/settings/{key}")
def setting(key:str,p:SettingUpdate,r:Request,a:Annotated[AuthenticatedAdmin,Depends(require_permissions("settings.write"))],s:Annotated[Session,Depends(get_db)]):
 ensure_settings(s);row=s.scalar(select(AdminSetting).where(AdminSetting.key==key))
 if not row:raise AdminAPIError(404,"SETTING_NOT_FOUND","Setting was not found")
 if any(x in key for x in("secret","password","private_key")):raise AdminAPIError(403,"SECRET_SETTING_DENIED","Secret configuration cannot be managed here")
 row.value=p.value;row.updated_by=a.user.id;ip,ua=request_context(r);append_audit_event(s,actor_id=a.user.id,actor_role=a.roles[0]if a.roles else None,action="settings.updated",resource_type="admin_setting",resource_id=row.id,result="success",ip_address=ip,user_agent=ua,safe_metadata={"setting_key":key});s.commit();return{"success":True}
class ReportRequest(BaseModel):report_type:Literal["prediction_summary","fhe_performance","ml_performance","privacy_compliance","security_events","audit_summary","benchmark"];format:Literal["json","csv"]="json"
@router.get("/reports")
def reports(_a:Annotated[AuthenticatedAdmin,Depends(require_permissions("reports.export"))],s:Annotated[Session,Depends(get_db)]):return page(s,ReportRecord,1,50,ReportRecord.created_at.desc())
@router.post("/reports/generate")
def report(p:ReportRequest,r:Request,a:Annotated[AuthenticatedAdmin,Depends(require_permissions("reports.export"))],s:Annotated[Session,Depends(get_db)]):
 counts={"predictions":s.scalar(select(func.count()).select_from(PredictionMetadata))or 0,"security_events":s.scalar(select(func.count()).select_from(SecurityEvent))or 0,"audit_events":s.scalar(select(func.count()).select_from(AuditLog))or 0};row=ReportRecord(report_type=p.report_type,format=p.format,status="completed",created_by=a.user.id,safe_parameters={},row_count=sum(counts.values()));s.add(row);s.flush();ip,ua=request_context(r);append_audit_event(s,actor_id=a.user.id,actor_role=a.roles[0]if a.roles else None,action="report.generated",resource_type="report",resource_id=row.id,result="success",ip_address=ip,user_agent=ua,safe_metadata={"report_type":p.report_type,"format":p.format});s.commit();return{"id":row.id,"status":"completed","generated_at":row.created_at,"report_type":p.report_type,"format":p.format,"summary":counts,"privacy":"Contains aggregate and privacy-safe metadata only"}
