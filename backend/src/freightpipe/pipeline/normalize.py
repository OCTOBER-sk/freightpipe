"""Normalization — dates, money, units, accessorial vocab (BACKEND.md §5.4).

100% deterministic, no LLM.
- Dates -> ISO 8601 (reference_date = job submission)
- Money -> {amount: float, currency: USD}
- Units -> weight to lbs
- Accessorial vocabulary mapping (controlled vocab + synonym table)
"""
from __future__ import annotations

import re
from datetime import datetime, date
from typing import Any

# ---------------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------------

# Common date formats in freight documents
DATE_FORMATS: list[str] = [
    "%Y-%m-%d",       # 2026-08-20
    "%m/%d/%Y",        # 08/20/2026
    "%m/%d/%y",        # 08/20/26
    "%m-%d-%Y",        # 08-20-2026
    "%m-%d-%y",        # 08-20-26
    "%d/%m/%Y",        # 20/08/2026 (ambiguous, prefer US)
    "%d/%m/%y",        # 20/08/26
    "%B %d, %Y",       # August 20, 2026
    "%b %d, %Y",       # Aug 20, 2026
    "%B %d %Y",        # August 20 2026
    "%b %d %Y",        # Aug 20 2026
    "%Y/%m/%d",        # 2026/08/20
    "%d-%m-%Y",        # 20-08-2026
    "%d-%m-%y",        # 20-08-26
]


def normalize_date(value: str | None, reference_date: date | None = None) -> str | None:
    """Normalize a date string to ISO 8601 (YYYY-MM-DD).

    Per BACKEND.md §5.4:
    - Dates -> ISO 8601
    - Resolved against reference_date (job submission date) for ambiguous formats
    - US MM/DD preferred unless carrier's address region indicates otherwise

    Args:
        value: Raw date string from extraction
        reference_date: Job submission date for resolving ambiguous formats

    Returns:
        ISO 8601 date string or None if unparseable
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Already ISO 8601
    iso_match = re.match(r"^(\d{4}-\d{2}-\d{2})$", value)
    if iso_match:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            return None

    # Try each format
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            # Handle 2-digit years: if year < 100, assume 2000s
            if parsed.year < 100:
                parsed = parsed.replace(year=parsed.year + 2000)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try to extract date components with regex
    # Pattern: various separators between numbers
    date_match = re.match(
        r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})",
        value,
    )
    if date_match:
        part1, part2, part3 = date_match.groups()
        # Determine if MM/DD/YYYY or DD/MM/YYYY
        # Default to US MM/DD per spec
        if len(part3) == 2:
            year = int(part3) + 2000
        else:
            year = int(part3)

        month = int(part1)
        day = int(part2)

        # Sanity: if month > 12, swap (likely DD/MM)
        if month > 12 and day <= 12:
            month, day = day, month

        try:
            parsed = date(year, month, day)
            return parsed.isoformat()
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# Money normalization
# ---------------------------------------------------------------------------

def normalize_money(value: Any) -> dict[str, Any] | None:
    """Normalize money to {amount: float, currency: USD}.

    Per BACKEND.md §5.4:
    - Strip currency symbols/commas
    - Store as {"amount": float, "currency": "USD"}

    Args:
        value: Raw money value (string, number, or dict)

    Returns:
        {"amount": float, "currency": "USD"} or None if unparseable
    """
    if value is None:
        return None

    # Already a dict with amount
    if isinstance(value, dict):
        amount = value.get("amount")
        currency = value.get("currency", "USD")
        if amount is not None:
            try:
                return {"amount": round(float(amount), 2), "currency": currency}
            except (ValueError, TypeError):
                return None
        return None

    # Numeric value
    if isinstance(value, (int, float)):
        return {"amount": round(float(value), 2), "currency": "USD"}

    # String value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # Strip currency symbols and whitespace
        cleaned = re.sub(r"[$€£¥]", "", value)
        cleaned = cleaned.strip()

        # Handle negative: parentheses or leading minus
        negative = False
        if cleaned.startswith("(") and cleaned.endswith(")"):
            negative = True
            cleaned = cleaned[1:-1]
        elif cleaned.startswith("-"):
            negative = True
            cleaned = cleaned[1:]

        # Remove commas
        cleaned = cleaned.replace(",", "")

        # Remove "USD" or other currency text
        cleaned = re.sub(r"\b(USD|CAD|MXN)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        try:
            amount = float(cleaned)
            if negative:
                amount = -amount
            return {"amount": round(amount, 2), "currency": "USD"}
        except ValueError:
            return None

    return None


# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------

# Weight conversion factors to pounds
WEIGHT_CONVERSIONS: dict[str, float] = {
    "lbs": 1.0,
    "lb": 1.0,
    "pounds": 1.0,
    "pound": 1.0,
    "kg": 2.20462,
    "kgs": 2.20462,
    "kilograms": 2.20462,
    "kilogram": 2.20462,
    "tons": 2000.0,
    "ton": 2000.0,
    "oz": 0.0625,
    "ounces": 0.0625,
}


def normalize_weight(value: Any, unit: str | None = None) -> float | None:
    """Normalize weight to pounds (lbs).

    Per BACKEND.md §5.4:
    - Weight always normalized to lbs
    - Flag but don't silently convert if source unit is ambiguous

    Args:
        value: Raw weight value (string or number)
        unit: Optional unit string (e.g., "lbs", "kg")

    Returns:
        Weight in lbs or None if unparseable
    """
    if value is None:
        return None

    # Extract numeric value
    if isinstance(value, (int, float)):
        numeric_value = float(value)
    elif isinstance(value, str):
        # Try to extract number and optional unit from string
        value = value.strip()
        if not value:
            return None

        # Pattern: number followed by optional unit
        match = re.match(r"([\d,]+\.?\d*)\s*([a-zA-Z]*)", value)
        if not match:
            return None

        num_str = match.group(1).replace(",", "")
        try:
            numeric_value = float(num_str)
        except ValueError:
            return None

        # Extract unit from string if not provided
        if unit is None and match.group(2):
            unit = match.group(2).lower()
    else:
        return None

    # Default to lbs if no unit specified
    if unit is None:
        unit = "lbs"

    unit = unit.lower().strip()

    # Look up conversion factor
    factor = WEIGHT_CONVERSIONS.get(unit)
    if factor is None:
        # Unknown unit, assume lbs
        return round(numeric_value, 2)

    return round(numeric_value * factor, 2)


# ---------------------------------------------------------------------------
# Accessorial vocabulary mapping
# ---------------------------------------------------------------------------

# Controlled vocabulary (BACKEND.md §5.4)
CONTROLLED_VOCAB: list[str] = [
    "detention",
    "layover",
    "lumper",
    "stop_off",
    "tarp",
    "other",
]

# Synonym table: maps common carrier-invoice terms to controlled vocab
ACCESSORIAL_SYNONYMS: dict[str, str] = {
    # Detention
    "detention": "detention",
    "detention charge": "detention",
    "detention fee": "detention",
    "driver detention": "detention",
    "truck detention": "detention",
    "wait time": "detention",
    "waiting time": "detention",
    "demurrage": "detention",

    # Layover
    "layover": "layover",
    "layover charge": "layover",
    "layover fee": "layover",
    "overnight": "layover",
    "overnight stay": "layover",
    "overnight parking": "layover",

    # Lumper
    "lumper": "lumper",
    "lumper fee": "lumper",
    "lumper charge": "lumper",
    "unloading fee": "lumper",
    "unloading charge": "lumper",
    "loading fee": "lumper",
    "loading charge": "lumper",
    "warehouse fee": "lumper",
    "hand unload": "lumper",

    # Stop off
    "stop off": "stop_off",
    "stop-off": "stop_off",
    "stop off charge": "stop_off",
    "stop off fee": "stop_off",
    "stop fee": "stop_off",
    "extra stop": "stop_off",
    "additional stop": "stop_off",
    "multi-stop": "stop_off",

    # Tarp
    "tarp": "tarp",
    "tarp charge": "tarp",
    "tarp fee": "tarp",
    "tarping": "tarp",
    "tarpaulin": "tarp",
    "tarps": "tarp",
}


def normalize_accessorial(raw_label: str | None) -> dict[str, str]:
    """Map an accessorial label to controlled vocabulary.

    Per BACKEND.md §5.4:
    - Maps to controlled vocab: detention, layover, lumper, stop_off, tarp, other
    - Unmapped strings kept as "other" with raw_label preserved

    Args:
        raw_label: Raw accessorial label from extraction

    Returns:
        {"type": "controlled_vocab_value", "raw_label": "original"}
    """
    if not raw_label or not isinstance(raw_label, str):
        return {"type": "other", "raw_label": raw_label or ""}

    normalized = raw_label.strip().lower()

    # Direct match
    if normalized in ACCESSORIAL_SYNONYMS:
        return {"type": ACCESSORIAL_SYNONYMS[normalized], "raw_label": raw_label.strip()}

    # Partial match: check if any synonym is a substring
    for synonym, vocab_type in ACCESSORIAL_SYNONYMS.items():
        if synonym in normalized or normalized in synonym:
            return {"type": vocab_type, "raw_label": raw_label.strip()}

    # No match -> other
    return {"type": "other", "raw_label": raw_label.strip()}


# ---------------------------------------------------------------------------
# Main normalization entry point
# ---------------------------------------------------------------------------

def normalize_extracted_fields(
    fields: dict[str, Any],
    doc_type: str,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Normalize all extracted fields for a document.

    Per BACKEND.md §5.4: 100% deterministic, no LLM.

    Args:
        fields: Raw extracted field values
        doc_type: Document type
        reference_date: Job submission date for date normalization

    Returns:
        Normalized field values
    """
    normalized: dict[str, Any] = {}

    for field_name, value in fields.items():
        # Date fields
        if field_name in ("pickup_date", "delivery_date", "due_date"):
            normalized[field_name] = normalize_date(value, reference_date)
            continue

        # Nested date fields (pickup.date, delivery.date)
        if isinstance(value, dict):
            normalized[field_name] = {}
            for sub_key, sub_value in value.items():
                if sub_key == "date":
                    normalized[field_name][sub_key] = normalize_date(sub_value, reference_date)
                elif field_name in ("linehaul_rate", "fuel_surcharge", "total_rate", "total_amount"):
                    normalized[field_name] = normalize_money(value)
                    break
                else:
                    normalized[field_name][sub_key] = sub_value
            continue

        # Money fields
        if field_name in ("linehaul_rate", "fuel_surcharge", "total_rate", "total_amount"):
            normalized[field_name] = normalize_money(value)
            continue

        # Weight fields
        if field_name == "weight":
            normalized[field_name] = normalize_weight(value)
            continue

        # Accessorial fields
        if field_name == "accessorials" and isinstance(value, list):
            normalized[field_name] = [
                normalize_accessorial(item.get("type") if isinstance(item, dict) else item)
                if isinstance(item, (dict, str))
                else item
                for item in value
            ]
            continue

        # Line items with amounts
        if field_name == "line_items" and isinstance(value, list):
            normalized_items = []
            for item in value:
                if isinstance(item, dict):
                    norm_item = dict(item)
                    if "amount" in norm_item:
                        norm_item["amount"] = normalize_money(norm_item["amount"])
                    normalized_items.append(norm_item)
                else:
                    normalized_items.append(item)
            normalized[field_name] = normalized_items
            continue

        # Everything else passes through
        normalized[field_name] = value

    return normalized
