import pandas as pd

from ml.config import FEATURES, RAW_DATA_PATH, TARGET


def test_dataset_has_required_columns() -> None:
    df = pd.read_csv(RAW_DATA_PATH)
    assert set(FEATURES + [TARGET]).issubset(df.columns)
    assert set(df[TARGET].dropna().unique()).issubset({0, 1})

