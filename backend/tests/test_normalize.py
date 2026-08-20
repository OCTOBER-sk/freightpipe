"""Tests for normalization — dates, money, units, accessorial vocab."""
from __future__ import annotations

from datetime import date

import pytest

from freightpipe.pipeline.normalize import (
    normalize_date,
    normalize_money,
    normalize_weight,
    normalize_accessorial,
    normalize_extracted_fields,
    CONTROLLED_VOCAB,
    ACCESSORIAL_SYNONYMS,
)


# ---------------------------------------------------------------------------
# Date normalization tests
# ---------------------------------------------------------------------------

class TestNormalizeDate:
    def test_iso_format_passthrough(self):
        assert normalize_date("2026-08-20") == "2026-08-20"

    def test_us_format_mm_dd_yyyy(self):
        assert normalize_date("08/20/2026") == "2026-08-20"

    def test_us_format_mm_dd_yy(self):
        assert normalize_date("08/20/26") == "2026-08-20"

    def test_dash_format(self):
        assert normalize_date("08-20-2026") == "2026-08-20"

    def test_long_month_format(self):
        assert normalize_date("August 20, 2026") == "2026-08-20"

    def test_short_month_format(self):
        assert normalize_date("Aug 20, 2026") == "2026-08-20"

    def test_yyyy_mm_dd_slash(self):
        assert normalize_date("2026/08/20") == "2026-08-20"

    def test_none_returns_none(self):
        assert normalize_date(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_date("") is None

    def test_invalid_date_returns_none(self):
        assert normalize_date("not a date") is None

    def test_invalid_month_day(self):
        assert normalize_date("13/32/2026") is None

    def test_ambiguous_date_prefers_us(self):
        # 03/04/25 should be March 4, 2025 (US MM/DD)
        result = normalize_date("03/04/25")
        assert result == "2025-03-04"

    def test_with_reference_date(self):
        # reference_date doesn't affect unambiguous dates
        ref = date(2026, 8, 20)
        assert normalize_date("2026-08-20", reference_date=ref) == "2026-08-20"


# ---------------------------------------------------------------------------
# Money normalization tests
# ---------------------------------------------------------------------------

class TestNormalizeMoney:
    def test_dollar_string(self):
        result = normalize_money("$1,850.00")
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_number_string(self):
        result = normalize_money("1850.00")
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_integer(self):
        result = normalize_money(1850)
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_float(self):
        result = normalize_money(1850.50)
        assert result == {"amount": 1850.50, "currency": "USD"}

    def test_dict_passthrough(self):
        result = normalize_money({"amount": 1850.00, "currency": "USD"})
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_dict_without_currency(self):
        result = normalize_money({"amount": 1850.00})
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_none_returns_none(self):
        assert normalize_money(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_money("") is None

    def test_negative_with_parens(self):
        result = normalize_money("($150.00)")
        assert result == {"amount": -150.00, "currency": "USD"}

    def test_negative_with_minus(self):
        result = normalize_money("-$150.00")
        assert result == {"amount": -150.00, "currency": "USD"}

    def test_strips_currency_text(self):
        result = normalize_money("1850.00 USD")
        assert result == {"amount": 1850.00, "currency": "USD"}

    def test_zero(self):
        result = normalize_money("$0.00")
        assert result == {"amount": 0.00, "currency": "USD"}

    def test_large_number(self):
        result = normalize_money("$1,234,567.89")
        assert result == {"amount": 1234567.89, "currency": "USD"}


# ---------------------------------------------------------------------------
# Weight normalization tests
# ---------------------------------------------------------------------------

class TestNormalizeWeight:
    def test_lbs_string(self):
        assert normalize_weight("15000 lbs") == 15000.0

    def test_lbs_number(self):
        assert normalize_weight(15000) == 15000.0

    def test_kg_conversion(self):
        result = normalize_weight("1000 kg")
        assert abs(result - 2204.62) < 0.01

    def test_kg_number_with_unit(self):
        result = normalize_weight(1000, unit="kg")
        assert abs(result - 2204.62) < 0.01

    def test_tons_conversion(self):
        assert normalize_weight("1 ton") == 2000.0

    def test_no_unit_defaults_to_lbs(self):
        assert normalize_weight("15000") == 15000.0

    def test_none_returns_none(self):
        assert normalize_weight(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_weight("") is None

    def test_comma_separated_number(self):
        assert normalize_weight("15,000 lbs") == 15000.0

    def test_float_weight(self):
        assert normalize_weight("15.5 lbs") == 15.5

    def test_unknown_unit_defaults_to_lbs(self):
        assert normalize_weight("15000 widgets") == 15000.0


# ---------------------------------------------------------------------------
# Accessorial vocabulary tests
# ---------------------------------------------------------------------------

class TestNormalizeAccessorial:
    def test_direct_match(self):
        result = normalize_accessorial("detention")
        assert result["type"] == "detention"
        assert result["raw_label"] == "detention"

    def test_synonym_match(self):
        result = normalize_accessorial("detention charge")
        assert result["type"] == "detention"
        assert result["raw_label"] == "detention charge"

    def test_lumper_synonym(self):
        result = normalize_accessorial("unloading fee")
        assert result["type"] == "lumper"

    def test_layover_synonym(self):
        result = normalize_accessorial("overnight stay")
        assert result["type"] == "layover"

    def test_stop_off_synonym(self):
        result = normalize_accessorial("extra stop")
        assert result["type"] == "stop_off"

    def test_tarp_synonym(self):
        result = normalize_accessorial("tarpaulin")
        assert result["type"] == "tarp"

    def test_unknown_maps_to_other(self):
        result = normalize_accessorial("custom fee")
        assert result["type"] == "other"
        assert result["raw_label"] == "custom fee"

    def test_none_returns_other(self):
        result = normalize_accessorial(None)
        assert result["type"] == "other"

    def test_empty_string_returns_other(self):
        result = normalize_accessorial("")
        assert result["type"] == "other"

    def test_case_insensitive(self):
        result = normalize_accessorial("DETENTION")
        assert result["type"] == "detention"

    def test_all_controlled_vocab_types_present(self):
        """Verify all controlled vocab types can be reached."""
        for vocab_type in CONTROLLED_VOCAB:
            # Find a synonym that maps to this type
            found = False
            for synonym, mapped_type in ACCESSORIAL_SYNONYMS.items():
                if mapped_type == vocab_type:
                    result = normalize_accessorial(synonym)
                    assert result["type"] == vocab_type
                    found = True
                    break
            if vocab_type != "other":
                assert found, f"No synonym found for controlled vocab type: {vocab_type}"


# ---------------------------------------------------------------------------
# Full normalization pipeline tests
# ---------------------------------------------------------------------------

class TestNormalizeExtractedFields:
    def test_rate_con_normalization(self):
        fields = {
            "load_number": "RC-48213",
            "pickup_date": "08/22/2026",
            "delivery_date": "08/24/2026",
            "linehaul_rate": "$1,850.00",
            "fuel_surcharge": "$275.00",
            "total_rate": "$2,125.00",
        }
        result = normalize_extracted_fields(fields, "rate_con")
        assert result["pickup_date"] == "2026-08-22"
        assert result["delivery_date"] == "2026-08-24"
        assert result["linehaul_rate"] == {"amount": 1850.00, "currency": "USD"}
        assert result["fuel_surcharge"] == {"amount": 275.00, "currency": "USD"}
        assert result["total_rate"] == {"amount": 2125.00, "currency": "USD"}

    def test_bol_normalization(self):
        fields = {
            "bol_number": "BOL-2026-55421",
            "pickup_date": "2026-08-22",
            "weight": "15,000 lbs",
            "pieces": 42,
        }
        result = normalize_extracted_fields(fields, "bol")
        assert result["weight"] == 15000.0
        assert result["pieces"] == 42

    def test_invoice_normalization(self):
        fields = {
            "invoice_number": "INV-2026-33100",
            "total_amount": "$2,275.00",
            "due_date": "09/23/2026",
            "line_items": [
                {"category": "linehaul", "amount": "$1,850.00"},
                {"category": "fuel", "amount": "$275.00"},
            ],
        }
        result = normalize_extracted_fields(fields, "invoice")
        assert result["total_amount"] == {"amount": 2275.00, "currency": "USD"}
        assert result["due_date"] == "2026-09-23"
        assert result["line_items"][0]["amount"] == {"amount": 1850.00, "currency": "USD"}

    def test_accessorials_normalization(self):
        fields = {
            "accessorials": [
                {"type": "detention charge", "amount": "$150.00"},
                {"type": "lumper fee", "amount": "$75.00"},
            ],
        }
        result = normalize_extracted_fields(fields, "rate_con")
        assert result["accessorials"][0]["type"] == "detention"
        assert result["accessorials"][1]["type"] == "lumper"

    def test_passthrough_unknown_fields(self):
        fields = {"custom_field": "custom_value"}
        result = normalize_extracted_fields(fields, "rate_con")
        assert result["custom_field"] == "custom_value"
