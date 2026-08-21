"""Shared test fixtures for FreightPipe backend tests."""
from __future__ import annotations

import io
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("OPENROUTER_API_KEYS", "or-key-1,or-key-2")
    monkeypatch.setenv("GEMINI_API_KEYS", "gem-key-1")
    monkeypatch.setenv("GROQ_API_KEYS", "groq-key-1")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "25")
    monkeypatch.setenv("LLM_DAILY_BUDGET_SOFT_CEILING_PCT", "90")


# ---------------------------------------------------------------------------
# UUID fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def job_id():
    return uuid4()


@pytest.fixture
def document_id():
    return uuid4()


@pytest.fixture
def shipment_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Mock asyncpg connection
# ---------------------------------------------------------------------------

class MockConnection:
    """Mock asyncpg.Connection for unit testing repos."""

    def __init__(self):
        self._records: dict[str, list] = {}
        self._queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query: str, *args):
        self._queries.append((query, args))
        return None

    async def fetch(self, query: str, *args):
        self._queries.append((query, args))
        return []

    async def execute(self, query: str, *args):
        self._queries.append((query, args))
        return "SELECT 0"


@pytest.fixture
def mock_conn():
    return MockConnection()


# ---------------------------------------------------------------------------
# Mock asyncpg pool
# ---------------------------------------------------------------------------

class MockPool:
    """Mock asyncpg.Pool that yields MockConnections."""

    def __init__(self):
        self.conn = MockConnection()

    def acquire(self):
        return self

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        pass

    async def close(self):
        pass


@pytest.fixture
def mock_pool():
    return MockPool()


# ---------------------------------------------------------------------------
# PDF fixtures
# ---------------------------------------------------------------------------

def make_minimal_pdf(pages: int = 1, text: str = "Test document") -> bytes:
    """Create a minimal valid PDF for testing."""
    objects = []
    obj_num = 1

    catalog_num = obj_num
    objects.append(f"{catalog_num} 0 obj\n<< /Type /Catalog /Pages {catalog_num + 1} 0 R >>\nendobj")
    obj_num += 1

    pages_num = obj_num
    page_refs = " ".join(f"{obj_num + i + 1} 0 R" for i in range(pages))
    objects.append(f"{pages_num} 0 obj\n<< /Type /Pages /Kids [{page_refs}] /Count {pages} >>\nendobj")
    obj_num += 1

    for i in range(pages):
        page_num = obj_num
        content_num = obj_num + 1
        stream_content = f"BT /F1 12 Tf 100 700 Td ({text} - Page {i + 1}) Tj ET"
        objects.append(
            f"{content_num} 0 obj\n<< /Length {len(stream_content)} >>\nstream\n{stream_content}\nendstream\nendobj"
        )
        objects.append(
            f"{page_num} 0 obj\n<< /Type /Page /Parent {pages_num} 0 R "
            f"/MediaBox [0 0 612 792] /Contents {content_num} 0 R "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj"
        )
        obj_num += 2

    header = "%PDF-1.4\n"
    body = "\n".join(objects)
    xref_offset = len(header.encode()) + len(body.encode())
    xref = f"xref\n0 {obj_num}\n"
    xref += "0000000000 65535 f \n"
    for i in range(1, obj_num):
        xref += f"{xref_offset:010d} 00000 n \n"
    trailer = f"trailer\n<< /Size {obj_num} /Root {catalog_num} 0 R >>\nstartxref\n0\n%%EOF"
    return (header + body + "\n" + xref + trailer).encode()


@pytest.fixture
def sample_rate_con_text():
    return """
    RATE CONFIRMATION
    Load #: RC-48213
    Broker: ABC Freight Brokerage
    Carrier: XYZ Transport Inc.
    Shipper: Acme Corp, 123 Industrial Blvd, Chicago IL
    Consignee: Widget Co, 456 Commerce Dr, Dallas TX
    Pickup: 2026-08-22, 8:00 AM - 12:00 PM
    Delivery: 2026-08-24, 8:00 AM - 5:00 PM
    Linehaul Rate: $1,850.00
    Fuel Surcharge: $275.00
    Total Rate: $2,125.00
    Payment Terms: Net 30
    """


@pytest.fixture
def sample_bol_text():
    return """
    BILL OF LADING
    BOL #: BOL-2026-55421
    Load #: RC-48213
    Shipper: Acme Corp, 123 Industrial Blvd, Chicago IL 60601
    Consignee: Widget Co, 456 Commerce Dr, Dallas TX 75201
    Description of Articles: General Freight - Machine Parts
    Weight: 15,000 LBS
    Pieces: 42
    Trailer #: TR-78901
    Signature of Receiver: _______________
    """


@pytest.fixture
def sample_pod_text():
    return """
    PROOF OF DELIVERY
    POD #: POD-2026-88712
    Load #: RC-48213
    Delivery Date: 2026-08-24
    Received By: John Smith
    Signature of Receiver: _______________
    Received in Good Order: Yes
    Damage Notes: None
    """


@pytest.fixture
def sample_invoice_text():
    return """
    CARRIER INVOICE
    Invoice #: INV-2026-33100
    Load #: RC-48213
    Carrier: XYZ Transport Inc.
    Line Items:
    - Linehaul: $1,850.00
    - Fuel Surcharge: $275.00
    - Detention: $150.00
    Total Amount Due: $2,275.00
    Due Date: 2026-09-23
    Remit To: XYZ Transport Inc., PO Box 1234, Dallas TX
    """


# ---------------------------------------------------------------------------
# Mock LLM Router
# ---------------------------------------------------------------------------

class MockLLMRouter:
    """Mock LLM router for testing pipeline stages."""

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.calls: list[dict] = []

    async def complete(self, task_type: str, prompt: str, **kwargs) -> dict:
        self.calls.append({"task_type": task_type, "prompt": prompt, **kwargs})
        if task_type in self.responses:
            return self.responses[task_type]
        if task_type == "classification":
            return {
                "text": '{"doc_type": "unknown", "confidence_reasoning": "mock"}',
                "model": "test-model", "provider": "test", "cached": False,
            }
        if task_type == "page_split":
            return {
                "text": '[{"page_start": 1, "page_end": 1, "doc_type": "unknown"}]',
                "model": "test-model", "provider": "test", "cached": False,
            }
        return {"text": "{}", "model": "test-model", "provider": "test", "cached": False}


@pytest.fixture
def mock_llm_router():
    return MockLLMRouter()
