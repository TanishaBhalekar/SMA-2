"""
Progressive Entity Resolution Engine.
Implements a multi-stage progressive matching pipeline:
  Stage 1: Deterministic / Exact Blocking (e.g. exact email, tax ID, phone)
  Stage 2: Fuzzy String Matching using RapidFuzz (token sort ratio, partial ratio)
  Stage 3: LLM Disambiguation using Google Gemini for ambiguous borderline candidates
"""

from typing import Dict, Any, List, Tuple
from rapidfuzz import fuzz
from backend.services.gemini_service import GeminiDisambiguationService


class ProgressiveResolutionEngine:
    def __init__(
        self,
        exact_threshold: float = 0.95,
        fuzzy_threshold: float = 0.80,
        enable_llm: bool = True
    ):
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold
        self.enable_llm = enable_llm
        self.gemini_service = GeminiDisambiguationService()

    def calculate_string_similarity(self, s1: str, s2: str) -> float:
        """Calculate normalized similarity between two strings using RapidFuzz token sort ratio."""
        if not s1 or not s2:
            return 0.0
        score = fuzz.token_sort_ratio(str(s1).strip().lower(), str(s2).strip().lower())
        return score / 100.0

    def evaluate_pair(
        self,
        record_a: Dict[str, Any],
        record_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Progressively evaluate two records to determine if they match.
        """
        # 1. Deterministic Exact Checks (e.g., exact email, national ID)
        email_a = str(record_a.get("email", "")).strip().lower()
        email_b = str(record_b.get("email", "")).strip().lower()
        if email_a and email_b and email_a == email_b:
            return {
                "match": True,
                "score": 1.0,
                "method": "deterministic",
                "reason": "Exact email match"
            }

        # 2. Fuzzy Matching on Display Names / Organization Names
        name_a = str(record_a.get("name") or record_a.get("display_name") or "")
        name_b = str(record_b.get("name") or record_b.get("display_name") or "")
        name_sim = self.calculate_string_similarity(name_a, name_b)

        # High confidence fuzzy match
        if name_sim >= self.exact_threshold:
            return {
                "match": True,
                "score": name_sim,
                "method": "rapidfuzz",
                "reason": f"High fuzzy name similarity ({name_sim:.2f})"
            }

        # 3. Ambiguous / Borderline Zone -> LLM Disambiguation
        if self.enable_llm and (self.fuzzy_threshold <= name_sim < self.exact_threshold):
            if self.gemini_service.is_available():
                llm_result = self.gemini_service.disambiguate_pair(record_a, record_b)
                return {
                    "match": llm_result.get("match", False),
                    "score": name_sim,
                    "method": "llm_gemini",
                    "reason": f"Borderline score ({name_sim:.2f}) disambiguated by Gemini LLM",
                    "llm_details": llm_result
                }

        # Accept if meets fuzzy threshold without LLM, otherwise reject
        is_match = name_sim >= self.fuzzy_threshold
        return {
            "match": is_match,
            "score": name_sim,
            "method": "rapidfuzz",
            "reason": f"Fuzzy comparison result ({name_sim:.2f})"
        }
