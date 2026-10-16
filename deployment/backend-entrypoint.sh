#!/bin/sh
set -eu
python -m alembic upgrade head
python -m backend.scripts.sync_enterprise_rbac
exec "$@"
