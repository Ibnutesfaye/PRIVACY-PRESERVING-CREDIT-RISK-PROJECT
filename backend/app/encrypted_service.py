from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import tempfile
from dataclasses import dataclass

from backend.app.config import get_application_settings
from backend.app.encrypted_schemas import EncryptedEvaluationRequest
from ml.config import PROJECT_ROOT


@dataclass(frozen=True)
class EvaluationArtifact:
    result_ciphertext: bytes
    request_ciphertext_bytes: int


class CiphertextEvaluationService:
    """Ciphertext-only adapter: this process has no decrypt operation or secret-key path."""

    def __init__(self) -> None:
        self.settings = get_application_settings()
        self.executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
        self.profile_directory = PROJECT_ROOT / "backend" / ".runtime" / "fhe-profiles" / self.settings.openfhe_profile_id
        self.work_directory = PROJECT_ROOT / "backend" / ".runtime" / "encrypted-evaluations"

    @property
    def ready(self) -> bool:
        required = (
            self.executable,
            self.profile_directory / "context.bin",
            self.profile_directory / "public-key.bin",
            self.profile_directory / "evaluation-mult-keys.bin",
            self.profile_directory / "profile.json",
        )
        return all(path.is_file() for path in required) and not (self.profile_directory / "secret-key.bin").exists()

    def public_artifact(self, name: str) -> Path:
        allowed = {"context": "context.bin", "public-key": "public-key.bin"}
        if name not in allowed:
            raise KeyError(name)
        path = self.profile_directory / allowed[name]
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    @property
    def context_fingerprint(self) -> str:
        context = self.profile_directory / "context.bin"
        if not context.is_file():
            raise FileNotFoundError(context)
        return hashlib.sha256(context.read_bytes()).hexdigest()

    def evaluate(self, request: EncryptedEvaluationRequest) -> EvaluationArtifact:
        if not self.ready:
            raise RuntimeError("The encrypted evaluator profile is not ready")
        if request.profile_id != self.settings.openfhe_profile_id:
            raise ValueError("The requested OpenFHE profile is not active")
        if request.model_version != self.settings.openfhe_model_version:
            raise ValueError("The requested model version is not active")
        if not hmac.compare_digest(request.context_fingerprint, self.context_fingerprint):
            raise ValueError("The requested crypto context is not active")

        decoded: list[bytes] = []
        total_bytes = 0
        for encoded in request.feature_ciphertexts:
            try:
                value = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError("A feature ciphertext is not valid base64") from error
            if not value:
                raise ValueError("Feature ciphertexts must not be empty")
            total_bytes += len(value)
            if total_bytes > self.settings.openfhe_max_ciphertext_bundle_bytes:
                raise ValueError("The ciphertext bundle exceeds the active profile limit")
            decoded.append(value)

        self.work_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.work_directory) as temporary:
            request_directory = Path(temporary) / "request"
            response_path = Path(temporary) / "response" / "result.ct"
            request_directory.mkdir()
            response_path.parent.mkdir()
            for index, value in enumerate(decoded):
                (request_directory / f"feature-{index}.ct").write_bytes(value)
            (request_directory / "batch.count").write_text(f"{request.batch_size}\n", encoding="ascii")

            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join(
                [str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")]
            )
            try:
                completed = subprocess.run(
                    [
                        str(self.executable),
                        "evaluate",
                        str(self.profile_directory / "context.bin"),
                        str(self.profile_directory / "evaluation-mult-keys.bin"),
                        str(request_directory),
                        str(response_path),
                    ],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.openfhe_worker_timeout_seconds,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError) as error:
                raise RuntimeError("The ciphertext evaluator could not complete") from error
            if completed.returncode != 0:
                raise RuntimeError("The ciphertext evaluator failed")
            if not response_path.is_file():
                raise RuntimeError("The ciphertext evaluator returned no result")
            return EvaluationArtifact(response_path.read_bytes(), total_bytes)


encrypted_service = CiphertextEvaluationService()
