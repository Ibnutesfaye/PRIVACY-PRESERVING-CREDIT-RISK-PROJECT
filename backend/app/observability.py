from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from prometheus_client import Counter, Gauge, Histogram


LOGGER = logging.getLogger("cipherscore")
HTTP_REQUESTS = Counter("cipherscore_http_requests_total", "HTTP requests", ["method", "route", "status_class"])
HTTP_LATENCY = Histogram("cipherscore_http_request_duration_seconds", "HTTP request latency", ["method", "route"])
FHE_EVALUATIONS = Counter("cipherscore_fhe_evaluations_total", "Ciphertext-only evaluations", ["profile", "outcome"])
FHE_EVALUATION_LATENCY = Histogram("cipherscore_fhe_evaluation_duration_seconds", "Ciphertext evaluator latency", ["profile"])
FHE_REQUEST_BYTES = Histogram("cipherscore_fhe_request_ciphertext_bytes", "Serialized ciphertext request bytes", ["profile"], buckets=(1_000_000, 5_000_000, 10_000_000, 20_000_000, 30_000_000, 40_000_000, 55_000_000))
AUTH_FAILURES = Counter("cipherscore_auth_failures_total", "Authentication and authorization failures", ["code"])
DATABASE_HEALTH = Gauge("cipherscore_database_healthy", "Database connectivity health (1 healthy, 0 unavailable)")
APPLICATION_READINESS = Gauge("cipherscore_application_ready", "Application dependency readiness (1 ready, 0 not ready)")
FHE_WORKER_READINESS = Gauge("cipherscore_fhe_worker_ready", "Encrypted evaluator readiness (1 ready, 0 not ready)")


def configure_logging() -> None:
    if LOGGER.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def log_event(event: str, *, level: str = "INFO", **fields: Any) -> None:
    """Emit an allow-listed structured event; callers must not pass request bodies or secrets."""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": "cipherscore-api",
        "event": event,
    }
    record.update({key: value for key, value in fields.items() if value is not None})
    log_method = LOGGER.error if level == "ERROR" else LOGGER.warning if level == "WARNING" else LOGGER.info
    log_method(json.dumps(record, separators=(",", ":"), default=str))
