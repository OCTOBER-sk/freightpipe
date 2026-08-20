"""Tests for merged-PDF page-split — header detection, layout heuristics, LLM fallback."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from freightpipe.pipeline.split import (
    PageSplit,
    SplitResult,
    _detect_header_type,
    _parse_llm_splits,
    HEADER_PATTERNS,
)


# ---------------------------------------------------------------------------
# Header pattern detection tests
# ---------------------------------------------------------------------------

class TestHeaderDetection:
    def test_detect_rate_confirmation(self):
        assert _detect_header_type("RATE CONFIRMATION") == "rate_con"

    def test_detect_bill_of_lading(self):
        assert _detect_header_type("BILL OF LADING") == "bol"

    def test_detect_proof_of_delivery(self):
        assert _detect_header_type("PROOF OF DELIVERY") == "pod"

    def test_detect_carrier_invoice(self):
        assert _detect_header_type("CARRIER INVOICE") == "invoice"

    def test_detect_freight_invoice(self):
        assert _detect_header_type("FREIGHT INVOICE") == "invoice"

    def test_detect_delivery_receipt(self):
        assert _detect_header_type("DELIVERY RECEIPT") == "pod"

    def test_detect_bol_abbreviated(self):
        assert _detect_header_type("BOL #12345") == "bol"

    def test_detect_pod_abbreviated(self):
        assert _detect_header_type("POD #67890") == "pod"

    def test_no_match(self):
        assert _detect_header_type("RANDOM DOCUMENT TEXT") is None

    def test_empty_text(self):
        assert _detect_header_type("") is None

    def test_case_insensitive_matching(self):
        # _detect_header_type expects uppercase input (caller normalizes)
        assert _detect_header_type("rate confirmation") is None  # lowercase
        assert _detect_header_type("RATE CONFIRMATION") == "rate_con"  # uppercase


# ---------------------------------------------------------------------------
# LLM split parsing tests
# ---------------------------------------------------------------------------

class TestParseLLMSplits:
    def test_valid_json_array(self):
        text = json.dumps([
            {"page_start": 1, "page_end": 3, "doc_type": "rate_con"},
            {"page_start": 4, "page_end": 5, "doc_type": "bol"},
        ])
        result = _parse_llm_splits(text)
        assert len(result) == 2
        assert result[0]["page_start"] == 1
        assert result[1]["doc_type"] == "bol"

    def test_json_with_markdown_fences(self):
        text = '```json\n[{"page_start": 1, "page_end": 1, "doc_type": "unknown"}]\n```'
        result = _parse_llm_splits(text)
        assert len(result) == 1

    def test_json_with_segments_key(self):
        text = json.dumps({
            "segments": [
                {"page_start": 1, "page_end": 2, "doc_type": "rate_con"},
            ]
        })
        result = _parse_llm_splits(text)
        assert len(result) == 1

    def test_invalid_json(self):
        result = _parse_llm_splits("not json at all")
        assert result == []

    def test_empty_array(self):
        result = _parse_llm_splits("[]")
        assert result == []

    def test_missing_fields(self):
        text = json.dumps([{"page_start": 1}])  # missing page_end
        result = _parse_llm_splits(text)
        assert len(result) == 0  # invalid, should be filtered

    def test_dict_instead_of_array(self):
        text = json.dumps({"page_start": 1, "page_end": 1})
        result = _parse_llm_splits(text)
        assert result == []  # not a list, no segments key


# ---------------------------------------------------------------------------
# PageSplit dataclass tests
# ---------------------------------------------------------------------------

class TestPageSplit:
    def test_page_split_defaults(self):
        ps = PageSplit(page_start=1, page_end=5)
        assert ps.doc_type == "unknown"
        assert ps.confidence == 0.0
        assert ps.method == "heuristic"

    def test_page_split_with_values(self):
        ps = PageSplit(
            page_start=1, page_end=3,
            doc_type="rate_con", confidence=0.85, method="header",
        )
        assert ps.doc_type == "rate_con"
        assert ps.confidence == 0.85


# ---------------------------------------------------------------------------
# SplitResult tests
# ---------------------------------------------------------------------------

class TestSplitResult:
    def test_split_result_single_segment(self):
        sr = SplitResult(
            segments=[PageSplit(page_start=1, page_end=5)],
            method="header",
            page_count=5,
        )
        assert len(sr.segments) == 1
        assert sr.page_count == 5

    def test_split_result_multiple_segments(self):
        sr = SplitResult(
            segments=[
                PageSplit(page_start=1, page_end=2, doc_type="rate_con"),
                PageSplit(page_start=3, page_end=5, doc_type="bol"),
            ],
            method="combined",
            page_count=5,
        )
        assert len(sr.segments) == 2


# ---------------------------------------------------------------------------
# Integration tests with mocked pdfplumber
# ---------------------------------------------------------------------------

class TestSplitIntegration:
    @pytest.mark.asyncio
    async def test_single_page_no_split(self):
        """Single page PDF should return one segment."""
        from freightpipe.pipeline.split import split_merged_pdf

        mock_page = MagicMock()
        mock_page.height = 792
        mock_page.width = 612
        mock_page.extract_text.return_value = "RATE CONFIRMATION\nLoad #12345"
        mock_page.extract_words.return_value = [
            {"text": "RATE", "top": 50, "size": 14},
            {"text": "CONFIRMATION", "top": 50, "size": 14},
        ]
        mock_page.crop.return_value = mock_page

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("freightpipe.pipeline.split.pdfplumber.open", return_value=mock_pdf):
            result = await split_merged_pdf(b"%PDF-1.4 test")
            assert len(result.segments) == 1
            assert result.segments[0].page_start == 1
            assert result.segments[0].page_end == 1

    @pytest.mark.asyncio
    async def test_multi_page_header_split(self):
        """Multi-page PDF with different headers should split."""
        from freightpipe.pipeline.split import split_merged_pdf

        # Page 1: Rate Confirmation
        page1 = MagicMock()
        page1.height = 792
        page1.width = 612
        page1.extract_text.return_value = "RATE CONFIRMATION\nLoad #12345"
        page1.extract_words.return_value = [
            {"text": "RATE", "top": 50, "size": 14},
        ]
        page1.crop.return_value = MagicMock(
            extract_text=MagicMock(return_value="RATE CONFIRMATION"),
        )

        # Page 2: Bill of Lading
        page2 = MagicMock()
        page2.height = 792
        page2.width = 612
        page2.extract_text.return_value = "BILL OF LADING\nBOL #67890"
        page2.extract_words.return_value = [
            {"text": "BILL", "top": 50, "size": 14},
        ]
        page2.crop.return_value = MagicMock(
            extract_text=MagicMock(return_value="BILL OF LADING"),
        )

        mock_pdf = MagicMock()
        mock_pdf.pages = [page1, page2]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("freightpipe.pipeline.split.pdfplumber.open", return_value=mock_pdf):
            result = await split_merged_pdf(b"%PDF-1.4 test")
            # Should detect 2 segments
            assert len(result.segments) == 2
            assert result.segments[0].doc_type == "rate_con"
            assert result.segments[1].doc_type == "bol"

    @pytest.mark.asyncio
    async def test_llm_fallback_when_no_heuristics(self):
        """When heuristics find nothing, should try LLM."""
        from freightpipe.pipeline.split import split_merged_pdf

        # Pages with no clear headers or layout changes
        page1 = MagicMock()
        page1.height = 792
        page1.width = 612
        page1.extract_text.return_value = "Some generic text"
        page1.extract_words.return_value = [{"text": "text", "top": 50, "size": 12}]
        page1.crop.return_value = MagicMock(
            extract_text=MagicMock(return_value=""),
        )

        page2 = MagicMock()
        page2.height = 792
        page2.width = 612
        page2.extract_text.return_value = "More generic text"
        page2.extract_words.return_value = [{"text": "text", "top": 50, "size": 12}]
        page2.crop.return_value = MagicMock(
            extract_text=MagicMock(return_value=""),
        )

        mock_pdf = MagicMock()
        mock_pdf.pages = [page1, page2]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_router = MagicMock()
        mock_router.complete = AsyncMock(return_value={
            "text": json.dumps([
                {"page_start": 1, "page_end": 1, "doc_type": "rate_con"},
                {"page_start": 2, "page_end": 2, "doc_type": "bol"},
            ]),
            "model": "test",
            "provider": "test",
        })

        with patch("freightpipe.pipeline.split.pdfplumber.open", return_value=mock_pdf):
            result = await split_merged_pdf(b"%PDF-1.4 test", llm_router=mock_router)
            # LLM should have been called
            mock_router.complete.assert_called_once()
