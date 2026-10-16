import json

import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR, PROCESSED_DIR, PROJECT_ROOT


def test_exported_fhe_input_matches_saved_model() -> None:
    manifest_path = PROJECT_ROOT / "openfhe" / "generated" / "model_input.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    data = np.load(PROCESSED_DIR / "train_test_data.npz")
    sample = data["X_test"][manifest["sample_index_in_saved_test_split"]]
    expected = float(model.decision_function(sample.reshape(1, -1))[0])
    assert np.allclose(sample, manifest["scaled_features"], rtol=0, atol=0)
    assert np.isclose(expected, manifest["plain_logit"], rtol=1e-14, atol=1e-14)

