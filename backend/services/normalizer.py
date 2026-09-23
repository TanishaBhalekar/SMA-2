"""
Field Normalization Service for Progressive Entity Resolution (PRJ-07).
Standardizes diverse operational field values into canonical formats.
"""

import re
from typing import Any, Optional

# Standard honorific prefixes to strip from personal names
HONORIFICS_REGEX = re.compile(
    r"^(?:mr|mrs|ms|miss|dr|prof|professor|shri|smt|rev|reverend|sir|dame|master|er)\.?\s+",
    re.IGNORECASE
)


def normalize_field(field_type: str, value: Any) -> str:
    """
    Normalizes a given field value based on its target canonical type.

    Rules:
      - 'email': strip, lowercase.
      - 'phone': strip non-digits; if 11-12 digits with prefix +91 or 0, normalize to standard 10 digits.
      - 'name': strip honorifics (Mr., Dr., etc.), remove redundant spacing, lowercase.
      - 'username': strip, lowercase, alphanumeric only.
      - default: trim whitespace, strip excess quotes.
    """
    if value is None:
        return ""

    val_str = str(value)
    ftype = field_type.strip().lower() if field_type else ""

    if ftype == "email":
        return val_str.strip().lower()

    elif ftype == "phone":
        # Strip all non-digit characters
        digits = re.sub(r"\D", "", val_str)
        # Handle country code +91 (12 digits) or trunk prefix 0 (11 digits)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        elif len(digits) == 13 and digits.startswith("091"):
            digits = digits[3:]
        elif len(digits) > 10 and digits.endswith(digits[-10:]) and (digits.startswith("91") or digits.startswith("0")):
            digits = digits[-10:]
        return digits

    elif ftype == "name":
        # Strip leading/trailing whitespace
        cleaned = val_str.strip()
        # Iteratively strip multiple/stacked honorifics (e.g., 'Prof. Dr. Jane Doe')
        while True:
            stripped = HONORIFICS_REGEX.sub("", cleaned).strip()
            if stripped == cleaned:
                break
            cleaned = stripped
        # Collapse multiple spaces and lowercase
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned

    elif ftype == "username":
        cleaned = val_str.strip().lower()
        # Retain alphanumeric only [a-z0-9]
        cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
        return cleaned

    else:
        # Default: trim whitespace, strip excess quotes
        cleaned = val_str.strip()
        # Strip paired or redundant outer quotes
        while len(cleaned) >= 2 and (
            (cleaned.startswith('"') and cleaned.endswith('"')) or
            (cleaned.startswith("'") and cleaned.endswith("'"))
        ):
            cleaned = cleaned[1:-1].strip()
        return cleaned
