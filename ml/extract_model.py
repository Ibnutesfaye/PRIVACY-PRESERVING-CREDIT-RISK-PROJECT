"""Export logistic-regression parameters and verify manual inference."""

from __future__ import annotations

import json

import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR, FEATURES, REPORTS_DIR


def sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-value))


def main() -> None:
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    data = np.load("data/processed/train_test_data.npz")
    x_test = data["X_test"]
    weights = model.coef_[0]
    bias = float(model.intercept_[0])
    manual_logits = x_test @ weights + bias
    sklearn_logits = model.decision_function(x_test)
    manual_probabilities = sigmoid(manual_logits)
    sklearn_probabilities = model.predict_proba(x_test)[:, 1]
    report = {
        "features": FEATURES,
        "weights": weights.tolist(),
        "bias": bias,
        "formula": "z = dot(weights, scaled_features) + bias",
        "max_absolute_logit_error": float(np.max(np.abs(manual_logits - sklearn_logits))),
        "max_absolute_probability_error": float(np.max(np.abs(manual_probabilities - sklearn_probabilities))),
        "verified": bool(np.allclose(manual_probabilities, sklearn_probabilities, rtol=1e-12, atol=1e-12)),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "model_parameters.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REPORTS_DIR / "manual_inference_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

