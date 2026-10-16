"""Restore a verified dump into an existing clean, non-development PostgreSQL DB."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.app.database import database_url
from backend.scripts.backup_database import postgres_tool


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    arguments = parser.parse_args()
    backup = arguments.backup.resolve()
    sidecar = backup.with_suffix(backup.suffix + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    if hashlib.sha256(backup.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Backup checksum validation failed")
    restore_url_text = os.environ.get("CIPHERSCORE_RESTORE_DATABASE_URL", "").strip()
    if not restore_url_text:
        raise RuntimeError("CIPHERSCORE_RESTORE_DATABASE_URL must identify a DBA-created clean test database")
    source_url, restore_url = make_url(database_url()), make_url(restore_url_text)
    if not restore_url.drivername.startswith("postgresql") or not restore_url.database:
        raise RuntimeError("Restore target must be PostgreSQL")
    if (restore_url.host, restore_url.port or 5432, restore_url.database) == (source_url.host, source_url.port or 5432, source_url.database):
        raise RuntimeError("Refusing to restore over the working application database")
    environment = os.environ.copy()
    environment["PGPASSWORD"] = restore_url.password or ""
    command = [postgres_tool("pg_restore"), "--exit-on-error", "--no-owner", "--no-privileges", "--host", restore_url.host or "127.0.0.1", "--port", str(restore_url.port or 5432), "--username", restore_url.username or "", "--dbname", restore_url.database, str(backup)]
    restored = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
    if restored.returncode != 0:
        raise RuntimeError(f"Restore failed with exit code {restored.returncode}; native details suppressed")
    migration_environment = environment.copy()
    migration_environment["ADMIN_DATABASE_URL"] = restore_url_text
    migrated = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[2], env=migration_environment, capture_output=True, text=True, check=False)
    if migrated.returncode != 0:
        raise RuntimeError(f"Migration verification failed with exit code {migrated.returncode}; details suppressed")
    engine = create_engine(restore_url_text, pool_pre_ping=True, pool_timeout=5, connect_args={"connect_timeout": 5})
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        predictions = connection.execute(text("SELECT count(*) FROM prediction_metadata")).scalar_one()
        metrics = connection.execute(text("SELECT count(*) FROM fhe_metrics")).scalar_one()
    engine.dispose()
    print({"status": "PASS", "revision": revision, "table_count": len(tables), "prediction_metadata_rows": predictions, "fhe_metric_rows": metrics})


if __name__ == "__main__":
    main()

