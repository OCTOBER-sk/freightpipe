"""Review queue — state machine + resolution logic (BACKEND.md §5.8).

State machine:
    pending -> in_review -> resolved
                  |
                  └──→ escalated -> resolved

Resolution types:
    - approved: accept extracted values as-is
    - corrected: override specific fields
    - escalated: manual intervention outside the API
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_review"],
    "in_review": ["resolved", "escalated"],
    "escalated": ["resolved"],
    "resolved": [],  # terminal state
}


# ---------------------------------------------------------------------------
# Review queue dataclass
# ---------------------------------------------------------------------------

@dataclass
class ReviewItem:
    """A review queue item."""
    id: str | None = None
    job_id: str | None = None
    reason: str = "low_confidence"
    state: str = "pending"
    assigned_to: str | None = None
    resolution_notes: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


@dataclass
class ResolutionResult:
    """Result of a resolution attempt."""
    success: bool
    item: ReviewItem | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------

def can_transition(current_state: str, target_state: str) -> bool:
    """Check if a state transition is valid.

    Per BACKEND.md §5.8:
    - pending -> in_review
    - in_review -> resolved | escalated
    - escalated -> resolved
    """
    allowed = VALID_TRANSITIONS.get(current_state, [])
    return target_state in allowed


def transition_to_in_review(item: ReviewItem, assigned_to: str | None = None) -> ResolutionResult:
    """Transition a review item from pending to in_review.

    Args:
        item: The review item to transition
        assigned_to: Who is claiming the review

    Returns:
        ResolutionResult with updated item or error
    """
    if not can_transition(item.state, "in_review"):
        return ResolutionResult(
            success=False,
            error=f"Cannot transition from '{item.state}' to 'in_review'",
        )

    item.state = "in_review"
    item.assigned_to = assigned_to
    return ResolutionResult(success=True, item=item)


def resolve_approved(
    item: ReviewItem,
    notes: str | None = None,
    assigned_to: str | None = None,
) -> ResolutionResult:
    """Resolve a review item as approved (accept values as-is).

    Per BACKEND.md §5.8:
    - approved: accept extracted values as-is
    - Writes back to extracted_fields/match_results
    - Flips parent job.status to 'complete'
    """
    if not can_transition(item.state, "resolved"):
        return ResolutionResult(
            success=False,
            error=f"Cannot resolve from state '{item.state}'",
        )

    item.state = "resolved"
    item.resolution_notes = notes or "Approved — values accepted as-is"
    item.assigned_to = assigned_to or item.assigned_to
    item.resolved_at = datetime.now(timezone.utc)
    return ResolutionResult(success=True, item=item)


def resolve_corrected(
    item: ReviewItem,
    corrected_fields: dict[str, Any],
    notes: str | None = None,
    assigned_to: str | None = None,
) -> ResolutionResult:
    """Resolve a review item as corrected (override specific fields).

    Per BACKEND.md §5.8:
    - corrected: override specific fields via corrected_fields
    - Writes back to extracted_fields/match_results
    - Flips parent job.status to 'complete'

    Args:
        item: The review item to resolve
        corrected_fields: Dict of field_name -> corrected value
        notes: Resolution notes
        assigned_to: Who resolved it
    """
    if not can_transition(item.state, "resolved"):
        return ResolutionResult(
            success=False,
            error=f"Cannot resolve from state '{item.state}'",
        )

    if not corrected_fields:
        return ResolutionResult(
            success=False,
            error="corrected_fields is required for 'corrected' resolution",
        )

    item.state = "resolved"
    item.resolution_notes = notes or f"Corrected fields: {', '.join(corrected_fields.keys())}"
    item.assigned_to = assigned_to or item.assigned_to
    item.resolved_at = datetime.now(timezone.utc)
    return ResolutionResult(success=True, item=item)


def resolve_escalated(
    item: ReviewItem,
    notes: str | None = None,
    assigned_to: str | None = None,
) -> ResolutionResult:
    """Escalate a review item (manual intervention outside the API).

    Per BACKEND.md §5.8:
    - escalated: held for manual intervention
    - Does not auto-resolve
    """
    if not can_transition(item.state, "escalated"):
        return ResolutionResult(
            success=False,
            error=f"Cannot escalate from state '{item.state}'",
        )

    item.state = "escalated"
    item.resolution_notes = notes or "Escalated for manual intervention"
    item.assigned_to = assigned_to or item.assigned_to
    item.resolved_at = datetime.now(timezone.utc)
    return ResolutionResult(success=True, item=item)


# ---------------------------------------------------------------------------
# Review reason classification
# ---------------------------------------------------------------------------

def classify_review_reason(reasons: list[str]) -> str:
    """Classify a list of HITL reasons into a primary review reason.

    Maps to BACKEND.md §3.1 review_queue.reason values:
    - low_confidence
    - discrepancy
    - classification_failed
    - needs_llm_capacity
    - validation_failed
    """
    if not reasons:
        return "low_confidence"

    # Priority order
    for reason in reasons:
        if "discrepancy" in reason:
            return "discrepancy"
    for reason in reasons:
        if "low_confidence" in reason:
            return "low_confidence"
    for reason in reasons:
        if "classification" in reason:
            return "classification_failed"
    for reason in reasons:
        if "validation" in reason:
            return "validation_failed"
    for reason in reasons:
        if "llm_capacity" in reason:
            return "needs_llm_capacity"

    return "low_confidence"


# ---------------------------------------------------------------------------
# Correction write-back helpers
# ---------------------------------------------------------------------------

def build_field_corrections(
    corrected_fields: dict[str, Any],
    document_id: str,
) -> list[dict[str, Any]]:
    """Build extracted_fields update dicts from corrected values.

    Args:
        corrected_fields: field_name -> corrected value
        document_id: The document these fields belong to

    Returns:
        List of dicts ready for extracted_fields.update_value calls
    """
    corrections = []
    for field_name, value in corrected_fields.items():
        corrections.append({
            "document_id": document_id,
            "field_name": field_name,
            "field_value": str(value) if value is not None else None,
            "confidence": 1.0,  # Human-corrected = maximum confidence
        })
    return corrections
