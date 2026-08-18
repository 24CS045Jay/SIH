"""Phase 8 comparison interpretation fields.

Revision ID: 0005_phase8_comparison_fields
Revises: 0004_phase7_workflows
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_phase8_comparison_fields"
down_revision = "0004_phase7_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("changes", sa.Column("interpretation", sa.Text(), nullable=False, server_default=""))
    op.add_column("changes", sa.Column("affected_department", sa.String(length=160), nullable=True))
    op.add_column("changes", sa.Column("priority", sa.Enum(name="actionpriority"), nullable=False, server_default="medium"))
    op.add_column("changes", sa.Column("required_action", sa.Text(), nullable=True))
    op.create_index("ix_changes_affected_department", "changes", ["affected_department"])
    op.create_index("ix_changes_priority", "changes", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_changes_priority", table_name="changes")
    op.drop_index("ix_changes_affected_department", table_name="changes")
    op.drop_column("changes", "required_action")
    op.drop_column("changes", "priority")
    op.drop_column("changes", "affected_department")
    op.drop_column("changes", "interpretation")
