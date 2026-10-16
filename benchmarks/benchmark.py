"""Combine measured conventional and OpenFHE results into one report."""

from __future__ import annotations

import json
from time import perf_counter

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from ml.config import ARTIFACTS_DIR, PROCESSED_DIR, PROJECT_ROOT, REPORTS_DIR


def metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    predictions = (scores >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
    }


def main() -> None:
    data = np.load(PROCESSED_DIR / "train_test_data.npz")
    x_test, y_test = data["X_test"], data["y_test"]
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    polynomial_report = json.loads((REPORTS_DIR / "polynomial_analysis.json").read_text(encoding="utf-8"))
    coefficients = np.asarray(polynomial_report["selected"]["coefficients_ascending"])

    repeats = 1000
    start = perf_counter()
    for _ in range(repeats):
        normal_scores = model.predict_proba(x_test)[:, 1]
    normal_total_ms = (perf_counter() - start) * 1000 / repeats

    logits = model.decision_function(x_test)
    polynomial_scores = np.polynomial.polynomial.polyval(logits, coefficients)
    fhe_scores = np.loadtxt(PROJECT_ROOT / "benchmarks" / "results" / "fhe_probabilities.csv")
    fhe_timing = json.loads(
        (PROJECT_ROOT / "benchmarks" / "results" / "fhe_timing.json").read_text(encoding="utf-8")
    )
    if fhe_scores.shape != y_test.shape:
        raise RuntimeError("FHE result count does not match the saved test split")

    report = {
        "samples": int(len(y_test)),
        "normal_ml": {
            "metrics": metrics(y_test, normal_scores),
            "mean_batch_inference_ms_over_1000_runs": normal_total_ms,
            "mean_per_sample_inference_ms": normal_total_ms / len(y_test),
        },
        "fhe_polynomial_ml": {
            "metrics": metrics(y_test, fhe_scores),
            "timing": fhe_timing,
            "fhe_vs_plain_polynomial_mean_absolute_error": float(np.mean(np.abs(fhe_scores - polynomial_scores))),
            "fhe_vs_plain_polynomial_max_absolute_error": float(np.max(np.abs(fhe_scores - polynomial_scores))),
            "fhe_score_min": float(fhe_scores.min()),
            "fhe_score_max": float(fhe_scores.max()),
        },
        "accuracy_difference_fhe_minus_normal": float(
            metrics(y_test, fhe_scores)["accuracy"] - metrics(y_test, normal_scores)["accuracy"]
        ),
        "notes": [
            "Normal timing measures predict_proba for the complete saved test batch, averaged over 1000 runs.",
            "FHE metrics use scores actually encrypted, evaluated, and decrypted by OpenFHE in one SIMD batch.",
            "FHE total includes context creation, file parsing, key generation, encryption, evaluation, decryption, and size serialization.",
        ],
    }
    output = PROJECT_ROOT / "benchmarks" / "results" / "comparison.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

