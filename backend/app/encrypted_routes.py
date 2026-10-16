from __future__ import annotations

import base64
import hashlib
import uuid
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.config import get_application_settings
from backend.app.encrypted_schemas import EncryptedEvaluationRequest, EncryptedEvaluationResponse
from backend.app.encrypted_service import encrypted_service
from backend.app.admin.auth import AuthenticatedAdmin, require_permissions
from backend.app.admin.audit import append_audit_event
from backend.app.admin.models import FheMetric, PredictionMetadata, utc_now
from backend.app.database import get_db
from backend.app.observability import FHE_EVALUATIONS, FHE_EVALUATION_LATENCY, FHE_REQUEST_BYTES


router = APIRouter(prefix="/api/v1/fhe", tags=["encrypted inference"])
EncryptedOperator = Annotated[AuthenticatedAdmin, Depends(require_permissions("applications.write"))]


@router.get("/profiles/current")
def current_profile(_operator: EncryptedOperator) -> dict[str, object]:
    settings = get_application_settings()
    if not settings.openfhe_encrypted_api_enabled:
        raise HTTPException(status_code=404, detail="Encrypted inference is disabled")
    return {
        "protocol_version": 1,
        "profile_id": settings.openfhe_profile_id,
        "model_version": settings.openfhe_model_version,
        "context_fingerprint": encrypted_service.context_fingerprint if encrypted_service.ready else None,
        "scheme": "CKKS",
        "feature_count": 7,
        "feature_order": [
            "person_age", "person_income", "person_emp_length", "loan_amnt",
            "loan_int_rate", "loan_percent_income", "cb_person_cred_hist_length",
        ],
        "input_representation": "training-fitted median imputation and StandardScaler",
        "batch_capacity": 8192,
        "ready": encrypted_service.ready,
        "secret_key_distributed_by_server": False,
    }


@router.get("/profiles/current/artifacts/{artifact_name}", response_class=FileResponse)
def public_profile_artifact(artifact_name: str, _operator: EncryptedOperator) -> FileResponse:
    if not get_application_settings().openfhe_encrypted_api_enabled:
        raise HTTPException(status_code=404, detail="Encrypted inference is disabled")
    try:
        path = encrypted_service.public_artifact(artifact_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown public profile artifact") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The encrypted inference profile is not ready") from error
    return FileResponse(path, media_type="application/octet-stream", filename=path.name)


@router.post("/evaluate", response_model=EncryptedEvaluationResponse)
def evaluate_ciphertexts(request: EncryptedEvaluationRequest, operator: EncryptedOperator, session: Annotated[Session, Depends(get_db)]) -> EncryptedEvaluationResponse:
    if not get_application_settings().openfhe_encrypted_api_enabled:
        raise HTTPException(status_code=404, detail="Encrypted inference is disabled")
    try:
        started = perf_counter()
        artifact = encrypted_service.evaluate(request)
        evaluation_time_ms = (perf_counter() - started) * 1000
    except ValueError as error:
        FHE_EVALUATIONS.labels(request.profile_id, "invalid").inc()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        FHE_EVALUATIONS.labels(request.profile_id, "failed").inc()
        raise HTTPException(status_code=503, detail="Encrypted evaluation is temporarily unavailable") from error
    FHE_EVALUATIONS.labels(request.profile_id, "success").inc()
    FHE_EVALUATION_LATENCY.labels(request.profile_id).observe(evaluation_time_ms / 1000)
    FHE_REQUEST_BYTES.labels(request.profile_id).observe(artifact.request_ciphertext_bytes)
    prediction_id = f"PRD-{uuid.uuid4().hex[:20].upper()}"
    metadata = PredictionMetadata(
        prediction_id=prediction_id,
        anonymous_user_id=hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32],
        completed_at=utc_now(),
        risk_class=None,
        risk_score_band=None,
        encryption_status="client_encrypted",
        evaluation_status="completed",
        model_version=request.model_version,
        fhe_profile=request.profile_id,
        evaluation_time_ms=evaluation_time_ms,
        total_latency_ms=evaluation_time_ms,
        ciphertext_size_bytes=artifact.request_ciphertext_bytes,
        request_status="completed",
        requested_by=operator.user.id,
    )
    session.add(metadata)
    session.flush()
    session.add(FheMetric(
        prediction_metadata_id=metadata.id,
        profile_id=request.profile_id,
        scheme="CKKS",
        key_generation_ms=None,
        encoding_time_ms=None,
        encryption_time_ms=None,
        evaluation_time_ms=evaluation_time_ms,
        decryption_time_ms=None,
        total_latency_ms=evaluation_time_ms,
        ciphertext_size_bytes=artifact.request_ciphertext_bytes,
    ))
    append_audit_event(
        session,
        actor_id=operator.user.id,
        actor_role=operator.roles[0] if operator.roles else None,
        action="encrypted_prediction.evaluated",
        resource_type="prediction_metadata",
        resource_id=prediction_id,
        result="success",
        safe_metadata={"profile_id": request.profile_id, "model_version": request.model_version, "batch_size": request.batch_size},
    )
    session.commit()
    return EncryptedEvaluationResponse(
        protocol_version=1,
        profile_id=request.profile_id,
        model_version=request.model_version,
        context_fingerprint=request.context_fingerprint,
        batch_size=request.batch_size,
        result_ciphertext=base64.b64encode(artifact.result_ciphertext).decode("ascii"),
        prediction_id=prediction_id,
        evaluation_time_ms=evaluation_time_ms,
    )
