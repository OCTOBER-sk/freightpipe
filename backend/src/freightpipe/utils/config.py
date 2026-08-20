"""Configuration from environment variables."""
import os

NEON_DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "freightpipe-docs")
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
LLM_DAILY_BUDGET_SOFT_CEILING_PCT = int(os.environ.get("LLM_DAILY_BUDGET_SOFT_CEILING_PCT", "90"))
JOB_RETRY_MAX_ATTEMPTS = int(os.environ.get("JOB_RETRY_MAX_ATTEMPTS", "3"))
