"""Seed clearly labeled privacy-safe development data with environment-only passwords."""
from __future__ import annotations
import os
from sqlalchemy import select
from backend.app.admin.models import AdminUser,Notification,PredictionMetadata,Role,SecurityEvent,UserRole
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.admin.security import hash_password
from backend.app.admin.model_routes import ensure_baseline
from backend.app.database import SessionLocal
ACCOUNTS=[("super_admin","DEMO_SUPER_ADMIN_PASSWORD"),("ml_fhe_analyst","DEMO_ANALYST_PASSWORD"),("auditor","DEMO_AUDITOR_PASSWORD"),("support_admin","DEMO_SUPPORT_PASSWORD")]
def main():
 s = SessionLocal()
 try:
  seed_roles_and_permissions(s);s.flush();roles={r.name:r for r in s.scalars(select(Role))}
  for role_name,env_name in ACCOUNTS:
   password=os.getenv(env_name,"")
   if not password:raise RuntimeError(f"{env_name} must be set; demo passwords are never hard-coded")
   email=f"demo.{role_name}@example.com"
   if not s.scalar(select(AdminUser).where(AdminUser.email==email)):
    user=AdminUser(email=email,full_name=f"Demo {role_name.replace('_',' ').title()}",password_hash=hash_password(password));s.add(user);s.flush();s.add(UserRole(user_id=user.id,role_id=roles[role_name].id))
  ensure_baseline(s)
  if not s.scalar(select(PredictionMetadata).where(PredictionMetadata.prediction_id=="DEMO-PRD-001")):s.add(PredictionMetadata(prediction_id="DEMO-PRD-001",anonymous_user_id="DEMO-USR-001",risk_class="LOW RISK",risk_score_band="0.25-0.49",encryption_status="successful",evaluation_status="successful",model_version="logistic-regression-baseline-v1",fhe_profile="ckks-balanced-degree7-v1",encryption_time_ms=12,evaluation_time_ms=21,decryption_time_ms=6,total_latency_ms=44,request_status="completed"))
  if not s.scalar(select(Notification).where(Notification.title=="Demo benchmark completed")):s.add(Notification(category="benchmark",severity="informational",title="Demo benchmark completed",message="Clearly labeled development notification; not a measured research result."))
  if not s.scalar(select(SecurityEvent).where(SecurityEvent.event_type=="demo_failed_login")):s.add(SecurityEvent(event_type="demo_failed_login",severity="low",summary="Demo security event for interface validation",safe_details={"demo":True}))
  s.commit()
 finally:
  s.close()
 print("Seeded four demo roles and clearly labeled privacy-safe development records.")
if __name__=="__main__":main()
