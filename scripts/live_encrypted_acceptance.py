"""Run a real HTTP trusted-client acceptance test against an isolated local API."""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

import httpx
import joblib
import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.admin.models import AdminUser, FheMetric, PredictionMetadata, Role, UserRole
from backend.app.admin.repository import seed_roles_and_permissions
from backend.app.admin.security import hash_password
from backend.app.database import Base
from ml.config import ARTIFACTS_DIR, PROJECT_ROOT
from trusted_client.client import TrustedClient, preprocess
from trusted_client.keystore import LocalDirectoryKeyStore

PROFILE = "acceptance-ckks-degree7-v1"
MODEL = "logistic-regression-baseline-v1"
PYTHON = Path(r"C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")


def free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def main() -> None:
    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    profile_directory = PROJECT_ROOT / "backend" / ".runtime" / "fhe-profiles" / PROFILE
    if profile_directory.exists():
        raise RuntimeError("Acceptance profile directory already exists; refusing to overwrite it")
    applicant = {
        "person_age": 37.0, "person_income": 54321.73, "person_emp_length": 8.0,
        "loan_amnt": 9876.54, "loan_int_rate": 13.27,
        "loan_percent_income": 0.1818, "cb_person_cred_hist_length": 11.0,
    }
    sentinels = ["54321.73", "9876.54", "13.27", "0.1818"]
    password = secrets.token_urlsafe(32)
    jwt_secret = secrets.token_urlsafe(48)
    process: subprocess.Popen[str] | None = None
    evidence: dict[str, object] = {}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        private = root / "private"
        database_path = root / "acceptance.sqlite"
        database_url = f"sqlite:///{database_path.as_posix()}"
        profile_directory.mkdir(parents=True)
        client = TrustedClient(executable, profile_directory, LocalDirectoryKeyStore(private), profile_id=PROFILE, model_version=MODEL)
        private.mkdir()
        try:
            client._native(["setup", str(profile_directory), str(private)])
            database = create_engine(database_url)
            Base.metadata.create_all(database)
            with Session(database) as session:
                seed_roles_and_permissions(session)
                role = session.scalar(select(Role).where(Role.name == "super_admin"))
                user = AdminUser(email="acceptance@example.com", full_name="Acceptance Operator", password_hash=hash_password(password))
                session.add(user)
                session.flush()
                session.add(UserRole(user_id=user.id, role_id=role.id))
                session.commit()
            database.dispose()

            port = free_port()
            environment = os.environ.copy()
            environment.update({
                "PYTHONPATH": str(PROJECT_ROOT / ".venv" / "Lib" / "site-packages"),
                "ADMIN_DATABASE_URL": database_url,
                "ADMIN_JWT_SECRET": jwt_secret,
                "APPLICATION_ENVIRONMENT": "test",
                "OPENFHE_PROFILE_ID": PROFILE,
                "OPENFHE_MODEL_VERSION": MODEL,
                "MODEL_PLAINTEXT_PREDICTION_ENABLED": "false",
            })
            process = subprocess.Popen(
                [str(PYTHON), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=PROJECT_ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True,
            )
            base_url = f"http://127.0.0.1:{port}"
            for _ in range(60):
                try:
                    if httpx.get(f"{base_url}/api/v1/system/liveness", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("Isolated acceptance API did not become live")

            login = httpx.post(
                f"{base_url}/api/admin/auth/login",
                json={"email": "acceptance@example.com", "password": password}, timeout=10,
            )
            login.raise_for_status()
            access_token = login.json()["access_token"]
            encrypted = client.predict([applicant], base_url, access_token)
            score = float(encrypted["scores"][0])
            scaled = preprocess([applicant])
            model = joblib.load(ARTIFACTS_DIR / "model.pkl")
            logit = float(model.decision_function(scaled)[0])
            coefficients = np.asarray([0.50000000000000755, 0.2351734039561946, 0, -0.012339842621857708, 0, 0.00039426355902358648, 0, -4.7453784873149767e-06])
            expected = float(np.polynomial.polynomial.polyval(logit, coefficients))

            database = create_engine(database_url)
            with Session(database) as session:
                metadata = session.scalar(select(PredictionMetadata).where(PredictionMetadata.prediction_id == encrypted["prediction_id"]))
                metric = session.scalar(select(FheMetric).where(FheMetric.prediction_metadata_id == metadata.id)) if metadata else None
            database.dispose()
            sqlite_text = "\n".join(database_path.read_bytes().decode("latin-1", errors="ignore").splitlines())
            evidence = {
                "status": "PASS",
                "transport": "real HTTP on isolated loopback service",
                "authenticated": login.status_code == 200,
                "authorized_ciphertext_api": metadata is not None,
                "prediction_id_present": bool(encrypted["prediction_id"]),
                "fhe_metric_linked": metric is not None,
                "plaintext_circuit_score": expected,
                "decrypted_fhe_score": score,
                "absolute_error": abs(score - expected),
                "classification_agreement": (score >= 0.5) == (expected >= 0.5),
                "secret_key_in_server_profile": (profile_directory / "secret-key.bin").exists(),
                "server_profile_files": sorted(path.name for path in profile_directory.iterdir()),
                "plaintext_sentinels_in_database": any(value in sqlite_text for value in sentinels),
                "remaining_evaluator_temp_entries": len(list((PROJECT_ROOT / "backend" / ".runtime" / "encrypted-evaluations").glob("tmp*"))),
            }
        finally:
            if process is not None:
                process.terminate()
                try:
                    output, _ = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    output, _ = process.communicate(timeout=5)
                evidence["plaintext_sentinels_in_server_logs"] = any(value in output for value in sentinels)
                evidence["secret_material_in_server_logs"] = password in output or jwt_secret in output or access_token in output if "access_token" in locals() else False
            if profile_directory.exists():
                shutil.rmtree(profile_directory)

    passed = (
        evidence.get("authenticated") is True
        and evidence.get("authorized_ciphertext_api") is True
        and evidence.get("fhe_metric_linked") is True
        and evidence.get("classification_agreement") is True
        and evidence.get("secret_key_in_server_profile") is False
        and evidence.get("plaintext_sentinels_in_database") is False
        and evidence.get("plaintext_sentinels_in_server_logs") is False
        and evidence.get("secret_material_in_server_logs") is False
        and evidence.get("remaining_evaluator_temp_entries") == 0
    )
    evidence["status"] = "PASS" if passed else "FAIL"
    destination = PROJECT_ROOT / "benchmarks" / "results" / "live_encrypted_acceptance.json"
    destination.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
