from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    user_roles: Mapped[list[UserRole]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    role_permissions: Mapped[list[RolePermission]] = relationship(back_populates="role", cascade="all, delete-orphan")
    user_roles: Mapped[list[UserRole]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255))

    role_permissions: Mapped[list[RolePermission]] = relationship(back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)

    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    assigned_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    user: Mapped[AdminUser] = relationship(back_populates="user_roles")
    role: Mapped[Role] = relationship(back_populates="user_roles")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    replaced_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped[AdminUser] = relationship(back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_timestamp_action", "timestamp", "action"),
        Index("ix_audit_actor_timestamp", "actor_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[str] = mapped_column(String(40), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (Index("ix_security_status_severity_created", "status", "severity", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    summary: Mapped[str] = mapped_column(String(255))
    safe_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PredictionMetadata(Base):
    __tablename__ = "prediction_metadata"
    __table_args__ = (
        Index("ix_prediction_created_status", "created_at", "request_status"),
        Index("ix_prediction_risk_created", "risk_class", "created_at"),
        Index("ix_prediction_model_created", "model_version", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("loan_applications.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)
    prediction_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    anonymous_user_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    risk_class: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    risk_score_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    encryption_status: Mapped[str] = mapped_column(String(24), index=True)
    evaluation_status: Mapped[str] = mapped_column(String(24), index=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    fhe_profile: Mapped[str] = mapped_column(String(80), index=True)
    encoding_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    encryption_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    decryption_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    ciphertext_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_status: Mapped[str] = mapped_column(String(24), index=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    model_type: Mapped[str] = mapped_column(String(80))
    dataset_version: Mapped[str] = mapped_column(String(80))
    polynomial_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), index=True)
    fhe_compatible: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    artifact_hash: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__="notifications"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=new_id);category:Mapped[str]=mapped_column(String(60),index=True);severity:Mapped[str]=mapped_column(String(20),index=True);title:Mapped[str]=mapped_column(String(160));message:Mapped[str]=mapped_column(String(500));status:Mapped[str]=mapped_column(String(20),default="unread",index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now,index=True)
class AdminSetting(Base):
    __tablename__="admin_settings"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=new_id);key:Mapped[str]=mapped_column(String(100),unique=True,index=True);value:Mapped[Any]=mapped_column(JSON);description:Mapped[str]=mapped_column(String(255));updated_by:Mapped[str|None]=mapped_column(String(36),nullable=True);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now,onupdate=utc_now)
class ReportRecord(Base):
    __tablename__="reports"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=new_id);report_type:Mapped[str]=mapped_column(String(80),index=True);format:Mapped[str]=mapped_column(String(12));status:Mapped[str]=mapped_column(String(20),index=True);created_by:Mapped[str]=mapped_column(String(36),index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now,index=True);safe_parameters:Mapped[dict[str,Any]]=mapped_column(JSON,default=dict);row_count:Mapped[int]=mapped_column(Integer,default=0)


class FheMetric(Base):
    __tablename__ = "fhe_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    prediction_metadata_id: Mapped[str | None] = mapped_column(ForeignKey("prediction_metadata.id", ondelete="SET NULL"), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    profile_id: Mapped[str] = mapped_column(String(80), index=True)
    scheme: Mapped[str] = mapped_column(String(20))
    key_generation_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    encoding_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    encryption_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_time_ms: Mapped[float] = mapped_column(Float)
    decryption_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[float] = mapped_column(Float, index=True)
    ciphertext_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_version_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id", ondelete="CASCADE"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    metric_name: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    dataset_split: Mapped[str] = mapped_column(String(40), default="test")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String(24), index=True)
    profile_id: Mapped[str] = mapped_column(String(80), index=True)
    started_by: Mapped[str] = mapped_column(String(36), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    safe_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    benchmark_run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id", ondelete="CASCADE"), index=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SystemHealthRecord(Base):
    __tablename__ = "system_health"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    service: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    safe_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint("risk_threshold >= 0 AND risk_threshold <= 1", name="ck_organization_risk_threshold"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    risk_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    model_version: Mapped[str] = mapped_column(String(80), default="logistic-regression-baseline-v1")
    openfhe_profile: Mapped[str] = mapped_column(String(80), default="ckks-balanced-degree7-v1")
    enabled_features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    security_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reporting_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_branch_organization_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    manager_user_id: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", "branch_id", name="uq_user_organization_branch_scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(24), default="branch")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    subject_reference_hash: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(160))
    lawful_basis: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoanApplication(Base):
    __tablename__ = "loan_applications"
    __table_args__ = (
        UniqueConstraint("organization_id", "application_number", name="uq_organization_application_number"),
        Index("ix_application_scope_status_created", "organization_id", "branch_id", "status", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_number: Mapped[str] = mapped_column(String(50), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="RESTRICT"), index=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True)
    consent_record_id: Mapped[str] = mapped_column(ForeignKey("consent_records.id", ondelete="RESTRICT"), index=True)
    customer_reference_hash: Mapped[str] = mapped_column(String(64), index=True)
    loan_product_code: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    model_recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_score_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prediction_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowHistory(Base):
    __tablename__ = "workflow_history"
    __table_args__ = (Index("ix_workflow_application_changed", "application_id", "changed_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("loan_applications.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    changed_by: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="RESTRICT"), index=True)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    safe_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DecisionRecord(Base):
    __tablename__ = "decision_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("loan_applications.id", ondelete="CASCADE"), index=True)
    officer_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="RESTRICT"), index=True)
    decision: Mapped[str] = mapped_column(String(30), index=True)
    model_recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CryptoParameterProfile(Base):
    __tablename__ = "crypto_parameter_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    scheme: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifact_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    __table_args__ = (UniqueConstraint("organization_id", "record_type", name="uq_retention_organization_record_type"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    record_type: Mapped[str] = mapped_column(String(60))
    retention_days: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(30), default="anonymize")
    legal_hold_required: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="RESTRICT"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
