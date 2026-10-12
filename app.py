import os
import sys
import io
import json
import base64
import logging
from flask import Flask, render_template, request, jsonify, send_file, Response
from dotenv import load_dotenv

# Load environment configuration (.env)
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nook.app")

from ai_service import generate_field_card
from narration_service import generate_narration_audio

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)
app.secret_key = os.environ.get("SECRET_KEY", "nook-nature-fieldwork-secret-key-default")

# Allowed MIME types for uploaded nature specimens
ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif"
}

@app.route("/")
def index():
    """Main fieldwork application interface."""
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Returns non-secret runtime configuration for the client (model ID, ElevenLabs Agent ID, features).
    Secrets (API keys) are strictly kept on the server.
    """
    model_id = os.environ.get("GEMMA_MODEL_ID", "gemma-4-31b-it")
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID", "").strip()
    has_gemini_key = bool(os.environ.get("GOOGLE_API_KEY", "").strip())
    has_elevenlabs_key = bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())

    return jsonify({
        "status": "ok",
        "model_id": model_id,
        "elevenlabs_agent_id": agent_id,
        "ai_ready": has_gemini_key,
        "tts_ready": has_elevenlabs_key
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_specimen():
    """
    OBSERVE & ANALYZE pipeline:
    Validates uploaded nature image (jpeg, png, webp, gif), passes bytes to Gemma 4 via google-genai,
    and returns a structured Field Card.
    Supports either multipart/form-data or application/json (base64 data URL).
    """
    try:
        image_bytes = None
        mime_type = "image/jpeg"

        # Case 1: multipart/form-data upload
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected."}), 400
            
            content_type = file.content_type or "image/jpeg"
            if content_type not in ALLOWED_MIME_TYPES:
                return jsonify({
                    "error": f"Invalid image format: '{content_type}'. Supported formats: JPEG, PNG, WebP, GIF."
                }), 400
            
            mime_type = content_type
            image_bytes = file.read()

        # Case 2: application/json containing base64 image data
        elif request.is_json:
            data = request.get_json() or {}
            raw_base64 = data.get("image", "")
            if not raw_base64:
                return jsonify({"error": "No image payload provided."}), 400

            # Parse data URL scheme: data:image/png;base64,....
            if "," in raw_base64:
                header, base64_str = raw_base64.split(",", 1)
                # extract mime
                if ";" in header and ":" in header:
                    mime_type = header.split(";")[0].split(":")[1]
            else:
                base64_str = raw_base64

            if mime_type not in ALLOWED_MIME_TYPES:
                # fallback check
                mime_type = "image/jpeg"

            try:
                image_bytes = base64.b64decode(base64_str)
            except Exception as b64_err:
                logger.error("Base64 decoding error: %s", b64_err)
                return jsonify({"error": "Invalid base64 image data."}), 400

        else:
            return jsonify({"error": "Unsupported request format. Send multipart form or JSON."}), 400

        if not image_bytes or len(image_bytes) == 0:
            return jsonify({"error": "Image file is empty."}), 400

        logger.info("Processing specimen observation: %d bytes, mime: %s", len(image_bytes), mime_type)

        # Execute Gemma 4 Multimodal inference
        field_card = generate_field_card(image_bytes=image_bytes, mime_type=mime_type)

        return jsonify({
            "status": "success",
            "field_card": field_card,
            "meta": {
                "model": os.environ.get("GEMMA_MODEL_ID", "gemma-4-31b-it"),
                "bytes": len(image_bytes),
                "mime_type": mime_type
            }
        })

    except Exception as e:
        logger.error("Error analyzing specimen: %s", e, exc_info=True)
        return jsonify({
            "status": "error",
            "error": f"Observation analysis failed: {str(e)}"
        }), 500

@app.route("/narrate", methods=["POST"])
def narrate_card():
    """
    NARRATE pipeline:
    POST /narrate receives card text and uses the ElevenLabs TTS API
    (Model: eleven_turbo_v2_5) to stream back an audio/mpeg or audio/wav binary stream.
    """
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()

        # If not provided directly in text, allow passing the field_card object to compose naturalist narration
        if not text and "field_card" in data:
            card = data["field_card"]
            ident = card.get("possible_identification", "")
            seen_bullets = ". ".join(card.get("seen", []))
            hyp = ". ".join(card.get("hypotheses", []))
            mission = card.get("observation_mission", "")
            text = f"Field Card. Possible identification: {ident}. Visual marks: {seen_bullets}. Working hypotheses: {hyp}. Immediate mission: {mission}"

        if not text:
            text = "Observe. Investigate. Create. Welcome to Nook."

        audio_bytes, mime_type = generate_narration_audio(text)

        return Response(
            audio_bytes,
            mimetype=mime_type,
            headers={
                "Content-Disposition": "inline; filename=field_narration.mp3",
                "Cache-Control": "no-cache",
                "Content-Length": str(len(audio_bytes))
            }
        )

    except Exception as e:
        logger.error("Narration endpoint failure: %s", e, exc_info=True)
        return jsonify({"error": f"Narration failed: {str(e)}"}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Render and monitoring."""
    return jsonify({
        "status": "healthy",
        "app": "Nook Fieldwork",
        "model": os.environ.get("GEMMA_MODEL_ID", "gemma-4-31b-it")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
    logger.info("Starting Nook Fieldwork web application on port %d (localhost:%d)", port, port)
    app.run(host="0.0.0.0", port=port, debug=debug)
