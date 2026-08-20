"""Confidence scoring — per-field + per-document + HITL routing (BACKEND.md §5.7).

Per-field confidence:
  - Rule-extracted: 0.95-0.99 fixed by extraction method
  - LLM-extracted: verification pass (second cheaper LLM call, yes/no + certainty)
  - OCR-sourced: ceiling 0.85 max

Per-document: weighted average of required fields, floored by classification confidence.

HITL routing: doc_confidence < 0.80 OR any field < 0.70 OR any discrepancy -> review_queue
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence thresholds (BACKEND.md §5.7)
# ---------------------------------------------------------------------------

DOCUMENT_CONFIDENCE_THRESHOLD = 0.80
FIELD_CONFIDENCE_THRESHOLD = 0.70

# Confidence ceilings/floors by extraction method
RULE_CONFIDENCE_HIGH = 0.99
RULE_CONFIDENCE_LOW = 0.95
LLM_DEFAULT_CONFIDENCE = 0.85
OCR_CONFIDENCE_CEILING = 0.85

# Required fields per doc type (for weighted average calculation)
REQUIRED_FIELDS: dict[str, list[str]] = {
    "rate_con": [
        "load_number", "broker_name", "carrier_name", "shipper", "consignee",
        "pickup", "delivery", "linehaul_rate", "total_rate",
    ],
    "bol": [
        "bol_number", "shipper", "consignee", "pickup_date",
        "freight_description", "weight", "pieces", "signature_present",
    ],
    "pod": ["delivery_date", "recipient_name", "signature_present"],
    "invoice": ["invoice_number", "load_number", "carrier_name", "line_items", "total_amount"],
}

# Weight for required vs optional fields in document confidence
REQUIRED_FIELD_WEIGHT = 2.0
OPTIONAL_FIELD_WEIGHT = 1.0


# ---------------------------------------------------------------------------
# Per-field confidence scoring
# ---------------------------------------------------------------------------

def score_field_confidence(
    extraction_method: str,
    base_confidence: float | None = None,
    verification_agreed: bool | None = None,
    verification_certainty: float | None = None,
) -> float:
    """Calculate per-field confidence based on extraction method.

    Per BACKEND.md §5.7:
    - Rule-extracted: 0.95-0.99 fixed by extraction method
    - LLM-extracted: verification pass (second cheaper LLM call)
    - OCR-sourced: ceiling 0.85 max

    Args:
        extraction_method: "rule" | "llm_text" | "llm_vision" | "ocr"
        base_confidence: Base confidence from extraction (used for LLM)
        verification_agreed: Whether verification pass agreed (LLM only)
        verification_certainty: Certainty from verification pass (LLM only)

    Returns:
        Confidence score 0.0-1.0
    """
    if extraction_method == "rule":
        # Rule-extracted: 0.95-0.99 fixed
        if base_confidence is not None:
            return max(RULE_CONFIDENCE_LOW, min(base_confidence, RULE_CONFIDENCE_HIGH))
        return RULE_CONFIDENCE_HIGH

    if extraction_method in ("llm_text", "llm_vision"):
        # LLM-extracted: use verification pass if available
        if verification_agreed is not None:
            if verification_agreed:
                # Verification agreed — use certainty, capped reasonable
                certainty = verification_certainty if verification_certainty is not None else LLM_DEFAULT_CONFIDENCE
                return min(certainty, 0.99)
            else:
                # Verification disagreed — sharply lower confidence
                return 0.50
        # No verification pass — use base confidence or default
        if base_confidence is not None:
            return min(base_confidence, 0.95)
        return LLM_DEFAULT_CONFIDENCE

    if extraction_method == "ocr":
        # OCR-sourced: ceiling 0.85
        if base_confidence is not None:
            return min(base_confidence, OCR_CONFIDENCE_CEILING)
        return OCR_CONFIDENCE_CEILING

    # Unknown method — conservative default
    if base_confidence is not None:
        return min(base_confidence, 0.80)
    return 0.80


# ---------------------------------------------------------------------------
# Per-document confidence scoring
# ---------------------------------------------------------------------------

@dataclass
class FieldConfidence:
    """Confidence info for a single field."""
    field_name: str
    confidence: float
    extraction_method: str
    is_required: bool


@dataclass
class DocumentConfidence:
    """Confidence info for a document."""
    doc_type: str
    document_confidence: float
    classification_confidence: float
    field_confidences: list[FieldConfidence]
    lowest_field_name: str | None = None
    lowest_field_confidence: float = 1.0


def score_document_confidence(
    doc_type: str,
    fields: dict[str, Any],
    field_confidences: dict[str, float],
    classification_confidence: float,
    extraction_methods: dict[str, str] | None = None,
) -> DocumentConfidence:
    """Calculate per-document confidence.

    Per BACKEND.md §5.7:
    - Weighted average of required-field confidences
    - Floored by classification confidence

    Args:
        doc_type: Document type (rate_con, bol, pod, invoice)
        fields: Extracted field values
        field_confidences: field_name -> confidence score
        classification_confidence: Classification confidence for this doc
        extraction_methods: field_name -> extraction method (optional)

    Returns:
        DocumentConfidence with overall score and per-field details
    """
    required = set(REQUIRED_FIELDS.get(doc_type, []))
    extraction_methods = extraction_methods or {}

    # Build field confidence list
    field_confs: list[FieldConfidence] = []
    for field_name, confidence in field_confidences.items():
        field_confs.append(FieldConfidence(
            field_name=field_name,
            confidence=confidence,
            extraction_method=extraction_methods.get(field_name, "unknown"),
            is_required=field_name in required,
        ))

    # Weighted average of all fields with confidences
    if not field_confs:
        return DocumentConfidence(
            doc_type=doc_type,
            document_confidence=classification_confidence,
            classification_confidence=classification_confidence,
            field_confidences=field_confs,
        )

    weighted_sum = 0.0
    weight_total = 0.0
    lowest_name: str | None = None
    lowest_conf = 1.0

    for fc in field_confs:
        weight = REQUIRED_FIELD_WEIGHT if fc.is_required else OPTIONAL_FIELD_WEIGHT
        weighted_sum += fc.confidence * weight
        weight_total += weight

        if fc.confidence < lowest_conf:
            lowest_conf = fc.confidence
            lowest_name = fc.field_name

    avg_confidence = weighted_sum / weight_total if weight_total > 0 else 0.0

    # Floor by classification confidence
    document_confidence = min(avg_confidence, classification_confidence)

    return DocumentConfidence(
        doc_type=doc_type,
        document_confidence=round(document_confidence, 3),
        classification_confidence=classification_confidence,
        field_confidences=field_confs,
        lowest_field_name=lowest_name,
        lowest_field_confidence=lowest_conf,
    )


# ---------------------------------------------------------------------------
# HITL routing decision
# ---------------------------------------------------------------------------

@dataclass
class HITLDecision:
    """Human-in-the-loop routing decision."""
    needs_review: bool
    reasons: list[str] = field(default_factory=list)


def should_route_to_hitl(
    document_confidences: list[DocumentConfidence],
    has_discrepancies: bool = False,
    discrepancy_reasons: list[str] | None = None,
) -> HITLDecision:
    """Determine if a job should be routed to human review.

    Per BACKEND.md §5.7:
    - document confidence < 0.80 -> review
    - any required field confidence < 0.70 -> review
    - any discrepancy_flag != none -> review

    Args:
        document_confidences: Confidence scores for all documents in the job
        has_discrepancies: Whether 3-way match found discrepancies
        discrepancy_reasons: List of discrepancy reason strings

    Returns:
        HITLDecision with needs_review flag and reasons
    """
    reasons: list[str] = []

    for doc_conf in document_confidences:
        # Check document-level confidence
        if doc_conf.document_confidence < DOCUMENT_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"low_confidence: {doc_conf.doc_type} document confidence "
                f"{doc_conf.document_confidence:.3f} < {DOCUMENT_CONFIDENCE_THRESHOLD}"
            )

        # Check per-field confidence for required fields
        for fc in doc_conf.field_confidences:
            if fc.is_required and fc.confidence < FIELD_CONFIDENCE_THRESHOLD:
                reasons.append(
                    f"low_confidence: {doc_conf.doc_type}.{fc.field_name} "
                    f"confidence {fc.confidence:.3f} < {FIELD_CONFIDENCE_THRESHOLD}"
                )

    # Check discrepancies
    if has_discrepancies and discrepancy_reasons:
        reasons.extend(discrepancy_reasons)

    return HITLDecision(
        needs_review=len(reasons) > 0,
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# LLM verification pass
# ---------------------------------------------------------------------------

VERIFICATION_PROMPT_TEMPLATE = """System: You are verifying an extracted value from a freight document.
Given the document excerpt below, does it support the following extracted value?
Answer with ONLY JSON: {{"agreed": true/false, "certainty": 0.0-1.0}}

Extracted field: {field_name}
Extracted value: {field_value}

Document excerpt:
{document_excerpt}"""


async def verify_field_with_llm(
    field_name: str,
    field_value: str,
    document_text: str,
    llm_router: Any,
) -> tuple[bool, float]:
    """Run a verification pass on an LLM-extracted field.

    Per BACKEND.md §5.7: a second, cheaper LLM call asks
    "does this excerpt support this exact value?" with yes/no + certainty.

    Args:
        field_name: Name of the field being verified
        field_value: The extracted value to verify
        document_text: Document text excerpt
        llm_router: LLM router instance

    Returns:
        (agreed, certainty) tuple
    """
    prompt = VERIFICATION_PROMPT_TEMPLATE.format(
        field_name=field_name,
        field_value=field_value,
        document_excerpt=document_text[:2000],
    )

    try:
        result = await llm_router.complete(
            task_type="verification",
            prompt=prompt,
            schema={
                "type": "object",
                "properties": {
                    "agreed": {"type": "boolean"},
                    "certainty": {"type": "number"},
                },
            },
        )

        response_text = result.get("text", "{}")
        import json
        # Strip markdown fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        parsed = json.loads(text)
        agreed = bool(parsed.get("agreed", False))
        certainty = float(parsed.get("certainty", 0.5))
        return agreed, max(0.0, min(certainty, 1.0))

    except Exception as e:
        logger.warning("Verification LLM call failed: %s", e)
        # On failure, assume disagreement (conservative)
        return False, 0.5
