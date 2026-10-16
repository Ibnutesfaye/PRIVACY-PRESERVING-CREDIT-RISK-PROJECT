"""Create the initial super administrator from environment variables."""

from __future__ import annotations

import os

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from backend.app.admin.audit import append_audit_event
from backend.app.admin.models import AdminUser, Role, UserRole
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.admin.security import hash_password, validate_strong_password
from backend.app.database import SessionLocal


def required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def main() -> None:
    email = str(TypeAdapter(EmailStr).validate_python(required_environment("ADMIN_SEED_EMAIL"))).lower()
    display_name = required_environment("ADMIN_SEED_NAME")
    password = required_environment("ADMIN_SEED_PASSWORD")
    validate_strong_password(password)

    with SessionLocal.begin() as session:
        seed_roles_and_permissions(session)
        role = session.scalar(select(Role).where(Role.name == "super_admin"))
        if role is None:
            raise RuntimeError("super_admin role was not seeded")

        existing = session.scalar(select(AdminUser).where(AdminUser.email == email))
        if existing:
            existing.full_name = display_name
            existing.password_hash = hash_password(password)
            existing.is_active = True
            existing.is_suspended = False
            existing.failed_login_count = 0
            existing.locked_until = None
            assignment = session.scalar(
                select(UserRole).where(
                    UserRole.user_id == existing.id,
                    UserRole.role_id == role.id,
                )
            )
            if assignment is None:
                session.add(UserRole(user_id=existing.id, role_id=role.id))
            append_audit_event(
                session,
                actor_id=existing.id,
                action="admin.seed.updated",
                resource_type="admin_user",
                resource_id=existing.id,
                result="success",
                safe_metadata={"role": role.name},
            )
            admin = existing
            operation = "Updated"
        else:
            admin = AdminUser(
                email=email,
                full_name=display_name,
                password_hash=hash_password(password),
                is_active=True,
            )
            session.add(admin)
            session.flush()
            session.add(UserRole(user_id=admin.id, role_id=role.id))
            append_audit_event(
                session,
                actor_id=admin.id,
                action="admin.seed.created",
                resource_type="admin_user",
                resource_id=admin.id,
                result="success",
                safe_metadata={"role": role.name},
            )
            operation = "Created"

    print(f"{operation} initial administrator {email} (id={admin.id}).")


if __name__ == "__main__":
    main()
