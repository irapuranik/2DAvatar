# Abstract

Motivational interviewing (MI) is a collaborative, goal-oriented communication style used to help people explore and resolve ambivalence to strengthen their personal motivation for change. It is a person-centered approach that focuses on empathy and autonomy, making it highly effective for addressing addiction, health behaviors, and mental health issues. However, because human standardized-patient resources are expensive and limited, practicing MI at scale remains a significant challenge. A safe, repeatable setting for conversation practice is essential if learners are expected to develop the timing, tone, and responsiveness that real clinical dialogue requires. Text-only interfaces are useful for content rehearsal, but they flatten many of the interpersonal signals that shape motivational interviewing (MI) encounters. Passive video has the opposite limitation: it can model delivery, but it cannot adapt to the learner’s choices in real time. For MI training to be effective, learners need an interactive system that responds dynamically while remaining grounded in clinically informed communication patterns.

To address this, a browser-deployable virtual patient system was developed that closes a real-time speech loop. The system captures user microphone input, processes it through automatic speech recognition, and uses a large language model, guided by MI-oriented prompts, to generate dialogue. This dialogue is passed through text-to-speech with timestamp alignment, which drives a 2D mouth animation using Rhubarb-style viseme cues. The platform merges essential educational workflows, such as assignments, transcripts, and cases, with a low-cost 2D avatar representation, intentionally avoiding hyper-realistic avatars for the primary practice mode. The system also uses Gemini image creation (Nano Banana Mode) to create the full set of mouth-shape visemes from one base character image. The prompts are designed to keep identity locked (same face, pose, framing, lighting, and colors) while changing only the mouth (and eyes for blink) for each viseme frame.  This document outlines the end-to-end architecture, implementation details, limitations, and a roadmap for empirical studies on skill transfer, perceived empathy, and engagement. Full project documentation is available in the included source files within the appendices.  



# Appendix A - 2D Virtual Patient README
(React/MUI, cases, admin, practice, assignments)
## Prerequisites
-	Python 3.11+ recommended
-	Node.js 18+ for the frontend
-	[ffmpeg](https://ffmpeg.org/) (used by pydub before Rhubarb)
-	[Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) — the default binary path

## Setup

```bash
cd virtual-patient-unified-local
```

## Backend 
```bash
cd backend
cp ../.env.example ../.env
# Edit ../.env — set OPENAI_API_KEY, ELEVEN_LABS_API_KEY, JWT_SECRET, optional SEED_ADMIN_*

python3 -m pip install -r requirements.txt
source .venv/bin/activate
python3 main.py
# API: http://127.0.0.1:5001 health: GET /health
```
## In a second terminal:
```bash
cd virtual-patient-unified-local/frontend-react 
npm install
npm run dev
# Opens Vite (default port from vite.config.ts, often http://localhost:3000)
```
Leave `VITE_API_URL` unset so the browser talks to the same origin and Vite **proxies** `/api` ## Auth (local)
-	Register and login use the API (`POST /api/auth/register`, `POST /api/auth/login`) and store
-	Optional: set `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` in `.env` to create an admin user .
Mouth PNGs live in `frontend-react/public/static/shapes/` (copied from POC-2D). The practice ### Viseme generation from `A.png` (optional, admin)
The viseme pipeline supports three backends controlled by `VISEME_IMAGE_BACKEND`:
`gemini`: Google Gemini image generation via `google-genai` SDK (set `GEMINI_API_KEY` in `.
All backends use the same generation flow:
-	**A.png** from text (`txt2img`)
-	**B–H, X, blink** from `A.png` (`img2img`) with strict identity-lock prompts
**Per case (recommended):** In **Admin -> Edit case**, either **Upload viseme reference (A.png) or **Generate B-H, X, blink**

**Global (demo only):** `POST /api/admin/visemes/generate-from-reference-a` with JSON `{ "prom

**Per-case API:** `POST /api/admin/visemes/generate-for-case` with `{ "case_id": "...", "promp

Custom `A.png` is generated when you use **Generate base face from prompt**. 

# Appendix B: Viseme Generation via Gemini

Configuration:
Set these values in .env (see virtual-patient-unified-local/.env.example):
`VISEME_IMAGE_BACKEND=gemini`
# Either key works (`NANOBANANA_API_KEY` is treated as alias)
`GEMINI_API_KEY=...`
# or
`NANOBANANA_API_KEY=...`
# Optional tuning
`GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview`
`GEMINI_IMAGE_WIDTH=512`
`GEMINI_IMAGE_HEIGHT=512`
`GEMINI_REQUEST_DELAY_S=1.0`
`GEMINI_MAX_RETRIES=3`
`GEMINI_RETRY_BACKOFF_S=5.0`

Notes:
If both keys are set, `GEMINI_API_KEY` is used first.
If no key is present and backend is gemini, generation fails with a clear error.
strength is accepted by API for consistency, but Gemini path does not use numeric img2img strength.

API Flow (Admin)

1) Global shape generation
`POST /api/admin/visemes/generate-from-reference-a`
Writes to global shapes directory (`frontend-react/public/static/shapes/`).
Requires existing `A.png` unless `generate_base_face_from_prompt=true`.

Example body:
{"prompt": "2D cartoon clinician, friendly expression, teal scrubs",
"character_hint": "female, shoulder-length dark hair, warm skin tone",
"generate_base_face_from_prompt": true}

2) Per-case generation (recommended)
`POST /api/admin/visemes/generate-for-case`
Writes to `frontend-react/public/generated/cases/{case_id}/shapes/`.
On success, updates case path so practice mode uses generated case-specific shapes.

Example body:
{"case_id": "your-case-id",
"prompt": "2D cartoon patient, middle-aged male",
"character_hint": "brown jacket, neutral lighting",
"generate_base_face_from_prompt": true}

3) Poll job status
`GET /api/admin/visemes/jobs/{job_id}`
Returns status fields like:
status (queued, running, completed, failed)
current_viseme
progress
written
error
Prompting Strategy (Identity Lock)
Gemini prompts in this project enforce:
same character identity
same camera framing/composition
same pose/head/eyes/hair placement
same lighting/colors/style
transparent PNG output
no text/watermarks/new objects
Per-viseme instructions only modify the specific mouth/eye target shape.
This is why character drift is minimized across frames.

Output Files
Expected generated files:
`A.png` (base / closed mouth for P/B/M pressure)
`B.png`
`C.png`
`D.png`
`E.png`
`F.png`
`G.png`
`H.png`
`X.png` (idle/relaxed closed mouth)
`blink.png` (eyes closed variant of A)

Error Handling & Troubleshooting
Common issues and fixes:

“`GEMINI_API_KEY` (or `NANOBANANA_API_KEY`) is required…”
Add one of the keys and restart backend.

“Gemini response did not contain an image…”
Verify model supports image output and account/API permissions are valid.

Job fails mid-run due to intermittent API errors
Increase retry/backoff:

`GEMINI_MAX_RETRIES`
`GEMINI_RETRY_BACKOFF_S`
optionally `GEMINI_REQUEST_DELAY_S`

Inconsistent image sizes across frames
Backend auto-resizes to configured target / reference size, but set consistent:
`GEMINI_IMAGE_WIDTH`
`GEMINI_IMAGE_HEIGHT`

Implementation References
Backend orchestrator: `virtual-patient-unified-local/backend/services/viseme_generation_service.py`
Admin routes + job queue/polling: `virtual-patient-unified-local/backend/routes/viseme_generation.py`
Config/env definitions: `virtual-patient-unified-local/backend/config.py`
Env template values: `virtual-patient-unified-local/.env.example`
Existing high-level project docs: `virtual-patient-unified-local/README.md`


# Appendix C: ElevenLabs Mood and Slider Examples

## ElevenLabs 3-Mood Slider Examples
These are three practical presets for the virtual patient voice, each paired with a generated ## Mood Presets
1.	Calm / Cooperative
-	stability: 0.78
-	similarity_boost: 0.82
-	style: 0.20
-	sample: `docs/presentation/audio/mood_calm.mp3`
2.	Anxious / Worried
-	stability: 0.36
-	similarity_boost: 0.75
-	style: 0.68
-	sample: `docs/presentation/audio/mood_anxious.mp3`
3.	Defensive / Irritable
-	stability: 0.46
-	similarity_boost: 0.72
-	style: 0.74
-	sample: `docs/presentation/audio/mood_defensive.mp3` ## Notes
-	Keep the spoken text constant across moods for clean comparisons.
-	If delivery sounds too flat, increase `style` by 0.05 to 0.10.
-	If voice identity drifts, increase `similarity_boost` by 0.0



