"""Tests for confidence scoring — rule vs LLM vs OCR confidence,
HITL threshold routing, verification pass (BACKEND.md §5.7)."""
from __future__ import annotations

import pytest

from freightpipe.pipeline.confidence import (
    score_field_confidence,
    score_document_confidence,
    should_route_to_hitl,
    FieldConfidence,
    DocumentConfidence,
    HITLDecision,
    DOCUMENT_CONFIDENCE_THRESHOLD,
    FIELD_CONFIDENCE_THRESHOLD,
    RULE_CONFIDENCE_HIGH,
    RULE_CONFIDENCE_LOW,
    OCR_CONFIDENCE_CEILING,
    LLM_DEFAULT_CONFIDENCE,
)


# ---------------------------------------------------------------------------
# Per-field confidence: rule-extracted
# ---------------------------------------------------------------------------

class TestRuleExtractedConfidence:
    def test_rule_default_high(self):
        """Rule-extracted with no base confidence gets highest default."""
        conf = score_field_confidence("rule")
        assert conf == RULE_CONFIDENCE_HIGH

    def test_rule_with_base_confidence(self):
        """Rule-extracted with base confidence clamped to 0.95-0.99."""
        conf = score_field_confidence("rule", base_confidence=0.97)
        assert conf == 0.97

    def test_rule_base_below_floor(self):
        """Base confidence below 0.95 gets clamped up."""
        conf = score_field_confidence("rule", base_confidence=0.80)
        assert conf == RULE_CONFIDENCE_LOW

    def test_rule_base_above_ceiling(self):
        """Base confidence above 0.99 gets clamped down."""
        conf = score_field_confidence("rule", base_confidence=1.0)
        assert conf == RULE_CONFIDENCE_HIGH


# ---------------------------------------------------------------------------
# Per-field confidence: LLM-extracted
# ---------------------------------------------------------------------------

class TestLLMExtractedConfidence:
    def test_llm_default(self):
        """LLM-extracted with no verification gets default confidence."""
        conf = score_field_confidence("llm_text")
        assert conf == LLM_DEFAULT_CONFIDENCE

    def test_llm_with_base_confidence(self):
        """LLM-extracted with base confidence capped at 0.95."""
        conf = score_field_confidence("llm_text", base_confidence=0.90)
        assert conf == 0.90

    def test_llm_base_above_ceiling(self):
        """LLM base confidence capped at 0.95."""
        conf = score_field_confidence("llm_text", base_confidence=0.99)
        assert conf == 0.95

    def test_llm_verification_agreed(self):
        """Verification pass agreed — use certainty."""
        conf = score_field_confidence(
            "llm_text",
            verification_agreed=True,
            verification_certainty=0.92,
        )
        assert conf == 0.92

    def test_llm_verification_disagreed(self):
        """Verification pass disagreed — sharply lower confidence."""
        conf = score_field_confidence(
            "llm_text",
            verification_agreed=False,
            verification_certainty=0.3,
        )
        assert conf == 0.50

    def test_llm_vision_method(self):
        """llm_vision follows same rules as llm_text."""
        conf = score_field_confidence("llm_vision")
        assert conf == LLM_DEFAULT_CONFIDENCE

    def test_llm_verification_agreed_high_certainty(self):
        """Verification agreed with high certainty — capped at 0.99."""
        conf = score_field_confidence(
            "llm_text",
            verification_agreed=True,
            verification_certainty=1.0,
        )
        assert conf == 0.99


# ---------------------------------------------------------------------------
# Per-field confidence: OCR-sourced
# ---------------------------------------------------------------------------

class TestOCRExtractedConfidence:
    def test_ocr_default(self):
        """OCR-sourced gets ceiling 0.85."""
        conf = score_field_confidence("ocr")
        assert conf == OCR_CONFIDENCE_CEILING

    def test_ocr_with_base_below_ceiling(self):
        """OCR with base confidence below ceiling — use base."""
        conf = score_field_confidence("ocr", base_confidence=0.70)
        assert conf == 0.70

    def test_ocr_with_base_above_ceiling(self):
        """OCR with base confidence above ceiling — cap at 0.85."""
        conf = score_field_confidence("ocr", base_confidence=0.95)
        assert conf == OCR_CONFIDENCE_CEILING


# ---------------------------------------------------------------------------
# Per-field confidence: unknown method
# ---------------------------------------------------------------------------

class TestUnknownMethodConfidence:
    def test_unknown_default(self):
        """Unknown method gets conservative 0.80."""
        conf = score_field_confidence("unknown")
        assert conf == 0.80

    def test_unknown_with_base(self):
        """Unknown method with base capped at 0.80."""
        conf = score_field_confidence("unknown", base_confidence=0.90)
        assert conf == 0.80


# ---------------------------------------------------------------------------
# Per-document confidence
# ---------------------------------------------------------------------------

class TestDocumentConfidence:
    def test_weighted_average(self):
        """Document confidence is weighted average of field confidences."""
        field_confs = {
            "load_number": 0.95,
            "broker_name": 0.90,
        }
        result = score_document_confidence(
            doc_type="rate_con",
            fields={"load_number": "RC-123", "broker_name": "ABC"},
            field_confidences=field_confs,
            classification_confidence=0.95,
        )
        # Both are required, so weighted avg = (0.95*2 + 0.90*2) / (2+2) = 0.925
        assert abs(result.document_confidence - 0.925) < 0.01

    def test_floored_by_classification(self):
        """Document confidence floored by classification confidence."""
        field_confs = {
            "load_number": 0.95,
        }
        result = score_document_confidence(
            doc_type="rate_con",
            fields={"load_number": "RC-123"},
            field_confidences=field_confs,
            classification_confidence=0.70,  # low classification
        )
        # Avg = 0.95, but floored by 0.70
        assert result.document_confidence == 0.70

    def test_required_fields_weighted_higher(self):
        """Required fields get 2x weight vs optional fields."""
        field_confs = {
            "load_number": 0.90,   # required, weight=2
            "payment_terms": 0.50,  # optional, weight=1
        }
        result = score_document_confidence(
            doc_type="rate_con",
            fields={"load_number": "RC-123", "payment_terms": "Net 30"},
            field_confidences=field_confs,
            classification_confidence=0.95,
        )
        # weighted avg = (0.90*2 + 0.50*1) / (2+1) = 2.3/3 = 0.7667
        assert abs(result.document_confidence - 0.767) < 0.01

    def test_no_fields(self):
        """No fields — uses classification confidence."""
        result = score_document_confidence(
            doc_type="rate_con",
            fields={},
            field_confidences={},
            classification_confidence=0.85,
        )
        assert result.document_confidence == 0.85

    def test_lowest_field_tracked(self):
        """Lowest field confidence is tracked."""
        field_confs = {
            "load_number": 0.95,
            "broker_name": 0.60,
        }
        result = score_document_confidence(
            doc_type="rate_con",
            fields={"load_number": "RC-123", "broker_name": "ABC"},
            field_confidences=field_confs,
            classification_confidence=0.95,
        )
        assert result.lowest_field_name == "broker_name"
        assert result.lowest_field_confidence == 0.60


# ---------------------------------------------------------------------------
# HITL routing
# ---------------------------------------------------------------------------

class TestHITLRouting:
    def test_no_review_needed(self):
        """All confidences above thresholds — no review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.95,
                classification_confidence=0.95,
                field_confidences=[
                    FieldConfidence("load_number", 0.95, "rule", True),
                ],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is False
        assert decision.reasons == []

    def test_low_document_confidence(self):
        """Document confidence below 0.80 -> review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.75,
                classification_confidence=0.80,
                field_confidences=[],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is True
        assert any("low_confidence" in r for r in decision.reasons)

    def test_low_field_confidence(self):
        """Required field confidence below 0.70 -> review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.90,
                classification_confidence=0.95,
                field_confidences=[
                    FieldConfidence("load_number", 0.65, "ocr", True),
                ],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is True
        assert any("load_number" in r for r in decision.reasons)

    def test_discrepancy_triggers_review(self):
        """Any discrepancy -> review regardless of confidence."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.95,
                classification_confidence=0.95,
                field_confidences=[],
            ),
        ]
        decision = should_route_to_hitl(
            doc_confs,
            has_discrepancies=True,
            discrepancy_reasons=["discrepancy: rate_delta on linehaul"],
        )
        assert decision.needs_review is True
        assert any("discrepancy" in r for r in decision.reasons)

    def test_optional_field_below_threshold_no_review(self):
        """Optional field below 0.70 does NOT trigger review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.90,
                classification_confidence=0.95,
                field_confidences=[
                    FieldConfidence("payment_terms", 0.50, "ocr", False),  # optional
                ],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is False

    def test_exact_threshold_no_review(self):
        """Exactly at threshold does NOT trigger review (< not <=)."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.80,  # exactly at threshold
                classification_confidence=0.95,
                field_confidences=[
                    FieldConfidence("load_number", 0.70, "rule", True),  # exactly at threshold
                ],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is False

    def test_below_exact_threshold_triggers_review(self):
        """Just below threshold triggers review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.799,
                classification_confidence=0.95,
                field_confidences=[
                    FieldConfidence("load_number", 0.699, "rule", True),
                ],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is True
        assert len(decision.reasons) == 2  # both doc and field

    def test_multiple_documents(self):
        """Multiple documents — any low confidence triggers review."""
        doc_confs = [
            DocumentConfidence(
                doc_type="rate_con",
                document_confidence=0.95,
                classification_confidence=0.95,
                field_confidences=[],
            ),
            DocumentConfidence(
                doc_type="bol",
                document_confidence=0.70,  # below threshold
                classification_confidence=0.80,
                field_confidences=[],
            ),
        ]
        decision = should_route_to_hitl(doc_confs)
        assert decision.needs_review is True
        assert any("bol" in r for r in decision.reasons)
