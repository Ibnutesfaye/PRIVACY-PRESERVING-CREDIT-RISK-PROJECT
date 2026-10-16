from __future__ import annotations

from ml.config import FEATURES
from ml.validate_artifacts import build_manifest


def test_approved_ml_bundle_is_internally_consistent() -> None:
    manifest = build_manifest()
    assert manifest["validation_status"] == "passed"
    assert manifest["feature_schema"]["features_in_order"] == FEATURES
    assert manifest["preprocessing"]["fit_scope"] == "training_split_only"
    assert manifest["threshold_profile"] == {
        "version": "binary-risk-0.5-v1",
        "high_risk_at_or_above": 0.5,
    }
    assert manifest["manual_inference_max_absolute_error"] <= 1e-12
    assert len(manifest["artifact_sha256"]) == 9
    assert all(len(digest) == 64 for digest in manifest["artifact_sha256"].values())
