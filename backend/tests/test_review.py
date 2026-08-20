"""Tests for review queue — state machine transitions, resolution types,
corrections write-back (BACKEND.md §5.8)."""
from __future__ import annotations

import pytest

from freightpipe.pipeline.review import (
    ReviewItem,
    ResolutionResult,
    can_transition,
    transition_to_in_review,
    resolve_approved,
    resolve_corrected,
    resolve_escalated,
    classify_review_reason,
    build_field_corrections,
    VALID_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# State machine transition tests
# ---------------------------------------------------------------------------

class TestCanTransition:
    def test_pending_to_in_review(self):
        assert can_transition("pending", "in_review") is True

    def test_in_review_to_resolved(self):
        assert can_transition("in_review", "resolved") is True

    def test_in_review_to_escalated(self):
        assert can_transition("in_review", "escalated") is True

    def test_escalated_to_resolved(self):
        assert can_transition("escalated", "resolved") is True

    def test_pending_to_resolved_invalid(self):
        assert can_transition("pending", "resolved") is False

    def test_pending_to_escalated_invalid(self):
        assert can_transition("pending", "escalated") is False

    def test_resolved_is_terminal(self):
        assert can_transition("resolved", "in_review") is False
        assert can_transition("resolved", "pending") is False
        assert can_transition("resolved", "escalated") is False

    def test_in_review_to_pending_invalid(self):
        assert can_transition("in_review", "pending") is False


# ---------------------------------------------------------------------------
# Transition to in_review
# ---------------------------------------------------------------------------

class TestTransitionToInReview:
    def test_from_pending(self):
        item = ReviewItem(state="pending")
        result = transition_to_in_review(item, assigned_to="reviewer1")
        assert result.success is True
        assert result.item.state == "in_review"
        assert result.item.assigned_to == "reviewer1"

    def test_from_pending_no_assignee(self):
        item = ReviewItem(state="pending")
        result = transition_to_in_review(item)
        assert result.success is True
        assert result.item.state == "in_review"
        assert result.item.assigned_to is None

    def test_from_in_review_fails(self):
        item = ReviewItem(state="in_review")
        result = transition_to_in_review(item)
        assert result.success is False
        assert "Cannot transition" in result.error

    def test_from_resolved_fails(self):
        item = ReviewItem(state="resolved")
        result = transition_to_in_review(item)
        assert result.success is False


# ---------------------------------------------------------------------------
# Resolution: approved
# ---------------------------------------------------------------------------

class TestResolveApproved:
    def test_from_in_review(self):
        item = ReviewItem(state="in_review")
        result = resolve_approved(item, notes="Looks good")
        assert result.success is True
        assert result.item.state == "resolved"
        assert result.item.resolution_notes == "Looks good"
        assert result.item.resolved_at is not None

    def test_from_escalated_succeeds(self):
        """Escalated can be resolved (per BACKEND.md §5.8: escalated -> resolved)."""
        item = ReviewItem(state="escalated")
        result = resolve_approved(item)
        assert result.success is True
        assert result.item.state == "resolved"

    def test_from_pending_fails(self):
        item = ReviewItem(state="pending")
        result = resolve_approved(item)
        assert result.success is False

    def test_default_notes(self):
        item = ReviewItem(state="in_review")
        result = resolve_approved(item)
        assert "Approved" in result.item.resolution_notes

    def test_preserves_assignee(self):
        item = ReviewItem(state="in_review", assigned_to="reviewer1")
        result = resolve_approved(item)
        assert result.item.assigned_to == "reviewer1"


# ---------------------------------------------------------------------------
# Resolution: corrected
# ---------------------------------------------------------------------------

class TestResolveCorrected:
    def test_from_in_review(self):
        item = ReviewItem(state="in_review")
        corrected = {"linehaul_rate": "1950.00"}
        result = resolve_corrected(item, corrected_fields=corrected)
        assert result.success is True
        assert result.item.state == "resolved"
        assert "linehaul_rate" in result.item.resolution_notes

    def test_empty_corrections_fails(self):
        item = ReviewItem(state="in_review")
        result = resolve_corrected(item, corrected_fields={})
        assert result.success is False
        assert "corrected_fields is required" in result.error

    def test_from_pending_fails(self):
        item = ReviewItem(state="pending")
        result = resolve_corrected(item, corrected_fields={"field": "value"})
        assert result.success is False

    def test_custom_notes(self):
        item = ReviewItem(state="in_review")
        result = resolve_corrected(
            item,
            corrected_fields={"load_number": "RC-99999"},
            notes="Load number was misread",
        )
        assert result.item.resolution_notes == "Load number was misread"


# ---------------------------------------------------------------------------
# Resolution: escalated
# ---------------------------------------------------------------------------

class TestResolveEscalated:
    def test_from_in_review(self):
        item = ReviewItem(state="in_review")
        result = resolve_escalated(item, notes="Illegible document")
        assert result.success is True
        assert result.item.state == "escalated"
        assert result.item.resolved_at is not None

    def test_from_pending_fails(self):
        item = ReviewItem(state="pending")
        result = resolve_escalated(item)
        assert result.success is False

    def test_from_escalated_fails(self):
        """Already escalated — cannot escalate again."""
        item = ReviewItem(state="escalated")
        result = resolve_escalated(item)
        assert result.success is False

    def test_escalated_can_then_resolve(self):
        """Escalated item can later be resolved."""
        item = ReviewItem(state="in_review")
        result1 = resolve_escalated(item, notes="Need manual review")
        assert result1.success is True

        result2 = resolve_approved(result1.item, notes="Manually verified")
        assert result2.success is True
        assert result2.item.state == "resolved"


# ---------------------------------------------------------------------------
# Full state machine flow
# ---------------------------------------------------------------------------

class TestFullFlow:
    def test_pending_to_resolved(self):
        """Full flow: pending -> in_review -> resolved (approved)."""
        item = ReviewItem(state="pending")
        r1 = transition_to_in_review(item, assigned_to="reviewer1")
        assert r1.success is True

        r2 = resolve_approved(r1.item, notes="All good")
        assert r2.success is True
        assert r2.item.state == "resolved"

    def test_pending_to_escalated_to_resolved(self):
        """Full flow: pending -> in_review -> escalated -> resolved."""
        item = ReviewItem(state="pending")
        r1 = transition_to_in_review(item)
        assert r1.success is True

        r2 = resolve_escalated(r1.item, notes="Illegible")
        assert r2.success is True
        assert r2.item.state == "escalated"

        r3 = resolve_approved(r2.item, notes="Manually verified")
        assert r3.success is True
        assert r3.item.state == "resolved"

    def test_pending_to_corrected(self):
        """Full flow: pending -> in_review -> resolved (corrected)."""
        item = ReviewItem(state="pending")
        r1 = transition_to_in_review(item, assigned_to="reviewer1")
        assert r1.success is True

        r2 = resolve_corrected(
            r1.item,
            corrected_fields={"linehaul_rate": "1950.00"},
            notes="Rate was wrong",
        )
        assert r2.success is True
        assert r2.item.state == "resolved"


# ---------------------------------------------------------------------------
# Review reason classification
# ---------------------------------------------------------------------------

class TestClassifyReviewReason:
    def test_discrepancy_priority(self):
        reasons = ["low_confidence: bol", "discrepancy: rate_delta on linehaul"]
        assert classify_review_reason(reasons) == "discrepancy"

    def test_low_confidence(self):
        reasons = ["low_confidence: rate_con document confidence 0.75"]
        assert classify_review_reason(reasons) == "low_confidence"

    def test_classification_failed(self):
        reasons = ["classification_failed: unknown doc type"]
        assert classify_review_reason(reasons) == "classification_failed"

    def test_validation_failed(self):
        reasons = ["validation_failed: money sanity"]
        assert classify_review_reason(reasons) == "validation_failed"

    def test_needs_llm_capacity(self):
        reasons = ["llm_capacity_exhausted"]
        assert classify_review_reason(reasons) == "needs_llm_capacity"

    def test_empty_reasons(self):
        assert classify_review_reason([]) == "low_confidence"

    def test_mixed_reasons_discrepancy_wins(self):
        reasons = [
            "low_confidence: something",
            "discrepancy: extra_accessorial on detention",
            "validation_failed: something",
        ]
        assert classify_review_reason(reasons) == "discrepancy"


# ---------------------------------------------------------------------------
# Correction write-back helpers
# ---------------------------------------------------------------------------

class TestBuildFieldCorrections:
    def test_single_correction(self):
        corrections = build_field_corrections(
            {"linehaul_rate": "1950.00"},
            document_id="doc-123",
        )
        assert len(corrections) == 1
        assert corrections[0]["field_name"] == "linehaul_rate"
        assert corrections[0]["field_value"] == "1950.00"
        assert corrections[0]["confidence"] == 1.0  # human-corrected
        assert corrections[0]["document_id"] == "doc-123"

    def test_multiple_corrections(self):
        corrections = build_field_corrections(
            {"linehaul_rate": "1950.00", "load_number": "RC-99999"},
            document_id="doc-123",
        )
        assert len(corrections) == 2
        field_names = {c["field_name"] for c in corrections}
        assert field_names == {"linehaul_rate", "load_number"}

    def test_none_value(self):
        corrections = build_field_corrections(
            {"optional_field": None},
            document_id="doc-123",
        )
        assert corrections[0]["field_value"] is None
