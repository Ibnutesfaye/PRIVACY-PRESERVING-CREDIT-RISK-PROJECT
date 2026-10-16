from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin.audit import append_audit_event
from backend.app.admin.auth import AuthenticatedAdmin, request_context, require_permissions
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.models import PredictionMetadata
from backend.app.admin.predictions import SORT_COLUMNS, csv_export, filtered_query, serialize, timeline
from backend.app.database import get_db
from fastapi import Request


router = APIRouter(prefix="/api/admin/predictions", tags=["Admin predictions"])
PredictionReader = Annotated[AuthenticatedAdmin, Depends(require_permissions("predictions.read"))]


@router.get("")
def list_predictions(
    _admin: PredictionReader, session: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=80), risk_class: str | None = None,
    request_status: str | None = None, encryption_status: str | None = None,
    model_version: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None,
    min_latency_ms: float | None = Query(None, ge=0), max_latency_ms: float | None = Query(None, ge=0),
    sort_by: Literal["created_at", "total_latency_ms", "risk_class", "request_status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
):
    query = filtered_query(search=search, risk_class=risk_class, request_status=request_status,
        encryption_status=encryption_status, model_version=model_version, date_from=date_from, date_to=date_to,
        min_latency_ms=min_latency_ms, max_latency_ms=max_latency_ms)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = SORT_COLUMNS[sort_by].asc() if sort_order == "asc" else SORT_COLUMNS[sort_by].desc()
    rows = session.scalars(query.order_by(order).offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [serialize(row) for row in rows], "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}


@router.get("/export")
def export_predictions(request: Request, _admin: Annotated[AuthenticatedAdmin, Depends(require_permissions("predictions.export"))], session: Annotated[Session, Depends(get_db)]):
    rows = session.scalars(select(PredictionMetadata).order_by(PredictionMetadata.created_at.desc()).limit(5000)).all()
    ip, agent = request_context(request)
    append_audit_event(session, actor_id=_admin.user.id, actor_role=_admin.roles[0] if _admin.roles else None,
        action="predictions.exported", resource_type="prediction_metadata", result="success",
        ip_address=ip, user_agent=agent, safe_metadata={"record_count": len(rows), "format": "csv"})
    session.commit()
    return Response(csv_export(rows), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=privacy-safe-predictions.csv"})


def get_row(session: Session, prediction_id: str) -> PredictionMetadata:
    row = session.scalar(select(PredictionMetadata).where(PredictionMetadata.prediction_id == prediction_id))
    if row is None:
        raise AdminAPIError(404, "PREDICTION_NOT_FOUND", "Prediction metadata was not found")
    return row


@router.get("/{prediction_id}")
def prediction_detail(prediction_id: str, _admin: PredictionReader, session: Annotated[Session, Depends(get_db)]):
    return serialize(get_row(session, prediction_id))


@router.get("/{prediction_id}/timeline")
def prediction_timeline(prediction_id: str, _admin: PredictionReader, session: Annotated[Session, Depends(get_db)]):
    return {"prediction_id": prediction_id, "items": timeline(get_row(session, prediction_id))}
