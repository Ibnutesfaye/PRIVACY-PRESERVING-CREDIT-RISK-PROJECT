"""Validate the approved ML bundle and emit a non-secret governance manifest."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from ml.config import ARTIFACTS_DIR, FEATURES, PROCESSED_DIR, PROJECT_ROOT, RANDOM_STATE, RAW_DATA_PATH, TEST_SIZE


MODEL_VERSION = "logistic-regression-baseline-v1"
DATASET_VERSION = "credit-risk-deduplicated-v1"
FEATURE_SCHEMA_VERSION = "numeric-fhe-seven-v1"
PREPROCESSING_VERSION = "median-standard-scaler-v1"
POLYNOMIAL_VERSION = "sigmoid-degree7-v1"
THRESHOLD_PROFILE = {"version": "binary-risk-0.5-v1", "high_risk_at_or_above": 0.5}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    predicted = (scores >= THRESHOLD_PROFILE["high_risk_at_or_above"]).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
    }


def build_manifest() -> dict[str, object]:
    required = {
        "dataset": RAW_DATA_PATH,
        "split": PROCESSED_DIR / "train_test_data.npz",
        "imputer": ARTIFACTS_DIR / "imputer.pkl",
        "scaler": ARTIFACTS_DIR / "scaler.pkl",
        "model": ARTIFACTS_DIR / "model.pkl",
        "parameters": ARTIFACTS_DIR / "model_parameters.json",
        "preprocessing_metadata": ARTIFACTS_DIR / "preprocessing_metadata.json",
        "polynomial_analysis": PROJECT_ROOT / "docs" / "reports" / "polynomial_analysis.json",
        "baseline_metrics": PROJECT_ROOT / "docs" / "reports" / "baseline_metrics.json",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing approved ML artifacts: {', '.join(missing)}")

    split = np.load(required["split"], allow_pickle=False)
    x_train, x_test = split["X_train"], split["X_test"]
    y_train, y_test = split["y_train"], split["y_test"]
    split_features = split["feature_names"].tolist()
    imputer = joblib.load(required["imputer"])
    scaler = joblib.load(required["scaler"])
    model = joblib.load(required["model"])
    parameters = json.loads(required["parameters"].read_text(encoding="utf-8"))
    preprocessing = json.loads(required["preprocessing_metadata"].read_text(encoding="utf-8"))
    polynomial = json.loads(required["polynomial_analysis"].read_text(encoding="utf-8"))
    reported = json.loads(required["baseline_metrics"].read_text(encoding="utf-8"))

    if split_features != FEATURES or parameters["features"] != FEATURES or preprocessing["features"] != FEATURES:
        raise RuntimeError("Feature order differs between code, split, parameters, or preprocessing metadata")
    if x_train.shape[1] != len(FEATURES) or x_test.shape[1] != len(FEATURES):
        raise RuntimeError("Processed feature matrix width is invalid")
    if len(imputer.statistics_) != len(FEATURES) or len(scaler.mean_) != len(FEATURES):
        raise RuntimeError("Preprocessing artifact dimensions are invalid")
    if model.coef_.shape != (1, len(FEATURES)) or model.intercept_.shape != (1,):
        raise RuntimeError("Logistic-regression artifact dimensions are invalid")

    logits = x_test @ model.coef_[0] + float(model.intercept_[0])
    scores = 1.0 / (1.0 + np.exp(-logits))
    sklearn_scores = model.predict_proba(x_test)[:, 1]
    max_manual_error = float(np.max(np.abs(scores - sklearn_scores)))
    if max_manual_error > 1e-12:
        raise RuntimeError("Manual logistic-regression inference does not match the saved model")

    measured = metrics(y_test, scores)
    for name, value in measured.items():
        if abs(value - float(reported[name])) > 1e-12:
            raise RuntimeError(f"Recomputed metric differs from baseline report: {name}")
    if polynomial["selected"]["degree"] != 7:
        raise RuntimeError("Approved polynomial selection is not degree 7")

    return {
        "manifest_version": 1,
        "validation_status": "passed",
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "feature_schema": {
            "version": FEATURE_SCHEMA_VERSION,
            "features_in_order": FEATURES,
            "sha256": canonical_hash(FEATURES),
        },
        "preprocessing": {
            "version": PREPROCESSING_VERSION,
            "fit_scope": "training_split_only",
            "imputation": "median",
            "scaling": "standard_scaler",
        },
        "polynomial_version": POLYNOMIAL_VERSION,
        "threshold_profile": THRESHOLD_PROFILE,
        "training_contract": {"random_state": RANDOM_STATE, "test_size": TEST_SIZE, "stratified": True},
        "sample_counts": {"training": int(len(y_train)), "test": int(len(y_test))},
        "class_counts": {
            "training": {str(value): int((y_train == value).sum()) for value in (0, 1)},
            "test": {str(value): int((y_test == value).sum()) for value in (0, 1)},
        },
        "metrics": measured,
        "manual_inference_max_absolute_error": max_manual_error,
        "artifact_sha256": {name: sha256_file(path) for name, path in required.items()},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "known_limitations": [
            "Seven numerical features only; categorical features are excluded.",
            "Class-1 recall is limited and requires business validation before pilot decisions.",
            "The model is not calibrated, fairness-audited, or approved for autonomous lending decisions.",
        ],
    }


def main() -> None:
    manifest = build_manifest()
    destination = ARTIFACTS_DIR / "model_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"validation_status": "passed", "manifest": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
