"""Tests for database repository CRUD operations (mocked asyncpg)."""
from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from freightpipe.db.repos import (
    accounts,
    api_keys,
    documents,
    extracted_fields,
    jobs,
    llm_cache,
    match_results,
    provider_usage_log,
    review_queue,
)


def _mock_conn(return_val=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=return_val)
    conn.fetch = AsyncMock(return_value=[return_val] if return_val else [])
    conn.execute = AsyncMock(return_value="DELETE 1")
    return conn


class TestAccountsRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "name": "Acme"}
        conn = _mock_conn(rec)
        result = await accounts.create(conn, name="Acme")
        conn.fetchrow.assert_awaited_once()
        assert result["name"] == "Acme"

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        aid = uuid4()
        rec = {"id": aid, "name": "Acme"}
        conn = _mock_conn(rec)
        result = await accounts.get_by_id(conn, aid)
        conn.fetchrow.assert_awaited_once()
        assert result["id"] == aid

    @pytest.mark.asyncio
    async def test_update_byok_keys(self):
        aid = uuid4()
        rec = {"id": aid, "llm_byok_keys": {"gemini": "key"}}
        conn = _mock_conn(rec)
        result = await accounts.update_byok_keys(conn, aid, {"gemini": "key"})
        conn.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete(self):
        conn = _mock_conn()
        conn.execute = AsyncMock(return_value="DELETE 1")
        result = await accounts.delete(conn, uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_list_all(self):
        rec = {"id": uuid4(), "name": "Acme"}
        conn = _mock_conn(rec)
        result = await accounts.list_all(conn, limit=10)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)


class TestApiKeysRepo:
    def test_hash_key(self):
        h = api_keys.hash_key("test-key")
        assert len(h) == 64
        assert h == api_keys.hash_key("test-key")

    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "key_hash": "abc123"}
        conn = _mock_conn(rec)
        result = await api_keys.create(conn, account_id=uuid4(), key_hash="abc123", label="prod")
        conn.fetchrow.assert_awaited_once()
        assert result["key_hash"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_by_hash(self):
        rec = {"id": uuid4(), "key_hash": "sha256hash"}
        conn = _mock_conn(rec)
        result = await api_keys.get_by_hash(conn, "sha256hash")
        conn.fetchrow.assert_awaited_once()
        assert result["key_hash"] == "sha256hash"

    @pytest.mark.asyncio
    async def test_list_by_account(self):
        aid = uuid4()
        rec = {"id": uuid4(), "account_id": aid}
        conn = _mock_conn(rec)
        result = await api_keys.list_by_account(conn, aid)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_revoke(self):
        kid = uuid4()
        rec = {"id": kid, "revoked_at": datetime.utcnow()}
        conn = _mock_conn(rec)
        result = await api_keys.revoke(conn, kid)
        conn.fetchrow.assert_awaited_once()
        assert result["revoked_at"] is not None


class TestJobsRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "status": "queued"}
        conn = _mock_conn(rec)
        result = await jobs.create(conn, account_id=uuid4(), source_filename="test.pdf", pdf_data=b"%PDF-1.4 test")
        conn.fetchrow.assert_awaited_once()
        assert result["status"] == "queued"

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        jid = uuid4()
        rec = {"id": jid}
        conn = _mock_conn(rec)
        result = await jobs.get_by_id(conn, jid)
        assert result["id"] == jid

    @pytest.mark.asyncio
    async def test_get_by_idempotency_key(self):
        aid, jid = uuid4(), uuid4()
        rec = {"id": jid, "account_id": aid, "idempotency_key": "idem-1"}
        conn = _mock_conn(rec)
        result = await jobs.get_by_idempotency_key(conn, aid, "idem-1")
        assert result["idempotency_key"] == "idem-1"

    @pytest.mark.asyncio
    async def test_update_status(self):
        jid = uuid4()
        rec = {"id": jid, "status": "complete", "completed_at": datetime.utcnow()}
        conn = _mock_conn(rec)
        result = await jobs.update_status(conn, jid, "complete")
        conn.fetchrow.assert_awaited_once()
        assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_list_paginated(self):
        aid = uuid4()
        rec = {"id": uuid4(), "account_id": aid, "status": "queued"}
        conn = _mock_conn(rec)
        result = await jobs.list_paginated(conn, aid, status="queued", limit=10)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_by_account_with_cursor(self):
        aid = uuid4()
        rec = {"id": uuid4(), "account_id": aid}
        conn = _mock_conn(rec)
        cursor = datetime.utcnow().isoformat()
        result = await jobs.list_by_account(conn, aid, cursor=cursor)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)


class TestDocumentsRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "doc_type": "rate_con"}
        conn = _mock_conn(rec)
        result = await documents.create(
            conn, job_id=uuid4(), page_start=1, page_end=1
        )
        conn.fetchrow.assert_awaited_once()
        assert result["doc_type"] == "rate_con"

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        did = uuid4()
        rec = {"id": did}
        conn = _mock_conn(rec)
        result = await documents.get_by_id(conn, did)
        assert result["id"] == did

    @pytest.mark.asyncio
    async def test_list_by_job(self):
        jid = uuid4()
        rec = {"id": uuid4(), "job_id": jid, "page_start": 1}
        conn = _mock_conn(rec)
        result = await documents.list_by_job(conn, jid)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_count_by_job(self):
        rec = {"cnt": 3}
        conn = _mock_conn(rec)
        result = await documents.count_by_job(conn, uuid4())
        assert result == 3


class TestExtractedFieldsRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "field_name": "linehaul_rate", "confidence": 0.95}
        conn = _mock_conn(rec)
        result = await extracted_fields.create(
            conn, document_id=uuid4(), field_name="linehaul_rate", confidence=0.95
        )
        conn.fetchrow.assert_awaited_once()
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_create_many(self):
        doc_id = uuid4()
        rec1 = {"id": uuid4(), "field_name": "load_number", "confidence": 0.97}
        rec2 = {"id": uuid4(), "field_name": "linehaul_rate", "confidence": 0.94}
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=[rec1, rec2])
        fields = [
            {"document_id": doc_id, "field_name": "load_number", "confidence": 0.97, "field_value": "RC-123"},
            {"document_id": doc_id, "field_name": "linehaul_rate", "confidence": 0.94, "field_value": "1850.00"},
        ]
        result = await extracted_fields.create_many(conn, fields)
        assert len(result) == 2
        assert conn.fetchrow.await_count == 2

    @pytest.mark.asyncio
    async def test_get_by_document_id(self):
        doc_id = uuid4()
        rec = {"id": uuid4(), "document_id": doc_id, "field_name": "weight"}
        conn = _mock_conn(rec)
        result = await extracted_fields.get_by_document_id(conn, doc_id)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_by_document(self):
        doc_id = uuid4()
        rec = {"id": uuid4(), "document_id": doc_id}
        conn = _mock_conn(rec)
        result = await extracted_fields.list_by_document(conn, doc_id)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)


class TestMatchResultsRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "line_item": "linehaul", "discrepancy_flag": "none"}
        conn = _mock_conn(rec)
        result = await match_results.create(conn, shipment_id=uuid4(), line_item="linehaul")
        conn.fetchrow.assert_awaited_once()
        assert result["discrepancy_flag"] == "none"

    @pytest.mark.asyncio
    async def test_create_many(self):
        sid = uuid4()
        rec1 = {"id": uuid4(), "line_item": "linehaul", "discrepancy_flag": "rate_delta"}
        rec2 = {"id": uuid4(), "line_item": "fuel_surcharge", "discrepancy_flag": "none"}
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(side_effect=[rec1, rec2])
        results = [
            {"shipment_id": sid, "line_item": "linehaul", "discrepancy_flag": "rate_delta"},
            {"shipment_id": sid, "line_item": "fuel_surcharge"},
        ]
        out = await match_results.create_many(conn, results)
        assert len(out) == 2
        assert conn.fetchrow.await_count == 2

    @pytest.mark.asyncio
    async def test_get_by_shipment_id(self):
        sid = uuid4()
        rec = {"id": uuid4(), "shipment_id": sid, "line_item": "detention"}
        conn = _mock_conn(rec)
        result = await match_results.get_by_shipment_id(conn, sid)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_by_shipment(self):
        sid = uuid4()
        rec = {"id": uuid4(), "shipment_id": sid}
        conn = _mock_conn(rec)
        result = await match_results.list_by_shipment(conn, sid)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)


class TestReviewQueueRepo:
    @pytest.mark.asyncio
    async def test_create(self):
        rec = {"id": uuid4(), "reason": "low_confidence", "state": "pending"}
        conn = _mock_conn(rec)
        result = await review_queue.create(conn, job_id=uuid4(), reason="low_confidence")
        conn.fetchrow.assert_awaited_once()
        assert result["state"] == "pending"

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        rid = uuid4()
        rec = {"id": rid}
        conn = _mock_conn(rec)
        result = await review_queue.get_by_id(conn, rid)
        assert result["id"] == rid

    @pytest.mark.asyncio
    async def test_list_paginated_with_state(self):
        rec = {"id": uuid4(), "state": "pending"}
        conn = _mock_conn(rec)
        result = await review_queue.list_paginated(conn, state="pending", limit=10)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_paginated_with_reason(self):
        rec = {"id": uuid4(), "reason": "discrepancy"}
        conn = _mock_conn(rec)
        result = await review_queue.list_paginated(conn, reason="discrepancy", limit=10)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_resolve_approved(self):
        rid = uuid4()
        rec = {"id": rid, "state": "resolved", "resolved_at": datetime.utcnow()}
        conn = _mock_conn(rec)
        result = await review_queue.resolve(conn, rid, resolution="approved")
        conn.fetchrow.assert_awaited_once()
        assert result["state"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_escalated(self):
        rid = uuid4()
        rec = {"id": rid, "state": "escalated", "resolved_at": datetime.utcnow()}
        conn = _mock_conn(rec)
        result = await review_queue.resolve(conn, rid, resolution="escalated")
        conn.fetchrow.assert_awaited_once()
        assert result["state"] == "escalated"

    @pytest.mark.asyncio
    async def test_list_by_state(self):
        rec = {"id": uuid4(), "state": "pending"}
        conn = _mock_conn(rec)
        result = await review_queue.list_by_state(conn, state="pending")
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)


class TestLlmCacheRepo:
    @pytest.mark.asyncio
    async def test_get_by_key(self):
        rec = {"cache_key": "abc", "response_json": {"text": "hello"}}
        conn = _mock_conn(rec)
        result = await llm_cache.get(conn, "abc")
        assert result["cache_key"] == "abc"

    @pytest.mark.asyncio
    async def test_set(self):
        rec = {"cache_key": "abc", "provider": "openrouter", "model": "llama"}
        conn = _mock_conn(rec)
        result = await llm_cache.set(
            conn, cache_key="abc", provider="openrouter",
            model="llama", response_json={"text": "hi"}
        )
        conn.fetchrow.assert_awaited_once()
        assert result["provider"] == "openrouter"

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 5")
        result = await llm_cache.cleanup_expired(conn)
        conn.execute.assert_awaited_once()
        assert result == "DELETE 5"

    @pytest.mark.asyncio
    async def test_delete_expired(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 3")
        result = await llm_cache.delete_expired(conn)
        conn.execute.assert_awaited_once()
        assert "3" in result

    @pytest.mark.asyncio
    async def test_count(self):
        rec = {"cnt": 42}
        conn = _mock_conn(rec)
        result = await llm_cache.count(conn)
        assert result == 42


class TestProviderUsageLogRepo:
    @pytest.mark.asyncio
    async def test_increment(self):
        rec = {"provider": "openrouter", "model": "llama", "request_count": 1}
        conn = _mock_conn(rec)
        result = await provider_usage_log.increment(conn, provider="openrouter", model="llama")
        conn.fetchrow.assert_awaited_once()
        assert result["request_count"] == 1

    @pytest.mark.asyncio
    async def test_increment_cache_hit(self):
        rec = {"provider": "gemini", "model": "flash", "request_count": 1, "cache_hit_count": 1}
        conn = _mock_conn(rec)
        result = await provider_usage_log.increment(
            conn, provider="gemini", model="flash", is_cache_hit=True
        )
        conn.fetchrow.assert_awaited_once()
        assert result["cache_hit_count"] == 1

    @pytest.mark.asyncio
    async def test_get_by_date_range(self):
        rec = {"provider": "groq", "model": "llama", "log_date": date.today()}
        conn = _mock_conn(rec)
        start = date.today() - timedelta(days=7)
        result = await provider_usage_log.get_by_date_range(
            conn, start_date=start, end_date=date.today()
        )
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_total_requests_today(self):
        rec = {"total": 100}
        conn = _mock_conn(rec)
        result = await provider_usage_log.get_total_requests_today(conn, provider="openrouter")
        assert result == 100

    @pytest.mark.asyncio
    async def test_get_daily_totals(self):
        rec = {"provider": "openrouter", "request_count": 50}
        conn = _mock_conn(rec)
        result = await provider_usage_log.get_daily_totals(conn)
        conn.fetch.assert_awaited_once()
        assert isinstance(result, list)
