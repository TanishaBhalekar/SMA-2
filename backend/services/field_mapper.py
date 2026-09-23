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
    "member_id",
    "address",
    "company",
    "loyalty_tier"
]

# High-priority identifier attributes for progressive entity resolution
IDENTIFIER_FIELDS = {"email", "phone", "username", "member_id"}

# Rule-based synonym dictionary for deterministic fast-path mapping
SYNONYM_MAP = {
    "name": [
        "name", "full_name", "fullname", "display_name", "client_name",
        "customer_name", "employee_name", "person_name", "emp_name", "user_name_display"
    ],
    "email": [
        "email", "email_id", "email_address", "e_mail", "mail", "user_email",
        "work_email", "personal_email", "contact_email", "primary_email"
    ],
    "phone": [
        "phone", "mobile", "mobile_no", "mobile_number", "contact_no",
        "contact_number", "contact", "telephone", "cell", "cell_phone",
        "phone_number", "platform_phone", "tel"
    ],
    "username": [
        "username", "user_name", "handle", "login", "alias", "account_name",
        "screen_name", "nick", "nickname"
    ],
    "member_id": [
        "member_id", "membership_id", "member_no", "membership_no",
        "loyalty_id", "card_number", "member_num"
    ],
    "address": [
        "address", "addr", "location", "street", "city", "residence",
        "postal_address", "billing_address", "shipping_address"
    ],
    "company": [
        "company", "organization", "organisation", "employer", "org",
        "company_name", "firm", "workplace", "business_name"
    ],
    "loyalty_tier": [
        "loyalty_tier", "tier", "membership_tier", "loyalty_status",
        "rewards_tier", "membership_level", "loyalty"
    ]
}

# Regex heuristics for column names
REGEX_RULES = [
    (re.compile(r"^.*(?:email|mail).*$", re.I), "email"),
    (re.compile(r"^.*(?:phone|mobile|contact_no|cell).*$", re.I), "phone"),
    (re.compile(r"^.*(?:full_?name|display_?name).*$", re.I), "name"),
    (re.compile(r"^.*(?:user_?name|handle|login).*$", re.I), "username"),
    (re.compile(r"^.*(?:member_?id|loyalty_?id).*$", re.I), "member_id"),
    (re.compile(r"^.*(?:address|street|city).*$", re.I), "address"),
    (re.compile(r"^.*(?:company|org(?:anization)?|employer).*$", re.I), "company"),
    (re.compile(r"^.*(?:loyalty|tier).*$", re.I), "loyalty_tier"),
]


def _rule_based_match(col_name: str, sample_values: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Attempt deterministic dictionary and regex-based matching for a column.
    """
    col_clean = col_name.strip().lower()

    # 1. Exact match against canonical vocabulary
    if col_clean in CANONICAL_FIELDS:
        return {
            "canonical_field": col_clean,
            "confidence": 1.0,
            "method": "rule_based",
            "reasoning": f"Exact match with canonical field '{col_clean}'."
        }

    # 2. Synonym dictionary check
    for canonical, synonyms in SYNONYM_MAP.items():
        if col_clean in synonyms:
            return {
                "canonical_field": canonical,
                "confidence": 0.95,
                "method": "rule_based",
                "reasoning": f"Column '{col_name}' matched synonym for canonical '{canonical}'."
            }

    # 3. Column name regex check
    for pattern, canonical in REGEX_RULES:
        if pattern.match(col_clean):
            return {
                "canonical_field": canonical,
                "confidence": 0.85,
                "method": "rule_based",
                "reasoning": f"Regex pattern matched canonical '{canonical}' for '{col_name}'."
            }

    # 4. Value-level regex inspection (e.g., if col_name is ambiguous like 'val1', check values)
    if sample_values:
        valid_samples = [str(s).strip() for s in sample_values if s is not None and str(s).strip()]
        if valid_samples:
            # Check email pattern in sample values
            if all("@" in s and "." in s.split("@")[-1] for s in valid_samples):
                return {
                    "canonical_field": "email",
                    "confidence": 0.90,
                    "method": "rule_based",
                    "reasoning": f"Values in column '{col_name}' exhibit valid email formats."
                }
            # Check phone pattern in sample values (digits with optional +, len 10-14)
            if all(re.match(r"^\+?[0-9\s\-]{9,15}$", s) for s in valid_samples):
                return {
                    "canonical_field": "phone",
                    "confidence": 0.85,
                    "method": "rule_based",
                    "reasoning": f"Values in column '{col_name}' conform to standard phone format."
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

Analyze the following database columns and their 3 sample values:
{json.dumps(unmapped_cols, indent=2)}

For each column, determine the best canonical field from {CANONICAL_FIELDS}.
If a column does not belong to any canonical field, assign "custom".

Respond strictly with valid JSON with the format:
{{
  "column_name": {{
    "canonical_field": "canonical_name_or_custom",
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
        # Clean markdown code blocks if present
        if resp_text.startswith("```"):
            resp_text = re.sub(r"^```(?:json)?\n?", "", resp_text)
            resp_text = re.sub(r"\n?```$", "", resp_text)

        parsed = json.loads(resp_text)
        for col, mapping in parsed.items():
            canonical = mapping.get("canonical_field", "custom")
            if canonical not in CANONICAL_FIELDS and canonical != "custom":
                canonical = "custom"
            confidence = float(mapping.get("confidence", 0.80))
            reasoning = mapping.get("reasoning", "Classified via Gemini LLM semantic analysis.")
            results[col] = {
                "canonical_field": canonical,
                "confidence": confidence,
                "method": "llm_gemini",
                "reasoning": reasoning
            }
    except Exception as e:
        # Gracefully handle API failures, network errors, or auth issues
        pass

    return results


def suggest_mappings(columns: List[str], sample_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Inspects schema columns and sample rows, suggesting canonical field mappings.

    Process:
      1. Fast rule-based regex and synonym dictionary matching.
      2. If unmapped or confidence < 0.80, queries Gemini API with column name + 3 sample values.
      3. Fallback: If GEMINI_API_KEY is missing or API fails, assigns 'custom' with 50% confidence.
      4. Assigns is_identifier = True for fields in ['email', 'phone', 'username', 'member_id'].
    """
    mappings: Dict[str, Dict[str, Any]] = {}
    unmapped_for_llm: Dict[str, List[Any]] = {}

    # Extract sample values per column (up to 3 samples)
    col_samples: Dict[str, List[Any]] = {col: [] for col in columns}
    for row in sample_rows[:3]:
        for col in columns:
            if col in row and row[col] is not None:
                col_samples[col].append(row[col])

    # Step 1: Rule-based mapping
    for col in columns:
        samples = col_samples.get(col, [])
        rule_match = _rule_based_match(col, samples)
        if rule_match and rule_match.get("confidence", 0) >= 0.80:
            mappings[col] = rule_match
        else:
            unmapped_for_llm[col] = samples[:3]

    # Step 2: LLM Disambiguation for unmapped or low-confidence columns
    if unmapped_for_llm:
        llm_results = _query_gemini_mappings(unmapped_for_llm)
        for col, llm_mapping in llm_results.items():
            if llm_mapping.get("confidence", 0) >= 0.80:
                mappings[col] = llm_mapping
                if col in unmapped_for_llm:
                    del unmapped_for_llm[col]

    # Step 3: Fallback for any remaining unmapped columns
    for col in columns:
        if col not in mappings:
            mappings[col] = {
                "canonical_field": "custom",
                "confidence": 0.50,
                "method": "fallback",
                "reasoning": "No matching rule and Gemini LLM unavailable or inconclusive; assigned fallback."
            }

    # Step 4: Mark identifiers
    for col, meta in mappings.items():
        canonical = meta.get("canonical_field")
        meta["is_identifier"] = bool(canonical in IDENTIFIER_FIELDS)

    return mappings
