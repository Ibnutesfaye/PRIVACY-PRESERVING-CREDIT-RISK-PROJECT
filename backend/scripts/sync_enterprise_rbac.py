"""Idempotently synchronize enterprise roles and permissions after migrations."""

from __future__ import annotations

from sqlalchemy import func, select

from backend.app.admin.models import Permission, Role
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.database import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        seed_roles_and_permissions(session)
        session.commit()
        role_count = session.scalar(select(func.count()).select_from(Role))
        permission_count = session.scalar(select(func.count()).select_from(Permission))
    print(f"PASS: synchronized {role_count} roles and {permission_count} permissions")


if __name__ == "__main__":
    main()
