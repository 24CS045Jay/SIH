"""add structure-aware rag chunk metadata

Revision ID: 0006_rag_chunk_metadata
Revises: 0005_phase8_comparison_fields
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_rag_chunk_metadata"
down_revision = "0005_phase8_comparison_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("chunks", "embedding_ref", existing_type=sa.String(length=512), type_=sa.Text(), existing_nullable=True)
    op.add_column("chunks", sa.Column("section_number", sa.String(length=80), nullable=True))
    op.add_column("chunks", sa.Column("section_title", sa.String(length=300), nullable=True))
    op.add_column("chunks", sa.Column("subsection", sa.String(length=300), nullable=True))
    op.add_column("chunks", sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("chunks", sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("chunks", sa.Column("ocr_confidence", sa.Float(), nullable=True))
    op.add_column("chunks", sa.Column("parent_context", sa.Text(), nullable=True))
    op.create_index("ix_chunks_section_number", "chunks", ["section_number"])
    op.create_index("ix_chunks_section_title", "chunks", ["section_title"])
    op.create_index("ix_chunks_chunk_index", "chunks", ["chunk_index"])


def downgrade() -> None:
    op.drop_index("ix_chunks_chunk_index", table_name="chunks")
    op.drop_index("ix_chunks_section_title", table_name="chunks")
    op.drop_index("ix_chunks_section_number", table_name="chunks")
    op.drop_column("chunks", "parent_context")
    op.drop_column("chunks", "ocr_confidence")
    op.drop_column("chunks", "token_count")
    op.drop_column("chunks", "chunk_index")
    op.drop_column("chunks", "subsection")
    op.drop_column("chunks", "section_title")
    op.drop_column("chunks", "section_number")
    op.alter_column("chunks", "embedding_ref", existing_type=sa.Text(), type_=sa.String(length=512), existing_nullable=True)
