"""Generate a fresh, diverse batch and compare plaintext circuit with real CKKS."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR, PROCESSED_DIR, PROJECT_ROOT

SEED = 20260807
POLYNOMIAL = np.asarray([0.50000000000000755, 0.2351734039561946, 0, -0.012339842621857708, 0, 0.00039426355902358648, 0, -4.7453784873149767e-06])


def run(arguments: list[str], environment: dict[str, str]) -> None:
    result = subprocess.run(arguments, cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        raise RuntimeError("Fresh OpenFHE verification stage failed")


def polynomial_score(logits: np.ndarray) -> np.ndarray:
    return np.polynomial.polynomial.polyval(logits, POLYNOMIAL)


def main() -> None:
    split = np.load(PROCESSED_DIR / "train_test_data.npz", allow_pickle=False)
    features = split["X_test"]
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    logits = model.decision_function(features)
    rng = np.random.default_rng(SEED)

    chosen: list[int] = []
    labels: list[str] = []
    categories = {
        "minimum_range": np.argsort(np.linalg.norm(features, axis=1))[-8:],
        "maximum_range": np.argsort(np.max(features, axis=1))[-8:],
        "typical": np.argsort(np.linalg.norm(features, axis=1))[:32],
        "high_risk": np.argsort(logits)[-32:],
        "low_risk": np.argsort(logits)[:32],
        "boundary": np.argsort(np.abs(logits))[:64],
        "random_valid": rng.choice(len(features), size=80, replace=False),
    }
    for category, indices in categories.items():
        for index in indices:
            value = int(index)
            if value not in chosen:
                chosen.append(value)
                labels.append(category)
    selected = features[np.asarray(chosen)]
    selected_logits = logits[np.asarray(chosen)]
    expected = polynomial_score(selected_logits)

    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")])
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        public, private, encrypted = root / "public", root / "private", root / "encrypted"
        source, result, scores = root / "fresh.csv", root / "result.ct", root / "scores.txt"
        np.savetxt(source, selected, delimiter=",", fmt="%.17g")
        run([str(executable), "setup", str(public), str(private)], environment)
        run([str(executable), "encrypt", str(public / "context.bin"), str(public / "public-key.bin"), str(source), str(encrypted)], environment)
        run([str(executable), "evaluate", str(public / "context.bin"), str(public / "evaluation-mult-keys.bin"), str(encrypted), str(result)], environment)
        run([str(executable), "decrypt", str(public / "context.bin"), str(private / "secret-key.bin"), str(result), str(len(selected)), str(scores)], environment)
        actual = np.loadtxt(scores)
        profile = json.loads((public / "profile.json").read_text(encoding="utf-8"))

    error = np.abs(actual - expected)
    expected_classes = expected >= 0.5
    actual_classes = actual >= 0.5
    report = {
        "generated_at_seed": SEED,
        "fresh_keys_and_ciphertexts": True,
        "sample_count": len(chosen),
        "category_counts": {name: labels.count(name) for name in categories},
        "ckks_profile": profile,
        "plain_circuit_vs_fhe": {
            "mean_absolute_error": float(error.mean()),
            "median_absolute_error": float(np.median(error)),
            "maximum_absolute_error": float(error.max()),
            "standard_deviation_absolute_error": float(error.std()),
            "classification_agreement": float(np.mean(expected_classes == actual_classes)),
            "threshold_crossing_mismatches": int(np.count_nonzero(expected_classes != actual_classes)),
        },
        "logit_range": [float(selected_logits.min()), float(selected_logits.max())],
        "expected_score_range": [float(expected.min()), float(expected.max())],
    }
    destination = PROJECT_ROOT / "benchmarks" / "results" / "fresh_pilot_equivalence.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

