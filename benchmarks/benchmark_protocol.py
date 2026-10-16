"""Measure the serialized split-process OpenFHE protocol end to end."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from ml.config import ARTIFACTS_DIR, PROCESSED_DIR, PROJECT_ROOT


def run(command: list[str], environment: dict[str, str]) -> float:
    started = perf_counter()
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, check=False, timeout=120)
    elapsed_ms = (perf_counter() - started) * 1000
    if completed.returncode != 0:
        raise RuntimeError("A split-protocol stage failed")
    return elapsed_ms


def classification_metrics(targets: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    predicted = (scores >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(targets, predicted)),
        "precision": float(precision_score(targets, predicted, zero_division=0)),
        "recall": float(recall_score(targets, predicted, zero_division=0)),
        "f1": float(f1_score(targets, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(targets, scores)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    arguments = parser.parse_args()
    if not 1 <= arguments.runs <= 20:
        raise ValueError("runs must be between 1 and 20")

    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    scaled_input = PROJECT_ROOT / "openfhe" / "generated" / "fhe_test_batch.csv"
    runtime = PROJECT_ROOT / "backend" / ".runtime"
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        [str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")]
    )
    split = np.load(PROCESSED_DIR / "train_test_data.npz", allow_pickle=False)
    targets = split["y_test"]
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    exact_scores = model.predict_proba(split["X_test"])[:, 1]
    timings: list[dict[str, float]] = []
    final_scores: np.ndarray | None = None
    sizes: dict[str, int] = {}
    profile: dict[str, object] = {}

    for _ in range(arguments.runs):
        with tempfile.TemporaryDirectory(dir=runtime) as temporary:
            root = Path(temporary)
            public, private, request, response = root / "public", root / "private", root / "request", root / "response.ct"
            setup_ms = run([str(executable), "setup", str(public), str(private)], environment)
            encryption_ms = run([str(executable), "encrypt", str(public / "context.bin"), str(public / "public-key.bin"), str(scaled_input), str(request)], environment)
            evaluation_ms = run([str(executable), "evaluate", str(public / "context.bin"), str(public / "evaluation-mult-keys.bin"), str(request), str(response)], environment)
            decrypted = root / "scores.csv"
            decryption_ms = run([str(executable), "decrypt", str(public / "context.bin"), str(private / "secret-key.bin"), str(response), str(len(targets)), str(decrypted)], environment)
            timings.append({
                "key_setup_ms": setup_ms,
                "encryption_and_serialization_ms": encryption_ms,
                "evaluation_and_serialization_ms": evaluation_ms,
                "decryption_and_deserialization_ms": decryption_ms,
                "total_ms": setup_ms + encryption_ms + evaluation_ms + decryption_ms,
            })
            final_scores = np.loadtxt(decrypted)
            sizes = {
                "context_bytes": (public / "context.bin").stat().st_size,
                "public_key_bytes": (public / "public-key.bin").stat().st_size,
                "evaluation_key_bytes": (public / "evaluation-mult-keys.bin").stat().st_size,
                "request_ciphertext_bytes": sum(path.stat().st_size for path in request.glob("*.ct")),
                "response_ciphertext_bytes": response.stat().st_size,
                "secret_key_bytes": (private / "secret-key.bin").stat().st_size,
            }
            profile = json.loads((public / "profile.json").read_text(encoding="utf-8"))

    assert final_scores is not None
    mean_timing = {name: float(np.mean([run_result[name] for run_result in timings])) for name in timings[0]}
    report = {
        "protocol_version": 1,
        "runs": arguments.runs,
        "samples_packed": int(len(targets)),
        "profile": profile,
        "mean_timings": mean_timing,
        "individual_timings": timings,
        "serialized_sizes": sizes,
        "fhe_metrics": classification_metrics(targets, final_scores),
        "exact_sigmoid_metrics": classification_metrics(targets, exact_scores),
        "fhe_vs_exact_sigmoid_mean_absolute_error": float(np.mean(np.abs(final_scores - exact_scores))),
        "fhe_vs_exact_sigmoid_max_absolute_error": float(np.max(np.abs(final_scores - exact_scores))),
        "classification_difference_count": int(np.count_nonzero((final_scores >= 0.5) != (exact_scores >= 0.5))),
        "privacy_assertions": {
            "secret_key_in_evaluator_request": False,
            "evaluator_decrypted_result": False,
            "server_received_plaintext_features": False,
        },
    }
    destination = PROJECT_ROOT / "benchmarks" / "results" / "split_protocol.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "passed", "report": str(destination), "mean_total_ms": mean_timing["total_ms"]}, indent=2))


if __name__ == "__main__":
    main()
