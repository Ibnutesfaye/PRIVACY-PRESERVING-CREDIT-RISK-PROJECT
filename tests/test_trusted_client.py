from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from ml.config import ARTIFACTS_DIR, FEATURES
from trusted_client.client import preprocess


def test_trusted_preprocessing_matches_training_artifacts_and_feature_order() -> None:
    applicant = {feature: float(index + 1) for index, feature in enumerate(FEATURES)}
    actual = preprocess([applicant])
    imputer = joblib.load(ARTIFACTS_DIR / "imputer.pkl")
    scaler = joblib.load(ARTIFACTS_DIR / "scaler.pkl")
    expected = scaler.transform(imputer.transform(pd.DataFrame([[applicant[name] for name in FEATURES]], columns=FEATURES)))
    np.testing.assert_array_equal(actual, expected)


def test_trusted_preprocessing_uses_training_medians_for_missing_values() -> None:
    actual = preprocess([{}])
    imputer = joblib.load(ARTIFACTS_DIR / "imputer.pkl")
    scaler = joblib.load(ARTIFACTS_DIR / "scaler.pkl")
    expected = scaler.transform([imputer.statistics_])
    np.testing.assert_allclose(actual, expected, rtol=0, atol=0)


def test_preprocessing_metadata_contract_is_exact() -> None:
    metadata = json.loads((ARTIFACTS_DIR / "preprocessing_metadata.json").read_text(encoding="utf-8"))
    scaler = joblib.load(ARTIFACTS_DIR / "scaler.pkl")
    imputer = joblib.load(ARTIFACTS_DIR / "imputer.pkl")
    assert metadata["features"] == FEATURES
    np.testing.assert_array_equal(metadata["imputer_statistics"], imputer.statistics_)
    np.testing.assert_array_equal(metadata["scaler_mean"], scaler.mean_)
    np.testing.assert_array_equal(metadata["scaler_scale"], scaler.scale_)


def test_trusted_preprocessing_rejects_non_model_fields() -> None:
    try:
        preprocess([{"person_income": 10, "password": "must-not-be-accepted"}])
    except ValueError as error:
        assert str(error) == "Applicant input contains unsupported fields"
    else:
        raise AssertionError("Unsupported input was accepted")
