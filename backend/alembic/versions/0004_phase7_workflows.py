"""Phase 7 alert and action workflow fields.

Revision ID: 0004_phase7_workflows
Revises: 0003_rag_audit_detail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_phase7_workflows"
down_revision = "0003_rag_audit_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for value in ["draft", "open", "blocked", "overdue", "closed", "rejected"]:
            op.execute(f"ALTER TYPE actionstatus ADD VALUE IF NOT EXISTS '{value}'")
        alert_status = postgresql.ENUM("draft", "needs_review", "approved", "assigned", "acknowledged", "in_progress", "completed", "verified_closed", "rejected", name="alertstatus")
        alert_status.create(bind, checkfirst=True)
        reviewer_col = sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True)
        status_col = sa.Column("status", sa.Enum(name="alertstatus"), nullable=False, server_default="draft")
        verified_by_col = sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True)
    else:
        reviewer_col = sa.Column("reviewer_id", sa.Uuid(), nullable=True)
        status_col = sa.Column("status", sa.String(50), nullable=False, server_default="draft")
        verified_by_col = sa.Column("verified_by", sa.Uuid(), nullable=True)

    op.add_column("alerts", sa.Column("title", sa.String(length=500), nullable=False, server_default="AI-generated alert"))
    op.add_column("alerts", sa.Column("suggested_department", sa.String(length=160), nullable=True))
    op.add_column("alerts", sa.Column("suggested_action", sa.Text(), nullable=True))
    op.add_column("alerts", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("source_excerpt", sa.Text(), nullable=True))
    op.add_column("alerts", reviewer_col)
    op.add_column("alerts", status_col)
    op.create_foreign_key("fk_alerts_reviewer_id_users", "alerts", "users", ["reviewer_id"], ["id"], ondelete="SET NULL")
    for table, column in [("alerts", "suggested_department"), ("alerts", "deadline"), ("alerts", "reviewer_id"), ("alerts", "status")]:
        op.create_index(f"ix_{table}_{column}", table, [column])
    op.add_column("actions", sa.Column("comments", sa.Text(), nullable=False, server_default=""))
    op.add_column("actions", sa.Column("completion_evidence", sa.Text(), nullable=True))
    op.add_column("actions", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("actions", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("actions", verified_by_col)
    op.add_column("actions", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_actions_verified_by_users", "actions", "users", ["verified_by"], ["id"], ondelete="SET NULL")
    for column in ["acknowledged_at", "completed_at", "verified_by", "verified_at"]:
        op.create_index(f"ix_actions_{column}", "actions", [column])


def downgrade() -> None:
    for column in ["verified_at", "verified_by", "completed_at", "acknowledged_at", "completion_evidence", "comments"]:
        op.drop_column("actions", column)
    op.drop_constraint("fk_alerts_reviewer_id_users", "alerts", type_="foreignkey")
    for column in ["status", "reviewer_id", "deadline", "suggested_department"]:
        op.drop_column("alerts", column)
    for column in ["source_excerpt", "suggested_action", "title"]:
        op.drop_column("alerts", column)
    op.execute("DROP TYPE IF EXISTS alertstatus")
