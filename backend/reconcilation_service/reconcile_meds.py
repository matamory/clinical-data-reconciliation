from ..ai_service.llm import llm_scoring, LLMScorer
from ..pydantic_models import PatientRecord, SourceRecord, SourceReliability, PatientContext, Lab, LabValue, ReconciliationResult, SafetyCheck
from typing import List, Dict, Optional, Any
from datetime import date, datetime
from collections import Counter
import math
import re


class MedicationReconciliation:
    """Hybrid reconciliation system combining deterministic and LLM scoring."""
    
    def __init__(self):
        self.uncertainty_threshold = 0.5
    
    # Governing: SPEC-0002 REQ "Deterministic Scoring", ADR-0002
    def deterministic_score(
        self,
        candidate: Dict[str, Any],
        patient_context: Dict[str, Any],
        all_sources: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate deterministic score based on:
        - Source reliability
        - Recency (with decay algorithm)
        - Agreement across sources
        """
        score = 0.0
        
        # 1. Source reliability component (0-1)
        reliability_map = {"high": 1.0, "medium": 0.7, "low": 0.4}
        reliability_score = reliability_map.get(candidate.get("source_reliability", "low"), 0.4)
        score += reliability_score * 0.3
        
        # 2. Recency component with relative decay (0-1)
        recency_score = self._calculate_recency_score(candidate, all_sources)
        score += recency_score * 0.3
        
        # 3. Agreement component (0-1)
        agreement_score = self._calculate_agreement_score(candidate, all_sources)
        score += agreement_score * 0.15

        # 4. Clinical appropriateness component (0-1)
        clinical_score = self._calculate_clinical_appropriateness(candidate, patient_context)
        score += clinical_score * 0.25
        
        return min(1.0, max(0.0, score))
    
    def _parse_source_date(self, source: Dict[str, Any]) -> Optional[date]:
        """Extract best available source date."""
        source_date = source.get("last_updated") or source.get("last_filled")
        if not source_date:
            return None

        if isinstance(source_date, str):
            try:
                return datetime.fromisoformat(source_date).date()
            except ValueError:
                return None
        if isinstance(source_date, date):
            return source_date
        return None

    def _calculate_recency_score(self, candidate: Dict[str, Any], all_sources: List[Dict[str, Any]]) -> float:
        """
        Calculate recency score relative to the newest source.
        The most recent source gets 1.0; older sources decay smoothly.
        """
        candidate_date = self._parse_source_date(candidate)
        if not candidate_date:
            return 0.5  # Neutral score if no date

        all_dates = [self._parse_source_date(s) for s in all_sources]
        all_dates = [d for d in all_dates if d is not None]
        if not all_dates:
            return 0.5

        newest_date = max(all_dates)
        days_from_newest = max(0, (newest_date - candidate_date).days)

        # Exponential decay against newest source
        decay_rate = 30
        recency_score = math.exp(-days_from_newest / decay_rate)
        return recency_score
    
    def _calculate_agreement_score(
        self,
        candidate: Dict[str, Any],
        all_sources: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate agreement score based on:
        - How many sources report similar medication
        - Pattern matching (regex normalization)
        - Frequency analysis
        """
        medication = candidate.get("medication", "")
        if not medication:
            return 0.0
        
        # Normalize medication name (lowercase, remove extra spaces)
        normalized = self._normalize_medication_name(medication)
        
        # Count matches
        matches = 0
        total_sources = len(all_sources)
        
        for source in all_sources:
            source_med = source.get("medication", "")
            if self._normalize_medication_name(source_med) == normalized:
                matches += 1
        
        if total_sources == 0:
            return 0.5
        
        agreement_score = matches / total_sources
        return agreement_score
    
    def _normalize_medication_name(self, name: str) -> str:
        """Normalize medication name for comparison."""
        # Keep dose/frequency; normalize punctuation and spacing only
        name = name.lower().strip()
        name = re.sub(r'[^\w\s\/\.-]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        return name

    def _extract_egfr(self, patient_context: Dict[str, Any]) -> Optional[float]:
        """Extract eGFR from multiple possible patient context shapes."""
        recent_labs = patient_context.get("recent_labs")
        if not recent_labs:
            return None

        # Support dict shape, e.g. {"eGFR": 45}
        if isinstance(recent_labs, dict):
            value = recent_labs.get("eGFR") or recent_labs.get("egfr")
            if isinstance(value, (int, float)):
                return float(value)
            return None

        # Support list shape from API model
        if isinstance(recent_labs, list):
            for lab in recent_labs:
                if not isinstance(lab, dict):
                    continue

                lab_name = str(lab.get("name", "")).lower()
                if lab_name not in {"egfr", "e_gfr", "estimated gfr"}:
                    continue

                value_obj = lab.get("value", {})
                if isinstance(value_obj, dict):
                    numeric = value_obj.get("numeric_value")
                    if isinstance(numeric, (int, float)):
                        return float(numeric)

                if isinstance(value_obj, (int, float)):
                    return float(value_obj)

        return None

    def _parse_medication_details(self, medication: str) -> Dict[str, Any]:
        """Parse medication into ingredient, dose (mg), and daily frequency estimate."""
        if not medication:
            return {"ingredient": "", "dose_mg": None, "times_per_day": None, "daily_dose_mg": None}

        normalized = medication.lower().strip()
        ingredient = re.split(r'\d', normalized, maxsplit=1)[0].strip()

        dose_match = re.search(r'(\d+(?:\.\d+)?)\s*mg\b', normalized)
        dose_mg = float(dose_match.group(1)) if dose_match else None

        if "twice daily" in normalized or "bid" in normalized:
            times_per_day = 2
        elif "three times daily" in normalized or "tid" in normalized:
            times_per_day = 3
        elif "four times daily" in normalized or "qid" in normalized:
            times_per_day = 4
        elif "once daily" in normalized or "daily" in normalized or "qd" in normalized:
            times_per_day = 1
        else:
            times_per_day = None

        daily_dose_mg = None
        if dose_mg is not None and times_per_day is not None:
            daily_dose_mg = dose_mg * times_per_day

        return {
            "ingredient": ingredient,
            "dose_mg": dose_mg,
            "times_per_day": times_per_day,
            "daily_dose_mg": daily_dose_mg
        }

    def _calculate_clinical_appropriateness(self, candidate: Dict[str, Any], patient_context: Dict[str, Any]) -> float:
        """Score medication appropriateness using simple deterministic clinical rules."""
        medication = candidate.get("medication", "")
        if not medication:
            return 0.5

        details = self._parse_medication_details(medication)
        ingredient = details.get("ingredient", "")
        daily_dose_mg = details.get("daily_dose_mg")
        egfr = self._extract_egfr(patient_context)

        score = 0.75

        # Kidney-function aware metformin rule
        if "metformin" in ingredient and egfr is not None and daily_dose_mg is not None:
            if egfr < 30:
                return 0.05
            if egfr <= 45:
                if daily_dose_mg <= 1000:
                    score = 1.0
                else:
                    # Governing: SPEC-0002 REQ "Deterministic Scoring" — any dose >1000 mg with eGFR ≤ 45 MUST score < 0.5
                    score = 0.35
            elif egfr < 60:
                if daily_dose_mg <= 2000:
                    score = 0.9
                else:
                    score = 0.6

        return min(1.0, max(0.0, score))
    
    def reconcile_medication(
        self,
        patient_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main reconciliation method combining deterministic and LLM scoring.
        
        Args:
            patient_record: Contains patient_context and sources
            
        Returns:
            Reconciliation result with scores and recommendations
        """
        patient_context = patient_record.get("patient_context", {})
        sources = patient_record.get("sources", [])
        
        if not sources:
            return self._create_empty_result("No medication sources provided")
        
        # Calculate scores for each candidate
        candidate_scores = []
        
        for source in sources:
            det_score = self.deterministic_score(source, patient_context, sources)
            candidate_scores.append({
                "source": source,
                "deterministic_score": det_score
            })
        
        # Get LLM scores
        llm_result = LLMScorer.score_medication(
            patient_context,
            sources
        )
        
        # Governing: SPEC-0002 REQ "Hybrid Score Combination" — set llm=det to avoid first-source bias
        # Assign LLM scores.
        # If LLM is unavailable (fallback), keep scoring deterministic to avoid first-source bias.
        llm_unavailable = llm_result.get("model_used") in {"fallback", "local-heuristic"}
        for score_obj in candidate_scores:
            if llm_unavailable:
                score_obj["llm_score"] = score_obj.get("deterministic_score", 0.5)
            elif score_obj["source"].get("medication") == llm_result.get("medication"):
                score_obj["llm_score"] = llm_result.get("llm_score", 0.5)
            else:
                score_obj["llm_score"] = 0.3  # Lower score for non-matching
        
        # Governing: SPEC-0002 REQ "Hybrid Score Combination", ADR-0002
        # Calculate hybrid scores and confidence
        for score_obj in candidate_scores:
            det = score_obj.get("deterministic_score", 0.5)
            llm = score_obj.get("llm_score", 0.5)
            # Weighted combination: 60% deterministic, 40% LLM
            score_obj["hybrid_score"] = (det * 0.6) + (llm * 0.4)
        
        # Find winner
        winner = max(candidate_scores, key=lambda x: x["hybrid_score"])
        
        # Calculate confidence using 4 factors
        confidence = self._calculate_confidence(
            candidate_scores,
            winner,
            llm_result
        )
        
        # Detect uncertainty signals
        uncertainty_signals = self._detect_uncertainty(sources, confidence)
        
        # Determine if review is needed
        requires_review = uncertainty_signals["total_uncertainty"] > 0
        
        # Generate safety check
        safety_check = self._check_safety(
            winner["source"].get("medication"),
            patient_context
        )
        
        # Generate recommended actions
        actions = self._generate_actions(
            winner,
            confidence,
            uncertainty_signals,
            sources,
            patient_context
        )
        
        return {
            "reconciled_medication": winner["source"].get("medication"),
            "confidence_score": confidence["overall"],
            "confidence_breakdown": confidence,
            "reasoning": self._generate_reasoning(
                winner,
                sources,
                confidence,
                patient_context,
                llm_result,
                candidate_scores
            ),
            "recommended_actions": actions,
            "clinical_safety_check": safety_check,
            "uncertainty_signals": uncertainty_signals,
            "requires_review": requires_review,
            "all_candidates": [
                {
                    "medication": s["source"].get("medication"),
                    "system": s["source"].get("system"),
                    "hybrid_score": s.get("hybrid_score", 0),
                    "deterministic_score": s.get("deterministic_score", 0),
                    "llm_score": s.get("llm_score", 0)
                }
                for s in candidate_scores
            ]
        }
    
    # Governing: SPEC-0002 REQ "Confidence Score Calibration", ADR-0002
    def _calculate_confidence(
        self,
        candidate_scores: List[Dict],
        winner: Dict,
        llm_result: Dict
    ) -> Dict[str, float]:
        """
        Calculate confidence using 4 factors:
        1. Candidate quality (0.7)
        2. Separation from 2nd place (0.1)
        3. LLM-Deterministic agreement (0.2)
        4. Uncertainty penalty (-0.1, applied elsewhere)
        """
        scores = sorted([s["hybrid_score"] for s in candidate_scores], reverse=True)
        
        # Factor 1: Quality of winning candidate
        quality = min(scores[0] if scores else 0, 1.0) * 0.7
        
        # Factor 2: Separation from second place
        separation = 0
        if len(scores) > 1:
            separation = min((scores[0] - scores[1]) * 0.5, 1.0) * 0.1
        else:
            separation = 0.1  # Only one candidate, max separation
        
        # Factor 3: Agreement between deterministic and LLM
        det_score = winner.get("deterministic_score", 0.5)
        llm_score = winner.get("llm_score", 0.5)
        agreement = (1.0 - abs(det_score - llm_score)) * 0.2
        
        # Factor 4: Uncertainty (negative)
        uncertainty = 0  # Calculated separately in uncertainty signals
        
        overall = quality + separation + agreement + uncertainty
        
        return {
            "overall": min(1.0, max(0.0, overall)),
            "quality": quality,
            "separation": separation,
            "agreement": agreement,
            "uncertainty": uncertainty
        }
    
    # Governing: SPEC-0002 REQ "Uncertainty Detection and Recommended Actions", ADR-0002
    def _detect_uncertainty(
        self,
        sources: List[Dict],
        confidence: Dict
    ) -> Dict[str, Any]:
        """Detect uncertainty signals."""
        signals = {
            "sources_conflict": 0,
            "missing_data": 0,
            "total_uncertainty": 0
        }
        
        # Check for conflicting sources
        medications = [s.get("medication") for s in sources]
        normalized_meds = [self._normalize_medication_name(m) for m in medications]
        
        if len(set(normalized_meds)) > 1:
            signals["sources_conflict"] = 1
        
        # Check for missing data
        if not sources or any(not s.get("medication") for s in sources):
            signals["missing_data"] = 1
        
        signals["total_uncertainty"] = signals["sources_conflict"] + signals["missing_data"]
        
        return signals
    
    def _check_safety(self, medication: str, patient_context: Dict) -> str:
        """Check medication safety."""
        if not medication or not patient_context:
            return "REVIEW_REQUIRED"
        
        try:
            safety_result = LLMScorer.validate_safety(medication, patient_context)
            if safety_result.get("error"):
                return "REVIEW_REQUIRED"
            # Governing: SPEC-0002 REQ "Safety Check" — LLM required for safety determination;
            # local-heuristic/fallback cannot confirm safety, so return REVIEW_REQUIRED
            if safety_result.get("model_used") in {"local-heuristic", "fallback"}:
                return "REVIEW_REQUIRED"

            if not safety_result.get("is_safe", True):
                return "FAILED"
            
            if safety_result.get("concerns"):
                return "REVIEW_REQUIRED"
            
            return "PASSED"
        except Exception:
            return "REVIEW_REQUIRED"
    
    def _generate_reasoning(
        self,
        winner: Dict,
        sources: List[Dict],
        confidence: Dict,
        patient_context: Dict,
        llm_result: Dict,
        candidate_scores: List[Dict]
    ) -> str:
        """Generate human-readable reasoning."""
        medication = winner["source"].get("medication")
        system = winner["source"].get("system")
        confidence_pct = confidence["overall"] * 100

        winner_details = self._parse_medication_details(medication or "")
        winner_ingredient = winner_details.get("ingredient", "")
        winner_daily_dose = winner_details.get("daily_dose_mg")
        egfr = self._extract_egfr(patient_context)

        # Case-specific narrative for metformin + renal context
        scenario_reasons = []

        winner_date = self._parse_source_date(winner.get("source", {}))
        clinical_sources = [
            s for s in sources
            if "pharmacy" not in str(s.get("system", "")).lower()
        ]
        clinical_dates = [self._parse_source_date(s) for s in clinical_sources]
        clinical_dates = [d for d in clinical_dates if d is not None]
        latest_clinical_date = max(clinical_dates) if clinical_dates else None

        if winner_date and latest_clinical_date and winner_date == latest_clinical_date:
            scenario_reasons.append("Primary care record is most recent clinical encounter.")

        if "metformin" in winner_ingredient and egfr is not None and egfr <= 45 and winner_daily_dose is not None and winner_daily_dose <= 1000:
            scenario_reasons.append(f"Dose reduction appropriate given declining kidney function (eGFR {int(egfr) if float(egfr).is_integer() else egfr}).")

        has_conflicting_pharmacy = False
        for source in sources:
            system_name = str(source.get("system", "")).lower()
            if "pharmacy" not in system_name:
                continue
            if self._normalize_medication_name(source.get("medication", "")) != self._normalize_medication_name(medication or ""):
                has_conflicting_pharmacy = True
                break

        if has_conflicting_pharmacy:
            scenario_reasons.append("Pharmacy fill may reflect old prescription.")

        llm_model_used = llm_result.get("model_used")
        llm_reasoning_text = (llm_result.get("reasoning") or "").strip()
        llm_selected_med = llm_result.get("medication")

        llm_is_actionable = (
            llm_model_used not in {"fallback", "local-heuristic", None}
            and llm_reasoning_text
            and llm_selected_med == medication
        )

        if scenario_reasons:
            if llm_is_actionable:
                scenario_reasons.append(f"LLM interpretation: {llm_reasoning_text}")
            return " ".join(scenario_reasons)

        # General winner explanation when no special-case clinical narrative applies
        winner_hybrid = winner.get("hybrid_score", 0.0)
        sorted_scores = sorted(candidate_scores, key=lambda item: item.get("hybrid_score", 0.0), reverse=True)
        second_hybrid = sorted_scores[1].get("hybrid_score", 0.0) if len(sorted_scores) > 1 else 0.0
        margin = max(0.0, winner_hybrid - second_hybrid)

        winner_date = self._parse_source_date(winner.get("source", {}))
        all_dates = [self._parse_source_date(s) for s in sources]
        all_dates = [d for d in all_dates if d is not None]
        newest_date = max(all_dates) if all_dates else None
        
        reasoning = f"Reconciled medication '{medication}' from {system} "
        reasoning += f"with {confidence_pct:.1f}% confidence. "

        if winner_date and newest_date and winner_date == newest_date:
            reasoning += "Selected source is the most recent available record. "
        
        if len(sources) > 1:
            reasoning += f"Evaluated {len(sources)} source(s). "
            reasoning += f"Winning candidate exceeded the next best option by {margin * 100:.1f} confidence points. "
        
        if confidence["quality"] > 0.3:
            reasoning += "Primary source is highly reliable. "
        
        if confidence["agreement"] > 0.15:
            reasoning += "LLM and deterministic scoring align. "

        if llm_is_actionable:
            reasoning += f"LLM interpretation: {llm_reasoning_text} "
        
        return reasoning
    
    # Governing: SPEC-0002 REQ "Uncertainty Detection and Recommended Actions", ADR-0002
    def _generate_actions(
        self,
        winner: Dict,
        confidence: Dict,
        uncertainty_signals: Dict,
        sources: List[Dict],
        patient_context: Dict
    ) -> List[str]:
        """Generate recommended actions."""
        winner_medication = winner.get("source", {}).get("medication", "")
        winner_details = self._parse_medication_details(winner_medication)
        winner_ingredient = winner_details.get("ingredient", "")
        winner_daily_dose = winner_details.get("daily_dose_mg")
        egfr = self._extract_egfr(patient_context)

        # Case-specific actions for metformin dose reconciliation with renal impairment
        if "metformin" in winner_ingredient and egfr is not None and egfr <= 45 and winner_daily_dose is not None and winner_daily_dose <= 1000:
            specific_actions = []

            has_hospital_conflict = any(
                "hospital" in str(s.get("system", "")).lower()
                and self._normalize_medication_name(s.get("medication", "")) != self._normalize_medication_name(winner_medication)
                for s in sources
            )
            has_pharmacy_conflict = any(
                "pharmacy" in str(s.get("system", "")).lower()
                and self._normalize_medication_name(s.get("medication", "")) != self._normalize_medication_name(winner_medication)
                for s in sources
            )

            if has_hospital_conflict:
                specific_actions.append(f"Update Hospital EHR to {winner_medication}")
            if has_pharmacy_conflict:
                specific_actions.append("Verify with pharmacist that correct dose is being filled")

            if specific_actions:
                return specific_actions

        actions = []
        
        if confidence["overall"] < 0.7:
            actions.append("Verify medication with patient or primary care provider")
        
        if uncertainty_signals.get("sources_conflict"):
            actions.append("Clarify conflicting medication records across systems")
        
        if uncertainty_signals.get("missing_data"):
            actions.append("Obtain complete medication history")
        
        actions.append("Review reconciliation result for clinical accuracy")
        
        if not actions:
            actions = ["Document reconciliation in patient record"]
        
        return actions
    
    def _create_empty_result(self, reason: str) -> Dict[str, Any]:
        """Create result when reconciliation cannot be performed."""
        return {
            "reconciled_medication": None,
            "confidence_score": 0.0,
            "reasoning": reason,
            "recommended_actions": [
                "Obtain medication sources",
                "Verify patient record"
            ],
            "clinical_safety_check": "REVIEW_REQUIRED",
            "uncertainty_signals": {
                "sources_conflict": 1,
                "missing_data": 1,
                "total_uncertainty": 2
            },
            "requires_review": True
        }


#================== RECONCILIATION LOGIC ==================
def reconcile(input_data: PatientRecord) -> ReconciliationResult:
    #Store the sources in dictionary where the key is the index of the source and the value is the source record
    sources = extract_sources(input_data)
    #Score each source in dictionary based on determinate scoring criteria including reliability, recency and agreement
    scores = {}
    for index, source in enumerate(sources):
        scores[index] = score_source(input_data, source, sources)

    best_index = max(scores, key=scores.get)
    best_source = sources[best_index]

    conflicts = determine_conflicts(sources)

    return ReconciliationResult(
        reconciled_medication=best_source.medication,
        confidence_score= calculate_confidence(list(scores.values()), scores[best_index], conflicts),
        reasoning=f"Source from {best_source.system} selected with reliability {best_source.source_reliability} and last updated on {best_source.last_updated}.",   #Placeholder for reasoning generation
        recommended_actions=["Review the medication name for accuracy.", "Check for any recent updates to the medication list."],
        clinical_safety_check= SafetyCheck.PASSED if not conflicts else SafetyCheck.REVIEW_REQUIRED
    )

def extract_sources(data:PatientRecord) ->List[SourceRecord]:
    if not data.sources:
        raise ValueError("No sources provided in the patient record.")
    return data.sources



#------------------- SCORING LOGIC -------------------
def score_source(patient_record: PatientRecord, curr_source: SourceRecord, all_sources: List[SourceRecord]) -> float:
    score = 0.0
    reliability_score = calc_reliability(curr_source.source_reliability.value)
    recency_score = calc_recency(curr_source.last_updated)
    agreement_score = calc_agreement(curr_source, all_sources)
    rule_score = (reliability_score * 0.45) + (recency_score * 0.35) + (agreement_score * 0.2)

    llm_result = llm_scoring(patient_record.patient_context, curr_source)
    score = rule_score* 0.5 + llm_result * 0.5
    #logging for debugging
    print( "rule_score: ", rule_score, " llm_score: ", llm_result, " final_score: ", score)

    return score


#Considerations for LLM scoring  & rule based scoring:
"""
ADAPTIVE WEIGHTSLimit range of LLM ouput to a specific range (e.g. 0.3 to 0.9) to prevent extreme scores that could skew the overall confidence calculation.
Detect the disagreement between LLM and rule-based scores. 
If there is a significant discrepancy (e.g. LLM gives a high score but rule-based scoring is low), this could indicate a potential issue that warrants further review.
In cases of significant disagreement, consider implementing a mechanism to flag the record for manual review or to adjust the confidence score downward to reflect the uncertainty.
Also, may want to weight the rule-based scoring more heavily in cases where there is large disagreement - rule 80% and llm 20% otherwise 70/30.
"""
    

#---------Helper functions for scoring criteria-------
def calc_reliability(reliability: str) -> float:
    if reliability == SourceReliability.low.value:
        return 0.5
    elif reliability == SourceReliability.medium.value:
        return 0.75
    elif reliability == SourceReliability.high.value:
        return 1.0
    else:
        raise ValueError(f"Unknown reliability level: {reliability}")
    
def calc_recency(last_updated: Optional[date]) -> float:
    if not last_updated:
        return 0.5
    days_difference = (date.today() - last_updated).days
    
    # Old records beyond 1 year are given a score of 0, while decay algorithm is applied for all other records
    if days_difference > 360:
        return 0.0
    
    half_life = 90  # Half-life of 90 days for recency decay
    decay_rate = math.log(2) / half_life
    weighted_score = math.exp(-decay_rate * days_difference)
    return weighted_score
    

def calc_agreement(curr_source: SourceRecord, all_sources: List[SourceRecord]) -> float:
    med_word_counter = Counter()
    for source in all_sources:
        if source == curr_source:
            continue
        normalized_med = normalize_medication(source.medication)
        med_word_counter.update(normalized_med.split())
        
    other_sources_count = len(all_sources) - 1
    if not med_word_counter or other_sources_count == 0:
        return 0.0

    curr_normalized_med = normalize_medication(curr_source.medication)
    curr_words = curr_normalized_med.split()

    if not curr_words:
        return 0.0

    matches = sum(med_word_counter[word] for word in curr_words if word in med_word_counter)
    score = float(matches) / (len(curr_words) * other_sources_count)
    return min(max(score, 0.0), 1.0)


#-------------------- END OF SCORING LOGIC -------------------

def normalize_medication(med_name:str) -> str:
    med_name = med_name.lower()
    med_name = re.sub(r'[^\w\s\+\/]', '', med_name)
    med_name = re.sub(r'\s+', ' ', med_name).strip()

    units = ['mg', 'g', 'mcg', 'ml', 'l', 'units', 'iu']
    for unit in units:
        med_name = re.sub(r'(\d+)\s*'+ unit, r'\1' + unit, med_name)

    return med_name


def determine_conflicts(sources: List[SourceRecord]) -> bool:
    normalized_meds = set()
    for source in sources:
        normalized_meds.add(normalize_medication(source.medication))
        
    return len(normalized_meds) > 1

#--------------------CONFIDENCE CALCULATION LOGIC --------------------
def calculate_confidence(scores: List[float], best_score: float, conflicts: bool) -> float:
    sorted_scores = sorted(scores, reverse=True)
    if len(sorted_scores) > 1:
        separation = best_score - sorted_scores[1]
    else:
        separation = 0.0

    confidence = 0.6 * best_score + 0.4 * separation
    
    if conflicts:
        confidence -= 0.1

    return max(0.0, min(confidence, 1.0))

#================== END OF RECONCILIATION LOGIC ==================



