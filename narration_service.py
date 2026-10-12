import os
import io
import math
import wave
import struct
import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger("nook.narration_service")

# Default voice and model settings
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (calm, contemplative voice)
DEFAULT_MODEL_ID = "eleven_turbo_v2_5"

def generate_narration_audio(text: str) -> Tuple[bytes, str]:
    """
    Sends narrative text to ElevenLabs TTS API using eleven_turbo_v2_5 model.
    Returns (audio_bytes, mime_type).
    Falls back to a clean procedural naturalist acoustic chime WAV if ElevenLabs key is unset or fails,
    ensuring zero client playback errors.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip() or DEFAULT_VOICE_ID
    model_id = os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID).strip() or DEFAULT_MODEL_ID

    if not text:
        text = "Observe. Investigate. Create. Welcome to Nook."

    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not configured. Generating pleasant acoustic fallback audio.")
        return generate_procedural_chime_wav(), "audio/wav"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.75,
            "style": 0.20,
            "use_speaker_boost": True
        }
    }

    try:
        logger.info("Requesting ElevenLabs TTS stream for %d characters (voice: %s, model: %s)...", len(text), voice_id, model_id)
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        
        if response.status_code == 200:
            logger.info("ElevenLabs narration generated successfully (%d bytes).", len(response.content))
            return response.content, "audio/mpeg"
        else:
            logger.error("ElevenLabs API returned %d: %s. Using acoustic chime fallback.", response.status_code, response.text[:200])
            return generate_procedural_chime_wav(), "audio/wav"

    except Exception as e:
        logger.error("ElevenLabs narration request failed: %s. Using acoustic fallback.", e, exc_info=True)
        return generate_procedural_chime_wav(), "audio/wav"


def generate_procedural_chime_wav() -> bytes:
    """
    Generates a soft, contemplative 3-second naturalist ambient chime WAV file (440Hz / 554.37Hz / 659.25Hz chord)
    with smooth cosine attack and decay envelopes so offline/unauthenticated users always get pleasant audio feedback.
    """
    sample_rate = 22050
    duration_s = 2.4
    num_samples = int(sample_rate * duration_s)
    
    # E-major ambient triad (E4, G#4, B4)
    freqs = [329.63, 415.30, 493.88]
    
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Natural exponential decay envelope
            envelope = math.exp(-2.2 * t) * (1.0 - math.exp(-30.0 * t))
            
            # Harmonic chime synthesis
            val = 0.0
            for f in freqs:
                val += math.sin(2.0 * math.pi * f * t)
            val = (val / len(freqs)) * envelope * 0.7
            
            # Clamp to 16-bit signed integer
            int_val = int(max(min(val, 0.999), -0.999) * 32767.0)
            frames.extend(struct.pack("<h", int_val))
            
        wav_file.writeframes(frames)

    return wav_io.getvalue()
