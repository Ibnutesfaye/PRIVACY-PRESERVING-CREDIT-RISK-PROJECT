import numpy as np

from ml.fairness_assessment import assess_groups
from ml.institutional_validation import threshold_analysis, validate_scores


def test_institutional_validation_metrics_and_thresholds() -> None:
    labels = np.asarray([0, 0, 1, 1] * 20)
    scores = np.asarray([0.1, 0.4, 0.6, 0.9] * 20)
    result = validate_scores(labels, scores)
    assert result["samples"] == 80
    assert result["roc_auc"] == 1.0
    assert result["confusion_matrix"] == {"tn": 40, "fp": 0, "fn": 0, "tp": 40}
    assert len(threshold_analysis(labels, scores)) == 7


def test_fairness_framework_reports_groups_without_using_them_as_features() -> None:
    labels = np.asarray([0, 1] * 40)
    scores = np.asarray([0.2, 0.8] * 40)
    groups = np.asarray(["approved-a"] * 40 + ["approved-b"] * 40)
    result = assess_groups(labels, scores, groups, minimum_group_size=30)
    assert set(result["groups"]) == {"approved-a", "approved-b"}
    assert all(row["status"] == "measured" for row in result["groups"].values())

