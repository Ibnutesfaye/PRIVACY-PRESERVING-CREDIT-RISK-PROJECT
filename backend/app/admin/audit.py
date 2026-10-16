from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.admin.models import AuditLog


PROHIBITED_METADATA_KEYS = {
    "password", "token", "secret", "secret_key", "income", "loan_amnt",
    "person_age", "interest_rate", "raw_features", "ciphertext",
}


def _validate_safe_metadata(metadata: dict[str, Any]) -> None:
    keys = {key.casefold() for key in metadata}
    prohibited = sorted(keys & PROHIBITED_METADATA_KEYS)
    if prohibited:
        raise ValueError(f"Sensitive audit metadata keys are prohibited: {', '.join(prohibited)}")


def append_audit_event(
    session: Session,
    *,
    action: str,
    resource_type: str,
    result: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    safe_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    metadata = safe_metadata or {}
    _validate_safe_metadata(metadata)
    previous = session.scalar(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1))
    previous_hash = previous.event_hash if previous else None
    timestamp = datetime.now(timezone.utc)
    canonical = json.dumps(
        {
            "timestamp": timestamp.isoformat(),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
            "ip_address": ip_address,
            "safe_metadata": metadata,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event = AuditLog(
        timestamp=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:512] or None,
        safe_metadata=metadata,
        previous_hash=previous_hash,
        event_hash=event_hash,
    )
    session.add(event)
    return event

