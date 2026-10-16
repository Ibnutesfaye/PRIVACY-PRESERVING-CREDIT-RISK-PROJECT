from __future__ import annotations

import secrets
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.admin.audit import append_audit_event
from backend.app.admin.config import AdminConfigurationError, get_admin_settings
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import AdminUser, RefreshToken, SecurityEvent, utc_now
from backend.app.admin.repository import authorization_for, get_user_with_authorization
from backend.app.admin.security import (
    create_access_token,
    create_refresh_secret,
    decode_access_token,
    hash_refresh_secret,
    normalize_email,
    password_hasher,
    password_needs_rehash,
    verify_password,
)
from backend.app.database import get_db


bearer_scheme = HTTPBearer(auto_error=False)
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def request_context(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


class LoginRateLimiter:
    """Small per-process IP limiter; production should use a shared store."""

    def __init__(self, attempts: int = 20, window_seconds: int = 60) -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.attempts:
                raise AdminAPIError(429, "AUTH_RATE_LIMITED", "Too many login attempts. Try again later.")
            events.append(now)


login_rate_limiter = LoginRateLimiter()


@dataclass
class AuthenticatedAdmin:
    user: AdminUser
    roles: list[str]
    permissions: list[str]


def authenticate_admin(
    session: Session,
    *,
    email: str,
    password: str,
    request: Request,
) -> tuple[AuthenticatedAdmin, str, str, datetime, datetime]:
    try:
        settings = get_admin_settings()
    except AdminConfigurationError as error:
        raise AdminAPIError(503, "ADMIN_AUTH_NOT_CONFIGURED", str(error)) from error

    ip_address, user_agent = request_context(request)
    login_rate_limiter.check(ip_address or "unknown")
    normalized = normalize_email(email)
    user = session.scalar(select(AdminUser).where(AdminUser.email == normalized))
    now = utc_now()

    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        append_audit_event(
            session,
            action="admin.login.failed",
            resource_type="admin_session",
            result="denied",
            ip_address=ip_address,
            user_agent=user_agent,
            safe_metadata={"reason": "invalid_credentials"},
        )
        session.commit()
        raise AdminAPIError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    locked_until = _aware(user.locked_until)
    if locked_until and locked_until > now:
        append_audit_event(
            session,
            actor_id=user.id,
            action="admin.login.blocked",
            resource_type="admin_user",
            resource_id=user.id,
            result="denied",
            ip_address=ip_address,
            user_agent=user_agent,
            safe_metadata={"reason": "account_locked"},
        )
        session.commit()
        raise AdminAPIError(423, "ACCOUNT_LOCKED", "Account is temporarily locked")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        locked = user.failed_login_count >= settings.max_failed_logins
        if locked:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            session.add(
                SecurityEvent(
                    event_type="repeated_failed_login",
                    severity="high",
                    summary="Administrator account locked after repeated failed login attempts",
                    actor_id=user.id,
                    safe_details={"failed_login_count": user.failed_login_count},
                )
            )
        append_audit_event(
            session,
            actor_id=user.id,
            action="admin.login.failed",
            resource_type="admin_user",
            resource_id=user.id,
            result="denied",
            ip_address=ip_address,
            user_agent=user_agent,
            safe_metadata={"reason": "invalid_credentials", "account_locked": locked},
        )
        session.commit()
        if locked:
            raise AdminAPIError(423, "ACCOUNT_LOCKED", "Account is temporarily locked")
        raise AdminAPIError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    if not user.is_active or user.is_suspended:
        append_audit_event(
            session,
            actor_id=user.id,
            action="admin.login.blocked",
            resource_type="admin_user",
            resource_id=user.id,
            result="denied",
            ip_address=ip_address,
            user_agent=user_agent,
            safe_metadata={"reason": "account_inactive"},
        )
        session.commit()
        raise AdminAPIError(403, "ACCOUNT_DISABLED", "Account is not available")

    if password_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    session.flush()
    hydrated = get_user_with_authorization(session, user.id)
    if hydrated is None:
        raise AdminAPIError(401, "INVALID_CREDENTIALS", "Invalid email or password")
    roles, permissions = authorization_for(hydrated)
    access_token, access_expires = create_access_token(
        user_id=user.id,
        roles=roles,
        permissions=permissions,
        settings=settings,
    )
    refresh_secret = create_refresh_secret()
    refresh_expires = now + timedelta(days=settings.refresh_token_days)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_secret(refresh_secret),
            expires_at=refresh_expires,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:512] or None,
        )
    )
    append_audit_event(
        session,
        actor_id=user.id,
        actor_role=roles[0] if roles else None,
        action="admin.login.succeeded",
        resource_type="admin_session",
        resource_id=user.id,
        result="success",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.commit()
    return AuthenticatedAdmin(hydrated, roles, permissions), access_token, refresh_secret, access_expires, refresh_expires


def rotate_refresh_token(
    session: Session,
    *,
    refresh_secret: str,
    request: Request,
) -> tuple[AuthenticatedAdmin, str, str, datetime, datetime]:
    try:
        settings = get_admin_settings()
    except AdminConfigurationError as error:
        raise AdminAPIError(503, "ADMIN_AUTH_NOT_CONFIGURED", str(error)) from error
    now = utc_now()
    token = session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_secret(refresh_secret))
    )
    if token is None or token.revoked_at is not None or (_aware(token.expires_at) or now) <= now:
        raise AdminAPIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired")
    user = get_user_with_authorization(session, token.user_id)
    if user is None or not user.is_active or user.is_suspended:
        raise AdminAPIError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired")
    roles, permissions = authorization_for(user)
    access_token, access_expires = create_access_token(
        user_id=user.id,
        roles=roles,
        permissions=permissions,
        settings=settings,
    )
    new_secret = create_refresh_secret()
    new_expires = now + timedelta(days=settings.refresh_token_days)
    replacement = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_secret(new_secret),
        expires_at=new_expires,
        ip_address=request_context(request)[0],
        user_agent=(request_context(request)[1] or "")[:512] or None,
    )
    session.add(replacement)
    session.flush()
    token.revoked_at = now
    token.replaced_by_id = replacement.id
    append_audit_event(
        session,
        actor_id=user.id,
        actor_role=roles[0] if roles else None,
        action="admin.token.refreshed",
        resource_type="admin_session",
        resource_id=replacement.id,
        result="success",
        ip_address=request_context(request)[0],
        user_agent=request_context(request)[1],
    )
    session.commit()
    return AuthenticatedAdmin(user, roles, permissions), access_token, new_secret, access_expires, new_expires


def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> AuthenticatedAdmin:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AdminAPIError(401, "AUTHENTICATION_REQUIRED", "A valid access token is required")
    try:
        settings = get_admin_settings()
        payload = decode_access_token(credentials.credentials, settings)
    except AdminConfigurationError as error:
        raise AdminAPIError(503, "ADMIN_AUTH_NOT_CONFIGURED", str(error)) from error
    except jwt.ExpiredSignatureError as error:
        raise AdminAPIError(401, "TOKEN_EXPIRED", "Access token has expired") from error
    except jwt.InvalidTokenError as error:
        raise AdminAPIError(401, "INVALID_TOKEN", "Access token is invalid") from error
    user = get_user_with_authorization(session, str(payload["sub"]))
    if user is None or not user.is_active or user.is_suspended:
        raise AdminAPIError(401, "INVALID_TOKEN", "Access token is invalid")
    roles, permissions = authorization_for(user)
    return AuthenticatedAdmin(user, roles, permissions)


def require_permissions(*required: str):  # type: ignore[no-untyped-def]
    def dependency(admin: Annotated[AuthenticatedAdmin, Depends(get_current_admin)]) -> AuthenticatedAdmin:
        missing = sorted(set(required) - set(admin.permissions))
        if missing:
            raise AdminAPIError(403, "INSUFFICIENT_PERMISSION", "Required permission is missing")
        return admin
    return dependency

