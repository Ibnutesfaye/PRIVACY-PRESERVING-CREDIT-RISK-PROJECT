from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.admin import dashboard
from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin, request_context, require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import BenchmarkResult, BenchmarkRun, FheMetric, utc_now
from backend.app.database import get_db
from ml.config import PROJECT_ROOT


router = APIRouter(prefix="/api/admin/fhe", tags=["Admin FHE"])
_benchmark_lock = threading.Lock()
_last_benchmark_at = 0.0


@router.get("/metrics")
def metrics(_admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("fhe.read"))]):
    measured = dashboard.fhe_performance()
    measured.update({"multiplicative_depth": 6, "scaling_modulus_bits": 50, "batch_size": 8192,
        "security_level": "OpenFHE default HEStd_128_classic", "feature_ciphertexts": 7,
        "rotations": 0, "plaintext_multiplications": 11, "ciphertext_multiplications": 4,
        "additions": 11, "boundary": "trusted-client and evaluator responsibilities are separated; the evaluator has no client secret key"})
    return measured


@router.get("/operational-metrics")
def operational_metrics(
    _admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("fhe.read"))],
    session: Annotated[Session, Depends(get_db)],
):
    rows = session.scalars(select(FheMetric).order_by(FheMetric.recorded_at.desc()).limit(100)).all()
    return {"items": [{column.name: getattr(row, column.name) for column in FheMetric.__table__.columns} for row in rows]}


@router.get("/profiles")
def profiles(_admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("fhe.read"))]):
    timing = dashboard.fhe_performance()
    return {"items": [{"id": "ckks-balanced-degree7-v1", "label": "Measured degree-7 profile",
        "status": "active_pilot", "measured": True, "depth": 6, "scale_bits": 50,
        "ring_dimension": timing["ring_dimension"], "batch_size": 8192,
        "evaluation_time_ms": next(item["milliseconds"] for item in timing["stages"] if item["stage"] == "Evaluation"),
        "mean_absolute_error": timing["mean_absolute_error"]}],
        "note": "Only one CKKS profile has been measured. No synthetic profile comparisons are shown."}


@router.post("/benchmarks")
def run_benchmark(request: Request,
    admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("fhe.benchmark"))],
    session: Annotated[Session, Depends(get_db)]):
    global _last_benchmark_at
    now = time.monotonic()
    if now - _last_benchmark_at < 60:
        raise AdminAPIError(429, "BENCHMARK_RATE_LIMITED", "Wait before running another benchmark")
    if not _benchmark_lock.acquire(blocking=False):
        raise AdminAPIError(409, "BENCHMARK_ALREADY_RUNNING", "An FHE benchmark is already running")
    try:
        run = BenchmarkRun(
            status="running", profile_id="ckks-balanced-degree7-v1",
            started_by=admin.user.id, safe_configuration={"approved_batch": "saved_test_set"},
        )
        session.add(run)
        session.commit()
        executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "day3_fhe_predict.exe"
        if not executable.exists():
            raise AdminAPIError(503, "OPENFHE_NOT_BUILT", "The OpenFHE benchmark executable is unavailable")
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "backend" / ".runtime") as temp:
            scores = Path(temp) / "scores.csv"
            timing = Path(temp) / "timing.json"
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join([str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")])
            completed = subprocess.run([str(executable), str(PROJECT_ROOT / "openfhe" / "generated" / "fhe_test_batch.csv"), str(scores), str(timing)], cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=120, check=False)
            if completed.returncode != 0:
                raise AdminAPIError(500, "BENCHMARK_FAILED", "The approved OpenFHE benchmark failed")
            result = json.loads(timing.read_text(encoding="utf-8"))
        run.status = "completed"
        run.completed_at = utc_now()
        session.add(BenchmarkResult(benchmark_run_id=run.id, metrics=result))
        _last_benchmark_at = time.monotonic()
        ip, agent = request_context(request)
        append_audit_event(session, actor_id=admin.user.id, actor_role=admin.roles[0] if admin.roles else None,
            action="fhe.benchmark.completed", resource_type="fhe_benchmark", result="success",
            ip_address=ip, user_agent=agent, safe_metadata={"profile": "ckks-balanced-degree7-v1", "samples": result["samples_packed"]})
        session.commit()
        return {"status": "completed", "measured": True, "result": result}
    finally:
        _benchmark_lock.release()
