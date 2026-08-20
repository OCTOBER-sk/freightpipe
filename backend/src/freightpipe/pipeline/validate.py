"""Domain validation — required fields, date/money sanity (BACKEND.md §5.5).

Deterministic rule checks run after normalization, before matching:
- Required fields present per doc type (per §3.2 required: true)
- Date sanity: pickup <= delivery <= due date
- Money sanity: total ≈ linehaul + fuel + accessorials within $0.02 tolerance
- Load number cross-reference
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Money tolerance for rounding (BACKEND.md §5.5)
MONEY_TOLERANCE = 0.02

# ---------------------------------------------------------------------------
# Required fields per doc type (BACKEND.md §3.2)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: dict[str, list[str]] = {
    "rate_con": [
        "load_number",
        "broker_name",
        "carrier_name",
        "shipper",
        "consignee",
        "pickup",
        "delivery",
        "linehaul_rate",
        "total_rate",
    ],
    "bol": [
        "bol_number",
        "shipper",
        "consignee",
        "pickup_date",
        "freight_description",
        "weight",
        "pieces",
        "signature_present",
    ],
    "pod": [
        "delivery_date",
        "recipient_name",
        "signature_present",
    ],
    "invoice": [
        "invoice_number",
        "load_number",
        "carrier_name",
        "line_items",
        "total_amount",
    ],
}


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """A single validation issue."""
    field: str
    rule: str  # required | date_sanity | money_sanity | load_number
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    """Result of document validation."""
    is_valid: bool
    issues: list[ValidationIssue]
    doc_type: str


# ---------------------------------------------------------------------------
# Required fields validation
# ---------------------------------------------------------------------------

def validate_required_fields(
    fields: dict[str, Any],
    doc_type: str,
) -> list[ValidationIssue]:
    """Check that all required fields are present and non-null.

    Per BACKEND.md §5.5: required fields check per doc type (§3.2).
    """
    issues: list[ValidationIssue] = []
    required = REQUIRED_FIELDS.get(doc_type, [])

    for field_name in required:
        value = fields.get(field_name)
        if value is None:
            issues.append(ValidationIssue(
                field=field_name,
                rule="required",
                message=f"Required field '{field_name}' is missing for {doc_type}",
                severity="error",
            ))
        elif isinstance(value, str) and not value.strip():
            issues.append(ValidationIssue(
                field=field_name,
                rule="required",
                message=f"Required field '{field_name}' is empty for {doc_type}",
                severity="error",
            ))
        elif isinstance(value, dict):
            # Check nested required objects (shipper, consignee, etc.)
            if not any(v is not None for v in value.values()):
                issues.append(ValidationIssue(
                    field=field_name,
                    rule="required",
                    message=f"Required field '{field_name}' is empty object for {doc_type}",
                    severity="error",
                ))

    return issues


# ---------------------------------------------------------------------------
# Date sanity validation
# ---------------------------------------------------------------------------

def _parse_date(value: Any) -> date | None:
    """Parse a date value (string or date object) to a date."""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def validate_date_sanity(fields: dict[str, Any], doc_type: str) -> list[ValidationIssue]:
    """Validate date ordering: pickup <= delivery <= due date.

    Per BACKEND.md §5.5:
    - pickup date <= delivery date
    - delivery date <= invoice due date (warn, not hard-fail, since due dates
      can legitimately precede delivery in prepay terms)
    """
    issues: list[ValidationIssue] = []

    # Get dates from fields
    pickup_date = _parse_date(fields.get("pickup_date"))
    if not pickup_date and isinstance(fields.get("pickup"), dict):
        pickup_date = _parse_date(fields["pickup"].get("date"))

    delivery_date = _parse_date(fields.get("delivery_date"))
    if not delivery_date and isinstance(fields.get("delivery"), dict):
        delivery_date = _parse_date(fields["delivery"].get("date"))

    due_date = _parse_date(fields.get("due_date"))

    # pickup <= delivery
    if pickup_date and delivery_date:
        if pickup_date > delivery_date:
            issues.append(ValidationIssue(
                field="pickup_date",
                rule="date_sanity",
                message=f"Pickup date ({pickup_date}) is after delivery date ({delivery_date})",
                severity="error",
            ))

    # delivery <= due date (warning, not error)
    if delivery_date and due_date:
        if delivery_date > due_date:
            issues.append(ValidationIssue(
                field="due_date",
                rule="date_sanity",
                message=f"Delivery date ({delivery_date}) is after invoice due date ({due_date}) — may be valid for prepay terms",
                severity="warning",
            ))

    return issues


# ---------------------------------------------------------------------------
# Money sanity validation
# ---------------------------------------------------------------------------

def _extract_money_amount(money_value: Any) -> float | None:
    """Extract numeric amount from a money value."""
    if money_value is None:
        return None
    if isinstance(money_value, (int, float)):
        return float(money_value)
    if isinstance(money_value, dict):
        amount = money_value.get("amount")
        if amount is not None:
            try:
                return float(amount)
            except (ValueError, TypeError):
                return None
    return None


def validate_money_sanity(fields: dict[str, Any], doc_type: str) -> list[ValidationIssue]:
    """Validate money totals: total ≈ linehaul + fuel + accessorials.

    Per BACKEND.md §5.5:
    - total_rate ≈ linehaul_rate + fuel_surcharge + sum(accessorials) within $0.02
    - Mismatch becomes a validation_failed review reason
    """
    issues: list[ValidationIssue] = []

    # Only applies to rate_con and invoice
    if doc_type not in ("rate_con", "invoice"):
        return issues

    # Get total
    total = _extract_money_amount(fields.get("total_rate") or fields.get("total_amount"))
    if total is None:
        return issues

    # Get components
    linehaul = _extract_money_amount(fields.get("linehaul_rate")) or 0.0
    fuel = _extract_money_amount(fields.get("fuel_surcharge")) or 0.0

    # Sum accessorials
    accessorial_total = 0.0
    accessorials = fields.get("accessorials", [])
    if isinstance(accessorials, list):
        for acc in accessorials:
            if isinstance(acc, dict):
                amount = _extract_money_amount(acc.get("amount"))
                if amount is not None:
                    accessorial_total += amount

    # Sum line items for invoices
    if doc_type == "invoice":
        line_items = fields.get("line_items", [])
        if isinstance(line_items, list) and not accessorials:
            for item in line_items:
                if isinstance(item, dict):
                    amount = _extract_money_amount(item.get("amount"))
                    if amount is not None:
                        accessorial_total += amount

    expected_total = linehaul + fuel + accessorial_total
    difference = abs(total - expected_total)

    if difference > MONEY_TOLERANCE:
        issues.append(ValidationIssue(
            field="total_rate" if doc_type == "rate_con" else "total_amount",
            rule="money_sanity",
            message=(
                f"Total ({total:.2f}) does not match sum of components "
                f"({expected_total:.2f}): linehaul={linehaul:.2f} + fuel={fuel:.2f} + "
                f"accessorials={accessorial_total:.2f} (difference: {difference:.2f})"
            ),
            severity="error",
        ))

    return issues


# ---------------------------------------------------------------------------
# Load number cross-reference
# ---------------------------------------------------------------------------

def validate_load_number_cross_reference(
    documents: list[dict[str, Any]],
) -> list[ValidationIssue]:
    """Validate that load numbers match across documents in a job.

    Per BACKEND.md §5.5:
    - If a load number appears on multiple documents, they must match exactly
    - Mismatch is flagged before shipment grouping proceeds
    """
    issues: list[ValidationIssue] = []

    # Collect load numbers per document
    load_numbers: dict[str, list[str]] = {}  # load_number -> [doc_ids]

    for doc in documents:
        doc_id = doc.get("id", "unknown")
        fields = doc.get("fields", {})
        load_num = fields.get("load_number")
        if load_num and isinstance(load_num, str) and load_num.strip():
            load_num = load_num.strip()
            if load_num not in load_numbers:
                load_numbers[load_num] = []
            load_numbers[load_num].append(doc_id)

    # If multiple different load numbers found, flag
    if len(load_numbers) > 1:
        load_list = list(load_numbers.keys())
        issues.append(ValidationIssue(
            field="load_number",
            rule="load_number",
            message=(
                f"Multiple different load numbers found across documents: "
                f"{', '.join(load_list)}. Documents may not belong to the same shipment."
            ),
            severity="error",
        ))

    return issues


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------

def validate_document(
    fields: dict[str, Any],
    doc_type: str,
) -> ValidationResult:
    """Validate a single document against domain rules.

    Per BACKEND.md §5.5: deterministic rule checks after normalization.

    Args:
        fields: Normalized field values
        doc_type: Document type

    Returns:
        ValidationResult with issues
    """
    issues: list[ValidationIssue] = []

    # 1. Required fields
    issues.extend(validate_required_fields(fields, doc_type))

    # 2. Date sanity
    issues.extend(validate_date_sanity(fields, doc_type))

    # 3. Money sanity
    issues.extend(validate_money_sanity(fields, doc_type))

    # Determine if valid (no errors, warnings are ok)
    has_errors = any(issue.severity == "error" for issue in issues)

    return ValidationResult(
        is_valid=not has_errors,
        issues=issues,
        doc_type=doc_type,
    )


def validate_job_documents(
    documents: list[dict[str, Any]],
) -> ValidationResult:
    """Validate all documents in a job, including cross-document checks.

    Args:
        documents: List of document dicts with 'id', 'doc_type', 'fields'

    Returns:
        Combined ValidationResult
    """
    all_issues: list[ValidationIssue] = []

    # Validate each document individually
    for doc in documents:
        doc_type = doc.get("doc_type", "unknown")
        fields = doc.get("fields", {})
        result = validate_document(fields, doc_type)
        all_issues.extend(result.issues)

    # Cross-document validation
    all_issues.extend(validate_load_number_cross_reference(documents))

    has_errors = any(issue.severity == "error" for issue in all_issues)

    return ValidationResult(
        is_valid=not has_errors,
        issues=all_issues,
        doc_type="job",
    )
