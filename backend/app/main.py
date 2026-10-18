import uuid
import re
import secrets
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.admin.dashboard_routes import router as admin_dashboard_router
from backend.app.admin.errors import AdminAPIError
from backend.app.admin.fhe_routes import router as admin_fhe_router
from backend.app.admin.model_routes import router as admin_model_router
from backend.app.admin.operations_routes import router as admin_operations_router
from backend.app.admin.prediction_routes import router as admin_prediction_router
from backend.app.admin.predictions import record_failure, record_success
from backend.app.admin.routes import router as admin_auth_router
from backend.app.admin.user_routes import router as admin_user_router
from backend.app.database import engine, get_db
from backend.app.config import get_application_settings
from backend.app.middleware import RequestBodyLimitMiddleware
from backend.app.observability import APPLICATION_READINESS, AUTH_FAILURES, DATABASE_HEALTH, FHE_WORKER_READINESS, HTTP_LATENCY, HTTP_REQUESTS, configure_logging, log_event
from backend.app.schemas import CreditRiskRequest, PredictionResponse
from backend.app.service import service
from backend.app.encrypted_routes import router as encrypted_inference_router
from backend.app.encrypted_service import encrypted_service
from backend.app.workflow_routes import router as enterprise_workflow_router

settings = get_application_settings()
configure_logging()

app = FastAPI(
    title="Privacy-Preserving Credit Risk API",
    version="0.3.0",
    description="Trusted local gateway for an OpenFHE CKKS encrypted evaluator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.security_max_request_bytes)

app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_prediction_router)
app.include_router(admin_fhe_router)
app.include_router(admin_model_router)
app.include_router(admin_user_router)
app.include_router(admin_operations_router)
app.include_router(encrypted_inference_router)
app.include_router(enterprise_workflow_router)


@app.middleware("http")
async def request_id_and_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    supplied_request_id = request.headers.get("x-request-id", "")
    request.state.request_id = supplied_request_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id) else str(uuid.uuid4())
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log_event(
            "request_failed",
            level="ERROR",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        raise
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https" or settings.application_environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    route_object = request.scope.get("route")
    route_template = getattr(route_object, "path", "unmatched")
    duration_seconds = perf_counter() - started
    HTTP_REQUESTS.labels(request.method, route_template, f"{response.status_code // 100}xx").inc()
    HTTP_LATENCY.labels(request.method, route_template).observe(duration_seconds)
    log_event(
        "request_completed",
        request_id=request.state.request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_seconds * 1000, 3),
    )
    return response


@app.exception_handler(AdminAPIError)
async def admin_error_handler(request: Request, error: AdminAPIError) -> JSONResponse:
    if error.status_code in {401, 403, 423, 429}:
        AUTH_FAILURES.labels(error.code).inc()
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


@app.get(
    "/health",
    summary="Check API, database, and OpenFHE readiness",
    description="Returns non-secret readiness metadata for the API, PostgreSQL connection, and compiled evaluator.",
)
def health() -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_connected = True
    except Exception:
        database_connected = False
    return {
        "status": "healthy" if database_connected else "degraded",
        "database": engine.dialect.name,
        "connected": database_connected,
        "openfhe": "ready" if service.executable.exists() else "not-built",
    }


@app.get("/api/v1/system/liveness", tags=["system"], summary="Process liveness probe")
def liveness() -> dict[str, str]:
    return {"status": "alive", "service": settings.application_service_name}


@app.get("/api/v1/system/readiness", tags=["system"], summary="Dependency readiness probe")
def readiness() -> JSONResponse:
    checks: dict[str, bool] = {
        "database": False,
        "openfhe_evaluator": service.executable.exists(),
        "encrypted_profile": encrypted_service.ready,
    }
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        engine.dispose()
    required_checks = [checks["database"]]
    if settings.application_environment == "production":
        required_checks.extend([checks["openfhe_evaluator"], checks["encrypted_profile"]])
    ready = all(required_checks)
    DATABASE_HEALTH.set(1 if checks["database"] else 0)
    FHE_WORKER_READINESS.set(1 if checks["openfhe_evaluator"] and checks["encrypted_profile"] else 0)
    APPLICATION_READINESS.set(1 if ready else 0)
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )


@app.get("/internal/metrics", include_in_schema=False)
def prometheus_metrics(request: Request) -> Response:
    configured = settings.resolved_metrics_token
    authorization = request.headers.get("authorization", "")
    bearer = authorization[7:] if authorization.casefold().startswith("bearer ") else ""
    supplied = request.headers.get("x-metrics-token", "") or bearer
    if configured is None:
        raise HTTPException(status_code=404, detail="Metrics endpoint is not configured")
    if not secrets.compare_digest(supplied, configured):
        raise HTTPException(status_code=401, detail="Metrics authentication failed")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Run a privacy-preserving credit-risk prediction",
    description=(
        "Validates customer inputs, applies training-fitted preprocessing, invokes the OpenFHE CKKS evaluator, "
        "and persists only privacy-safe operational metadata."
    ),
    responses={500: {"description": "Encrypted evaluation failed"}},
)
def predict(request: CreditRiskRequest, session: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    # Do not log or persist request values. FastAPI/Uvicorn access logs contain
    # method/path/status but not request bodies by default.
    if not settings.model_plaintext_prediction_enabled:
        raise HTTPException(status_code=404, detail="The plaintext compatibility endpoint is disabled")
    try:
        result = service.predict(request)
        record_success(session, result)
        return result
    except RuntimeError as error:
        record_failure(session, "FHE_EVALUATION_FAILED")
        raise HTTPException(status_code=500, detail="The encrypted prediction could not be evaluated") from error
