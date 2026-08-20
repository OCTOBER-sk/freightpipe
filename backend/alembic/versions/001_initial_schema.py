"""Initial schema — all 9 tables from BACKEND.md §3.1.

Revision ID: 001_initial
Revises:
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- accounts ---
    op.create_table(
        "accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("llm_byok_keys", JSONB(), server_default=sa.text("'{}'::jsonb")),
    )

    # --- api_keys ---
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_api_keys_account", "api_keys", ["account_id"])

    # --- jobs ---
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("idempotency_key", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("source_r2_key", sa.Text(), nullable=False),
        sa.Column("shipment_id", UUID(as_uuid=True)),
        sa.Column("webhook_url", sa.Text()),
        sa.Column("error", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("account_id", "idempotency_key", name="uq_jobs_account_idempotency"),
    )
    op.create_index("idx_jobs_account_status", "jobs", ["account_id", "status"])
    op.create_index("idx_jobs_shipment", "jobs", ["shipment_id"])

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.Text()),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("r2_key", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.Text()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("classification_confidence", sa.Numeric(4, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_documents_job", "documents", ["job_id"])

    # --- extracted_fields ---
    op.create_table(
        "extracted_fields",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("field_value", sa.Text()),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("source_page", sa.Integer()),
        sa.Column("source_bbox", JSONB()),
        sa.Column("extraction_method", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_extracted_fields_document", "extracted_fields", ["document_id"])
    op.create_index("idx_extracted_fields_name", "extracted_fields", ["field_name"])

    # --- match_results ---
    op.create_table(
        "match_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shipment_id", UUID(as_uuid=True), nullable=False),
        sa.Column("line_item", sa.Text(), nullable=False),
        sa.Column("rate_con_value", sa.Text()),
        sa.Column("bol_pod_value", sa.Text()),
        sa.Column("invoice_value", sa.Text()),
        sa.Column("discrepancy_flag", sa.Text()),
        sa.Column("discrepancy_amount", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_match_results_shipment", "match_results", ["shipment_id"])

    # --- review_queue ---
    op.create_table(
        "review_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("assigned_to", sa.Text()),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_review_queue_job", "review_queue", ["job_id"])
    op.create_index("idx_review_queue_state", "review_queue", ["state"])

    # --- llm_cache ---
    op.create_table(
        "llm_cache",
        sa.Column("cache_key", sa.Text(), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("response_json", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ttl_expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_llm_cache_ttl", "llm_cache", ["ttl_expires_at"])

    # --- provider_usage_log ---
    op.create_table(
        "provider_usage_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("provider", "model", "log_date", name="uq_provider_usage_log"),
    )


def downgrade() -> None:
    op.drop_table("provider_usage_log")
    op.drop_table("llm_cache")
    op.drop_table("review_queue")
    op.drop_table("match_results")
    op.drop_table("extracted_fields")
    op.drop_table("documents")
    op.drop_table("jobs")
    op.drop_table("api_keys")
    op.drop_table("accounts")
