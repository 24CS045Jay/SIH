"""Store RAG query and citation detail in audit events.

Revision ID: 0003_rag_audit_detail
Revises: 0002_upload_status
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_rag_audit_detail"
down_revision = "0002_upload_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    default_expr = sa.text("'{}'::json") if op.get_bind().dialect.name == "postgresql" else sa.text("'{}'")
    op.add_column("audit_events", sa.Column("detail", sa.JSON(), nullable=False, server_default=default_expr))
    op.alter_column("audit_events", "detail", server_default=None)


def downgrade() -> None:
    op.drop_column("audit_events", "detail")
