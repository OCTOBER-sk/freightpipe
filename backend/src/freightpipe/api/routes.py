"""FreightPipe API routes — all 18 endpoints from BACKEND.md §4.1."""
from fastapi import APIRouter

router = APIRouter(prefix="/v1")

# TODO: Implement all endpoints from BACKEND.md §4.1
# POST /documents, GET /jobs, GET /jobs/{id}, GET /jobs/{id}/result
# GET /review-queue, POST /review-queue/{id}/resolve
# GET /documents/{id}/pdf, POST /webhooks/test, GET /health
# GET/POST /api-keys, DELETE /api-keys/{id}
# GET/PUT /settings/webhook, GET /analytics/usage
