"""Clean, split, impute, and scale the numerical FHE-friendly features."""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ml.config import ARTIFACTS_DIR, FEATURES, PROCESSED_DIR, RANDOM_STATE, RAW_DATA_PATH, TARGET, TEST_SIZE


def main() -> None:
    df = pd.read_csv(RAW_DATA_PATH)
    # Remove only exact source-row duplicates. Selecting columns before this step
    # could incorrectly merge people who share numerical values but differ in
    # categorical attributes.
    selected = df.drop_duplicates()[FEATURES + [TARGET]].copy()
    selected = selected[selected[TARGET].isin([0, 1])]

    x = selected[FEATURES]
    y = selected[TARGET].astype(int)
    x_train_raw, x_test_raw, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train_imputed = imputer.fit_transform(x_train_raw)
    x_test_imputed = imputer.transform(x_test_raw)
    x_train = scaler.fit_transform(x_train_imputed)
    x_test = scaler.transform(x_test_imputed)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        PROCESSED_DIR / "train_test_data.npz",
        X_train=x_train,
        X_test=x_test,
        y_train=y_train.to_numpy(),
        y_test=y_test.to_numpy(),
        feature_names=np.asarray(FEATURES),
    )
    joblib.dump(imputer, ARTIFACTS_DIR / "imputer.pkl")
    joblib.dump(scaler, ARTIFACTS_DIR / "scaler.pkl")
    metadata = {
        "features": FEATURES,
        "target": TARGET,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "rows_after_exact_full_row_deduplication": int(len(selected)),
        "training_samples": int(len(y_train)),
        "test_samples": int(len(y_test)),
        "training_class_distribution": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "test_class_distribution": {str(k): int(v) for k, v in y_test.value_counts().items()},
        "imputer_statistics": imputer.statistics_.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
    }
    (ARTIFACTS_DIR / "preprocessing_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
