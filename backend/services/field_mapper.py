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
        "patient_name", "contact_name", "agent_name", "staff_name", "lead", "owner"
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

# Name tokens for human personal/contact names
NAME_TOKENS = {
    "name", "fullname", "fname", "lname", "contact", "person",
    "patient", "client", "customer", "employee", "agent", "staff",
    "lead", "owner", "emp", "primary_contact", "display_name"
}

# Negative company / institutional / system tokens that disqualify a name mapping
NEGATIVE_COMPANY_TOKENS = {
    "company", "comp", "org", "organization", "organisation", "business",
    "firm", "corp", "corporation", "vendor", "agency", "hospital",
    "clinic", "school", "college", "bank", "store", "brand", "table",
    "file", "db", "column", "col", "dept", "department", "team"
}


def tokenize_header(header: str) -> List[str]:
    """Tokenizes column header by snake_case, camelCase, hyphens, and whitespace."""
    s = re.sub(r'([a-z])([A-Z])', r'\1_\2', str(header).strip())
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s).lower().strip('_')
    return [t for t in s.split('_') if t]


def is_name_like_value(val: Any) -> bool:
    """
    Determines if a sample cell value resembles a spaced human personal name
    (e.g., 'Rohit Sen', 'Aarav Patel', 'Rahul Sharma', 'Dr. Amit K. Patel').
    """
    if val is None:
        return False
    clean = str(val).strip()
    if not clean or len(clean) < 3 or len(clean) > 60:
        return False
    # Negative checks: cannot be email, URL, digits, or system flags
    if "@" in clean or "http://" in clean or "https://" in clean or "www." in clean:
        return False
    if re.search(r"\d", clean):
        return False
    # Strip honorific prefixes
    stripped = re.sub(
        r"^(?:mr|mrs|ms|miss|dr|prof|professor|er|shri|smt|rev|sir|master)\.?\s+",
        "",
        clean,
        flags=re.IGNORECASE
    ).strip()
    tokens = stripped.split()
    # Spaced alphabetic strings like "Rohit Sen" or "Aarav Patel" (2 to 4 tokens)
    if 2 <= len(tokens) <= 4:
        if all(re.match(r"^[A-Za-z\.\'\-]+$", t) and len(t) >= 1 for t in tokens):
            lower_tokens = [t.lower() for t in tokens]
            status_words = {
                "active", "inactive", "pending", "failed", "completed", "standard",
                "gold", "silver", "platinum", "tier", "true", "false", "unknown", "null", "none",
                "yes", "no", "high", "medium", "low"
            }
            if any(t in status_words for t in lower_tokens):
                return False
            return True
    return False


# Legacy alias
_is_human_name_sample = is_name_like_value


def detect_column_mapping(col_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Universal, dataset-agnostic column mapping detector.
    Combines header tokenization, negative token disqualification,
    and cell value pattern analysis.
    """
    tokens = tokenize_header(col_name)
    col_clean = "_".join(tokens)
    valid_samples = [
        str(s).strip() for s in sample_values
        if s is not None and str(s).strip() and str(s).strip().lower() != "nan"
    ][:5]

    has_neg_company = any(t in NEGATIVE_COMPANY_TOKENS for t in tokens)

    # 1. Email detection (checked first so email_id is not treated as generic _id)
    if (
        any(t in ("email", "mail", "e_mail", "user_email", "work_email", "personal_email", "contact_email", "primary_email") for t in tokens)
        or col_clean.endswith(("email", "mail", "email_id", "email_address"))
        or (valid_samples and all("@" in s and "." in s.split("@")[-1] for s in valid_samples))
    ):
        return {
            "canonical_field": "email",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched email identifier pattern."
        }

    # 2. Phone detection
    if (
        any(t in ("phone", "mobile", "contact_no", "contact_cell", "telephone", "cell", "cell_phone", "contact_number", "phone_number", "tel") for t in tokens)
        or any(k in col_clean for k in ("phone", "mobile", "contact_no", "contact_cell"))
        or (valid_samples and all(re.match(r"^\+?[0-9\s\-]{9,15}$", s) for s in valid_samples))
    ):
        return {
            "canonical_field": "phone",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched phone identifier pattern."
        }

    # 3. Username detection
    if (
        any(t in ("username", "user_name", "handle", "user_handle", "login", "alias", "screen_name") for t in tokens)
        or col_clean.endswith(("username", "handle"))
    ):
        return {
            "canonical_field": "username",
            "confidence": 0.95,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched username identifier pattern."
        }

    # 4. Source Record ID / Tracking Keys: ending in _id, _code, _num
    if (
        col_clean in ("id", "record_id", "source_record_id", "user_key", "rec_id", "customer_id", "contact_id", "company_id", "member_id", "entry_id")
        or col_clean.endswith(("_id", "_code", "_num", "record_id", "id"))
        or (tokens and tokens[-1] in ("id", "code", "num", "key", "no"))
    ):
        return {
            "canonical_field": "source_record_id",
            "confidence": 0.98,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' conforms to entity record identifier/key pattern."
        }

    # 5. Human Name Detection (Header Tokenization & Sample Analysis)
    # Check if headers contain name tokens WITHOUT negative company tokens
    has_name_token = (
        any(t in NAME_TOKENS for t in tokens)
        or any(t.endswith("name") for t in tokens)
        or col_clean in SYNONYM_MAP["name"]
    )

    if has_name_token and not has_neg_company:
        return {
            "canonical_field": "name",
            "confidence": 0.98,
            "method": "token_analysis",
            "reasoning": f"Header '{col_name}' contains personal name tokens without organizational qualifiers."
        }

    # Check cell value pattern analysis (>= 60% ratio of spaced alphabetic strings)
    if valid_samples and not has_neg_company:
        name_like_count = sum(1 for s in valid_samples if is_name_like_value(s))
        ratio = name_like_count / len(valid_samples)
        if ratio >= 0.60:
            return {
                "canonical_field": "name",
                "confidence": 0.95 if ratio >= 0.8 else 0.88,
                "method": "cell_value_pattern_analysis",
                "reasoning": f"Sample values in '{col_name}' ({int(ratio*100)}% matching, e.g. '{valid_samples[0]}') conform to personal name structure."
            }

    # Fuzzy match check for name tokens
    try:
        from rapidfuzz import fuzz
        if not has_neg_company:
            for name_var in NAME_TOKENS:
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
        has_neg_company
        or any(t in ("company", "organization", "organisation", "employer", "firm", "business", "org", "workplace") for t in tokens)
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
        any(t in ("address", "city", "street", "location", "residence", "postal_address", "state", "zip", "zipcode", "country") for t in tokens)
        or any(k in col_clean for k in ("address", "city", "location", "street"))
    ):
        return {
            "canonical_field": "address",
            "confidence": 0.95,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched address/location field."
        }

    # 8. Loyalty Tier rule
    if any(t in ("loyalty_tier", "tier", "membership_tier", "loyalty_status", "rewards_tier", "loyalty") for t in tokens):
        return {
            "canonical_field": "loyalty_tier",
            "confidence": 0.90,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' matched loyalty tier attribute."
        }

    # 9. Metadata rule
    if (
        any(t in ("account_status", "notes", "status", "description", "comments", "remarks", "metadata", "extra") for t in tokens)
        or any(k in col_clean for k in ("status", "notes", "comment", "desc"))
    ):
        return {
            "canonical_field": "metadata",
            "confidence": 0.90,
            "method": "rule_based",
            "reasoning": f"Column '{col_name}' mapped to metadata/status attribute."
        }

    return None


# Backward-compatible alias
_rule_based_match = detect_column_mapping


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
    Safe Identifier Isolation:
      - ONLY 'email', 'phone', and 'username' receive is_identifier = True.
      - 'name', 'source_record_id', 'address', 'company', 'metadata' have is_identifier = False.
    """
    mappings: Dict[str, Dict[str, Any]] = {}
    unmapped_for_llm: Dict[str, List[Any]] = {}

    # Extract up to 5 sample values per column
    col_samples: Dict[str, List[Any]] = {}
    if column_samples:
        col_samples = {
            col: [s for s in samples if s is not None and str(s).strip() and str(s).strip().lower() != "nan"][:5]
            for col, samples in column_samples.items()
        }
    else:
        col_samples = {col: [] for col in columns}
        for row in sample_rows:
            for col in columns:
                if col in row and row[col] is not None:
                    val_str = str(row[col]).strip()
                    if val_str and val_str.lower() != "nan" and val_str not in col_samples[col]:
                        col_samples[col].append(val_str)
                    if len(col_samples[col]) >= 5:
                        break

    # Step 1: Dataset-agnostic detection
    for col in columns:
        samples = col_samples.get(col, [])
        match = detect_column_mapping(col, samples)
        if match and match.get("confidence", 0) >= 0.80:
            mappings[col] = match
        else:
            unmapped_for_llm[col] = samples[:5]

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

    # Step 4: Strict Safe Identifier Isolation
    # ONLY email, phone, and username can be identifiers.
    # Strictly guarantee is_identifier = False for name, source_record_id, etc.
    for col, meta in mappings.items():
        canonical = meta.get("canonical_field")
        meta["is_identifier"] = bool(canonical in ("email", "phone", "username"))

    return mappings

