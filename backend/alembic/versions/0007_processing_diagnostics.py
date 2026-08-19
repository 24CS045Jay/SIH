"""add document processing diagnostics

Revision ID: 0007_processing_diagnostics
Revises: 0006_rag_chunk_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_processing_diagnostics"
down_revision = "0006_rag_chunk_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_versions", sa.Column("processing_stage", sa.String(length=40), nullable=False, server_default="queued"))
    op.add_column("document_versions", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_index("ix_document_versions_processing_stage", "document_versions", ["processing_stage"])


def downgrade() -> None:
    op.drop_index("ix_document_versions_processing_stage", table_name="document_versions")
    op.drop_column("document_versions", "error_message")
    op.drop_column("document_versions", "processing_stage")
