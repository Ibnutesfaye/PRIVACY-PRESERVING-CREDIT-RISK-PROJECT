from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Sequence

import httpx
import joblib
import numpy as np
import pandas as pd

from ml.config import ARTIFACTS_DIR, FEATURES, PROJECT_ROOT
from trusted_client.keystore import KeyStore

MODEL_VERSION = "logistic-regression-baseline-v1"
PROFILE_ID = "ckks-balanced-degree7-v1"


def preprocess(applicants: Sequence[dict[str, Any]]) -> np.ndarray:
    """Impute and scale raw values locally in the exact training feature order."""
    if not applicants:
        raise ValueError("At least one applicant is required")
    if len(applicants) > 8192:
        raise ValueError("The encrypted batch exceeds 8192 applicants")
    rows: list[list[float]] = []
    for applicant in applicants:
        unknown = set(applicant) - set(FEATURES)
        if unknown:
            raise ValueError("Applicant input contains unsupported fields")
        row = []
        for feature in FEATURES:
            value = applicant.get(feature)
            row.append(np.nan if value is None else float(value))
        rows.append(row)
    imputer = joblib.load(ARTIFACTS_DIR / "imputer.pkl")
    scaler = joblib.load(ARTIFACTS_DIR / "scaler.pkl")
    ordered = pd.DataFrame(np.asarray(rows, dtype=float), columns=FEATURES)
    return scaler.transform(imputer.transform(ordered))


class TrustedClient:
    def __init__(self, executable: Path, public_bundle: Path, key_store: KeyStore, *, profile_id: str = PROFILE_ID, model_version: str = MODEL_VERSION) -> None:
        self.executable = executable.resolve()
        self.public_bundle = public_bundle.resolve()
        self.key_store = key_store
        self.profile_id = profile_id
        self.model_version = model_version

    @staticmethod
    def _environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([
            str(PROJECT_ROOT / "openfhe" / "install" / "lib"),
            r"C:\msys64\mingw64\bin",
            environment.get("PATH", ""),
        ])
        return environment

    def _native(self, arguments: list[str], timeout: int = 120) -> None:
        try:
            result = subprocess.run(
                [str(self.executable), *arguments], cwd=PROJECT_ROOT,
                env=self._environment(), capture_output=True, text=True,
                timeout=timeout, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("The local cryptographic operation could not complete") from error
        if result.returncode != 0:
            raise RuntimeError("The local cryptographic operation failed")

    def predict(self, applicants: Sequence[dict[str, Any]], api_url: str, access_token: str) -> dict[str, Any]:
        if not access_token:
            raise ValueError("An access token is required")
        scaled = preprocess(applicants)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scaled_path = root / "scaled.csv"
            encrypted_dir = root / "encrypted"
            result_path = root / "result.ct"
            scores_path = root / "scores.txt"
            np.savetxt(scaled_path, scaled, delimiter=",", fmt="%.17g")
            self._native([
                "encrypt", str(self.public_bundle / "context.bin"),
                str(self.public_bundle / "public-key.bin"), str(scaled_path), str(encrypted_dir),
            ])
            ciphertexts = [
                base64.b64encode((encrypted_dir / f"feature-{index}.ct").read_bytes()).decode("ascii")
                for index in range(len(FEATURES))
            ]
            payload = {
                "protocol_version": 1, "profile_id": self.profile_id,
                "model_version": self.model_version,
                "context_fingerprint": hashlib.sha256((self.public_bundle / "context.bin").read_bytes()).hexdigest(),
                "batch_size": len(applicants),
                "feature_ciphertexts": ciphertexts,
            }
            try:
                response = httpx.post(
                    f"{api_url.rstrip('/')}/api/v1/fhe/evaluate", json=payload,
                    headers={"Authorization": f"Bearer {access_token}"}, timeout=180,
                )
                response.raise_for_status()
                body = response.json()
                result_path.write_bytes(base64.b64decode(body["result_ciphertext"], validate=True))
            except (httpx.HTTPError, KeyError, ValueError) as error:
                raise RuntimeError("Encrypted prediction submission failed") from error
            self._native([
                "decrypt", str(self.public_bundle / "context.bin"),
                str(self.key_store.secret_key_path()), str(result_path),
                str(len(applicants)), str(scores_path),
            ])
            scores = [float(line) for line in scores_path.read_text(encoding="utf-8").splitlines()]
            return {"prediction_id": body["prediction_id"], "scores": scores}


def load_applicants(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("Input must be a JSON array of applicant objects")
    return value
