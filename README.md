<<<<<<< HEAD
<<<<<<< HEAD
# Nook — Observe. Investigate. Create.
> Production-grade ecological fieldwork web companion powered by the **Gemma 4** open-weight multimodal model (`gemma-4-31b-it` / `gemma-4-26b-a4b-it`) and ElevenLabs conversational voice.

Designed with an **Artisanal Minimalism** philosophy and smart-casual naturalist tone, Nook encourages users to leave their screens, step into the wild, hone their observation skills, and preserve memories in an offline-first local field journal.

---

## Core Architecture & Pipeline

1. **Observe**: Mobile-first capture interface (`capture="environment"`) with client-side canvas optimization, drag-and-drop, and camera support.
2. **Analyze**: Flask processes JPEG, PNG, WebP, or GIF images, streaming bytes directly to **Gemma 4 Multimodal** via the official `google-genai` Python SDK. Generates an 8-facet naturalist field card constrained to $\le 25$ words per string:
   - `seen`: 3–6 direct visual marks (color, shape, texture).
   - `possible_identification`: Cautious, humble identification.
   - `alternatives`: Plausible other origins or species.
   - `hypotheses`: 2 working theories on state and environmental cause.
   - `uncertain`: Optical and subterranean limits of the photograph.
   - `investigation_question`: Attention-building challenge.
   - `observation_mission`: Immediate non-invasive outdoor action.
   - `atelier`: Safe, creative crafting activity with fallen elements or sketches.
3. **Narrate**: `POST /narrate` generates speech using **ElevenLabs TTS** (`eleven_turbo_v2_5`) or plays acoustic naturalist chimes when offline/unauthenticated.
4. **Investigate**: Real-time voice field debrief via the official `<elevenlabs-convai>` conversational voice widget.
5. **Preserve**: Complete session preservation in client-side `localStorage` (offline-first, 100% private), with digital souvenirs/posters and automatic background re-sync when network reconnects.

---

## Quickstart & Running Locally (Port 5000)

### 1. Setup Environment
```bash
cd Nook
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials (`.env`)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your API keys:
- `GOOGLE_API_KEY`: Google Gemini / Gemma API key.
- `GEMMA_MODEL_ID`: Defaults to `gemma-4-31b-it` (can be switched to `gemma-4-26b-a4b-it`).
- `ELEVENLABS_API_KEY`: ElevenLabs TTS key for field narration.
- `ELEVENLABS_AGENT_ID`: Optional Conversational Voice agent ID for real-time talk debriefs.

### 3. Launch Flask on Port 5000
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser or phone browser.

---

## Deployment on Render (Free Tier)
A complete `render.yaml` blueprint is included:
1. Connect your repository to Render.
2. Select **New Web Service** using `render.yaml` or set:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
3. Add `GOOGLE_API_KEY`, `ELEVENLABS_API_KEY`, and `ELEVENLABS_AGENT_ID` in the Render Environment Variables tab.

---

## Offline Wild Mode
- Powered by `static/sw.js` (PWA Service Worker).
- When deep in forests with 0 bars of reception, observations and crafting notes save to browser storage immediately.
- As soon as network signal is regained, background sync updates pending field entries automatically without page refreshes.
=======
# Nook
>>>>>>> origin/main
=======
# Nook
>>>>>>> origin/main
