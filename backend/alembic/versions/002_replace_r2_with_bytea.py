"""Replace R2 with BYTEA storage for PDFs.

Revision ID: 002_replace_r2_with_bytea
Revises: 001_initial
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002_replace_r2_with_bytea"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pdf_data BYTEA column to jobs
    op.add_column("jobs", sa.Column("pdf_data", sa.LargeBinary()))

    # Rename source_r2_key to source_filename in jobs
    op.alter_column("jobs", "source_r2_key", new_column_name="source_filename")

    # Drop r2_key from documents
    op.drop_column("documents", "r2_key")


def downgrade() -> None:
    # Restore r2_key to documents
    op.add_column("documents", sa.Column("r2_key", sa.Text(), nullable=False, server_default=""))

    # Rename source_filename back to source_r2_key in jobs
    op.alter_column("jobs", "source_filename", new_column_name="source_r2_key")

    # Remove pdf_data from jobs
    op.drop_column("jobs", "pdf_data")
