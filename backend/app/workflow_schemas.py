from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OrganizationCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    name: str = Field(min_length=2, max_length=180)
    risk_threshold: float = Field(default=0.5, ge=0, le=1)
    model_version: str = Field(default="logistic-regression-baseline-v1", min_length=1, max_length=80)
    openfhe_profile: str = Field(default="ckks-balanced-degree7-v1", min_length=1, max_length=80)


class BranchCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    name: str = Field(min_length=2, max_length=180)
    manager_user_id: str | None = None


class MembershipCreate(BaseModel):
    user_id: str
    branch_id: str | None = None
    scope: str = Field(pattern=r"^(organization|branch)$")


class ConsentCreate(BaseModel):
    subject_reference_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    purpose: str = Field(min_length=3, max_length=160)
    lawful_basis: str = Field(min_length=3, max_length=80)
    evidence_hash: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class ApplicationCreate(BaseModel):
    application_number: str = Field(pattern=r"^[A-Za-z0-9_-]{3,50}$")
    organization_id: str
    branch_id: str
    consent_record_id: str
    customer_reference_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    loan_product_code: str = Field(pattern=r"^[A-Za-z0-9_-]{2,60}$")


class TransitionRequest(BaseModel):
    to_status: str
    expected_version: int = Field(ge=1)
    reason_code: str | None = Field(default=None, max_length=80)
    safe_note: str | None = Field(default=None, max_length=500)

    @field_validator("to_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class PredictionReference(BaseModel):
    prediction_id: str = Field(min_length=3, max_length=40)
    model_recommendation: str = Field(pattern=r"^(LOW RISK|HIGH RISK)$")
    risk_score_band: str = Field(pattern=r"^(LOW|MEDIUM|HIGH)$")
    expected_version: int = Field(ge=1)


class DecisionCreate(BaseModel):
    decision: str = Field(pattern=r"^(APPROVED|REJECTED)$")
    expected_version: int = Field(ge=1)
    override_reason: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
