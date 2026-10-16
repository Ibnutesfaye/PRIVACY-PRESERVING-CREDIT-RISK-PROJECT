"""Add governed model versions."""
from alembic import op
import sqlalchemy as sa
revision="20260805_0003"; down_revision="20260805_0002"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("model_versions",sa.Column("id",sa.String(36),primary_key=True),sa.Column("version",sa.String(80),nullable=False),sa.Column("model_name",sa.String(120),nullable=False),sa.Column("model_type",sa.String(80),nullable=False),sa.Column("dataset_version",sa.String(80),nullable=False),sa.Column("polynomial_version",sa.String(80),nullable=False),sa.Column("status",sa.String(24),nullable=False),sa.Column("fhe_compatible",sa.Boolean(),nullable=False),sa.Column("validation_passed",sa.Boolean(),nullable=False),sa.Column("metrics",sa.JSON(),nullable=False),sa.Column("artifact_hash",sa.String(64),nullable=False),sa.Column("notes",sa.Text(),nullable=True),sa.Column("created_by",sa.String(36),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("approved_by",sa.String(36),nullable=True),sa.Column("approved_at",sa.DateTime(timezone=True),nullable=True),sa.Column("activated_at",sa.DateTime(timezone=True),nullable=True))
    op.create_index("ix_model_versions_version","model_versions",["version"],unique=True);op.create_index("ix_model_versions_status","model_versions",["status"])
def downgrade(): op.drop_table("model_versions")
