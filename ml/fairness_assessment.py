"""Controlled validation-only group assessment; group attributes are not model inputs."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


def assess_groups(y_true, scores, groups, threshold: float = 0.5, minimum_group_size: int = 30) -> dict[str, object]:
    y = np.asarray(y_true, dtype=int)
    probability = np.asarray(scores, dtype=float)
    group = np.asarray(groups)
    if not (len(y) == len(probability) == len(group)) or len(y) == 0:
        raise ValueError("Labels, scores, and groups must have equal non-zero length")
    results: dict[str, object] = {}
    for value in np.unique(group):
        mask = group == value
        count = int(mask.sum())
        if count < minimum_group_size:
            results[str(value)] = {"samples": count, "status": "insufficient_sample"}
            continue
        actual, score = y[mask], probability[mask]
        predicted = score >= threshold
        negative, positive = actual == 0, actual == 1
        results[str(value)] = {
            "samples": count, "status": "measured",
            "selection_rate": float(predicted.mean()),
            "false_positive_rate": float(predicted[negative].mean()) if negative.any() else None,
            "false_negative_rate": float((~predicted[positive]).mean()) if positive.any() else None,
            "brier_score": float(brier_score_loss(actual, score)),
            "mean_predicted_risk": float(score.mean()),
            "observed_default_rate": float(actual.mean()),
            "roc_auc": float(roc_auc_score(actual, score)) if len(np.unique(actual)) == 2 else None,
        }
    return {"threshold": threshold, "minimum_group_size": minimum_group_size, "groups": results}

