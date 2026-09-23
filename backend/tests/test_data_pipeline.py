"""
Integration tests for synthetic data generation pipeline (PRJ-07).
Validates schema compliance and 4-database progressive discovery chaining.
"""

from pathlib import Path
import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def test_synthetic_csv_files_exist():
    """Verify that all 4 disparate operational silo CSVs exist."""
    required_files = ["hr_db.csv", "crm_db.csv", "platform_db.csv", "membership_db.csv"]
    for fname in required_files:
        path = DATA_DIR / fname
        assert path.exists(), f"Missing required dataset: {fname}"


def test_synthetic_csv_schemas():
    """Verify exact column definitions for each silo."""
    df_hr = pd.read_csv(DATA_DIR / "hr_db.csv")
    df_crm = pd.read_csv(DATA_DIR / "crm_db.csv")
    df_platform = pd.read_csv(DATA_DIR / "platform_db.csv")
    df_membership = pd.read_csv(DATA_DIR / "membership_db.csv")

    assert list(df_hr.columns) == ["employee_id", "full_name", "email", "mobile_number"]
    assert list(df_crm.columns) == ["client_id", "name", "email_id", "contact_no", "address"]
    assert list(df_platform.columns) == ["username", "phone", "company", "registered_ip"]
    assert list(df_membership.columns) == ["member_id", "email", "username", "loyalty_tier"]

    assert len(df_hr) == 1200
    assert len(df_crm) == 1200
    assert len(df_platform) == 1200
    assert len(df_membership) == 1200


def test_progressive_enrichment_chain():
    """Verify the 4-hop progressive discovery path for John Doe."""
    df_hr = pd.read_csv(DATA_DIR / "hr_db.csv")
    df_crm = pd.read_csv(DATA_DIR / "crm_db.csv")
    df_platform = pd.read_csv(DATA_DIR / "platform_db.csv")
    df_membership = pd.read_csv(DATA_DIR / "membership_db.csv")

    # Hop 1: HR DB
    hr_match = df_hr[df_hr["full_name"] == "John Doe"]
    assert not hr_match.empty
    mobile = str(hr_match.iloc[0]["mobile_number"]).strip()
    assert mobile == "9876543210"

    # Hop 2: CRM DB via contact_no
    crm_match = df_crm[df_crm["contact_no"].astype(str).str.strip() == mobile]
    assert not crm_match.empty
    assert crm_match.iloc[0]["address"] == "Mumbai"

    # Hop 3: Platform DB via phone
    plat_match = df_platform[df_platform["phone"].astype(str).str.strip() == mobile]
    assert not plat_match.empty
    username = plat_match.iloc[0]["username"]
    assert username == "johndoe"
    assert plat_match.iloc[0]["company"] == "ABC Pvt Ltd"

    # Hop 4: Membership DB via username
    mem_match = df_membership[df_membership["username"] == username]
    assert not mem_match.empty
    assert mem_match.iloc[0]["member_id"] == "M1042"
    assert mem_match.iloc[0]["loyalty_tier"] == "Platinum"


def test_sql_dumps_exist_and_non_empty():
    """Verify presence and non-trivial content in SQL dump files."""
    for sql_file in ["hr_db.sql", "crm_db.sql"]:
        path = DATA_DIR / sql_file
        assert path.exists()
        assert path.stat().st_size > 50000
