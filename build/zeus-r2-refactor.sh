#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/backend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
REFACTOR: Replace Cloudflare R2 with Postgres BYTEA storage for PDFs

Sandy's constraint: no credit card required services. R2 needs a card. Store PDFs directly in Postgres (Neon) instead.

CHANGES NEEDED:

1. src/freightpipe/pipeline/ingest.py — REPLACE the R2 section (lines 99-166):
   - Remove: get_r2_client(), upload_to_r2(), generate_r2_key(), generate_split_r2_key(), get_signed_url()
   - Remove: import boto3, from botocore.config import Config as BotoConfig
   - The create_job() function should store pdf_data directly in the jobs table (column: pdf_data BYTEA)
   - Change source_r2_key to source_filename in the create_job call
   - Remove the R2 upload step and the source_r2_key update step

2. src/freightpipe/api/routes.py — UPDATE the PDF endpoint (lines 418-453):
   - GET /v1/documents/{document_id}/pdf should return the PDF data directly from the jobs table
   - Instead of generating a signed R2 URL, fetch pdf_data from the job row and return it as a Response with content_type=application/pdf
   - Also update the POST /v1/documents endpoint (around line 84) to use source_filename instead of r2_key

3. src/freightpipe/models/schemas.py — already updated (source_r2_key -> source_filename, r2_key removed from Document)

4. src/freightpipe/db/repos/jobs.py — UPDATE:
   - Change source_r2_key parameter to source_filename
   - Add pdf_data: bytes parameter to the create method
   - Update the INSERT query to include pdf_data column
   - Add a get_pdf_data(job_id) method to fetch just the PDF bytes

5. src/freightpipe/db/repos/documents.py — UPDATE:
   - Remove r2_key from the create method and INSERT query

6. src/freightpipe/pipeline/__init__.py — UPDATE:
   - Remove upload_to_r2 from exports

7. src/freightpipe/utils/config.py — already updated (R2 vars removed)

8. alembic/versions/ — ADD a new migration 002_replace_r2_with_bytea.py:
   - ALTER TABLE jobs ADD COLUMN pdf_data BYTEA
   - ALTER TABLE jobs RENAME COLUMN source_r2_key TO source_filename
   - ALTER TABLE documents DROP COLUMN r2_key

IMPORTANT: After making changes, run: python -m pytest tests/ -v --tb=short
Fix any test failures caused by the refactor. Tests that referenced r2_key or R2 must be updated.

Do NOT change any files outside of the ones listed above.
Do NOT add boto3 or any new dependencies.
" 2>&1 | tee /tmp/zeus-r2-refactor.log
