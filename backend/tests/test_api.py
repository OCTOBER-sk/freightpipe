"""Tests for FreightPipe API routes — 20+ test cases covering all endpoints."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from freightpipe.api.auth import get_account_id
from freightpipe.api.routes import router
from freightpipe.api.rate_limit import _windows as rate_limit_windows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_API_KEY = "fp_live_test_key_12345"
TEST_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()
TEST_ACCOUNT_ID = uuid4()


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


class FakeRecord(dict):
    """Dict that supports attribute access like asyncpg.Record."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def _record(d: dict) -> FakeRecord:
    return FakeRecord(d)


class _CtxMgr:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_rate_limits():
    rate_limit_windows.clear()
    yield
    rate_limit_windows.clear()


@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Api-Key": TEST_API_KEY}


def _override_auth(app):
    """Override the get_account_id dependency to return TEST_ACCOUNT_ID."""
    async def _fake_auth():
        return TEST_ACCOUNT_ID
    app.dependency_overrides[get_account_id] = _fake_auth


def _make_mock_pool(conn):
    pool = MagicMock()
    pool.acquire.return_value = _CtxMgr(conn)
    return pool


# ---------------------------------------------------------------------------
# 1. Health check (unauthenticated)
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["worker"] == "ok"
        assert data["processor"] == "ok"


# ---------------------------------------------------------------------------
# 2-4. Auth tests
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_api_key_returns_401(self, client):
        resp = client.get("/v1/jobs")
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["error"]["code"] == "unauthorized"

    def test_invalid_api_key_returns_401(self, client):
        with patch("freightpipe.api.auth.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers={"X-Api-Key": "bad_key"})
            assert resp.status_code == 401

    def test_valid_api_key_passes_auth(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs", headers=auth_headers)
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5-6. POST /v1/documents
# ---------------------------------------------------------------------------

class TestSubmitDocument:
    def _minimal_pdf(self):
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"

    def test_submit_pdf_returns_202(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                "status": "queued", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": None,
            }))
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post(
                "/v1/documents",
                headers=auth_headers,
                files={"file": ("test.pdf", self._minimal_pdf(), "application/pdf")},
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert data["status"] == "queued"
        assert "created_at" in data

    def test_submit_invalid_pdf_returns_400(self, app, client, auth_headers):
        _override_auth(app)
        resp = client.post(
            "/v1/documents",
            headers=auth_headers,
            files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"]["code"] == "invalid_pdf"

    def test_submit_oversized_pdf_returns_413(self, app, client, auth_headers):
        _override_auth(app)
        big_content = b"%PDF" + b"x" * (26 * 1024 * 1024)
        resp = client.post(
            "/v1/documents",
            headers=auth_headers,
            files={"file": ("big.pdf", big_content, "application/pdf")},
        )
        assert resp.status_code == 413
        data = resp.json()
        assert data["detail"]["error"]["code"] == "file_too_large"

    def test_idempotent_replay_returns_existing_job(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        idem_key = "test-idem-key-123"

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID,
                "idempotency_key": idem_key, "status": "complete",
                "source_r2_key": "uploads/test.pdf", "shipment_id": None,
                "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.post(
                "/v1/documents",
                headers={**auth_headers, "Idempotency-Key": idem_key},
                files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert data["idempotent_replay"] is True


# ---------------------------------------------------------------------------
# 7-8. GET /v1/jobs
# ---------------------------------------------------------------------------

class TestListJobs:
    def test_list_jobs_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)
        job_id = uuid4()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool, \
             patch("freightpipe.api.routes._doc_count", return_value=0), \
             patch("freightpipe.api.routes._review_items_for_job", return_value=[]):
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[
                _record({
                    "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                    "status": "complete", "source_r2_key": "uploads/test.pdf",
                    "shipment_id": None, "webhook_url": None, "error": None,
                    "created_at": now, "updated_at": now, "completed_at": now,
                })
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.get("/v1/jobs", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "next_cursor" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["job_id"] == str(job_id)

    def test_list_jobs_with_status_filter(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/jobs?status=complete", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_jobs_pagination_cursor(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)
        cursor = now.isoformat()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs?cursor={cursor}&limit=10", headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 9. GET /v1/jobs/{job_id}
# ---------------------------------------------------------------------------

class TestGetJob:
    def test_get_job_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                "status": "complete", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": now,
            }))
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)

            resp = client.get(f"/v1/jobs/{job_id}", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert data["status"] == "complete"

    def test_get_job_not_found_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["error"]["code"] == "job_not_found"

    def test_get_job_wrong_account_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        other_account = uuid4()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": other_account, "idempotency_key": None,
                "status": "complete", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 10. GET /v1/jobs/{job_id}/result
# ---------------------------------------------------------------------------

class TestGetJobResult:
    def test_result_not_complete_returns_409(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                "status": "extracting", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": None,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs/{job_id}/result", headers=auth_headers)
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error"]["code"] == "job_not_complete"

    def test_result_complete_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        job_id = uuid4()
        doc_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool, \
             patch("freightpipe.api.routes._review_items_for_job", return_value=[]):
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                "status": "complete", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": now,
            }))
            # Return documents for list_by_job, empty for extracted_fields and match_results
            call_count = {"n": 0}
            doc_record = _record({
                "id": doc_id, "job_id": job_id, "doc_type": "rate_con",
                "page_start": 1, "page_end": 1, "r2_key": "docs/test.pdf",
                "extraction_method": "text", "raw_text": None,
                "classification_confidence": 0.95, "created_at": now,
            })

            async def mock_fetch(query, *args):
                call_count["n"] += 1
                if "documents" in query:
                    return [doc_record]
                return []

            conn.fetch = mock_fetch
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs/{job_id}/result", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert "documents" in data
        assert "match_results" in data


# ---------------------------------------------------------------------------
# 11. GET /v1/review-queue
# ---------------------------------------------------------------------------

class TestReviewQueue:
    def test_list_review_queue_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)
        item_id = uuid4()
        job_id = uuid4()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[
                _record({
                    "id": item_id, "job_id": job_id, "reason": "low_confidence",
                    "state": "pending", "assigned_to": None, "resolution_notes": None,
                    "created_at": now, "resolved_at": None,
                })
            ])
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                "status": "needs_review", "source_r2_key": "uploads/test.pdf",
                "shipment_id": None, "webhook_url": None, "error": None,
                "created_at": now, "updated_at": now, "completed_at": now,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/review-queue", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "next_cursor" in data


# ---------------------------------------------------------------------------
# 12. POST /v1/review-queue/{item_id}/resolve
# ---------------------------------------------------------------------------

class TestResolveReview:
    def test_resolve_approved_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        item_id = uuid4()
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(side_effect=[
                _record({"id": item_id, "job_id": job_id, "reason": "low_confidence",
                         "state": "pending", "assigned_to": None, "resolution_notes": None,
                         "created_at": now, "resolved_at": None}),
                _record({"id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                         "status": "needs_review", "source_r2_key": "uploads/test.pdf",
                         "shipment_id": None, "webhook_url": None, "error": None,
                         "created_at": now, "updated_at": now, "completed_at": now}),
                _record({"id": item_id, "job_id": job_id, "reason": "low_confidence",
                         "state": "resolved", "assigned_to": None, "resolution_notes": "looks good",
                         "created_at": now, "resolved_at": now}),
                _record({"id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                         "status": "complete", "source_r2_key": "uploads/test.pdf",
                         "shipment_id": None, "webhook_url": None, "error": None,
                         "created_at": now, "updated_at": now, "completed_at": now}),
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.post(
                f"/v1/review-queue/{item_id}/resolve",
                headers=auth_headers,
                json={"resolution": "approved", "notes": "looks good"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "resolved"

    def test_resolve_not_found_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.post(
                f"/v1/review-queue/{uuid4()}/resolve",
                headers=auth_headers,
                json={"resolution": "approved"},
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 13. GET /v1/documents/{document_id}/pdf
# ---------------------------------------------------------------------------

class TestDocumentPdf:
    def test_get_pdf_url_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        doc_id = uuid4()
        job_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(side_effect=[
                _record({"id": doc_id, "job_id": job_id, "doc_type": "rate_con",
                         "page_start": 1, "page_end": 1, "r2_key": "docs/test.pdf",
                         "extraction_method": "text", "raw_text": None,
                         "classification_confidence": 0.95, "created_at": now}),
                _record({"id": job_id, "account_id": TEST_ACCOUNT_ID, "idempotency_key": None,
                         "status": "complete", "source_r2_key": "uploads/test.pdf",
                         "shipment_id": None, "webhook_url": None, "error": None,
                         "created_at": now, "updated_at": now, "completed_at": now}),
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/documents/{doc_id}/pdf", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert data["expires_in"] == 300

    def test_get_pdf_not_found_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/documents/{uuid4()}/pdf", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 14. POST /v1/webhooks/test
# ---------------------------------------------------------------------------

class TestWebhookTest:
    def test_webhook_test_returns_result(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.test_webhook") as mock_test:
            mock_test.return_value = {"delivered": True, "status_code": 200}
            resp = client.post(
                "/v1/webhooks/test",
                headers=auth_headers,
                json={"webhook_url": "https://example.com/hook"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["delivered"] is True

    def test_webhook_test_missing_url_returns_400(self, app, client, auth_headers):
        _override_auth(app)
        resp = client.post(
            "/v1/webhooks/test",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 15-16. API keys CRUD
# ---------------------------------------------------------------------------

class TestApiKeys:
    def test_list_api_keys_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)
        key_id = uuid4()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[
                _record({"id": key_id, "account_id": TEST_ACCOUNT_ID,
                         "key_hash": "abc123", "label": "Production",
                         "created_at": now, "revoked_at": None})
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/api-keys", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["key_prefix"] == "fp_live_abc1"

    def test_create_api_key_returns_201(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)
        key_id = uuid4()

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": key_id, "account_id": TEST_ACCOUNT_ID,
                "key_hash": "hash", "label": "Test",
                "created_at": now, "revoked_at": None,
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.post(
                "/v1/api-keys",
                headers=auth_headers,
                json={"label": "Test"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "key" in data
        assert data["key"].startswith("fp_live_")
        assert data["label"] == "Test"

    def test_revoke_api_key_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        key_id = uuid4()
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(side_effect=[
                _record({"id": key_id, "account_id": TEST_ACCOUNT_ID,
                         "key_hash": "hash", "label": "Test",
                         "created_at": now, "revoked_at": None}),
                _record({"id": key_id, "account_id": TEST_ACCOUNT_ID,
                         "key_hash": "hash", "label": "Test",
                         "created_at": now, "revoked_at": now}),
            ])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.delete(f"/v1/api-keys/{key_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(key_id)
        assert data["revoked_at"] is not None

    def test_revoke_api_key_not_found_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.delete(f"/v1/api-keys/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 17-18. Webhook settings
# ---------------------------------------------------------------------------

class TestWebhookSettings:
    def test_get_webhook_settings_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_ACCOUNT_ID, "name": "Test Account",
                "created_at": now,
                "llm_byok_keys": {"webhook_url": "https://example.com/hook", "webhook_secret": "whsec_abc"},
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/settings/webhook", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["webhook_url"] == "https://example.com/hook"

    def test_get_webhook_settings_not_configured_returns_404(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_ACCOUNT_ID, "name": "Test Account",
                "created_at": now, "llm_byok_keys": {},
            }))
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/settings/webhook", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_webhook_settings_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        now = datetime.now(timezone.utc)

        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=_record({
                "id": TEST_ACCOUNT_ID, "name": "Test Account",
                "created_at": now, "llm_byok_keys": {},
            }))
            conn.execute = AsyncMock(return_value="UPDATE 1")
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.put(
                "/v1/settings/webhook",
                headers=auth_headers,
                json={"webhook_url": "https://example.com/new-hook"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["webhook_url"] == "https://example.com/new-hook"
        assert "webhook_secret" in data


# ---------------------------------------------------------------------------
# 19. Analytics usage
# ---------------------------------------------------------------------------

class TestAnalyticsUsage:
    def test_usage_returns_200(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetch = AsyncMock(return_value=[])
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get("/v1/analytics/usage?period=30d", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "30d"
        assert "jobs" in data
        assert "llm_usage" in data


# ---------------------------------------------------------------------------
# 20. Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_exceeded_returns_429(self, app, client, auth_headers):
        _override_auth(app)
        from freightpipe.api import rate_limit as rl_module

        for _ in range(60):
            rl_module._windows[TEST_ACCOUNT_ID].append(
                datetime.now(timezone.utc).timestamp()
            )

        resp = client.post(
            "/v1/documents",
            headers=auth_headers,
            files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["detail"]["error"]["code"] == "rate_limited"


# ---------------------------------------------------------------------------
# 21. Error envelope format
# ---------------------------------------------------------------------------

class TestErrorEnvelope:
    def test_error_envelope_has_correct_structure(self, app, client, auth_headers):
        _override_auth(app)
        with patch("freightpipe.api.routes.get_pool") as mock_get_pool:
            conn = MagicMock()
            conn.fetchrow = AsyncMock(return_value=None)
            mock_get_pool.return_value = _make_mock_pool(conn)
            resp = client.get(f"/v1/jobs/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        error = detail["error"]
        assert "code" in error
        assert "message" in error
        assert "request_id" in error
        assert error["code"] == "job_not_found"
