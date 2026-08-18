"""Add upload pipeline statuses.

Revision ID: 0002_document_processing_statuses
Revises: 0001_phase1_baseline
"""
from alembic import op

revision = "0002_upload_status"
down_revision = "0001_phase1_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE versionstatus ADD VALUE IF NOT EXISTS 'queued' BEFORE 'processing'")
    op.execute("ALTER TYPE versionstatus ADD VALUE IF NOT EXISTS 'review_ready' AFTER 'ready'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values in place. These values are
    # intentionally retained on downgrade because existing rows may reference them.
    pass
