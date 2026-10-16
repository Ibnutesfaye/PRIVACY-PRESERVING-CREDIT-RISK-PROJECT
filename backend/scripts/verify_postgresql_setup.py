"""Verify PostgreSQL schema and seeded administrator without exposing secrets."""

from __future__ import annotations

import json
import os

from sqlalchemy import inspect, select, text

from backend.app.admin.models import AdminUser, Role, UserRole
from backend.app.admin.security import verify_password
from backend.app.database import SessionLocal, engine


REQUIRED_TABLES = {
    "admin_users", "roles", "permissions", "role_permissions", "user_roles",
    "refresh_tokens", "audit_logs", "security_events", "prediction_metadata",
    "model_versions", "notifications", "admin_settings", "reports", "fhe_metrics",
    "model_metrics", "benchmark_runs", "benchmark_results", "system_health",
}


def required(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"{name} must be set for setup verification")
    return value


def main() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("setup verification is not connected to PostgreSQL")
    tables = set(inspect(engine).get_table_names())
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise RuntimeError("required database tables are missing: " + ", ".join(missing))

    email = required("ADMIN_SEED_EMAIL").strip().lower()
    password = required("ADMIN_SEED_PASSWORD")
    with SessionLocal() as session:
        admin = session.scalar(select(AdminUser).where(AdminUser.email == email))
        if admin is None or not admin.is_active or admin.is_suspended:
            raise RuntimeError("seeded administrator is unavailable or inactive")
        if not verify_password(password, admin.password_hash):
            raise RuntimeError("seeded administrator credential verification failed")
        super_role = session.scalar(select(Role).where(Role.name == "super_admin"))
        if super_role is None:
            raise RuntimeError("super_admin role is missing")
        assignment = session.scalar(
            select(UserRole).where(
                UserRole.user_id == admin.id,
                UserRole.role_id == super_role.id,
            )
        )
        if assignment is None:
            raise RuntimeError("seeded administrator lacks the super_admin role")

    with engine.connect() as connection:
        identity = connection.execute(
            text("SELECT current_database(), current_user")
        ).one()
    print(json.dumps({
        "database": identity[0],
        "database_user": identity[1],
        "required_tables_verified": len(REQUIRED_TABLES),
        "administrator_verified": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
