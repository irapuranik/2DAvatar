# Virtual Patient — Unified Local

Merged application: **POC-1** feature set (React/MUI, cases, admin, practice, assignments, transcripts, image library, global prompt, voice chat) with **POC-2D** Rhubarb lip-sync and **2D mouth shapes** in practice (no photo avatar).

The original folders `virtual-patient-poc-1` and `virtual-patient-poc-2d` are unchanged; this project is a separate copy.

## Prerequisites

- Python 3.11+ recommended
- Node.js 18+ for the frontend
- [ffmpeg](https://ffmpeg.org/) (used by pydub before Rhubarb)
- [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) — the default binary path is set in `backend/config.py`; override with `RHUBARB_PATH` in `.env` if needed

## Setup

```bash
cd virtual-patient-unified-local

# Backend
cd backend
cp ../.env.example ../.env
# Edit ../.env — set OPENAI_API_KEY, ELEVEN_LABS_API_KEY, JWT_SECRET, optional SEED_ADMIN_*

python3 -m pip install -r requirements.txt
python3 main.py
# API: http://127.0.0.1:5001  health: GET /health
```

In a second terminal:

```bash
cd virtual-patient-unified-local/frontend-react
npm install
npm run dev
# Opens Vite (default port from vite.config.ts, often http://localhost:3000)
```

Leave `VITE_API_URL` unset so the browser talks to the same origin and Vite **proxies** `/api`, `/ws`, and `/uploads` to the backend (see `vite.config.ts`).

## Auth (local)

- Register and login use the API (`POST /api/auth/register`, `POST /api/auth/login`) and store a JWT in `localStorage`. No Supabase is required.
- Optional: set `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` in `.env` to create an admin user on startup if that email is not present.

## 2D avatar assets

Mouth PNGs live in `frontend-react/public/static/shapes/` (copied from POC-2D). The practice page uses `/static/shapes/*.png` from the Vite dev server or build output.

### Viseme generation from `A.png` (optional, admin)

The viseme pipeline supports three backends controlled by `VISEME_IMAGE_BACKEND`:

1. `local` (default): fully local diffusion on your machine, no cloud credits.
2. `hf`: Hugging Face router/providers (requires token permissions and available credits).
3. `gemini`: Google Gemini image generation via `google-genai` SDK (set `GEMINI_API_KEY` in `.env`).

All backends use the same generation flow:
- **A.png** from text (`txt2img`)
- **B–H, X, blink** from `A.png` (`img2img`) with strict identity-lock prompts

For the local backend, install backend dependencies (`torch`, `diffusers`, etc.) from `backend/requirements.txt`.
The custom local generator includes automatic quality checks (identity/background/mouth-shape) and retries per viseme.
For HF backend, create a token at [Hugging Face access tokens](https://huggingface.co/settings/tokens) and enable **Make calls to Inference Providers**.

**Per case (recommended):** In **Admin -> Edit case**, either **Upload viseme reference (A.png)** or check **Generate base face from prompt** and describe the character (e.g. “cartoon doctor”); then **Generate B–H, X, blink**. Files go to `frontend-react/public/generated/cases/{caseId}/shapes/`. If you neither upload nor use the checkbox, the job copies global `public/static/shapes/A.png` into the case folder first.

**Global (demo only):** `POST /api/admin/visemes/generate-from-reference-a` with JSON `{ "prompt": "...", "character_hint": "...", "strength": 0.30 }`, then poll `GET /api/admin/visemes/jobs/{job_id}`.

**Per-case API:** `POST /api/admin/visemes/generate-for-case` with `{ "case_id": "...", "prompt": "...", "character_hint": "..." }`, same job polling.

`A.png` is written when you use **Generate base face from prompt**. Lower `LOCAL_IMG2IMG_STRENGTH` or `HF_IMG2IMG_STRENGTH` keeps outputs closer to the same face.

Optional LoRA hook for local generation:
- Set `CUSTOM_LOCAL_LORA_DIR` and `CUSTOM_LOCAL_LORA_SCALE` in `.env`
- Dataset/training format reference: `backend/docs/viseme_lora_dataset.md`

## API notes

- WebSocket `audio_chunk` messages include `cues` (Rhubarb `mouthCues`) for the 2D face.
- SQLite database file defaults to `backend/aimii.db` when `DATABASE_URL` is unset.
