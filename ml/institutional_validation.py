"""Institutional validation metrics; does not authorize or train a production model."""

from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)


def validate_scores(y_true, scores, threshold: float = 0.5, calibration_bins: int = 10) -> dict[str, object]:
    y = np.asarray(y_true, dtype=int)
    probability = np.asarray(scores, dtype=float)
    if len(y) != len(probability) or len(y) == 0:
        raise ValueError("Labels and scores must have equal non-zero length")
    if not np.isin(y, [0, 1]).all() or not np.isfinite(probability).all():
        raise ValueError("Labels must be binary and scores finite")
    predicted = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    observed, predicted_probability = calibration_curve(y, probability, n_bins=calibration_bins, strategy="quantile")
    return {
        "samples": int(len(y)), "threshold": threshold,
        "roc_auc": float(roc_auc_score(y, probability)),
        "pr_auc": float(average_precision_score(y, probability)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "brier_score": float(brier_score_loss(y, probability)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else None,
        "observed_default_rate": float(y.mean()),
        "predicted_default_rate": float(probability.mean()),
        "calibration": [{"predicted": float(p), "observed": float(o)} for p, o in zip(predicted_probability, observed)],
    }


def threshold_analysis(y_true, scores, thresholds=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)) -> list[dict[str, object]]:
    return [validate_scores(y_true, scores, float(threshold), calibration_bins=10) for threshold in thresholds]

