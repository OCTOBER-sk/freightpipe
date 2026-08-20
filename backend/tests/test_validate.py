"""Tests for domain validation — required fields, date sanity, money sanity."""
from __future__ import annotations

from datetime import date

import pytest

from freightpipe.pipeline.validate import (
    validate_required_fields,
    validate_date_sanity,
    validate_money_sanity,
    validate_load_number_cross_reference,
    validate_document,
    validate_job_documents,
    ValidationResult,
    ValidationIssue,
    REQUIRED_FIELDS,
    MONEY_TOLERANCE,
)


# ---------------------------------------------------------------------------
# Required fields tests
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_rate_con_all_present(self):
        fields = {
            "load_number": "RC-48213",
            "broker_name": "ABC Brokerage",
            "carrier_name": "XYZ Transport",
            "shipper": {"name": "Acme", "address": "123 Main St"},
            "consignee": {"name": "Widget Co", "address": "456 Oak Ave"},
            "pickup": {"location": "Chicago", "date": "2026-08-22"},
            "delivery": {"location": "Dallas", "date": "2026-08-24"},
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "total_rate": {"amount": 2125.00, "currency": "USD"},
        }
        issues = validate_required_fields(fields, "rate_con")
        assert len(issues) == 0

    def test_rate_con_missing_field(self):
        fields = {
            "load_number": "RC-48213",
            # missing broker_name
        }
        issues = validate_required_fields(fields, "rate_con")
        assert any(i.field == "broker_name" for i in issues)

    def test_bol_all_present(self):
        fields = {
            "bol_number": "BOL-123",
            "shipper": {"name": "Acme"},
            "consignee": {"name": "Widget Co"},
            "pickup_date": "2026-08-22",
            "freight_description": "Machine Parts",
            "weight": 15000,
            "pieces": 42,
            "signature_present": True,
        }
        issues = validate_required_fields(fields, "bol")
        assert len(issues) == 0

    def test_bol_missing_signature(self):
        fields = {
            "bol_number": "BOL-123",
            "shipper": {"name": "Acme"},
            "consignee": {"name": "Widget Co"},
            "pickup_date": "2026-08-22",
            "freight_description": "Machine Parts",
            "weight": 15000,
            "pieces": 42,
            # missing signature_present
        }
        issues = validate_required_fields(fields, "bol")
        assert any(i.field == "signature_present" for i in issues)

    def test_pod_all_present(self):
        fields = {
            "delivery_date": "2026-08-24",
            "recipient_name": "John Smith",
            "signature_present": True,
        }
        issues = validate_required_fields(fields, "pod")
        assert len(issues) == 0

    def test_pod_missing_recipient(self):
        fields = {
            "delivery_date": "2026-08-24",
            "signature_present": True,
            # missing recipient_name
        }
        issues = validate_required_fields(fields, "pod")
        assert any(i.field == "recipient_name" for i in issues)

    def test_invoice_all_present(self):
        fields = {
            "invoice_number": "INV-123",
            "load_number": "RC-48213",
            "carrier_name": "XYZ Transport",
            "line_items": [{"category": "linehaul", "amount": {"amount": 1850, "currency": "USD"}}],
            "total_amount": {"amount": 1850, "currency": "USD"},
        }
        issues = validate_required_fields(fields, "invoice")
        assert len(issues) == 0

    def test_empty_string_field(self):
        fields = {"load_number": ""}
        issues = validate_required_fields(fields, "rate_con")
        assert any(i.field == "load_number" for i in issues)

    def test_empty_object_field(self):
        fields = {"shipper": {}}
        issues = validate_required_fields(fields, "rate_con")
        assert any(i.field == "shipper" for i in issues)

    def test_unknown_doc_type(self):
        issues = validate_required_fields({}, "unknown")
        assert len(issues) == 0  # no required fields for unknown


# ---------------------------------------------------------------------------
# Date sanity tests
# ---------------------------------------------------------------------------

class TestDateSanity:
    def test_valid_date_order(self):
        fields = {
            "pickup_date": "2026-08-22",
            "delivery_date": "2026-08-24",
            "due_date": "2026-09-23",
        }
        issues = validate_date_sanity(fields, "rate_con")
        assert len(issues) == 0

    def test_pickup_after_delivery(self):
        fields = {
            "pickup_date": "2026-08-24",
            "delivery_date": "2026-08-22",
        }
        issues = validate_date_sanity(fields, "rate_con")
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "pickup" in issues[0].message.lower()

    def test_delivery_after_due_date(self):
        fields = {
            "delivery_date": "2026-09-24",
            "due_date": "2026-09-23",
        }
        issues = validate_date_sanity(fields, "invoice")
        assert len(issues) == 1
        assert issues[0].severity == "warning"  # warning, not error

    def test_same_pickup_delivery(self):
        fields = {
            "pickup_date": "2026-08-22",
            "delivery_date": "2026-08-22",
        }
        issues = validate_date_sanity(fields, "rate_con")
        assert len(issues) == 0  # same day is valid

    def test_missing_dates_no_error(self):
        issues = validate_date_sanity({}, "rate_con")
        assert len(issues) == 0

    def test_nested_date_fields(self):
        fields = {
            "pickup": {"date": "2026-08-22"},
            "delivery": {"date": "2026-08-24"},
        }
        issues = validate_date_sanity(fields, "rate_con")
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Money sanity tests
# ---------------------------------------------------------------------------

class TestMoneySanity:
    def test_valid_total(self):
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "fuel_surcharge": {"amount": 275.00, "currency": "USD"},
            "total_rate": {"amount": 2125.00, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 0

    def test_total_with_accessorials(self):
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "fuel_surcharge": {"amount": 275.00, "currency": "USD"},
            "accessorials": [
                {"type": "detention", "amount": {"amount": 150.00, "currency": "USD"}},
            ],
            "total_rate": {"amount": 2275.00, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 0

    def test_total_mismatch(self):
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "fuel_surcharge": {"amount": 275.00, "currency": "USD"},
            "total_rate": {"amount": 2500.00, "currency": "USD"},  # wrong total
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "money_sanity" in issues[0].rule

    def test_within_tolerance(self):
        # $0.01 difference is within $0.02 tolerance
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "fuel_surcharge": {"amount": 275.00, "currency": "USD"},
            "total_rate": {"amount": 2125.01, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 0

    def test_outside_tolerance(self):
        # $0.03 difference exceeds $0.02 tolerance
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "fuel_surcharge": {"amount": 275.00, "currency": "USD"},
            "total_rate": {"amount": 2125.03, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 1

    def test_invoice_total(self):
        fields = {
            "line_items": [
                {"category": "linehaul", "amount": {"amount": 1850.00, "currency": "USD"}},
                {"category": "fuel", "amount": {"amount": 275.00, "currency": "USD"}},
            ],
            "total_amount": {"amount": 2125.00, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "invoice")
        assert len(issues) == 0

    def test_non_rate_doc_skipped(self):
        issues = validate_money_sanity({}, "bol")
        assert len(issues) == 0

    def test_missing_total_skipped(self):
        fields = {
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
        }
        issues = validate_money_sanity(fields, "rate_con")
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Load number cross-reference tests
# ---------------------------------------------------------------------------

class TestLoadNumberCrossReference:
    def test_matching_load_numbers(self):
        documents = [
            {"id": "doc1", "fields": {"load_number": "RC-48213"}},
            {"id": "doc2", "fields": {"load_number": "RC-48213"}},
            {"id": "doc3", "fields": {"load_number": "RC-48213"}},
        ]
        issues = validate_load_number_cross_reference(documents)
        assert len(issues) == 0

    def test_mismatched_load_numbers(self):
        documents = [
            {"id": "doc1", "fields": {"load_number": "RC-48213"}},
            {"id": "doc2", "fields": {"load_number": "RC-99999"}},
        ]
        issues = validate_load_number_cross_reference(documents)
        assert len(issues) == 1
        assert issues[0].severity == "error"

    def test_missing_load_numbers_ok(self):
        documents = [
            {"id": "doc1", "fields": {}},
            {"id": "doc2", "fields": {}},
        ]
        issues = validate_load_number_cross_reference(documents)
        assert len(issues) == 0

    def test_partial_load_numbers(self):
        documents = [
            {"id": "doc1", "fields": {"load_number": "RC-48213"}},
            {"id": "doc2", "fields": {}},  # no load number
        ]
        issues = validate_load_number_cross_reference(documents)
        assert len(issues) == 0  # only one load number found, no conflict


# ---------------------------------------------------------------------------
# Full validation pipeline tests
# ---------------------------------------------------------------------------

class TestValidateDocument:
    def test_valid_rate_con(self):
        fields = {
            "load_number": "RC-48213",
            "broker_name": "ABC Brokerage",
            "carrier_name": "XYZ Transport",
            "shipper": {"name": "Acme", "address": "123 Main St"},
            "consignee": {"name": "Widget Co", "address": "456 Oak Ave"},
            "pickup": {"location": "Chicago", "date": "2026-08-22"},
            "delivery": {"location": "Dallas", "date": "2026-08-24"},
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "total_rate": {"amount": 1850.00, "currency": "USD"},
        }
        result = validate_document(fields, "rate_con")
        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_invalid_rate_con_missing_fields(self):
        fields = {"load_number": "RC-48213"}
        result = validate_document(fields, "rate_con")
        assert result.is_valid is False
        assert any(i.rule == "required" for i in result.issues)

    def test_valid_pod(self):
        fields = {
            "delivery_date": "2026-08-24",
            "recipient_name": "John Smith",
            "signature_present": True,
        }
        result = validate_document(fields, "pod")
        assert result.is_valid is True

    def test_validation_with_warnings(self):
        """Warnings don't make validation fail."""
        fields = {
            "load_number": "RC-48213",
            "broker_name": "ABC Brokerage",
            "carrier_name": "XYZ Transport",
            "shipper": {"name": "Acme"},
            "consignee": {"name": "Widget Co"},
            "pickup": {"date": "2026-08-22"},
            "delivery": {"date": "2026-08-24"},
            "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
            "total_rate": {"amount": 1850.00, "currency": "USD"},
            "due_date": "2026-08-20",  # before delivery = warning
        }
        result = validate_document(fields, "rate_con")
        # Should still be valid (warnings don't fail)
        assert result.is_valid is True
        assert any(i.severity == "warning" for i in result.issues)


class TestValidateJobDocuments:
    def test_valid_job(self):
        documents = [
            {
                "id": "doc1",
                "doc_type": "rate_con",
                "fields": {
                    "load_number": "RC-48213",
                    "broker_name": "ABC Brokerage",
                    "carrier_name": "XYZ Transport",
                    "shipper": {"name": "Acme"},
                    "consignee": {"name": "Widget Co"},
                    "pickup": {"date": "2026-08-22"},
                    "delivery": {"date": "2026-08-24"},
                    "linehaul_rate": {"amount": 1850.00, "currency": "USD"},
                    "total_rate": {"amount": 1850.00, "currency": "USD"},
                },
            },
            {
                "id": "doc2",
                "doc_type": "bol",
                "fields": {
                    "bol_number": "BOL-123",
                    "load_number": "RC-48213",
                    "shipper": {"name": "Acme"},
                    "consignee": {"name": "Widget Co"},
                    "pickup_date": "2026-08-22",
                    "freight_description": "Machine Parts",
                    "weight": 15000,
                    "pieces": 42,
                    "signature_present": True,
                },
            },
        ]
        result = validate_job_documents(documents)
        assert result.is_valid is True

    def test_job_with_mismatched_load_numbers(self):
        documents = [
            {"id": "doc1", "doc_type": "rate_con", "fields": {"load_number": "RC-48213"}},
            {"id": "doc2", "doc_type": "bol", "fields": {"load_number": "RC-99999"}},
        ]
        result = validate_job_documents(documents)
        assert result.is_valid is False
        assert any(i.rule == "load_number" for i in result.issues)
