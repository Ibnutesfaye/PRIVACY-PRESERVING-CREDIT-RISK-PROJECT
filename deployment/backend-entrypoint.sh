#!/bin/sh
set -eu

python -c '
import sys, time
from sqlalchemy import text
from backend.app.database import engine

deadline = time.time() + 60
while time.time() < deadline:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
'

python -m alembic upgrade head
python -m backend.scripts.sync_enterprise_rbac
exec "$@"
