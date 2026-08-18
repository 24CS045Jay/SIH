"""Create the complete CHA-225 Phase 2 relational schema.

Revision ID: 0001_phase1_baseline
Revises:
"""
from alembic import op

from app.models import Base

revision = "0001_phase1_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The ORM metadata is the single schema contract for this initial revision.
    # It includes PostgreSQL enums, foreign keys, uniqueness rules, and indexes.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
