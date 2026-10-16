"""Add notifications, settings, and report records."""
from alembic import op
import sqlalchemy as sa
revision="20260805_0004";down_revision="20260805_0003";branch_labels=None;depends_on=None
def upgrade():
 op.create_table("notifications",sa.Column("id",sa.String(36),primary_key=True),sa.Column("category",sa.String(60),nullable=False),sa.Column("severity",sa.String(20),nullable=False),sa.Column("title",sa.String(160),nullable=False),sa.Column("message",sa.String(500),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
 op.create_table("admin_settings",sa.Column("id",sa.String(36),primary_key=True),sa.Column("key",sa.String(100),nullable=False),sa.Column("value",sa.JSON(),nullable=False),sa.Column("description",sa.String(255),nullable=False),sa.Column("updated_by",sa.String(36),nullable=True),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
 op.create_table("reports",sa.Column("id",sa.String(36),primary_key=True),sa.Column("report_type",sa.String(80),nullable=False),sa.Column("format",sa.String(12),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("created_by",sa.String(36),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("safe_parameters",sa.JSON(),nullable=False),sa.Column("row_count",sa.Integer(),nullable=False))
 for table,cols in {"notifications":["category","severity","status","created_at"],"admin_settings":["key"],"reports":["report_type","status","created_by","created_at"]}.items():
  for col in cols:op.create_index(f"ix_{table}_{col}",table,[col],unique=table=="admin_settings" and col=="key")
def downgrade():op.drop_table("reports");op.drop_table("admin_settings");op.drop_table("notifications")
