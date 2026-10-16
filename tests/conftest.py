from __future__ import annotations

import os
from pathlib import Path

import pytest


# The application has no database fallback. Tests explicitly select an isolated
# local database before application modules are imported.
TEST_DATABASE = Path(__file__).resolve().parents[1] / "backend" / "test-admin.db"
os.environ.setdefault("ADMIN_DATABASE_URL", f"sqlite:///{TEST_DATABASE.as_posix()}")
os.environ.setdefault("ADMIN_JWT_SECRET", "test-only-secret-at-least-thirty-two-characters")


@pytest.fixture(autouse=True)
def ensure_file_test_database_schema():
    """Keep the shared file test DB valid across modules with isolated DB fixtures."""
    from backend.app.admin import models  # noqa: F401
    from backend.app.database import Base, engine

    Base.metadata.create_all(engine)
    yield
