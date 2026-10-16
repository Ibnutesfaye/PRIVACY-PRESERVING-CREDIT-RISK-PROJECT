"""Allow client-owned encryption and decryption timing stages to be absent."""

from alembic import op
import sqlalchemy as sa

revision = "20260807_0007"
down_revision = "20260807_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("fhe_metrics", "encryption_time_ms", existing_type=sa.Float(), nullable=True)
    op.alter_column("fhe_metrics", "decryption_time_ms", existing_type=sa.Float(), nullable=True)


def downgrade():
    op.execute("UPDATE fhe_metrics SET encryption_time_ms = 0 WHERE encryption_time_ms IS NULL")
    op.execute("UPDATE fhe_metrics SET decryption_time_ms = 0 WHERE decryption_time_ms IS NULL")
    op.alter_column("fhe_metrics", "encryption_time_ms", existing_type=sa.Float(), nullable=False)
    op.alter_column("fhe_metrics", "decryption_time_ms", existing_type=sa.Float(), nullable=False)
