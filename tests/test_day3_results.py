import json

from ml.config import PROJECT_ROOT, REPORTS_DIR


def test_polynomial_selection_meets_declared_error() -> None:
    report = json.loads((REPORTS_DIR / "polynomial_analysis.json").read_text(encoding="utf-8"))
    assert report["selected"]["degree"] == 7
    assert report["selected"]["grid_max_absolute_error"] <= 0.02
    assert report["observed_test_logit_min"] >= report["interval"][0]
    assert report["observed_test_logit_max"] <= report["interval"][1]


def test_full_fhe_metrics_match_baseline() -> None:
    report_path = PROJECT_ROOT / "benchmarks" / "results" / "comparison.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["samples"] == 6484
    assert report["accuracy_difference_fhe_minus_normal"] == 0.0
    assert report["fhe_polynomial_ml"]["fhe_vs_plain_polynomial_max_absolute_error"] < 1e-6

