"""Tests for 3-way match engine — all discrepancy flag types, tolerance handling,
multi-line-item matching (BACKEND.md §5.6)."""
from __future__ import annotations

import pytest

from freightpipe.pipeline.match import (
    match_shipment,
    MatchLineItem,
    has_discrepancies,
    match_results_to_dicts,
    _extract_money_amount,
    _extract_numeric,
    _get_accessorials_map,
    MONEY_TOLERANCE,
)
from freightpipe.models.schemas import DiscrepancyFlag


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _rate_con(
    linehaul: float = 1850.0,
    fuel: float = 275.0,
    accessorials: list[dict] | None = None,
) -> dict:
    """Build a minimal rate-con fields dict."""
    fields = {
        "linehaul_rate": {"amount": linehaul, "currency": "USD"},
        "fuel_surcharge": {"amount": fuel, "currency": "USD"},
    }
    if accessorials:
        fields["accessorials"] = accessorials
    return fields


def _invoice(
    linehaul: float = 1850.0,
    fuel: float = 275.0,
    extra_items: list[dict] | None = None,
) -> dict:
    """Build a minimal invoice fields dict."""
    items = [
        {"category": "linehaul", "amount": {"amount": linehaul, "currency": "USD"}},
        {"category": "fuel_surcharge", "amount": {"amount": fuel, "currency": "USD"}},
    ]
    if extra_items:
        items.extend(extra_items)
    return {"line_items": items}


def _bol(weight: float = 15000, pieces: int = 42) -> dict:
    return {"weight": weight, "pieces": pieces}


def _pod(weight: float = 15000, pieces: int = 42) -> dict:
    return {"weight": weight, "pieces": pieces}


# ---------------------------------------------------------------------------
# Value extraction tests
# ---------------------------------------------------------------------------

class TestExtractMoneyAmount:
    def test_float(self):
        assert _extract_money_amount(1850.0) == 1850.0

    def test_int(self):
        assert _extract_money_amount(150) == 150.0

    def test_dict(self):
        assert _extract_money_amount({"amount": 275.50, "currency": "USD"}) == 275.50

    def test_string(self):
        assert _extract_money_amount("$1,850.00") == 1850.0

    def test_none(self):
        assert _extract_money_amount(None) is None

    def test_invalid_string(self):
        assert _extract_money_amount("abc") is None


class TestExtractNumeric:
    def test_float(self):
        assert _extract_numeric(15000.0) == 15000.0

    def test_int(self):
        assert _extract_numeric(42) == 42.0

    def test_string_with_commas(self):
        assert _extract_numeric("15,000") == 15000.0

    def test_none(self):
        assert _extract_numeric(None) is None


# ---------------------------------------------------------------------------
# Accessorial extraction tests
# ---------------------------------------------------------------------------

class TestGetAccessorialsMap:
    def test_rate_con_accessorials(self):
        fields = {
            "accessorials": [
                {"type": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
                {"type": "lumper", "amount": {"amount": 75.0, "currency": "USD"}},
            ],
        }
        result = _get_accessorials_map(fields)
        assert result == {"detention": 150.0, "lumper": 75.0}

    def test_invoice_line_items(self):
        fields = {
            "line_items": [
                {"category": "linehaul", "amount": {"amount": 1850.0, "currency": "USD"}},
                {"category": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
                {"category": "fuel_surcharge", "amount": {"amount": 275.0, "currency": "USD"}},
            ],
        }
        result = _get_accessorials_map(fields)
        assert result == {"detention": 150.0}

    def test_empty(self):
        assert _get_accessorials_map({}) == {}


# ---------------------------------------------------------------------------
# Linehaul match tests
# ---------------------------------------------------------------------------

class TestLinehaulMatch:
    def test_matching_linehaul(self):
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            _invoice(linehaul=1850.0),
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.discrepancy_flag == DiscrepancyFlag.NONE
        assert linehaul.rate_con_value == "1850.00"
        assert linehaul.invoice_value == "1850.00"

    def test_linehaul_rate_delta(self):
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            _invoice(linehaul=1950.0),
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.discrepancy_flag == DiscrepancyFlag.RATE_DELTA
        assert linehaul.discrepancy_amount == 100.0

    def test_linehaul_within_tolerance(self):
        # $0.01 difference is within $0.02 tolerance
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            _invoice(linehaul=1850.01),
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.discrepancy_flag == DiscrepancyFlag.NONE

    def test_linehaul_outside_tolerance(self):
        # $0.03 difference exceeds $0.02 tolerance
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            _invoice(linehaul=1850.03),
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.discrepancy_flag == DiscrepancyFlag.RATE_DELTA

    def test_linehaul_only_rate_con(self):
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            {"line_items": []},
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.rate_con_value == "1850.00"
        assert linehaul.invoice_value is None
        assert linehaul.discrepancy_flag == DiscrepancyFlag.NONE

    def test_linehaul_only_invoice(self):
        results = match_shipment(
            {"linehaul_rate": None},
            None, None,
            _invoice(linehaul=1850.0),
        )
        linehaul = next(r for r in results if r.line_item == "linehaul")
        assert linehaul.rate_con_value is None
        assert linehaul.invoice_value == "1850.00"


# ---------------------------------------------------------------------------
# Fuel surcharge match tests
# ---------------------------------------------------------------------------

class TestFuelSurchargeMatch:
    def test_matching_fuel(self):
        results = match_shipment(
            _rate_con(fuel=275.0),
            None, None,
            _invoice(fuel=275.0),
        )
        fuel = next(r for r in results if r.line_item == "fuel_surcharge")
        assert fuel.discrepancy_flag == DiscrepancyFlag.NONE

    def test_fuel_rate_delta(self):
        results = match_shipment(
            _rate_con(fuel=275.0),
            None, None,
            _invoice(fuel=300.0),
        )
        fuel = next(r for r in results if r.line_item == "fuel_surcharge")
        assert fuel.discrepancy_flag == DiscrepancyFlag.RATE_DELTA
        assert fuel.discrepancy_amount == 25.0


# ---------------------------------------------------------------------------
# Accessorial match tests
# ---------------------------------------------------------------------------

class TestAccessorialMatch:
    def test_extra_accessorial(self):
        """Accessorial on invoice but not rate-con -> extra_accessorial."""
        results = match_shipment(
            _rate_con(),
            None, None,
            _invoice(extra_items=[
                {"category": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
            ]),
        )
        detention = next(r for r in results if r.line_item == "detention")
        assert detention.discrepancy_flag == DiscrepancyFlag.EXTRA_ACCESSORIAL
        assert detention.discrepancy_amount == 150.0

    def test_missing_accessorial(self):
        """Accessorial on rate-con but not invoice -> missing_accessorial."""
        results = match_shipment(
            _rate_con(accessorials=[
                {"type": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
            ]),
            None, None,
            _invoice(),
        )
        detention = next(r for r in results if r.line_item == "detention")
        assert detention.discrepancy_flag == DiscrepancyFlag.MISSING_ACCESSORIAL

    def test_matching_accessorial(self):
        results = match_shipment(
            _rate_con(accessorials=[
                {"type": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
            ]),
            None, None,
            _invoice(extra_items=[
                {"category": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
            ]),
        )
        detention = next(r for r in results if r.line_item == "detention")
        assert detention.discrepancy_flag == DiscrepancyFlag.NONE

    def test_accessorial_rate_delta(self):
        results = match_shipment(
            _rate_con(accessorials=[
                {"type": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
            ]),
            None, None,
            _invoice(extra_items=[
                {"category": "detention", "amount": {"amount": 200.0, "currency": "USD"}},
            ]),
        )
        detention = next(r for r in results if r.line_item == "detention")
        assert detention.discrepancy_flag == DiscrepancyFlag.RATE_DELTA
        assert detention.discrepancy_amount == 50.0

    def test_multiple_accessorials(self):
        """Multiple accessorial types matched correctly."""
        results = match_shipment(
            _rate_con(accessorials=[
                {"type": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
                {"type": "lumper", "amount": {"amount": 75.0, "currency": "USD"}},
            ]),
            None, None,
            _invoice(extra_items=[
                {"category": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
                {"category": "lumper", "amount": {"amount": 75.0, "currency": "USD"}},
            ]),
        )
        detention = next(r for r in results if r.line_item == "detention")
        lumper = next(r for r in results if r.line_item == "lumper")
        assert detention.discrepancy_flag == DiscrepancyFlag.NONE
        assert lumper.discrepancy_flag == DiscrepancyFlag.NONE


# ---------------------------------------------------------------------------
# Weight/pieces variance tests
# ---------------------------------------------------------------------------

class TestWeightVariance:
    def test_matching_weight(self):
        results = match_shipment(None, _bol(weight=15000), _pod(weight=15000), None)
        weight = next(r for r in results if r.line_item == "weight")
        assert weight.discrepancy_flag == DiscrepancyFlag.NONE

    def test_weight_variance(self):
        results = match_shipment(None, _bol(weight=15000), _pod(weight=16000), None)
        weight = next(r for r in results if r.line_item == "weight")
        assert weight.discrepancy_flag == DiscrepancyFlag.WEIGHT_VARIANCE
        assert weight.discrepancy_amount == 1000.0

    def test_weight_within_tolerance(self):
        # 0.5% variance is within 1% tolerance
        results = match_shipment(None, _bol(weight=10000), _pod(weight=10050), None)
        weight = next(r for r in results if r.line_item == "weight")
        assert weight.discrepancy_flag == DiscrepancyFlag.NONE

    def test_weight_only_bol(self):
        results = match_shipment(None, _bol(weight=15000), {}, None)
        weight = next(r for r in results if r.line_item == "weight")
        assert weight.bol_pod_value == "15000"
        assert weight.invoice_value is None


class TestPiecesVariance:
    def test_matching_pieces(self):
        results = match_shipment(None, _bol(pieces=42), _pod(pieces=42), None)
        pieces = next(r for r in results if r.line_item == "pieces")
        assert pieces.discrepancy_flag == DiscrepancyFlag.NONE

    def test_pieces_variance(self):
        results = match_shipment(None, _bol(pieces=42), _pod(pieces=40), None)
        pieces = next(r for r in results if r.line_item == "pieces")
        assert pieces.discrepancy_flag == DiscrepancyFlag.PIECES_VARIANCE
        assert pieces.discrepancy_amount == -2.0


# ---------------------------------------------------------------------------
# Full 3-way match tests
# ---------------------------------------------------------------------------

class TestFullMatch:
    def test_clean_match_no_discrepancies(self):
        """All values match — no discrepancies."""
        results = match_shipment(
            _rate_con(linehaul=1850.0, fuel=275.0),
            _bol(weight=15000, pieces=42),
            _pod(weight=15000, pieces=42),
            _invoice(linehaul=1850.0, fuel=275.0),
        )
        has_disc, reasons = has_discrepancies(results)
        assert has_disc is False
        assert reasons == []

    def test_multiple_discrepancies(self):
        """Multiple discrepancies detected."""
        results = match_shipment(
            _rate_con(linehaul=1850.0, fuel=275.0),
            _bol(weight=15000, pieces=42),
            _pod(weight=16000, pieces=40),
            _invoice(
                linehaul=1950.0,
                fuel=275.0,
                extra_items=[
                    {"category": "detention", "amount": {"amount": 150.0, "currency": "USD"}},
                ],
            ),
        )
        has_disc, reasons = has_discrepancies(results)
        assert has_disc is True
        assert len(reasons) == 4  # rate_delta, extra_accessorial, weight_variance, pieces_variance
        assert any("rate_delta" in r for r in reasons)
        assert any("weight_variance" in r for r in reasons)
        assert any("pieces_variance" in r for r in reasons)
        assert any("extra_accessorial" in r for r in reasons)

    def test_none_sources(self):
        """All sources are None — no matches possible."""
        results = match_shipment(None, None, None, None)
        assert len(results) > 0  # still produces line items
        has_disc, reasons = has_discrepancies(results)
        assert has_disc is False


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_match_results_to_dicts(self):
        results = match_shipment(
            _rate_con(linehaul=1850.0),
            None, None,
            _invoice(linehaul=1850.0),
        )
        dicts = match_results_to_dicts(results, "shipment-123")
        assert len(dicts) > 0
        assert all(d["shipment_id"] == "shipment-123" for d in dicts)
        assert all("line_item" in d for d in dicts)
        assert all("discrepancy_flag" in d for d in dicts)

    def test_has_discrepancies(self):
        items = [
            MatchLineItem(line_item="linehaul", discrepancy_flag=DiscrepancyFlag.NONE),
            MatchLineItem(line_item="detention", discrepancy_flag=DiscrepancyFlag.EXTRA_ACCESSORIAL),
        ]
        has_disc, reasons = has_discrepancies(items)
        assert has_disc is True
        assert len(reasons) == 1
        assert "extra_accessorial" in reasons[0]
