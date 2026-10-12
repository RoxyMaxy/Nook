import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("nook.parser")

def extract_json_block(text: str) -> str:
    """
    Extract JSON string from potential Markdown code fences or raw response text.
    Handles ```json ... ```, ``` ... ```, or bracket search.
    """
    if not text:
        return ""
    
    cleaned = text.strip()
    
    # Check for markdown code fences
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(fence_pattern, cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Check if there is an outer curly brace pair
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()
        
    return cleaned


def limit_words(text: str, max_words: int = 25) -> str:
    """Ensure a string does not exceed the naturalist constraint of max 25 words."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    words = text.strip().split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]) + "..."


def sanitize_field_card(data: Any) -> Dict[str, Any]:
    """
    Validates and normalizes the parsed dictionary into the strict Field Card schema.
    Applies the cautious naturalist constraint (max 25 words per string).
    """
    if not isinstance(data, dict):
        raise ValueError("Field Card data must be a JSON dictionary.")

    # 1. "seen": 3 to 6 direct visual observations (color, shape, texture)
    raw_seen = data.get("seen", [])
    if isinstance(raw_seen, str):
        raw_seen = [s.strip() for s in raw_seen.split("\n") if s.strip()]
    elif not isinstance(raw_seen, list):
        raw_seen = []
        
    seen = [limit_words(str(item), 25) for item in raw_seen if item]
    if not seen:
        seen = ["Clear visual specimen captured under outdoor daylight."]
    seen = seen[:6]

    # 2. "possible_identification": cautious naturalist tone
    raw_ident = data.get("possible_identification") or "Unidentified natural specimen"
    possible_ident = limit_words(str(raw_ident), 25)

    # 3. "alternatives": 1 or 2 other plausible options
    raw_alt = data.get("alternatives", [])
    if isinstance(raw_alt, str):
        raw_alt = [a.strip() for a in raw_alt.split("\n") if a.strip()]
    elif not isinstance(raw_alt, list):
        raw_alt = []
    alternatives = [limit_words(str(item), 25) for item in raw_alt if item][:2]
    if not alternatives:
        alternatives = ["Related native species sharing comparable color and surface features."]

    # 4. "hypotheses": 2 possible explanations regarding state or origin
    raw_hyp = data.get("hypotheses", [])
    if isinstance(raw_hyp, str):
        raw_hyp = [h.strip() for h in raw_hyp.split("\n") if h.strip()]
    elif not isinstance(raw_hyp, list):
        raw_hyp = []
    hypotheses = [limit_words(str(item), 25) for item in raw_hyp if item][:2]
    if not hypotheses:
        hypotheses = ["Shape and coloration reflect recent ambient temperature and sunlight exposure."]

    # 5. "uncertain": what photo cannot tell due to limitations
    raw_uncert = data.get("uncertain") or "Internal texture, scent, and underground root development remain invisible in this frame."
    uncertain = limit_words(str(raw_uncert), 25)

    # 6. "investigation_question": attention & observation skill development
    raw_q = data.get("investigation_question") or "Look closely at the underside or nearby surroundings: what unnoticed details appear?"
    investigation_question = limit_words(str(raw_q), 25)

    # 7. "observation_mission": outdoor action without touching/disturbing nature
    raw_mission = data.get("observation_mission") or "Take a few steps back and look around to see where else in this habitat this specimen grows or rests."
    observation_mission = limit_words(str(raw_mission), 25)

    # 8. "atelier": creative crafting task based on found objects safely
    raw_atelier = data.get("atelier") or "Make a light sketch of its primary shape and lines in your pocket notebook."
    atelier = limit_words(str(raw_atelier), 25)

    return {
        "seen": seen,
        "possible_identification": possible_ident,
        "alternatives": alternatives,
        "hypotheses": hypotheses,
        "uncertain": uncertain,
        "investigation_question": investigation_question,
        "observation_mission": observation_mission,
        "atelier": atelier
    }


def parse_gemma_json(raw_text: str) -> Dict[str, Any]:
    """
    Parses and sanitizes raw text output from Gemma 4 into a valid Field Card structure.
    Catches formatting anomalies and guarantees schema adherence.
    """
    cleaned_block = extract_json_block(raw_text)
    try:
        parsed = json.loads(cleaned_block)
        return sanitize_field_card(parsed)
    except Exception as e:
        logger.warning("Standard JSON parse failed (%s). Attempting relaxed heuristic parsing...", e)
        # Fallback: check if we can fix common JSON slip-ups like trailing commas
        cleaned_block_fixed = re.sub(r",\s*([\]}])", r"\1", cleaned_block)
        try:
            parsed = json.loads(cleaned_block_fixed)
            return sanitize_field_card(parsed)
        except Exception as inner_e:
            logger.error("Failed relaxed JSON parse: %s. Raw preview: %s", inner_e, raw_text[:200])
            raise ValueError(f"Could not parse valid Field Card JSON from Gemma response: {inner_e}")
