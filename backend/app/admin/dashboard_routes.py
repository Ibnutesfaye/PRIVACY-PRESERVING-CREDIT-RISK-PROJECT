from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.admin import dashboard
from backend.app.admin.auth import AuthenticatedAdmin, require_permissions
from backend.app.database import get_db


router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin dashboard"])
DashboardReader = Annotated[AuthenticatedAdmin, Depends(require_permissions("dashboard.read"))]


@router.get("/summary")
def get_summary(_admin: DashboardReader, session: Annotated[Session, Depends(get_db)]):
    return dashboard.summary(session)


@router.get("/activity")
def get_activity(
    _admin: DashboardReader,
    session: Annotated[Session, Depends(get_db)],
    days: int = Query(default=7, ge=1, le=31),
):
    return dashboard.activity(session, days)


@router.get("/risk-distribution")
def get_risk_distribution(_admin: DashboardReader, session: Annotated[Session, Depends(get_db)]):
    return dashboard.risk_distribution(session)


@router.get("/fhe-performance")
def get_fhe_performance(_admin: DashboardReader):
    return dashboard.fhe_performance()


@router.get("/privacy")
def get_privacy(_admin: DashboardReader):
    return dashboard.privacy_summary()
