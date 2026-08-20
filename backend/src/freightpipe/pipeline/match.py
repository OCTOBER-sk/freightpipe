"""3-way match engine — rate-con ↔ BOL/POD ↔ invoice (BACKEND.md §5.6).

For each line item category (linehaul, fuel_surcharge, each accessorial type,
weight, pieces):
  1. Pull value from each source doc that has it
  2. Compare pairwise where both exist
  3. Write one row per line item per shipment to match_results
  4. Any discrepancy_flag != none -> review_required
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from freightpipe.models.schemas import DiscrepancyFlag

logger = logging.getLogger(__name__)

# Money tolerance for rate delta detection ($0.02 for rounding, per §5.5)
MONEY_TOLERANCE = 0.02

# Weight/pieces variance tolerance (percentage)
WEIGHT_VARIANCE_TOLERANCE = 0.01  # 1%
PIECES_VARIANCE_TOLERANCE = 0.0   # exact match required for pieces


# ---------------------------------------------------------------------------
# Match result dataclass
# ---------------------------------------------------------------------------

@dataclass
class MatchLineItem:
    """A single line item match result."""
    line_item: str
    rate_con_value: str | None = None
    bol_pod_value: str | None = None
    invoice_value: str | None = None
    discrepancy_flag: DiscrepancyFlag = DiscrepancyFlag.NONE
    discrepancy_amount: float | None = None


# ---------------------------------------------------------------------------
# Value extraction helpers
# ---------------------------------------------------------------------------

def _extract_money_amount(value: Any) -> float | None:
    """Extract numeric amount from a money value (float, int, or dict)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        amount = value.get("amount")
        if amount is not None:
            try:
                return float(amount)
            except (ValueError, TypeError):
                return None
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _extract_numeric(value: Any) -> float | None:
    """Extract a numeric value (weight, pieces, etc.)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _money_str(amount: float | None) -> str | None:
    """Format a money amount as a string for storage."""
    if amount is None:
        return None
    return f"{amount:.2f}"


def _numeric_str(value: float | None) -> str | None:
    """Format a numeric value as a string for storage."""
    if value is None:
        return None
    if value == int(value):
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------------------
# Accessorial extraction
# ---------------------------------------------------------------------------

def _get_accessorials_map(fields: dict[str, Any]) -> dict[str, float]:
    """Extract accessorial type -> amount mapping from document fields.

    Handles both:
    - rate_con format: accessorials = [{"type": "detention", "amount": {...}}]
    - invoice format: line_items = [{"category": "detention", "amount": {...}}]
    """
    result: dict[str, float] = {}

    # Rate-con accessorials
    accessorials = fields.get("accessorials", [])
    if isinstance(accessorials, list):
        for acc in accessorials:
            if isinstance(acc, dict):
                acc_type = acc.get("type", "other")
                amount = _extract_money_amount(acc.get("amount"))
                if amount is not None:
                    result[acc_type] = amount

    # Invoice line items (accessorials are non-linehaul, non-fuel items)
    line_items = fields.get("line_items", [])
    if isinstance(line_items, list):
        for item in line_items:
            if isinstance(item, dict):
                category = item.get("category", "").lower()
                # Skip linehaul and fuel — they're handled separately
                if category in ("linehaul", "fuel", "fuel_surcharge"):
                    continue
                amount = _extract_money_amount(item.get("amount"))
                if amount is not None:
                    # Normalize category name
                    normalized = category.replace(" ", "_").replace("-", "_")
                    result[normalized] = amount

    return result


# ---------------------------------------------------------------------------
# Core match logic
# ---------------------------------------------------------------------------

def match_shipment(
    rate_con_fields: dict[str, Any] | None,
    bol_fields: dict[str, Any] | None,
    pod_fields: dict[str, Any] | None,
    invoice_fields: dict[str, Any] | None,
) -> list[MatchLineItem]:
    """Run 3-way match for a shipment.

    Per BACKEND.md §5.6:
    - Compares rate-con ↔ BOL/POD ↔ invoice
    - Returns one MatchLineItem per line item category

    Args:
        rate_con_fields: Normalized fields from rate confirmation (or None)
        bol_fields: Normalized fields from BOL (or None)
        pod_fields: Normalized fields from POD (or None)
        invoice_fields: Normalized fields from invoice (or None)

    Returns:
        List of MatchLineItem for each line item category
    """
    results: list[MatchLineItem] = []

    # --- Linehaul ---
    results.append(_match_money_line(
        line_item="linehaul",
        rate_con_value=_extract_money_amount(
            rate_con_fields.get("linehaul_rate") if rate_con_fields else None
        ),
        invoice_value=_get_invoice_line_amount(invoice_fields, "linehaul"),
    ))

    # --- Fuel surcharge ---
    results.append(_match_money_line(
        line_item="fuel_surcharge",
        rate_con_value=_extract_money_amount(
            rate_con_fields.get("fuel_surcharge") if rate_con_fields else None
        ),
        invoice_value=_get_invoice_line_amount(invoice_fields, "fuel_surcharge")
            or _get_invoice_line_amount(invoice_fields, "fuel"),
    ))

    # --- Accessorials ---
    rc_accessorials = _get_accessorials_map(rate_con_fields) if rate_con_fields else {}
    inv_accessorials = _get_accessorials_map(invoice_fields) if invoice_fields else {}

    all_accessorial_types = set(rc_accessorials.keys()) | set(inv_accessorials.keys())
    for acc_type in sorted(all_accessorial_types):
        rc_amount = rc_accessorials.get(acc_type)
        inv_amount = inv_accessorials.get(acc_type)

        if rc_amount is not None and inv_amount is not None:
            # Both exist — compare
            diff = abs(inv_amount - rc_amount)
            if diff > MONEY_TOLERANCE:
                results.append(MatchLineItem(
                    line_item=acc_type,
                    rate_con_value=_money_str(rc_amount),
                    invoice_value=_money_str(inv_amount),
                    discrepancy_flag=DiscrepancyFlag.RATE_DELTA,
                    discrepancy_amount=round(inv_amount - rc_amount, 2),
                ))
            else:
                results.append(MatchLineItem(
                    line_item=acc_type,
                    rate_con_value=_money_str(rc_amount),
                    invoice_value=_money_str(inv_amount),
                ))
        elif rc_amount is not None and inv_amount is None:
            # On rate-con but not invoice -> missing_accessorial
            results.append(MatchLineItem(
                line_item=acc_type,
                rate_con_value=_money_str(rc_amount),
                discrepancy_flag=DiscrepancyFlag.MISSING_ACCESSORIAL,
            ))
        elif rc_amount is None and inv_amount is not None:
            # On invoice but not rate-con -> extra_accessorial
            results.append(MatchLineItem(
                line_item=acc_type,
                invoice_value=_money_str(inv_amount),
                discrepancy_flag=DiscrepancyFlag.EXTRA_ACCESSORIAL,
                discrepancy_amount=round(inv_amount, 2),
            ))

    # --- Weight (BOL vs POD) ---
    bol_weight = _extract_numeric(
        bol_fields.get("weight") if bol_fields else None
    )
    pod_weight = _extract_numeric(
        pod_fields.get("weight") if pod_fields else None
    )
    results.append(_match_quantity_line(
        line_item="weight",
        bol_value=bol_weight,
        pod_value=pod_weight,
        variance_flag=DiscrepancyFlag.WEIGHT_VARIANCE,
        tolerance=WEIGHT_VARIANCE_TOLERANCE,
    ))

    # --- Pieces (BOL vs POD) ---
    bol_pieces = _extract_numeric(
        bol_fields.get("pieces") if bol_fields else None
    )
    pod_pieces = _extract_numeric(
        pod_fields.get("pieces") if pod_fields else None
    )
    results.append(_match_quantity_line(
        line_item="pieces",
        bol_value=bol_pieces,
        pod_value=pod_pieces,
        variance_flag=DiscrepancyFlag.PIECES_VARIANCE,
        tolerance=PIECES_VARIANCE_TOLERANCE,
    ))

    return results


def _get_invoice_line_amount(
    invoice_fields: dict[str, Any] | None,
    category: str,
) -> float | None:
    """Get amount for a specific line item category from invoice line_items."""
    if not invoice_fields:
        return None

    line_items = invoice_fields.get("line_items", [])
    if not isinstance(line_items, list):
        return None

    for item in line_items:
        if isinstance(item, dict):
            item_category = item.get("category", "").lower().replace(" ", "_").replace("-", "_")
            if item_category == category:
                return _extract_money_amount(item.get("amount"))

    return None


def _match_money_line(
    line_item: str,
    rate_con_value: float | None,
    invoice_value: float | None,
) -> MatchLineItem:
    """Compare a money line item between rate-con and invoice."""
    if rate_con_value is None and invoice_value is None:
        return MatchLineItem(line_item=line_item)

    if rate_con_value is not None and invoice_value is not None:
        diff = abs(invoice_value - rate_con_value)
        if diff > MONEY_TOLERANCE:
            return MatchLineItem(
                line_item=line_item,
                rate_con_value=_money_str(rate_con_value),
                invoice_value=_money_str(invoice_value),
                discrepancy_flag=DiscrepancyFlag.RATE_DELTA,
                discrepancy_amount=round(invoice_value - rate_con_value, 2),
            )
        return MatchLineItem(
            line_item=line_item,
            rate_con_value=_money_str(rate_con_value),
            invoice_value=_money_str(invoice_value),
        )

    # Only one side has a value — not a discrepancy, just incomplete data
    return MatchLineItem(
        line_item=line_item,
        rate_con_value=_money_str(rate_con_value),
        invoice_value=_money_str(invoice_value),
    )


def _match_quantity_line(
    line_item: str,
    bol_value: float | None,
    pod_value: float | None,
    variance_flag: DiscrepancyFlag,
    tolerance: float,
) -> MatchLineItem:
    """Compare a quantity line item between BOL and POD."""
    if bol_value is None and pod_value is None:
        return MatchLineItem(line_item=line_item)

    if bol_value is not None and pod_value is not None:
        # Check variance
        if bol_value != 0:
            variance_pct = abs(pod_value - bol_value) / abs(bol_value)
        elif pod_value != 0:
            variance_pct = 1.0  # 100% variance from zero
        else:
            variance_pct = 0.0

        if variance_pct > tolerance:
            return MatchLineItem(
                line_item=line_item,
                bol_pod_value=_numeric_str(bol_value),
                invoice_value=_numeric_str(pod_value),
                discrepancy_flag=variance_flag,
                discrepancy_amount=round(pod_value - bol_value, 2),
            )
        return MatchLineItem(
            line_item=line_item,
            bol_pod_value=_numeric_str(bol_value),
            invoice_value=_numeric_str(pod_value),
        )

    # Only one side has a value
    return MatchLineItem(
        line_item=line_item,
        bol_pod_value=_numeric_str(bol_value),
        invoice_value=_numeric_str(pod_value),
    )


# ---------------------------------------------------------------------------
# Review-required check
# ---------------------------------------------------------------------------

def has_discrepancies(match_results: list[MatchLineItem]) -> tuple[bool, list[str]]:
    """Check if any match results have discrepancies.

    Returns:
        (review_required, list_of_reason_strings)
    """
    reasons: list[str] = []
    for item in match_results:
        if item.discrepancy_flag != DiscrepancyFlag.NONE:
            reasons.append(
                f"discrepancy: {item.discrepancy_flag.value} on {item.line_item}"
            )
    return len(reasons) > 0, reasons


# ---------------------------------------------------------------------------
# Serialization helpers (for DB storage)
# ---------------------------------------------------------------------------

def match_results_to_dicts(
    match_results: list[MatchLineItem],
    shipment_id: Any,
) -> list[dict[str, Any]]:
    """Convert MatchLineItem list to dicts suitable for DB insertion."""
    return [
        {
            "shipment_id": shipment_id,
            "line_item": item.line_item,
            "rate_con_value": item.rate_con_value,
            "bol_pod_value": item.bol_pod_value,
            "invoice_value": item.invoice_value,
            "discrepancy_flag": item.discrepancy_flag.value,
            "discrepancy_amount": item.discrepancy_amount,
        }
        for item in match_results
    ]
