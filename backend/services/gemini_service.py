"""
Google Gemini integration service using google-genai SDK.
Used for semantic disambiguation on borderline entity match candidates.
"""

from typing import Dict, Any, Optional
from backend.config import GEMINI_API_KEY


class GeminiDisambiguationService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def disambiguate_pair(
        self,
        record_a: Dict[str, Any],
        record_b: Dict[str, Any],
        context_hints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask Gemini to evaluate whether two records represent the exact same real-world entity.
        Returns match decision, confidence, and reasoning.
        """
        if not self.is_available():
            return {
                "match": False,
                "confidence": 0.5,
                "reasoning": "Gemini client not configured; fallback default applied.",
                "llm_invoked": False
            }

        prompt = f"""
You are an expert Entity Resolution and Record Linkage system.
Determine if the following two records refer to the same real-world entity (e.g. same person or organization).

Record A: {record_a}
Record B: {record_b}
{f"Context: {context_hints}" if context_hints else ""}

Respond strictly with valid JSON with keys:
- "is_same_entity": true or false
- "confidence": float between 0.0 and 1.0
- "reasoning": brief explanation of why they are or are not the same entity.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text_resp = response.text.strip()
            return {
                "match": "true" in text_resp.lower(),
                "raw_response": text_resp,
                "llm_invoked": True
            }
        except Exception as e:
            return {
                "match": False,
                "confidence": 0.0,
                "reasoning": f"Gemini invocation error: {str(e)}",
                "llm_invoked": True,
                "error": str(e)
            }
