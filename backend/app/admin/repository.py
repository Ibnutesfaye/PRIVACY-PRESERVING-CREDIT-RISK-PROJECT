from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.admin.constants import PERMISSIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from backend.app.admin.models import AdminUser, Permission, Role, RolePermission, UserRole


def seed_roles_and_permissions(session: Session) -> None:
    permission_rows = {row.code: row for row in session.scalars(select(Permission)).all()}
    for code, description in PERMISSIONS.items():
        if code not in permission_rows:
            row = Permission(code=code, description=description)
            session.add(row)
            permission_rows[code] = row
    session.flush()

    role_rows = {row.name: row for row in session.scalars(select(Role)).all()}
    for name, description in ROLE_DESCRIPTIONS.items():
        if name not in role_rows:
            row = Role(name=name, description=description, is_system=True)
            session.add(row)
            role_rows[name] = row
    session.flush()

    existing = {
        (row.role_id, row.permission_id)
        for row in session.scalars(select(RolePermission)).all()
    }
    for role_name, codes in ROLE_PERMISSIONS.items():
        role = role_rows[role_name]
        for code in codes:
            key = (role.id, permission_rows[code].id)
            if key not in existing:
                session.add(RolePermission(role_id=role.id, permission_id=permission_rows[code].id))


def get_user_with_authorization(session: Session, user_id: str) -> AdminUser | None:
    return session.scalar(
        select(AdminUser)
        .where(AdminUser.id == user_id)
        .options(
            selectinload(AdminUser.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
    )


def authorization_for(user: AdminUser) -> tuple[list[str], list[str]]:
    roles = sorted({user_role.role.name for user_role in user.user_roles})
    permissions = sorted(
        {
            role_permission.permission.code
            for user_role in user.user_roles
            for role_permission in user_role.role.role_permissions
        }
    )
    return roles, permissions

