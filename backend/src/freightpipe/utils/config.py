"""Configuration from environment variables."""
import os

NEON_DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
LLM_DAILY_BUDGET_SOFT_CEILING_PCT = int(os.environ.get("LLM_DAILY_BUDGET_SOFT_CEILING_PCT", "90"))
JOB_RETRY_MAX_ATTEMPTS = int(os.environ.get("JOB_RETRY_MAX_ATTEMPTS", "3"))
