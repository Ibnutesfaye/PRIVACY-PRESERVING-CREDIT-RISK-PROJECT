from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from backend.app.admin.models import FheMetric, PredictionMetadata


MODEL_VERSION = "logistic-regression-baseline-v1"
FHE_PROFILE = "ckks-balanced-degree7-v1"


def new_prediction_id() -> str:
    return f"PRD-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def new_anonymous_id() -> str:
    return f"USR-{secrets.token_hex(3).upper()}"


def score_band(score: float) -> str:
    if score < 0.25:
        return "0.00-0.24"
    if score < 0.5:
        return "0.25-0.49"
    if score < 0.75:
        return "0.50-0.74"
    return "0.75-1.00"


def record_success(session: Session, result: dict[str, object]) -> PredictionMetadata:
    timing = result["timing"]
    assert isinstance(timing, dict)
    score = float(result["risk_score"])
    row = PredictionMetadata(
        prediction_id=new_prediction_id(), anonymous_user_id=new_anonymous_id(),
        completed_at=datetime.now(timezone.utc), risk_class=str(result["prediction"]),
        risk_score_band=score_band(score), encryption_status="successful",
        evaluation_status="successful", model_version=MODEL_VERSION, fhe_profile=FHE_PROFILE,
        encoding_time_ms=None, encryption_time_ms=float(timing["encryption_ms"]),
        evaluation_time_ms=float(timing["evaluation_ms"]), decryption_time_ms=float(timing["decryption_ms"]),
        total_latency_ms=float(timing["total_latency_ms"]), ciphertext_size_bytes=None,
        request_status="completed", error_code=None,
    )
    session.add(row)
    session.flush()
    session.add(FheMetric(
        prediction_metadata_id=row.id, profile_id=FHE_PROFILE, scheme="CKKS",
        key_generation_ms=float(timing["key_generation_ms"]), encoding_time_ms=None,
        encryption_time_ms=float(timing["encryption_ms"]), evaluation_time_ms=float(timing["evaluation_ms"]),
        decryption_time_ms=float(timing["decryption_ms"]), total_latency_ms=float(timing["total_latency_ms"]),
        ciphertext_size_bytes=None,
    ))
    session.commit()
    return row


def record_failure(session: Session, error_code: str) -> PredictionMetadata:
    row = PredictionMetadata(
        prediction_id=new_prediction_id(), anonymous_user_id=new_anonymous_id(),
        completed_at=datetime.now(timezone.utc), encryption_status="failed",
        evaluation_status="failed", model_version=MODEL_VERSION, fhe_profile=FHE_PROFILE,
        request_status="failed", error_code=error_code,
    )
    session.add(row)
    session.commit()
    return row


def serialize(row: PredictionMetadata) -> dict[str, object]:
    return {column.name: getattr(row, column.name) for column in PredictionMetadata.__table__.columns}


SORT_COLUMNS = {
    "created_at": PredictionMetadata.created_at,
    "total_latency_ms": PredictionMetadata.total_latency_ms,
    "risk_class": PredictionMetadata.risk_class,
    "request_status": PredictionMetadata.request_status,
}


def filtered_query(*, search: str | None, risk_class: str | None, request_status: str | None,
                   encryption_status: str | None, model_version: str | None,
                   date_from: datetime | None, date_to: datetime | None,
                   min_latency_ms: float | None, max_latency_ms: float | None) -> Select:
    query = select(PredictionMetadata)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(PredictionMetadata.prediction_id.ilike(term), PredictionMetadata.anonymous_user_id.ilike(term)))
    if risk_class:
        query = query.where(PredictionMetadata.risk_class == risk_class)
    if request_status:
        query = query.where(PredictionMetadata.request_status == request_status)
    if encryption_status:
        query = query.where(PredictionMetadata.encryption_status == encryption_status)
    if model_version:
        query = query.where(PredictionMetadata.model_version == model_version)
    if date_from:
        query = query.where(PredictionMetadata.created_at >= date_from)
    if date_to:
        query = query.where(PredictionMetadata.created_at <= date_to)
    if min_latency_ms is not None:
        query = query.where(PredictionMetadata.total_latency_ms >= min_latency_ms)
    if max_latency_ms is not None:
        query = query.where(PredictionMetadata.total_latency_ms <= max_latency_ms)
    return query


def timeline(row: PredictionMetadata) -> list[dict[str, object]]:
    successful = row.request_status == "completed"
    stages = [
        ("Request received", "completed"), ("Input validation completed", "completed"),
        ("Trusted gateway preprocessing", "completed" if successful else "unknown"),
        ("CKKS encryption", row.encryption_status),
        ("Homomorphic evaluation", row.evaluation_status),
        ("Encrypted result returned and decrypted", "completed" if successful else "not_reached"),
        ("Request completed", row.request_status),
    ]
    return [{"stage": stage, "status": status, "timestamp": row.completed_at if index == len(stages)-1 else row.created_at} for index, (stage, status) in enumerate(stages)]


def csv_export(rows: list[PredictionMetadata]) -> str:
    output = io.StringIO()
    fields = ["prediction_id", "anonymous_user_id", "created_at", "risk_class", "risk_score_band", "encryption_status", "evaluation_status", "model_version", "fhe_profile", "total_latency_ms", "request_status", "error_code"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        data = serialize(row)
        writer.writerow({field: data[field] for field in fields})
    return output.getvalue()
