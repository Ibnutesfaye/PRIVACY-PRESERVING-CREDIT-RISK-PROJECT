"""Inspect the raw credit-risk dataset and write a factual JSON report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.config import RAW_DATA_PATH, REPORTS_DIR, TARGET


def _native(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def build_report(csv_path: Path = RAW_DATA_PATH) -> dict[str, Any]:
    df = pd.read_csv(csv_path)
    categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical = df.select_dtypes(include=np.number).columns.tolist()

    numeric_ranges = {
        column: {
            "min": _native(df[column].min()),
            "max": _native(df[column].max()),
            "mean": _native(df[column].mean()),
            "median": _native(df[column].median()),
        }
        for column in numerical
    }

    outliers: dict[str, Any] = {}
    for column in numerical:
        series = df[column].dropna()
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers[column] = {
            "iqr_lower_bound": _native(lower),
            "iqr_upper_bound": _native(upper),
            "count": int(((series < lower) | (series > upper)).sum()),
        }

    invalid_rules = {
        "person_age_outside_18_100": int(((df["person_age"] < 18) | (df["person_age"] > 100)).sum()),
        "person_income_nonpositive": int((df["person_income"] <= 0).sum()),
        "person_emp_length_negative": int((df["person_emp_length"] < 0).sum()),
        "loan_amnt_nonpositive": int((df["loan_amnt"] <= 0).sum()),
        "loan_int_rate_outside_0_100": int(((df["loan_int_rate"] < 0) | (df["loan_int_rate"] > 100)).sum()),
        "loan_percent_income_outside_0_1": int(((df["loan_percent_income"] < 0) | (df["loan_percent_income"] > 1)).sum()),
        "credit_history_nonpositive": int((df["cb_person_cred_hist_length"] <= 0).sum()),
        "target_not_binary": int((~df[TARGET].isin([0, 1])).sum()),
    }

    return {
        "source": str(csv_path),
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": df.columns.tolist(),
        "data_types": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "missing_values": {column: int(count) for column, count in df.isna().sum().items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "target_distribution": {str(key): int(value) for key, value in df[TARGET].value_counts(dropna=False).items()},
        "categorical_values": {
            column: sorted(df[column].dropna().astype(str).unique().tolist()) for column in categorical
        },
        "numerical_ranges": numeric_ranges,
        "iqr_outliers": outliers,
        "invalid_value_checks": invalid_rules,
        "notes": {
            "leakage": "loan_grade may encode underwriting decisions and is excluded from the first FHE model.",
            "missing_data": "Numeric missing values are imputed using medians learned from training data only.",
            "duplicates": "Exact duplicates are removed before splitting to avoid cross-split duplication.",
        },
    }


def main() -> None:
    report = build_report()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / "dataset_analysis.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved report: {output_path}")


if __name__ == "__main__":
    main()

