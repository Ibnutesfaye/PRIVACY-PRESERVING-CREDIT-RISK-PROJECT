from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin.models import AuditLog, PredictionMetadata, SecurityEvent
from ml.config import PROJECT_ROOT


BENCHMARK_PATH = PROJECT_ROOT / "benchmarks" / "results" / "comparison.json"
BASELINE_PATH = PROJECT_ROOT / "docs" / "reports" / "baseline_metrics.json"


@lru_cache(maxsize=1)
def measured_results() -> tuple[dict, dict]:
    with BENCHMARK_PATH.open(encoding="utf-8") as handle:
        benchmark = json.load(handle)
    with BASELINE_PATH.open(encoding="utf-8") as handle:
        baseline = json.load(handle)
    return benchmark, baseline


def summary(session: Session) -> dict[str, object]:
    benchmark, baseline = measured_results()
    fhe = benchmark["fhe_polynomial_ml"]
    timing = fhe["timing"]
    open_security_events = session.scalar(
        select(func.count()).select_from(SecurityEvent).where(SecurityEvent.status == "open")
    ) or 0
    today = datetime.now(timezone.utc).date()
    total_predictions = session.scalar(select(func.count()).select_from(PredictionMetadata)) or 0
    today_predictions = session.scalar(select(func.count()).select_from(PredictionMetadata).where(func.date(PredictionMetadata.created_at) == today)) or 0
    successful = session.scalar(select(func.count()).select_from(PredictionMetadata).where(PredictionMetadata.evaluation_status == "successful")) or 0
    failed = session.scalar(select(func.count()).select_from(PredictionMetadata).where(PredictionMetadata.request_status == "failed")) or 0
    return {
        "operational_predictions": {
            "total": total_predictions,
            "today": today_predictions,
            "successful_fhe": successful,
            "failed_fhe": failed,
            "source": "privacy_safe_prediction_metadata",
        },
        "measured_research": {
            "evaluated_samples": benchmark["samples"],
            "accuracy": baseline["accuracy"],
            "precision": baseline["precision"],
            "recall": baseline["recall"],
            "f1": baseline["f1"],
            "roc_auc": baseline["roc_auc"],
            "normal_inference_ms": benchmark["normal_ml"]["mean_batch_inference_ms_over_1000_runs"],
            "fhe_total_latency_ms": timing["total_latency_ms"],
            "accuracy_difference": benchmark["accuracy_difference_fhe_minus_normal"],
            "source": "measured_test_set_benchmark",
        },
        "system": {
            "active_model": "logistic-regression-baseline-v1",
            "fhe_scheme": timing["scheme"],
            "polynomial_degree": timing["polynomial_degree"],
            "open_security_events": open_security_events,
        },
    }


def activity(session: Session, days: int = 7) -> dict[str, object]:
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = session.execute(
        select(func.date(AuditLog.timestamp), func.count(AuditLog.id))
        .where(AuditLog.timestamp >= start)
        .group_by(func.date(AuditLog.timestamp))
        .order_by(func.date(AuditLog.timestamp))
    ).all()
    counts = {str(day): count for day, count in rows}
    prediction_rows = session.execute(
        select(func.date(PredictionMetadata.created_at), func.count(PredictionMetadata.id))
        .where(PredictionMetadata.created_at >= start)
        .group_by(func.date(PredictionMetadata.created_at))
    ).all()
    prediction_counts = {str(day): count for day, count in prediction_rows}
    points = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).date().isoformat()
        points.append({"date": day, "admin_events": counts.get(day, 0), "predictions": prediction_counts.get(day, 0)})
    recent = session.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(6)).all()
    return {
        "series": points,
        "recent": [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "action": event.action,
                "result": event.result,
                "resource_type": event.resource_type,
                "actor_role": event.actor_role,
            }
            for event in recent
        ],
        "prediction_activity_available": True,
    }


def risk_distribution(session: Session | None = None) -> dict[str, object]:
    if session is not None:
        rows = session.execute(
            select(PredictionMetadata.risk_class, func.count(PredictionMetadata.id))
            .where(PredictionMetadata.risk_class.is_not(None))
            .group_by(PredictionMetadata.risk_class)
        ).all()
        if rows:
            items = [{"risk_class": risk, "count": count} for risk, count in rows]
            return {"source": "privacy_safe_prediction_metadata", "total": sum(item["count"] for item in items), "items": items}
    _, baseline = measured_results()
    matrix = baseline["confusion_matrix"]
    predicted_low = matrix[0][0] + matrix[1][0]
    predicted_high = matrix[0][1] + matrix[1][1]
    return {
        "source": "measured_test_set_predictions",
        "total": predicted_low + predicted_high,
        "items": [
            {"risk_class": "LOW RISK", "count": predicted_low},
            {"risk_class": "HIGH RISK", "count": predicted_high},
        ],
    }


def fhe_performance() -> dict[str, object]:
    benchmark, _ = measured_results()
    timing = benchmark["fhe_polynomial_ml"]["timing"]
    return {
        "source": "measured_openfhe_test_set_benchmark",
        "scheme": timing["scheme"],
        "ring_dimension": timing["ring_dimension"],
        "polynomial_degree": timing["polynomial_degree"],
        "stages": [
            {"stage": "Key generation", "milliseconds": timing["key_generation_ms"]},
            {"stage": "Encryption", "milliseconds": timing["encryption_ms"]},
            {"stage": "Evaluation", "milliseconds": timing["evaluation_ms"]},
            {"stage": "Decryption", "milliseconds": timing["decryption_ms"]},
        ],
        "total_latency_ms": timing["total_latency_ms"],
        "ciphertext_size_bytes": timing["seven_input_ciphertexts_bytes"],
        "mean_absolute_error": benchmark["fhe_polynomial_ml"]["fhe_vs_plain_polynomial_mean_absolute_error"],
    }


def privacy_summary() -> dict[str, object]:
    return {
        "compliance_status": "pilot_controls_verified",
        "encrypted_test_samples": measured_results()[0]["samples"],
        "secret_key_exposure_incidents": 0,
        "plaintext_storage_incidents": 0,
        "checks": [
            {"name": "Evaluator receives encrypted features", "status": "implemented"},
            {"name": "Secret key excluded from homomorphic evaluation operations", "status": "pilot_verified"},
            {"name": "Raw financial fields excluded from admin schema", "status": "implemented"},
            {"name": "Browser-side encryption", "status": "planned"},
            {"name": "Production TLS enforcement", "status": "planned"},
        ],
        "boundary": "Client and evaluator responsibilities are separated in code, but run in one local C++ process. Process-level key isolation is planned.",
        "note": "Zero incidents means no incidents were recorded by the current monitoring controls; it is not proof of absence outside the monitored pilot environment.",
    }
