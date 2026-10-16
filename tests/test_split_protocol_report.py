from __future__ import annotations

import json

from ml.config import PROJECT_ROOT


def test_measured_split_protocol_preserves_classification_and_privacy_boundary() -> None:
    report = json.loads((PROJECT_ROOT / "benchmarks" / "results" / "split_protocol.json").read_text(encoding="utf-8"))
    assert report["runs"] >= 3
    assert report["samples_packed"] == 6484
    assert report["classification_difference_count"] == 0
    assert report["fhe_metrics"]["accuracy"] == report["exact_sigmoid_metrics"]["accuracy"]
    assert report["fhe_vs_exact_sigmoid_max_absolute_error"] < 0.01
    assert report["profile"]["security_level"].startswith("HEStd_128_classic")
    assert report["privacy_assertions"] == {
        "secret_key_in_evaluator_request": False,
        "evaluator_decrypted_result": False,
        "server_received_plaintext_features": False,
    }
