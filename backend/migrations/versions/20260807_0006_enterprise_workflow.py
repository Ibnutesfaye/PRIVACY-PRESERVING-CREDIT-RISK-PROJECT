"""Add organization-scoped application governance workflow."""

from alembic import op
import sqlalchemy as sa

revision = "20260807_0006"
down_revision = "20260805_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("organizations",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False), sa.Column("logo_url", sa.String(500)),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("risk_threshold", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False), sa.Column("openfhe_profile", sa.String(80), nullable=False),
        sa.Column("enabled_features", sa.JSON(), nullable=False), sa.Column("security_policy", sa.JSON(), nullable=False),
        sa.Column("reporting_configuration", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("risk_threshold >= 0 AND risk_threshold <= 1", name="ck_organization_risk_threshold"),
        sa.UniqueConstraint("code"), sa.UniqueConstraint("name"))
    op.create_index("ix_organizations_code", "organizations", ["code"]); op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_table("branches",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False), sa.Column("name", sa.String(180), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("manager_user_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_branch_organization_code"))
    for column in ("organization_id", "status"): op.create_index(f"ix_branches_{column}", "branches", [column])
    op.create_table("organization_memberships",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("branch_id", sa.String(36), sa.ForeignKey("branches.id", ondelete="CASCADE")), sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("user_id", "organization_id", "branch_id", name="uq_user_organization_branch_scope"))
    for column in ("user_id", "organization_id", "branch_id"): op.create_index(f"ix_organization_memberships_{column}", "organization_memberships", [column])
    op.create_table("consent_records",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_reference_hash", sa.String(64), nullable=False), sa.Column("purpose", sa.String(160), nullable=False), sa.Column("lawful_basis", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("evidence_hash", sa.String(64)), sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True)))
    for column in ("organization_id", "subject_reference_hash", "status"): op.create_index(f"ix_consent_records_{column}", "consent_records", [column])
    op.create_table("loan_applications",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("application_number", sa.String(50), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("branch_id", sa.String(36), sa.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="SET NULL")),
        sa.Column("consent_record_id", sa.String(36), sa.ForeignKey("consent_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_reference_hash", sa.String(64), nullable=False), sa.Column("loan_product_code", sa.String(60), nullable=False),
        sa.Column("status", sa.String(40), nullable=False), sa.Column("model_recommendation", sa.String(20)), sa.Column("risk_score_band", sa.String(20)),
        sa.Column("prediction_id", sa.String(40)), sa.Column("version", sa.Integer(), nullable=False), sa.Column("retention_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "application_number", name="uq_organization_application_number"))
    for column in ("application_number", "organization_id", "branch_id", "created_by", "assigned_to", "consent_record_id", "customer_reference_hash", "status", "prediction_id", "retention_expires_at", "created_at"):
        op.create_index(f"ix_loan_applications_{column}", "loan_applications", [column])
    op.create_index("ix_application_scope_status_created", "loan_applications", ["organization_id", "branch_id", "status", "created_at"])
    op.create_table("workflow_history",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("application_id", sa.String(36), sa.ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(40)), sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("changed_by", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason_code", sa.String(80)), sa.Column("safe_note", sa.String(500)), sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("application_id", "changed_by"): op.create_index(f"ix_workflow_history_{column}", "workflow_history", [column])
    op.create_index("ix_workflow_application_changed", "workflow_history", ["application_id", "changed_at"])
    op.create_table("decision_records",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("application_id", sa.String(36), sa.ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("officer_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False), sa.Column("model_recommendation", sa.String(20)), sa.Column("is_override", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.String(500)), sa.Column("note", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("application_id", "officer_id", "decision"): op.create_index(f"ix_decision_records_{column}", "decision_records", [column])
    op.create_table("crypto_parameter_profiles",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("profile_id", sa.String(80), nullable=False), sa.Column("scheme", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("parameters", sa.JSON(), nullable=False), sa.Column("artifact_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("profile_id"))
    op.create_index("ix_crypto_parameter_profiles_profile_id", "crypto_parameter_profiles", ["profile_id"]); op.create_index("ix_crypto_parameter_profiles_status", "crypto_parameter_profiles", ["status"])
    op.create_table("retention_policies",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_type", sa.String(60), nullable=False), sa.Column("retention_days", sa.Integer(), nullable=False), sa.Column("action", sa.String(30), nullable=False),
        sa.Column("legal_hold_required", sa.Boolean(), nullable=False), sa.Column("updated_by", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("organization_id", "record_type", name="uq_retention_organization_record_type"))
    op.create_index("ix_retention_policies_organization_id", "retention_policies", ["organization_id"])
    for column, foreign in (("application_id", "loan_applications.id"), ("organization_id", "organizations.id"), ("branch_id", "branches.id"), ("requested_by", "admin_users.id")):
        op.add_column("prediction_metadata", sa.Column(column, sa.String(36), nullable=True))
        op.create_foreign_key(f"fk_prediction_metadata_{column}", "prediction_metadata", foreign.split('.')[0], [column], ["id"], ondelete="SET NULL")
        op.create_index(f"ix_prediction_metadata_{column}", "prediction_metadata", [column])


def downgrade():
    for column in ("requested_by", "branch_id", "organization_id", "application_id"):
        op.drop_index(f"ix_prediction_metadata_{column}", table_name="prediction_metadata")
        op.drop_constraint(f"fk_prediction_metadata_{column}", "prediction_metadata", type_="foreignkey")
        op.drop_column("prediction_metadata", column)
    for table in ("retention_policies", "crypto_parameter_profiles", "decision_records", "workflow_history", "loan_applications", "consent_records", "organization_memberships", "branches", "organizations"):
        op.drop_table(table)
