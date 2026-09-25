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

    # Specific specification test cases
    assert normalize_field("phone", "+91 98765 10001") == "9876510001"
    assert normalize_field("phone", "98765-10001") == "9876510001"
    assert normalize_field("phone", "+919876510001") == "9876510001"
    assert normalize_field("phone", "+1 98765 10001") == "9876510001"

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
    """Verify username normalization: lowercase, strip @, preserve alphanumeric, underscore, dot."""
    assert normalize_field("username", " @John_Doe.99! ") == "john_doe.99"
    assert normalize_field("username", "Cool-User#42") == "cooluser42"
    assert normalize_field("username", "AdminUser") == "adminuser"
    assert normalize_field("username", "@aarav_p") == "aarav_p"
    assert normalize_field("username", "vikram.k") == "vikram.k"


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
    """Verify fallback to metadata for unrecognized columns without name/email/phone samples."""
    columns = ["arbitrary_metric_x", "registered_ip"]
    sample_rows = [
        {"arbitrary_metric_x": 42.5, "registered_ip": "10.0.0.1"},
        {"arbitrary_metric_x": 100.2, "registered_ip": "10.0.0.2"},
    ]

    mappings = suggest_mappings(columns, sample_rows)

    assert mappings["arbitrary_metric_x"]["canonical_field"] in ("metadata", "custom")
    assert mappings["arbitrary_metric_x"]["is_identifier"] is False
    assert mappings["arbitrary_metric_x"]["method"] == "fallback"


def test_name_mapping_variations():
    """Verify that all specified name variations reliably map to canonical 'name'."""
    from backend.services.field_mapper import suggest_mappings
    name_cols = [
        "name", "full_name", "patient_name", "customer_name", "client_name",
        "primary_contact", "contact_name", "employee_name", "agent_name", "staff_name"
    ]
    sample_rows = [{col: "Test User" for col in name_cols}]
    mappings = suggest_mappings(name_cols, sample_rows)

    for col in name_cols:
        assert mappings[col]["canonical_field"] == "name", f"Column '{col}' did not map to 'name': {mappings[col]}"
        assert mappings[col]["is_identifier"] is False


def test_novel_dataset_rohit_sen_sample_maps_to_name():
    """Verify that novel/unmapped column headers with sample 'Rohit Sen' map to canonical 'name' rather than 'metadata'."""
    from backend.services.field_mapper import suggest_mappings
    columns = ["unknown_lead_profile"]
    sample_rows = [{"unknown_lead_profile": "Rohit Sen"}]
    mappings = suggest_mappings(columns, sample_rows)

    assert mappings["unknown_lead_profile"]["canonical_field"] == "name"
    assert mappings["unknown_lead_profile"]["is_identifier"] is False


def test_universal_normalize_phone_function():
    """Verify normalize_phone logic adheres strictly to standard."""
    from backend.services.normalizer import normalize_phone

    assert normalize_phone("+91 98765 10001") == "9876510001"
    assert normalize_phone("98765-10001") == "9876510001"
    assert normalize_phone("+919876510001") == "9876510001"
    assert normalize_phone("09876510001") == "9876510001"
    assert normalize_phone("1-800-555-0199") == "8005550199"
    assert normalize_phone("9876510001") == "9876510001"
    assert normalize_phone("") == ""
    assert normalize_phone(None) == ""


def test_token_analysis_name_vs_negative_company_tokens():
    """
    Verify:
      - Headers with name tokens WITHOUT negative company tokens map to 'name'.
      - Headers with negative company tokens map to 'company', not 'name'.
      - is_identifier is strictly False for name.
    """
    from backend.services.field_mapper import suggest_mappings

    name_tokens = [
        "name", "fullname", "fname", "lname", "contact", "person",
        "patient", "client", "customer", "employee", "agent", "staff",
        "lead", "owner"
    ]
    sample_rows = [{t: "Sample Value" for t in name_tokens}]
    mappings = suggest_mappings(name_tokens, sample_rows)

    for t in name_tokens:
        assert mappings[t]["canonical_field"] == "name", f"Token '{t}' did not map to 'name'"
        assert mappings[t]["is_identifier"] is False, f"Name field for '{t}' must have is_identifier=False"

    # Negative company tokens should NOT map to name
    company_cols = ["company_name", "org_name", "vendor_name", "hospital_name", "firm_name"]
    comp_mappings = suggest_mappings(company_cols, [{c: "Acme Corp" for c in company_cols}])
    for c in company_cols:
        assert comp_mappings[c]["canonical_field"] == "company", f"Column '{c}' should map to 'company', not 'name'"
        assert comp_mappings[c]["is_identifier"] is False


def test_arbitrary_headers_cell_pattern_analysis_ratio():
    """
    Verify:
      - Non-standard headers (e.g. 'n_nom', 'p_lead', 'rep') with >=60% spaced alphabetic names
        (e.g. 'Rohit Sen', 'Aarav Patel') map automatically to 'name'.
      - is_identifier is strictly False.
    """
    from backend.services.field_mapper import suggest_mappings

    cols = ["n_nom", "p_lead", "rep"]
    col_samples = {
        "n_nom": ["Rohit Sen", "Aarav Patel", "Rahul Sharma", "Pooja Roy", "V. Kumar"], # 100% names
        "p_lead": ["Amit Kumar", "Dr. Sunita Rao", "Kavita Reddy", "Unknown", "None"], # 3/5 = 60% names
        "rep": ["Priya Mehta", "Devendra Verma", "Cody Garrett", "A. B. Singh", "Rajesh Jain"], # 100% names
    }

    mappings = suggest_mappings(cols, [], column_samples=col_samples)

    for c in cols:
        assert mappings[c]["canonical_field"] == "name", f"Arbitrary header '{c}' failed to map to 'name': {mappings[c]}"
        assert mappings[c]["is_identifier"] is False
        assert mappings[c]["confidence"] >= 0.85


def test_safe_identifier_isolation_and_source_record_id():
    """
    Verify:
      - ONLY 'email', 'phone', and 'username' have is_identifier=True.
      - Columns ending in _id, _code, _num map to 'source_record_id' with is_identifier=False.
      - 'address', 'company', 'metadata' have is_identifier=False.
    """
    from backend.services.field_mapper import suggest_mappings

    cols = [
        "patient_id", "client_code", "record_num", "user_email", "contact_phone",
        "user_handle", "shipping_address", "employer_company", "profile_status"
    ]
    sample_rows = [{
        "patient_id": "P101",
        "client_code": "CL-88",
        "record_num": "99401",
        "user_email": "test@example.com",
        "contact_phone": "9876543210",
        "user_handle": "johndoe",
        "shipping_address": "123 Main St",
        "employer_company": "Initech",
        "profile_status": "Active"
    }]

    mappings = suggest_mappings(cols, sample_rows)

    # _id, _code, _num
    assert mappings["patient_id"]["canonical_field"] == "source_record_id"
    assert mappings["patient_id"]["is_identifier"] is False
    assert mappings["client_code"]["canonical_field"] == "source_record_id"
    assert mappings["client_code"]["is_identifier"] is False
    assert mappings["record_num"]["canonical_field"] == "source_record_id"
    assert mappings["record_num"]["is_identifier"] is False

    # Identifiers: email, phone, username
    assert mappings["user_email"]["is_identifier"] is True
    assert mappings["contact_phone"]["is_identifier"] is True
    assert mappings["user_handle"]["is_identifier"] is True

    # Other non-identifiers
    assert mappings["shipping_address"]["is_identifier"] is False
    assert mappings["employer_company"]["is_identifier"] is False
    assert mappings["profile_status"]["is_identifier"] is False


