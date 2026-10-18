"""Allow client-owned encryption and decryption timing stages to be absent."""

from alembic import op
import sqlalchemy as sa

revision = "20260807_0007"
down_revision = "20260807_0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fhe_metrics") as batch_op:
        batch_op.alter_column("encryption_time_ms", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("decryption_time_ms", existing_type=sa.Float(), nullable=True)


def downgrade():
    op.execute("UPDATE fhe_metrics SET encryption_time_ms = 0 WHERE encryption_time_ms IS NULL")
    op.execute("UPDATE fhe_metrics SET decryption_time_ms = 0 WHERE decryption_time_ms IS NULL")
    with op.batch_alter_table("fhe_metrics") as batch_op:
        batch_op.alter_column("encryption_time_ms", existing_type=sa.Float(), nullable=False)
        batch_op.alter_column("decryption_time_ms", existing_type=sa.Float(), nullable=False)
