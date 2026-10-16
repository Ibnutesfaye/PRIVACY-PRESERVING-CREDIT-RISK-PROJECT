from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import (
    AuthenticatedAdmin,
    authenticate_admin,
    get_current_admin,
    request_context,
    rotate_refresh_token,
)
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import RefreshToken, utc_now
from backend.app.admin.schemas import (
    AdminIdentity,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
)
from backend.app.admin.security import hash_refresh_secret
from backend.app.database import get_db


router = APIRouter(prefix="/api/admin/auth", tags=["Admin authentication"])


def token_response(
    admin: AuthenticatedAdmin,
    access_token: str,
    refresh_token: str,
    access_expires_at,  # type: ignore[no-untyped-def]
    refresh_expires_at,  # type: ignore[no-untyped-def]
) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        admin=AdminIdentity(
            id=admin.user.id,
            email=admin.user.email,
            full_name=admin.user.full_name,
            roles=admin.roles,
            permissions=admin.permissions,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    result = authenticate_admin(
        session,
        email=str(payload.email),
        password=payload.password.get_secret_value(),
        request=request,
    )
    return token_response(*result)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    result = rotate_refresh_token(
        session,
        refresh_secret=payload.refresh_token.get_secret_value(),
        request=request,
    )
    return token_response(*result)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    request: Request,
    admin: Annotated[AuthenticatedAdmin, Depends(get_current_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    token = session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_secret(payload.refresh_token.get_secret_value()),
            RefreshToken.user_id == admin.user.id,
        )
    )
    if token is None or token.revoked_at is not None:
        raise AdminAPIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired")
    token.revoked_at = utc_now()
    ip_address, user_agent = request_context(request)
    append_audit_event(
        session,
        actor_id=admin.user.id,
        actor_role=admin.roles[0] if admin.roles else None,
        action="admin.logout",
        resource_type="admin_session",
        resource_id=token.id,
        result="success",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.commit()
    return MessageResponse(success=True, message="Logged out")


@router.get("/me", response_model=AdminIdentity)
def me(admin: Annotated[AuthenticatedAdmin, Depends(get_current_admin)]) -> AdminIdentity:
    return AdminIdentity(
        id=admin.user.id,
        email=admin.user.email,
        full_name=admin.user.full_name,
        roles=admin.roles,
        permissions=admin.permissions,
    )

