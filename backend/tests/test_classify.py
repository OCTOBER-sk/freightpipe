"""Tests for document classification — rules-first + LLM escalation."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from freightpipe.pipeline.classify import (
    classify_rules,
    classify_document,
    ClassificationResult,
    CLASSIFICATION_PATTERNS,
    _normalize_text,
    _parse_llm_classification,
)


# ---------------------------------------------------------------------------
# Text normalization tests
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_uppercases(self):
        assert _normalize_text("rate confirmation") == "RATE CONFIRMATION"

    def test_collapses_whitespace(self):
        assert _normalize_text("rate   confirmation\n\nbill") == "RATE CONFIRMATION BILL"

    def test_strips(self):
        assert _normalize_text("  RATE CONFIRMATION  ") == "RATE CONFIRMATION"


# ---------------------------------------------------------------------------
# Rules-based classification tests
# ---------------------------------------------------------------------------

class TestClassifyRules:
    def test_rate_confirmation(self, sample_rate_con_text):
        result = classify_rules(sample_rate_con_text)
        assert result.doc_type == "rate_con"
        assert result.confidence >= 0.75
        assert result.method == "rules"

    def test_bill_of_lading(self, sample_bol_text):
        result = classify_rules(sample_bol_text)
        assert result.doc_type == "bol"
        assert result.confidence >= 0.75

    def test_proof_of_delivery(self, sample_pod_text):
        result = classify_rules(sample_pod_text)
        assert result.doc_type == "pod"
        assert result.confidence >= 0.75

    def test_carrier_invoice(self, sample_invoice_text):
        result = classify_rules(sample_invoice_text)
        assert result.doc_type == "invoice"
        assert result.confidence >= 0.75

    def test_unknown_document(self):
        result = classify_rules("This is just some random text with no freight keywords.")
        assert result.doc_type == "unknown"
        assert result.confidence == 0.0

    def test_empty_text(self):
        result = classify_rules("")
        assert result.doc_type == "unknown"
        assert result.confidence == 0.0

    def test_ambiguous_returns_low_confidence(self):
        """Text with mixed signals should have lower confidence."""
        text = "RATE CONFIRMATION and also BILL OF LADING reference"
        result = classify_rules(text)
        # Should detect both, but one should be primary
        assert result.doc_type in ("rate_con", "bol")
        # Scores should be close
        scores = sorted(result.scores.values(), reverse=True)
        if len(scores) >= 2:
            assert scores[0] - scores[1] < 0.5  # They should be somewhat close

    def test_case_insensitive(self):
        result = classify_rules("rate confirmation")
        assert result.doc_type == "rate_con"

    def test_bol_number_pattern(self):
        result = classify_rules("BOL #12345 Shipment Details")
        assert result.doc_type == "bol"

    def test_invoice_number_pattern(self):
        result = classify_rules("Invoice #INV-2026-001 Amount Due: $500")
        assert result.doc_type == "invoice"


# ---------------------------------------------------------------------------
# LLM classification parsing tests
# ---------------------------------------------------------------------------

class TestParseLLMClassification:
    def test_valid_json(self):
        text = '{"doc_type": "rate_con", "confidence_reasoning": "header says rate confirmation"}'
        result = _parse_llm_classification(text)
        assert result["doc_type"] == "rate_con"

    def test_json_with_markdown_fences(self):
        text = '```json\n{"doc_type": "bol", "confidence_reasoning": "BOL header"}\n```'
        result = _parse_llm_classification(text)
        assert result["doc_type"] == "bol"

    def test_invalid_json_fallback(self):
        text = "The document type is rate_con based on the header."
        result = _parse_llm_classification(text)
        assert result["doc_type"] == "rate_con"

    def test_invalid_doc_type(self):
        text = '{"doc_type": "invalid_type"}'
        result = _parse_llm_classification(text)
        assert result["doc_type"] == "unknown"

    def test_completely_invalid(self):
        text = "not json at all and no keywords"
        result = _parse_llm_classification(text)
        assert result["doc_type"] == "unknown"


# ---------------------------------------------------------------------------
# Full classification pipeline tests
# ---------------------------------------------------------------------------

class TestClassifyDocument:
    @pytest.mark.asyncio
    async def test_rules_sufficient_no_llm(self, sample_rate_con_text, mock_llm_router):
        """When rules score >= 0.75, LLM should not be called."""
        result = await classify_document(sample_rate_con_text, mock_llm_router)
        assert result.doc_type == "rate_con"
        assert result.method == "rules"
        assert len(mock_llm_router.calls) == 0  # LLM not called

    @pytest.mark.asyncio
    async def test_rules_insufficient_escalates_to_llm(self, mock_llm_router):
        """When rules score < 0.75, should escalate to LLM."""
        mock_llm_router.responses["classification"] = {
            "text": '{"doc_type": "bol", "confidence_reasoning": "clear BOL header"}',
            "model": "test",
            "provider": "test",
            "cached": False,
        }
        # Ambiguous text that won't match well with rules
        result = await classify_document(
            "Shipping document for load #12345. Please deliver to warehouse.",
            mock_llm_router,
        )
        # Should have called LLM
        assert len(mock_llm_router.calls) == 1
        assert mock_llm_router.calls[0]["task_type"] == "classification"

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_rules(self, mock_llm_router):
        """When LLM fails, should fall back to rules result."""
        from freightpipe.llm.router import LLMCapacityExhausted
        mock_llm_router.complete = AsyncMock(side_effect=LLMCapacityExhausted("exhausted"))

        # Text with some rule matches
        result = await classify_document(
            "RATE CONFIRMATION Load #12345",
            mock_llm_router,
        )
        # Should still return a result (from rules)
        assert result.doc_type == "rate_con"

    @pytest.mark.asyncio
    async def test_no_router_returns_rules_only(self, sample_rate_con_text):
        """Without LLM router, should return rules-only result."""
        result = await classify_document(sample_rate_con_text, llm_router=None)
        assert result.doc_type == "rate_con"
        assert result.method == "rules"

    @pytest.mark.asyncio
    async def test_llm_unknown_falls_back_to_rules(self, mock_llm_router, sample_rate_con_text):
        """When LLM returns unknown, should fall back to rules result."""
        mock_llm_router.responses["classification"] = {
            "text": '{"doc_type": "unknown", "confidence_reasoning": "not sure"}',
            "model": "test",
            "provider": "test",
            "cached": False,
        }
        # Force LLM escalation by using ambiguous text
        result = await classify_document(
            "Some ambiguous shipping document",
            mock_llm_router,
        )
        # Should fall back to rules (which returns unknown for this text)
        assert result.doc_type == "unknown"
