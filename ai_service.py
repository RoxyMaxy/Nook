import os
import io
import json
import base64
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types
from parser_helper import parse_gemma_json

logger = logging.getLogger("nook.ai_service")

# Naturalist Fieldwork System Prompt demanding strict JSON schema and tone
NATURALIST_PROMPT = """You are Nook's Field Naturalist AI, powered by Gemma 4.
Your purpose is to observe nature with humility, encourage exploration, cultivate keen attention, and inspire creative interaction without disturbing the wild.
Analyze the provided nature specimen image with realistic, grounded naturalist observation.

IMPORTANT TONE & VOCABULARY GUIDELINES:
1. Grounded & Realistic: Look directly at the real details in the photo (actual colors, spots, tears, vein directions, insect marks, crooked edges, dryness, decay, soil, textures). Avoid generic boilerplate filler like "organic edge geometry" or "resilient native perennial".
2. Accessible Naturalist Language: Use clear, concrete, scientific yet friendly terms that everyday nature explorers can easily grasp (e.g. "veins running parallel", "crooked serrated edges", "small dried brown spot near the tip", "velvety surface", "leaf margin"). Never overwhelm the user with dense, impenetrable academic jargon that would make them give up.
3. Realistic Identification: Give a tangible, common identification with plausible relatives in parentheses, e.g. "Hazelnut leaf (or possibly young elm or beech)" or "White clover leaf (or wood sorrel)", stating it cautiously as possible rather than dogmatic fact.
4. Tangible Hypotheses: Propose realistic, relatable explanations for its current state (e.g. "Autumn is setting in, causing the green chlorophyll to fade into yellow and brown", "Sun scorch or lack of water during hot summer days caused this dry tip", "A caterpillar or beetle chewed the notched edge").
5. Word limit: MAXIMUM 25 words per string entry. Be concise, vivid, and observational.
6. Return ONLY a valid JSON object matching this exact schema:

{
  "seen": [
    "Specific observation 1 (e.g., Organic pigment with hues of green and yellow, with a little dried brown spot at its tip)",
    "Specific observation 2 (e.g., Vein patterns running parallel from the main central rib to the edges)",
    "Specific observation 3 (e.g., Crooked, slightly toothed edges with a soft textured surface)",
    "Specific observation 4 (optional additional visual mark)"
  ],
  "possible_identification": "Grounded name, e.g. Hazelnut leaf (or possibly young elm or alder)",
  "alternatives": [
    "Plausible alternative 1 (e.g., Hornbeam leaf with similar parallel veins)",
    "Plausible alternative 2 (e.g., Young beech leaf showing early seasonal discoloration)"
  ],
  "hypotheses": [
    "First hypothesis on why it looks like this (e.g., Autumn is approaching, so green pigments are breaking down into yellow hues)",
    "Second hypothesis on its condition (e.g., Might have suffered sun scorch during late summer, creating the dry brown tip)"
  ],
  "uncertain": "What the photo cannot reveal (e.g., Whether the leaf was picked fresh from a branch or found fallen on the forest floor)",
  "investigation_question": "An accessible curiosity prompt (e.g., Turn it over gently: are the veins raised on the underside, and are there tiny hairs?)",
  "observation_mission": "A safe outdoor micro-action (e.g., Take five quiet steps back and see if other leaves on the same tree or bush share this pattern)",
  "atelier": "A simple creative crafting task (e.g., Place the leaf under scrap paper and rub gently with a pencil to reveal its vein skeleton)"
}

Do not include markdown outside the JSON block. Output pure JSON.
"""

def generate_field_card(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Calls Gemma 4 Multimodal model using the official google-genai SDK.
    Accepts raw image bytes and returns a sanitized Field Card dictionary.
    """
    model_id = os.environ.get("GEMMA_MODEL_ID", "gemma-4-31b-it")
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()

    logger.info("Initializing Gemma 4 inference with model: %s (image size: %d bytes, mime: %s)", model_id, len(image_bytes), mime_type)

    if not api_key:
        logger.error("GOOGLE_API_KEY not configured.")
        raise RuntimeError("GOOGLE_API_KEY is not set. Please configure it in your environment.")

    try:
        client = genai.Client(api_key=api_key)
        
        # Prepare the multimodal image part
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        models_to_try = [model_id]
        alternate_model = "gemma-4-26b-a4b-it" if "31b" in model_id else "gemma-4-31b-it"
        if alternate_model not in models_to_try:
            models_to_try.append(alternate_model)

        last_error = None
        for current_model in models_to_try:
            try:
                logger.info("Attempting multimodal inference with model: %s", current_model)
                response = client.models.generate_content(
                    model=current_model,
                    contents=[
                        image_part,
                        NATURALIST_PROMPT
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        top_p=0.9
                    )
                )

                response_text = response.text or ""
                if response_text.strip():
                    logger.info("Raw Gemma 4 response length: %d chars from %s", len(response_text), current_model)
                    return parse_gemma_json(response_text)
            except Exception as model_err:
                logger.warning("Inference with %s failed: %s. Trying next...", current_model, model_err)
                last_error = model_err

        if last_error:
            raise last_error

    except Exception as e:
        logger.error("Error during Gemma 4 inference: %s", e, exc_info=True)
        raise RuntimeError(f"Gemma 4 observation analysis error: {e}")





def limit_text(text: str, max_words: int) -> str:
    words = text.split()
    return " ".join(words[:max_words])



