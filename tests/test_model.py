import joblib
import numpy as np

from ml.config import ARTIFACTS_DIR


def test_saved_model_predicts_probabilities() -> None:
    model = joblib.load(ARTIFACTS_DIR / "model.pkl")
    data = np.load("data/processed/train_test_data.npz")
    probabilities = model.predict_proba(data["X_test"][:5])
    assert probabilities.shape == (5, 2)
    assert np.all((probabilities >= 0) & (probabilities <= 1))

