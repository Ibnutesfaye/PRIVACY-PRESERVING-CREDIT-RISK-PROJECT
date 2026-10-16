from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class EncryptedEvaluationRequest(BaseModel):
    protocol_version: int = Field(default=1, ge=1, le=1)
    profile_id: str = Field(min_length=1, max_length=80)
    model_version: str = Field(default="logistic-regression-baseline-v1", min_length=1, max_length=80)
    context_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_size: int = Field(ge=1, le=8192)
    feature_ciphertexts: list[str] = Field(min_length=7, max_length=7)

    @field_validator("feature_ciphertexts")
    @classmethod
    def ciphertexts_must_be_present(cls, values: list[str]) -> list[str]:
        if any(not value for value in values):
            raise ValueError("All seven feature ciphertexts are required")
        return values


class EncryptedEvaluationResponse(BaseModel):
    protocol_version: int
    profile_id: str
    model_version: str
    context_fingerprint: str
    batch_size: int
    result_ciphertext: str
    result_encoding: str = "base64"
    evaluator_decrypted_result: bool = False
    prediction_id: str
    evaluation_time_ms: float
