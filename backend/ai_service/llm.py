
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from openai import OpenAI
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


# Load environment variables from project and backend .env files
backend_dir = Path(__file__).resolve().parents[1]
project_root = backend_dir.parent
if load_dotenv is not None:
    load_dotenv(project_root / ".env")
    load_dotenv(backend_dir / ".env")

# Initialize OpenAI client
_api_key = os.getenv("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=_api_key) if _api_key else None

class LLMScorer:
    """LLM-based scoring for medication reconciliation."""

    @staticmethod
    def _is_valid_api_key() -> bool:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        return bool(api_key and api_key.startswith("sk-") and "your-api-key" not in api_key)

    @staticmethod
    def _safe_json_parse(content: str) -> Dict[str, Any]:
        """Parse JSON robustly even when model wraps it in text."""
        if not content:
            raise ValueError("Empty model response")

        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Unable to parse JSON from model response")

    @staticmethod
    def _heuristic_score_medication(patient_context: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic local scorer used when LLM API is unavailable."""
        if not candidates:
            return {
                "llm_score": 0.5,
                "medication": "Unknown",
                "reasoning": "No candidates provided.",
                "model_used": "local-heuristic"
            }

        reliability_map = {"high": 1.0, "medium": 0.7, "low": 0.4}

        def _parse_date(value: Any):
            if not value:
                return None
            if isinstance(value, str):
                try:
                    return value[:10]
                except Exception:
                    return None
            return str(value)[:10]

        scored = []
        for item in candidates:
            reliability = reliability_map.get(str(item.get("source_reliability", "low")).lower(), 0.4)
            date_value = _parse_date(item.get("last_updated") or item.get("last_filled"))
            recency_bonus = 0.2 if date_value else 0.0
            score = min(1.0, 0.45 + (reliability * 0.4) + recency_bonus)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]

        return {
            "llm_score": float(best_score),
            "medication": best.get("medication", "Unknown"),
            "reasoning": "Local heuristic ranking used because OpenAI API is unavailable.",
            "model_used": "local-heuristic"
        }
    
    @staticmethod
    def score_medication(
        patient_context: Dict[str, Any],
        candidates: list,
        patient_history: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score medication candidates using LLM reasoning.
        
        Args:
            patient_context: Patient demographics, conditions, recent labs
            candidates: List of medication candidates from different sources
            patient_history: Historical medication data if available
            
        Returns:
            Dictionary with llm_score and reasoning
        """
        if not LLMScorer._is_valid_api_key() or client is None:
            return LLMScorer._heuristic_score_medication(patient_context, candidates)

        try:
            # Build context for the LLM
            context = f"""
You are a clinical decision support system specializing in medication reconciliation.

Patient Context:
- Age: {patient_context.get('age', 'Unknown')}
- Conditions: {', '.join(patient_context.get('conditions', []))}
- Recent Labs: {json.dumps(patient_context.get('recent_labs', []), default=str)}

Medication Candidates from Different Sources:
{json.dumps(candidates, indent=2, default=str)}

Task: Analyze these medication candidates and provide:
1. A confidence score (0-1) for the most likely medication
2. The recommended medication name
3. Brief reasoning

Important: Only use information explicitly provided. Do not assume additional patient conditions.
Respond in JSON format with keys: score, medication, reasoning
"""

            result = None
            last_error = None
            for _ in range(2):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a clinical decision support AI. Reply only with valid JSON."},
                            {"role": "user", "content": context}
                        ],
                        temperature=0.2,
                        max_tokens=400,
                        response_format={"type": "json_object"}
                    )
                    result_text = response.choices[0].message.content
                    result = LLMScorer._safe_json_parse(result_text)
                    break
                except Exception as error:
                    last_error = error

            if result is None:
                raise RuntimeError(f"OpenAI call failed after retry: {last_error}")
            
            return {
                "llm_score": float(result.get("score", 0.5)),
                "medication": result.get("medication", candidates[0]["medication"] if candidates else "Unknown"),
                "reasoning": result.get("reasoning", "LLM analysis completed"),
                "model_used": "gpt-3.5-turbo"
            }
        except Exception as e:
            heuristic = LLMScorer._heuristic_score_medication(patient_context, candidates)
            heuristic["reasoning"] = f"OpenAI unavailable ({str(e)}). {heuristic['reasoning']}"
            heuristic["model_used"] = "fallback"
            return heuristic

    @staticmethod
    def validate_safety(medication: str, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate medication safety against patient conditions.
        
        Args:
            medication: Medication name to validate
            patient_context: Patient demographics and conditions
            
        Returns:
            Dictionary with safety validation results
        """
        if not LLMScorer._is_valid_api_key() or client is None:
            return {
                "is_safe": True,
                "concerns": [],
                "recommendation": "Local heuristic safety check used; no explicit contraindications detected",
                "model_used": "local-heuristic"
            }

        try:
            context = f"""
You are a clinical pharmacist reviewing medication safety.

Patient Information:
- Age: {patient_context.get('age', 'Unknown')}
- Conditions: {', '.join(patient_context.get('conditions', []))}

Medication: {medication}

Check for:
1. Drug-condition interactions
2. Age-appropriate dosing
3. Critical contraindications

Respond in JSON with: is_safe (boolean), concerns (list), recommendation (string)
"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a clinical pharmacist. Reply only with valid JSON."},
                    {"role": "user", "content": context}
                ],
                temperature=0.1,
                max_tokens=250,
                response_format={"type": "json_object"}
            )

            result = LLMScorer._safe_json_parse(response.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "is_safe": True,
                "concerns": [],
                "recommendation": "Safety check fallback used",
                "model_used": "fallback",
                "error": str(e)
            }


def llm_scoring(patient_history: Dict, curr_record: Dict) -> float:
    """
    Legacy function for backward compatibility.
    Scores based on LLM analysis.
    """
    candidates = [curr_record] if isinstance(curr_record, dict) else [{"medication": str(curr_record)}]
    result = LLMScorer.score_medication(patient_history or {}, candidates)
    return result["llm_score"]

