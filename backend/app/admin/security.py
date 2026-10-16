from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from backend.app.admin.config import AdminSettings


password_hasher = PasswordHasher(time_cost=3, memory_cost=1024, parallelism=1)


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_strong_password(password: str) -> None:
    requirements = [
        (len(password) >= 14, "at least 14 characters"),
        (bool(re.search(r"[A-Z]", password)), "an uppercase letter"),
        (bool(re.search(r"[a-z]", password)), "a lowercase letter"),
        (bool(re.search(r"\d", password)), "a digit"),
        (bool(re.search(r"[^A-Za-z0-9]", password)), "a symbol"),
    ]
    missing = [label for valid, label in requirements if not valid]
    if missing:
        raise ValueError("Password must contain " + ", ".join(missing))


def hash_password(password: str) -> str:
    validate_strong_password(password)
    return password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hasher.verify(encoded_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(encoded_hash: str) -> bool:
    try:
        return password_hasher.check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return True


def create_access_token(
    *,
    user_id: str,
    roles: list[str],
    permissions: list[str],
    settings: AdminSettings,
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "roles": roles,
        "permissions": permissions,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), expires_at


def decode_access_token(token: str, settings: AdminSettings) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"require": ["sub", "type", "jti", "iat", "exp"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


def create_refresh_secret() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_secret(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

