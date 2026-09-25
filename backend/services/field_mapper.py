"""
AI-Driven Schema Inspection and Column Mapping Service (PRJ-07).
Maps disparate operational database columns to a canonical entity vocabulary
using rule-based heuristics, regex, and Google Gemini LLM fallback.
"""

import json
import re
from typing import List, Dict, Any, Optional

from backend.config import GEMINI_API_KEY

# Canonical entity vocabulary
CANONICAL_FIELDS = [
    "name",
    "email",
    "phone",
    "username",
    "source_record_id",
    "member_id",
    "address",
    "company",
    "metadata",
    "loyalty_tier"
]

# High-priority whitelisted default identifier attributes for progressive entity resolution.
# source_record_id (e.g. customer_id, client_id, member_id, rep_id) is strictly is_identifier=False.
IDENTIFIER_FIELDS = {"email", "phone", "username"}

# Rule-based synonym dictionary for deterministic fast-path mapping
SYNONYM_MAP = {
    "name": [
        "name", "full_name", "fullname", "display_name", "client_name",
        "customer_name", "employee_name", "person_name", "emp_name", "primary_contact",
        "patient_name", "contact_name", "agent_name", "staff_name"
    ],
    "email": [
        "email", "email_id", "email_address", "e_mail", "mail", "user_email",
        "work_email", "personal_email", "contact_email", "primary_email"
    ],
    "phone": [
        "phone", "mobile", "mobile_no", "mobile_number", "contact_no",
        "contact_number", "contact", "telephone", "cell", "cell_phone",
        "phone_number", "contact_cell", "tel"
    ],
    "username": [
        "username", "user_name", "handle", "user_handle", "login", "alias", "account_name",
        "screen_name", "nick", "nickname"
    ],
    "source_record_id": [
        "source_record_id", "record_id", "id", "customer_id", "contact_id",
        "company_id", "member_id", "user_key", "user_id", "account_id",
        "rec_id", "client_id", "entry_id"
    ],
    "member_id": [
        "member_id", "membership_id", "member_no", "membership_no",
        "loyalty_id", "card_number", "member_num"
    ],
    "address": [
        "address", "addr", "location", "street", "city", "residence",
        "postal_address", "billing_address", "shipping_address", "street_address"
    ],
    "company": [
        "company", "organization", "organisation", "employer", "org",
        "company_name", "firm", "workplace", "business_name", "org_name"
    ],
    "metadata": [
        "account_status", "notes", "status", "description", "comments",
        "remarks", "metadata", "extra", "profile_status"
    ],
    "loyalty_tier": [
        "loyalty_tier", "tier", "membership_tier", "loyalty_status",
        "rewards_tier", "membership_level", "loyalty"
    ]
}


def _is_human_name_sample(val: Any) -> bool:
    """Detect if sample string represents a probable human personal name (e.g. 'Rohit Sen')."""
    if val is None:
        return False
    clean = str(val).strip()
    if not clean or len(clean) < 3 or len(clean) > 60:
        return False
    if "@" in clean or "http://" in clean or "https://" in clean or "www." in clean:
        return False
    if re.search(r"\d", clean):
        return False
    stripped = re.sub(r"^(?:mr|mrs|ms|miss|dr|prof|er|shri|smt)\.?\s+", "", clean, flags=re.IGNORECASE).strip()
    tokens = stripped.split()
    if 2 <= len(tokens) <= 4:
        if all(re.match(r"^[A-Za-z\.\'\-]+$", t) and len(t) >= 1 for t in tokens):
            lower_tokens = [t.lower() for t in tokens]
            status_words = {
                "active", "inactive", "pending", "failed", "completed", "standard",
                "gold", "silver", "platinum", "tier", "true", "false", "unknown", "null", "none"
            }
            if any(t in status_words for t in lower_tokens):
                return False
            return True
    return False


def _rule_based_match(col_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Attempt deterministic dictionary and pattern-based matching for a column.
    Follows canonical target mapping rules:
      - Columns ending with _id, _code, _key, record_id, id -> source_record_id (identifier)
      - username, user_handle, handle -> username (identifier)
      - company, organization, org_name -> company
      - city, street_address, address, location -> address
      - email, email_address, work_email -> email (identifier)
      - phone, mobile_number, contact_no, contact_cell -> phone (identifier)
      - full_name, name, primary_contact -> name
      - account_status, notes, etc. -> metadata
    """
    col_clean = col_name.strip().lower().replace(" ", "_").replace("-", "_")

    # 1. Email rule (checked first to prevent email_id being matched as generic _id)
    if (
        col_clean in ("email", "email_address", "work_email", "email_id", "contact_email", "user_email", "personal_email", "primary_email", "mail")
        or "email" in col_clean
        or col_clean.endswith("mail")
    ):
        return {
            "canonical_field": "email",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched email identifier pattern."
        }

    # 2. Phone rule
    if (
        col_clean in ("phone", "mobile_number", "contact_no", "contact_cell", "mobile", "telephone", "cell", "cell_phone", "contact_number", "phone_number")
        or any(k in col_clean for k in ("phone", "mobile", "contact_no", "contact_cell"))
    ):
        return {
            "canonical_field": "phone",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched phone identifier pattern."
        }

    # 3. Username rule
    if (
        col_clean in ("username", "user_handle", "handle", "user_name", "login", "alias", "screen_name")
        or col_clean.endswith(("username", "handle"))
    ):
        return {
            "canonical_field": "username",
            "confidence": 0.95,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched username identifier pattern."
        }

    # 4. Identifier ID checks: ending with _id, _code, _key, record_id, id
    if (
        col_clean in ("id", "record_id", "source_record_id", "user_key", "rec_id", "customer_id", "contact_id", "company_id", "member_id")
        or col_clean.endswith(("_id", "_code", "_key", "record_id", "id"))
    ):
        return {
            "canonical_field": "source_record_id",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' conforms to entity record identifier pattern."
        }

    # 5. Name rule
    # Recognize variations: name, full_name, patient_name, customer_name, client_name,
    # primary_contact, contact_name, employee_name, agent_name, staff_name
    NAME_PATTERNS = {
        "name", "full_name", "fullname", "patient_name", "customer_name",
        "client_name", "primary_contact", "contact_name", "employee_name",
        "agent_name", "staff_name", "person_name", "display_name", "emp_name"
    }
    NAME_REGEX = re.compile(
        r"(?:^|_)(?:full_?name|patient_?name|customer_?name|client_?name|primary_?contact|contact_?name|employee_?name|agent_?name|staff_?name|person_?name)(?:$|_)",
        re.IGNORECASE
    )
    is_name_match = (
        col_clean in NAME_PATTERNS
        or bool(NAME_REGEX.search(col_clean))
        or (
            col_clean.endswith(("_name", "name"))
            and not col_clean.endswith((
                "company_name", "org_name", "organization_name", "business_name",
                "firm_name", "brand_name", "user_name", "username", "account_name",
                "table_name", "file_name", "col_name", "column_name"
            ))
        )
    )
    if is_name_match:
        return {
            "canonical_field": "name",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched human person/contact name."
        }

    # Fuzzy match check for name variations
    try:
        from rapidfuzz import fuzz
        for name_var in ("name", "full_name", "patient_name", "customer_name", "client_name", "primary_contact", "contact_name", "employee_name", "agent_name", "staff_name"):
            if fuzz.ratio(col_clean, name_var) >= 85:
                return {
                    "canonical_field": "name",
                    "confidence": 0.92,
                    "method": "fuzzy_match",
                    "reasoning": f"Column '{col_name}' fuzzy-matched person name variation '{name_var}'."
                }
    except Exception:
        pass

    # 6. Company rule
    if (
        col_clean in ("company", "organization", "org_name", "employer", "firm", "business_name", "company_name", "org")
        or "company" in col_clean
        or "organization" in col_clean
    ):
        return {
            "canonical_field": "company",
            "confidence": 0.95,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched company/organization field."
        }

    # 7. Address rule
    if (
        col_clean in ("city", "street_address", "address", "location", "street", "residence", "postal_address", "state", "zip", "zipcode")
        or any(k in col_clean for k in ("address", "city", "location", "street"))
    ):
        return {
            "canonical_field": "address",
            "confidence": 0.95,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched address/location field."
        }

    # 8. Metadata rule
    if (
        col_clean in ("account_status", "notes", "status", "description", "comments", "remarks", "tier", "loyalty_tier", "metadata")
        or any(k in col_clean for k in ("status", "notes", "comment", "desc"))
    ):
        return {
            "canonical_field": "metadata",
            "confidence": 0.90,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' mapped to metadata/status attribute."
        }

    # 9. Value-level regex inspection for ambiguous columns
    if sample_values:
        valid_samples = [str(s).strip() for s in sample_values if s is not None and str(s).strip() and str(s).strip().lower() != "nan"]
        if valid_samples:
            if all("@" in s and "." in s.split("@")[-1] for s in valid_samples):
                return {
                    "canonical_field": "email",
                    "confidence": 0.90,
                    "method": "rule_based",
                    "reasoning": f"Sample values in '{col_name}' exhibit valid email format."
                }
            if all(re.match(r"^\+?[0-9\s\-]{9,15}$", s) for s in valid_samples):
                return {
                    "canonical_field": "phone",
                    "confidence": 0.85,
                    "method": "rule_based",
                    "reasoning": f"Sample values in '{col_name}' conform to standard phone format."
                }
            # Detect personal names (e.g. 'Rohit Sen', 'Rahul Sharma') in novel/unmapped datasets
            if all(_is_human_name_sample(s) for s in valid_samples):
                return {
                    "canonical_field": "name",
                    "confidence": 0.88,
                    "method": "rule_based",
                    "reasoning": f"Sample values in '{col_name}' (e.g. '{valid_samples[0]}') conform to personal name format."
                }

    return None


def _query_gemini_mappings(unmapped_cols: Dict[str, List[Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Query Gemini API using google-genai SDK to classify unmapped columns based on name and sample values.
    """
    results: Dict[str, Dict[str, Any]] = {}
    if not GEMINI_API_KEY:
        return results

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""
You are an expert data architect mapping operational database fields to a canonical data schema.
Canonical Target Fields: {CANONICAL_FIELDS}

Analyze the following database columns and their sample values:
{json.dumps(unmapped_cols, indent=2)}

For each column, determine the best canonical field from {CANONICAL_FIELDS}.
If a column does not belong to any canonical field, assign "metadata".

Respond strictly with valid JSON with the format:
{{
  "column_name": {{
    "canonical_field": "canonical_name",
    "confidence": 0.85,
    "reasoning": "brief explanation"
  }}
}}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        resp_text = response.text.strip()
        if resp_text.startswith("```"):
            resp_text = re.sub(r"^```(?:json)?\n?", "", resp_text)
            resp_text = re.sub(r"\n?```$", "", resp_text)

        parsed = json.loads(resp_text)
        for col, mapping in parsed.items():
            canonical = mapping.get("canonical_field", "metadata")
            if canonical not in CANONICAL_FIELDS:
                canonical = "metadata"
            confidence = float(mapping.get("confidence", 0.80))
            reasoning = mapping.get("reasoning", "Classified via Gemini LLM semantic analysis.")
            results[col] = {
                "canonical_field": canonical,
                "confidence": confidence,
                "method": "llm_gemini",
                "reasoning": reasoning
            }
    except Exception:
        pass

    return results


def suggest_mappings(
    columns: List[str],
    sample_rows: List[Dict[str, Any]],
    column_samples: Optional[Dict[str, List[Any]]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Inspects schema columns and sample rows, suggesting canonical field mappings.
    Assigns is_identifier = True for fields in IDENTIFIER_FIELDS.
    """
    mappings: Dict[str, Dict[str, Any]] = {}
    unmapped_for_llm: Dict[str, List[Any]] = {}

    # Extract sample values per column (non-null, non-empty, up to 3 samples)
    col_samples: Dict[str, List[Any]] = {}
    if column_samples:
        col_samples = {col: [s for s in samples if s is not None and str(s).strip() and str(s).strip().lower() != "nan"][:3] for col, samples in column_samples.items()}
    else:
        col_samples = {col: [] for col in columns}
        for row in sample_rows:
            for col in columns:
                if col in row and row[col] is not None:
                    val_str = str(row[col]).strip()
                    if val_str and val_str.lower() != "nan" and val_str not in col_samples[col]:
                        col_samples[col].append(val_str)

    # Step 1: Rule-based mapping
    for col in columns:
        samples = col_samples.get(col, [])
        rule_match = _rule_based_match(col, samples)
        if rule_match and rule_match.get("confidence", 0) >= 0.80:
            mappings[col] = rule_match
        else:
            unmapped_for_llm[col] = samples[:3]

    # Step 2: LLM Disambiguation for unmapped columns
    if unmapped_for_llm:
        llm_results = _query_gemini_mappings(unmapped_for_llm)
        for col, llm_mapping in llm_results.items():
            if llm_mapping.get("confidence", 0) >= 0.80:
                mappings[col] = llm_mapping
                if col in unmapped_for_llm:
                    del unmapped_for_llm[col]

    # Step 3: Fallback for any remaining unmapped columns -> map to metadata
    for col in columns:
        if col not in mappings:
            mappings[col] = {
                "canonical_field": "metadata",
                "confidence": 0.70,
                "method": "fallback",
                "reasoning": f"Defaulted to metadata attribute for column '{col}'."
            }

    # Step 4: Mark identifiers
    for col, meta in mappings.items():
        canonical = meta.get("canonical_field")
        meta["is_identifier"] = bool(canonical in IDENTIFIER_FIELDS)

    return mappings
