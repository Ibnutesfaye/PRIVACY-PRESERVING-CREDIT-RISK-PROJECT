"""Train and evaluate the conventional logistic-regression baseline."""

from __future__ import annotations

import json
from time import perf_counter

import joblib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from ml.config import ARTIFACTS_DIR, RANDOM_STATE, REPORTS_DIR


def main() -> None:
    data = np.load("data/processed/train_test_data.npz")
    x_train, x_test = data["X_train"], data["X_test"]
    y_train, y_test = data["y_train"], data["y_test"]

    model = LogisticRegression(max_iter=2000, random_state=RANDOM_STATE, class_weight=None)
    start = perf_counter()
    model.fit(x_train, y_train)
    training_seconds = perf_counter() - start

    start = perf_counter()
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    inference_seconds = perf_counter() - start
    matrix = confusion_matrix(y_test, predictions)
    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "confusion_matrix": matrix.tolist(),
        "training_seconds": training_seconds,
        "total_test_inference_seconds": inference_seconds,
        "mean_inference_seconds_per_sample": inference_seconds / len(x_test),
        "training_samples": int(len(x_train)),
        "test_samples": int(len(x_test)),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "model.pkl")
    (REPORTS_DIR / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Logistic Regression Confusion Matrix")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "confusion_matrix.png", dpi=160)
    plt.close()

    fpr, tpr, _ = roc_curve(y_test, probabilities)
    plt.plot(fpr, tpr, label=f"ROC-AUC = {metrics['roc_auc']:.4f}")
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "roc_curve.png", dpi=160)
    plt.close()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

