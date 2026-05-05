# Abstract

Motivational interviewing (MI) is a collaborative, goal-oriented communication style used to help people explore and resolve ambivalence to strengthen their personal motivation for change. It is a person-centered approach that focuses on empathy and autonomy, making it highly effective for addressing addiction, health behaviors, and mental health issues. However, because human standardized-patient resources are expensive and limited, practicing MI at scale remains a significant challenge. A safe, repeatable setting for conversation practice is essential if learners are expected to develop the timing, tone, and responsiveness that real clinical dialogue requires. Text-only interfaces are useful for content rehearsal, but they flatten many of the interpersonal signals that shape motivational interviewing (MI) encounters. Passive video has the opposite limitation: it can model delivery, but it cannot adapt to the learner’s choices in real time. For MI training to be effective, learners need an interactive system that responds dynamically while remaining grounded in clinically informed communication patterns.

To address this, a browser-deployable virtual patient system was developed that closes a real-time speech loop. The system captures user microphone input, processes it through automatic speech recognition, and uses a large language model, guided by MI-oriented prompts, to generate dialogue. This dialogue is passed through text-to-speech with timestamp alignment, which drives a 2D mouth animation using Rhubarb-style viseme cues. The platform merges essential educational workflows, such as assignments, transcripts, and cases, with a low-cost 2D avatar representation, intentionally avoiding hyper-realistic avatars for the primary practice mode. The system also uses Gemini image creation (Nano Banana Mode) to create the full set of mouth-shape visemes from one base character image. The prompts are designed to keep identity locked (same face, pose, framing, lighting, and colors) while changing only the mouth (and eyes for blink) for each viseme frame.  This document outlines the end-to-end architecture, implementation details, limitations, and a roadmap for empirical studies on skill transfer, perceived empathy, and engagement. Full project documentation is available in the included source files within the appendices.  



# Virtual Patient — Unified Local
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

# Backend 
```bash
cd backend
cp ../.env.example ../.env
# Edit ../.env — set OPENAI_API_KEY, ELEVEN_LABS_API_KEY, JWT_SECRET, optional SEED_ADMIN_*

python3 -m pip install -r requirements.txt
source .venv/bin/activate
python3 main.py
# API: http://127.0.0.1:5001 health: GET /health
```
In a second terminal:
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


