from __future__ import annotations
from typing import Annotated
from pydantic import BaseModel,EmailStr,Field,SecretStr
from fastapi import APIRouter,Depends,Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin,request_context,require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import AdminUser,Permission,RefreshToken,Role,RolePermission,UserRole,utc_now
from backend.app.admin.repository import authorization_for,get_user_with_authorization,seed_roles_and_permissions
from backend.app.admin.security import hash_password
from backend.app.database import get_db

router=APIRouter(prefix="/api/admin",tags=["Admin users and roles"])
class UserCreate(BaseModel):
    email:EmailStr;full_name:str=Field(min_length=2,max_length=160);password:SecretStr;role_ids:list[str]=Field(min_length=1,max_length=4)
class UserUpdate(BaseModel):
    full_name:str|None=Field(None,min_length=2,max_length=160);role_ids:list[str]|None=None;is_active:bool|None=None
class RoleCreate(BaseModel):
    name:str=Field(pattern=r"^[a-z][a-z0-9_]{2,79}$");description:str=Field(min_length=3,max_length=255);permission_codes:list[str]
class RoleUpdate(BaseModel):
    description:str|None=Field(None,min_length=3,max_length=255);permission_codes:list[str]|None=None
def user_data(session,user):
    hydrated=get_user_with_authorization(session,user.id);roles,permissions=authorization_for(hydrated) if hydrated else([],[])
    return {"id":user.id,"email":user.email,"full_name":user.full_name,"roles":roles,"permissions":permissions,"is_active":user.is_active,"is_suspended":user.is_suspended,"last_login_at":user.last_login_at,"failed_login_count":user.failed_login_count,"created_at":user.created_at,"created_by":user.created_by}
def audit(request,session,admin,action,resource,id,metadata=None):
    ip,agent=request_context(request);append_audit_event(session,actor_id=admin.user.id,actor_role=admin.roles[0] if admin.roles else None,action=action,resource_type=resource,resource_id=id,result="success",ip_address=ip,user_agent=agent,safe_metadata=metadata or {})
@router.get("/users")
def users(_admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("users.read"))],session:Annotated[Session,Depends(get_db)]):seed_roles_and_permissions(session);session.flush();return{"items":[user_data(session,u) for u in session.scalars(select(AdminUser).order_by(AdminUser.created_at.desc())).all()]}
@router.post("/users",status_code=201)
def create_user(payload:UserCreate,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("users.write"))],session:Annotated[Session,Depends(get_db)]):
    email=str(payload.email).casefold();
    if session.scalar(select(AdminUser).where(AdminUser.email==email)):raise AdminAPIError(409,"DUPLICATE_EMAIL","An administrator with that email already exists")
    roles=session.scalars(select(Role).where(Role.id.in_(payload.role_ids))).all()
    if len(roles)!=len(set(payload.role_ids)):raise AdminAPIError(422,"INVALID_ROLE","One or more roles are invalid")
    user=AdminUser(email=email,full_name=payload.full_name.strip(),password_hash=hash_password(payload.password.get_secret_value()),created_by=admin.user.id);session.add(user);session.flush()
    for role in roles:session.add(UserRole(user_id=user.id,role_id=role.id,assigned_by=admin.user.id))
    audit(request,session,admin,"admin.user.created","admin_user",user.id,{"roles":[r.name for r in roles]});session.commit();return user_data(session,user)
@router.patch("/users/{user_id}")
def update_user(user_id:str,payload:UserUpdate,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("users.write"))],session:Annotated[Session,Depends(get_db)]):
    user=session.get(AdminUser,user_id)
    if not user:raise AdminAPIError(404,"ADMIN_USER_NOT_FOUND","Administrator was not found")
    if payload.full_name is not None:user.full_name=payload.full_name.strip()
    if payload.is_active is not None:user.is_active=payload.is_active
    if payload.role_ids is not None:
        roles=session.scalars(select(Role).where(Role.id.in_(payload.role_ids))).all()
        if len(roles)!=len(set(payload.role_ids)):raise AdminAPIError(422,"INVALID_ROLE","One or more roles are invalid")
        for row in session.scalars(select(UserRole).where(UserRole.user_id==user.id)):session.delete(row)
        for role in roles:session.add(UserRole(user_id=user.id,role_id=role.id,assigned_by=admin.user.id))
    audit(request,session,admin,"admin.user.updated","admin_user",user.id);session.commit();return user_data(session,user)
@router.post("/users/{user_id}/suspend")
def suspend(user_id:str,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("users.write"))],session:Annotated[Session,Depends(get_db)]):
    if user_id==admin.user.id:raise AdminAPIError(409,"SELF_SUSPENSION_DENIED","You cannot suspend your own account")
    user=session.get(AdminUser,user_id)
    if not user:raise AdminAPIError(404,"ADMIN_USER_NOT_FOUND","Administrator was not found")
    user.is_suspended=True
    for token in session.scalars(select(RefreshToken).where(RefreshToken.user_id==user.id,RefreshToken.revoked_at.is_(None))):token.revoked_at=utc_now()
    audit(request,session,admin,"admin.user.suspended","admin_user",user.id);session.commit();return{"success":True}
@router.post("/users/{user_id}/revoke-sessions")
def revoke(user_id:str,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("users.write"))],session:Annotated[Session,Depends(get_db)]):
    rows=session.scalars(select(RefreshToken).where(RefreshToken.user_id==user_id,RefreshToken.revoked_at.is_(None))).all()
    for token in rows:token.revoked_at=utc_now()
    audit(request,session,admin,"admin.sessions.revoked","admin_user",user_id,{"session_count":len(rows)});session.commit();return{"success":True,"revoked":len(rows)}
@router.get("/roles")
def roles(_admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("roles.read"))],session:Annotated[Session,Depends(get_db)]):
    seed_roles_and_permissions(session);session.commit();result=[]
    for role in session.scalars(select(Role).order_by(Role.name)).all():
        codes=session.scalars(select(Permission.code).join(RolePermission).where(RolePermission.role_id==role.id)).all();result.append({"id":role.id,"name":role.name,"description":role.description,"is_system":role.is_system,"permissions":sorted(codes)})
    return{"items":result,"permissions":[{"id":p.id,"code":p.code,"description":p.description} for p in session.scalars(select(Permission).order_by(Permission.code)).all()]}
def set_permissions(session,role,codes):
    permissions=session.scalars(select(Permission).where(Permission.code.in_(codes))).all()
    if len(permissions)!=len(set(codes)):raise AdminAPIError(422,"INVALID_PERMISSION","One or more permissions are invalid")
    for row in session.scalars(select(RolePermission).where(RolePermission.role_id==role.id)):session.delete(row)
    for permission in permissions:session.add(RolePermission(role_id=role.id,permission_id=permission.id))
@router.post("/roles",status_code=201)
def create_role(payload:RoleCreate,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("roles.write"))],session:Annotated[Session,Depends(get_db)]):
    if session.scalar(select(Role).where(Role.name==payload.name)):raise AdminAPIError(409,"DUPLICATE_ROLE","Role already exists")
    role=Role(name=payload.name,description=payload.description,is_system=False);session.add(role);session.flush();set_permissions(session,role,payload.permission_codes);audit(request,session,admin,"role.created","role",role.id);session.commit();return{"id":role.id,"name":role.name}
@router.patch("/roles/{role_id}")
def update_role(role_id:str,payload:RoleUpdate,request:Request,admin:Annotated[AuthenticatedAdmin,Depends(require_permissions("roles.write"))],session:Annotated[Session,Depends(get_db)]):
    role=session.get(Role,role_id)
    if not role:raise AdminAPIError(404,"ROLE_NOT_FOUND","Role was not found")
    if payload.description is not None:role.description=payload.description
    if payload.permission_codes is not None:set_permissions(session,role,payload.permission_codes)
    audit(request,session,admin,"role.updated","role",role.id);session.commit();return{"id":role.id,"name":role.name}
