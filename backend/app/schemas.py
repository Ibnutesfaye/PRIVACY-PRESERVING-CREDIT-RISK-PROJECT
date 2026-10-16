from pydantic import BaseModel, Field


class CreditRiskRequest(BaseModel):
    person_age: float = Field(ge=18, le=100)
    person_income: float = Field(gt=0, le=10_000_000)
    person_emp_length: float | None = Field(default=None, ge=0, le=80)
    loan_amnt: float = Field(gt=0, le=1_000_000)
    loan_int_rate: float | None = Field(default=None, ge=0, le=100)
    loan_percent_income: float = Field(ge=0, le=1)
    cb_person_cred_hist_length: float = Field(gt=0, le=100)


class TimingResponse(BaseModel):
    key_generation_ms: float
    encryption_ms: float
    evaluation_ms: float
    decryption_ms: float
    total_latency_ms: float


class PrivacyResponse(BaseModel):
    scheme: str
    encrypted_inference: bool
    evaluator_received_plaintext_features: bool
    trusted_gateway_received_plaintext_features: bool
    secret_key_available_to_evaluator: bool
    architecture_note: str


class PredictionResponse(BaseModel):
    risk_score: float
    raw_fhe_score: float
    prediction: str
    timing: TimingResponse
    privacy: PrivacyResponse

