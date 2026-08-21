"""Add users table and link accounts to users.

Revision ID: 003_add_users
Revises: 002_replace_r2_with_bytea
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "003_add_users"
down_revision = "002_replace_r2_with_bytea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("phone", sa.Text()),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    op.add_column(
        "accounts",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("idx_accounts_user", "accounts", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_accounts_user", table_name="accounts")
    op.drop_column("accounts", "user_id")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
