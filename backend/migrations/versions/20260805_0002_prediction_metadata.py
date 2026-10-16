"""Add privacy-safe prediction metadata.

Revision ID: 20260805_0002
Revises: 20260805_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20260805_0002"
down_revision = "20260805_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_metadata",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prediction_id", sa.String(40), nullable=False),
        sa.Column("anonymous_user_id", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_class", sa.String(20), nullable=True),
        sa.Column("risk_score_band", sa.String(20), nullable=True),
        sa.Column("encryption_status", sa.String(24), nullable=False),
        sa.Column("evaluation_status", sa.String(24), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("fhe_profile", sa.String(80), nullable=False),
        sa.Column("encoding_time_ms", sa.Float(), nullable=True),
        sa.Column("encryption_time_ms", sa.Float(), nullable=True),
        sa.Column("evaluation_time_ms", sa.Float(), nullable=True),
        sa.Column("decryption_time_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=True),
        sa.Column("ciphertext_size_bytes", sa.Integer(), nullable=True),
        sa.Column("request_status", sa.String(24), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
    )
    op.create_index("ix_prediction_metadata_prediction_id", "prediction_metadata", ["prediction_id"], unique=True)
    for column in ("anonymous_user_id", "created_at", "risk_class", "encryption_status", "evaluation_status", "model_version", "fhe_profile", "total_latency_ms", "request_status", "error_code"):
        op.create_index(f"ix_prediction_metadata_{column}", "prediction_metadata", [column])
    op.create_index("ix_prediction_created_status", "prediction_metadata", ["created_at", "request_status"])
    op.create_index("ix_prediction_risk_created", "prediction_metadata", ["risk_class", "created_at"])
    op.create_index("ix_prediction_model_created", "prediction_metadata", ["model_version", "created_at"])


def downgrade() -> None:
    op.drop_table("prediction_metadata")
