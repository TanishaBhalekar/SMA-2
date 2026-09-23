"""
Unit tests for field normalizer and schema mapper (PRJ-07).
Validates email, phone, name, username, and default normalization rules,
as well as canonical mapping and fallback logic.
"""

import pytest
from backend.services.normalizer import normalize_field
from backend.services.field_mapper import suggest_mappings, CANONICAL_FIELDS, IDENTIFIER_FIELDS


# ============================================================================
# Field Normalization Tests
# ============================================================================

def test_normalize_email():
    """Verify email normalization: strip whitespace and lowercase."""
    assert normalize_field("email", " John.Doe@Example.COM ") == "john.doe@example.com"
    assert normalize_field("email", "ALICE@GMAIL.COM  ") == "alice@gmail.com"
    assert normalize_field("email", "user+tag@domain.org") == "user+tag@domain.org"


def test_normalize_phone():
    """Verify phone normalization: strip non-digits, normalize +91 / 0 to 10 digits."""
    # Standard 10-digit
    assert normalize_field("phone", "9876543210") == "9876543210"

    # With +91 country prefix
    assert normalize_field("phone", "+91 98765 43210") == "9876543210"
    assert normalize_field("phone", "+91-9876543210") == "9876543210"
    assert normalize_field("phone", "919876543210") == "9876543210"

    # With trunk prefix 0
    assert normalize_field("phone", "09876543210") == "9876543210"
    assert normalize_field("phone", "0-9876543210") == "9876543210"

    # With punctuation / spaces
    assert normalize_field("phone", "+91 (987) 654-3210") == "9876543210"


def test_normalize_name():
    """Verify name normalization: strip honorifics, redundant spacing, lowercase."""
    assert normalize_field("name", "Mr. John Doe") == "john doe"
    assert normalize_field("name", "Dr. Jane Smith") == "jane smith"
    assert normalize_field("name", "Mrs. Sarah Connor") == "sarah connor"
    assert normalize_field("name", "Ms. Amanda Lee") == "amanda lee"
    assert normalize_field("name", "Prof. Robert Downey") == "robert downey"
    assert normalize_field("name", "  Dr.  Albert   Einstein  ") == "albert einstein"
    assert normalize_field("name", "Michael J. Fox") == "michael j. fox"


def test_normalize_username():
    """Verify username normalization: lowercase, strip, alphanumeric only."""
    assert normalize_field("username", " @John_Doe.99! ") == "johndoe99"
    assert normalize_field("username", "Cool-User#42") == "cooluser42"
    assert normalize_field("username", "AdminUser") == "adminuser"


def test_normalize_default():
    """Verify default normalization: trim whitespace, strip excess quotes."""
    assert normalize_field("unknown_type", "  'quoted value'  ") == "quoted value"
    assert normalize_field("text", '  "another quote"  ') == "another quote"
    assert normalize_field("text", "   plain text   ") == "plain text"
    assert normalize_field("text", None) == ""


# ============================================================================
# Field Mapper Tests
# ============================================================================

def test_field_mapper_rule_based():
    """Verify rule-based and synonym dictionary mapping."""
    columns = ["full_name", "email_id", "contact_no", "company", "address"]
    sample_rows = [
        {
            "full_name": "John Doe",
            "email_id": "john@example.com",
            "contact_no": "9876543210",
            "company": "ABC Pvt Ltd",
            "address": "Mumbai"
        }
    ]

    mappings = suggest_mappings(columns, sample_rows)

    assert mappings["full_name"]["canonical_field"] == "name"
    assert mappings["email_id"]["canonical_field"] == "email"
    assert mappings["contact_no"]["canonical_field"] == "phone"
    assert mappings["company"]["canonical_field"] == "company"
    assert mappings["address"]["canonical_field"] == "address"

    # Identifiers check
    assert mappings["email_id"]["is_identifier"] is True
    assert mappings["contact_no"]["is_identifier"] is True
    assert mappings["company"]["is_identifier"] is False
    assert mappings["address"]["is_identifier"] is False


def test_field_mapper_fallback_unmapped():
    """Verify fallback to custom (50% confidence) for unrecognized columns."""
    columns = ["arbitrary_metric_x", "registered_ip"]
    sample_rows = [
        {"arbitrary_metric_x": 42.5, "registered_ip": "10.0.0.1"},
        {"arbitrary_metric_x": 100.2, "registered_ip": "10.0.0.2"},
    ]

    mappings = suggest_mappings(columns, sample_rows)

    assert mappings["arbitrary_metric_x"]["canonical_field"] in ("metadata", "custom")
    assert mappings["arbitrary_metric_x"]["is_identifier"] is False
    assert mappings["arbitrary_metric_x"]["method"] == "fallback"
