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


def normalize_phone(val: Any) -> str:
    if not val:
        return ""
    # Strip all non-digit characters
    digits = re.sub(r'\D', '', str(val))
    # Standardize international and trunk prefixes
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[-10:]
    elif len(digits) == 11 and digits.startswith(('1', '0')):
        digits = digits[-10:]
    return digits


def normalize_field(field_type: str, value: Any) -> str:
    """
    Normalizes a given field value based on its target canonical type according to
    the exact mathematical specification.

    Rules:
      - 'email': trim, lowercase, strip whitespace: str(val).strip().lower().
      - 'phone':
          - Strip all non-digit characters: digits = re.sub(r'\\D', '', str(val))
          - If len == 12 and starts with '91' (India), take digits[-10:]
          - If len == 11 and starts with ('1', '0'), take digits[-10:]
          - Guarantees "+91 98765 10001", "98765-10001", and "+919876510001" normalize identically to "9876510001".
      - 'username':
          - Strip whitespace, lowercase, remove leading '@':
            re.sub(r'[^a-zA-Z0-9_\\.]', '', str(val).strip().lower().lstrip('@'))
      - 'source_record_id':
          - Store as clean text (e.g. "C301", "B101", "E101") purely as a source tracking tag.
      - 'name':
          - Strip honorifics, collapse redundant whitespace, preserve casing or lowercase for comparison.
      - default:
          - trim whitespace, strip excess outer quotes.
    """
    if value is None:
        return ""

    val_str = str(value)
    ftype = field_type.strip().lower() if field_type else ""

    if ftype == "email":
        return val_str.strip().lower()

    elif ftype == "phone":
        return normalize_phone(val_str)

    elif ftype == "username":
        return re.sub(r"[^a-zA-Z0-9_\.]", "", val_str.strip().lower().lstrip("@"))

    elif ftype in ("source_record_id", "record_id", "id", "customer_id", "client_id", "member_id", "rep_id"):
        # Purely tracking tag, not a matching identifier
        return val_str.strip()

    elif ftype == "name":
        cleaned = val_str.strip()
        while True:
            stripped = HONORIFICS_REGEX.sub("", cleaned).strip()
            if stripped == cleaned:
                break
            cleaned = stripped
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned.lower()

    else:
        # Default: trim whitespace, strip excess quotes
        cleaned = val_str.strip()
        while len(cleaned) >= 2 and (
            (cleaned.startswith('"') and cleaned.endswith('"')) or
            (cleaned.startswith("'") and cleaned.endswith("'"))
        ):
            cleaned = cleaned[1:-1].strip()
        return cleaned
