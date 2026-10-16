import json

from ml.config import PROJECT_ROOT


def test_measured_fhe_weighted_sum_is_within_tolerance() -> None:
    result_path = PROJECT_ROOT / "benchmarks" / "results" / "day2_fhe_verification.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["scheme"] == "CKKS"
    assert result["secret_key_available_to_server"] is False
    assert result["verified"] is True
    assert result["absolute_error"] < 1e-6

