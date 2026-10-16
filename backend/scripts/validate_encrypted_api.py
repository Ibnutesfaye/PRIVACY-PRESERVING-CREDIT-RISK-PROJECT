"""Post a saved ciphertext bundle through FastAPI without exposing plaintext."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_directory", type=Path)
    parser.add_argument("result_path", type=Path)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--access-token", default=os.environ.get("CIPHERSCORE_ACCESS_TOKEN"))
    arguments = parser.parse_args()
    if not arguments.access_token:
        raise RuntimeError("Provide --access-token or CIPHERSCORE_ACCESS_TOKEN locally")

    payload = {
        "protocol_version": 1,
        "profile_id": "ckks-balanced-degree7-v1",
        "model_version": "logistic-regression-baseline-v1",
        "context_fingerprint": hashlib.sha256((Path("backend/.runtime/fhe-profiles/ckks-balanced-degree7-v1/context.bin")).read_bytes()).hexdigest(),
        "batch_size": arguments.batch_size,
        "feature_ciphertexts": [
            base64.b64encode((arguments.bundle_directory / f"feature-{index}.ct").read_bytes()).decode("ascii")
            for index in range(7)
        ],
    }
    response = TestClient(app).post(
        "/api/v1/fhe/evaluate",
        json=payload,
        headers={"Authorization": f"Bearer {arguments.access_token}"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Encrypted API returned status {response.status_code}")
    body = response.json()
    if body["evaluator_decrypted_result"] is not False or "risk_score" in body:
        raise RuntimeError("Encrypted API response violated the ciphertext-only contract")
    result = base64.b64decode(body["result_ciphertext"], validate=True)
    arguments.result_path.write_bytes(result)
    print(f"PASS: encrypted API returned {len(result)} ciphertext bytes and no plaintext score")


if __name__ == "__main__":
    main()
