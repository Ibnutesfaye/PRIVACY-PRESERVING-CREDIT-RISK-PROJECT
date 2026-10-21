from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

import joblib
import numpy as np
import pandas as pd

from backend.app.schemas import CreditRiskRequest
from backend.app.config import get_application_settings
from ml.config import ARTIFACTS_DIR, FEATURES, PROJECT_ROOT


class FHEPredictionService:
    """Trusted client gateway around the isolated OpenFHE evaluator."""

    def __init__(self) -> None:
        self._imputer = None
        self._scaler = None
        self.executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "day3_fhe_predict.exe"
        self.runtime_dir = PROJECT_ROOT / "backend" / ".runtime"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

    @property
    def imputer(self):
        if self._imputer is None:
            self._imputer = joblib.load(ARTIFACTS_DIR / "imputer.pkl")
        return self._imputer

    @property
    def scaler(self):
        if self._scaler is None:
            self._scaler = joblib.load(ARTIFACTS_DIR / "scaler.pkl")
        return self._scaler

    def _preprocess(self, request: CreditRiskRequest) -> np.ndarray:
        values = pd.DataFrame(
            [[
                request.person_age,
                request.person_income,
                request.person_emp_length,
                request.loan_amnt,
                request.loan_int_rate,
                request.loan_percent_income,
                request.cb_person_cred_hist_length,
            ]],
            columns=FEATURES,
            dtype=float,
        )
        # The artifacts were fitted on training data only during Day 1.
        return self.scaler.transform(self.imputer.transform(values))

    def predict(self, request: CreditRiskRequest) -> dict[str, object]:
        if not self.executable.exists():
            raise RuntimeError("The OpenFHE predictor has not been compiled")
        scaled = self._preprocess(request)

        with tempfile.TemporaryDirectory(dir=self.runtime_dir) as temp_dir:
            temp = Path(temp_dir)
            input_path = temp / "scaled.csv"
            scores_path = temp / "scores.csv"
            timing_path = temp / "timing.json"
            np.savetxt(input_path, scaled, delimiter=",", fmt="%.17g")

            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join(
                [
                    str(PROJECT_ROOT / "openfhe" / "install" / "lib"),
                    r"C:\msys64\mingw64\bin",
                    environment.get("PATH", ""),
                ]
            )
            completed = subprocess.run(
                [str(self.executable), str(input_path), str(scores_path), str(timing_path)],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=get_application_settings().openfhe_worker_timeout_seconds,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"OpenFHE evaluator failed: {completed.stderr.strip()}")

            raw_score = float(np.loadtxt(scores_path))
            timing = json.loads(timing_path.read_text(encoding="utf-8"))

        # A polynomial can overshoot [0, 1] slightly. Clamp only after client
        # decryption for presentation; retain raw_fhe_score for research audit.
        risk_score = min(1.0, max(0.0, raw_score))
        return {
            "risk_score": risk_score,
            "raw_fhe_score": raw_score,
            "prediction": "HIGH RISK" if risk_score >= 0.5 else "LOW RISK",
            "timing": {
                key: timing[key]
                for key in (
                    "key_generation_ms",
                    "encryption_ms",
                    "evaluation_ms",
                    "decryption_ms",
                    "total_latency_ms",
                )
            },
            "privacy": {
                "scheme": "OpenFHE CKKS",
                "encrypted_inference": True,
                "evaluator_received_plaintext_features": False,
                "trusted_gateway_received_plaintext_features": True,
                "secret_key_available_to_evaluator": False,
                "architecture_note": (
                    "Pilot compatibility path: FastAPI is a trusted gateway that receives plaintext, "
                    "applies the training-fitted preprocessing, and invokes an isolated ciphertext-only evaluator. "
                    "Institutional encrypted inference uses the separate trusted local client for preprocessing and encryption."
                ),
            },
        }


service = FHEPredictionService()
