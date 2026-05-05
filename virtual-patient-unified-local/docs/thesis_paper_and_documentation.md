# A Real-Time 2D Virtual Patient for Motivational Interviewing Training

**Author:** Irapuranik  
**Date:** April 30, 2026  
**Project:** Virtual Patient - Unified Local

## Abstract

Motivational Interviewing (MI) training requires repeated, high-quality interpersonal practice, yet standardized patient programs are constrained by cost, staffing, and scheduling. This thesis presents a real-time, browser-based virtual patient platform that combines automatic speech recognition, large language model dialogue generation, text-to-speech synthesis, and 2D viseme-based animation for embodied interaction. The system integrates educational workflows (authentication, case administration, assignments, transcripts, and live practice) with a modular conversation pipeline over WebSockets. A key contribution is a low-cost 2D avatar strategy using Rhubarb-compatible mouth cues and optional diffusion-based viseme set generation with LoRA-supported personalization. The implementation supports local-first deployment while preserving extensibility for cloud backends and research experimentation. This document provides both a research-style analysis and full technical documentation for replication, extension, and thesis submission.

## Keywords

Motivational Interviewing, Virtual Patient, Medical Education, Conversational AI, Lip Sync, Whisper, ElevenLabs, FastAPI, React, LoRA

---

## 1. Introduction

Motivational Interviewing (MI) is an evidence-based, person-centered counseling method used to strengthen intrinsic motivation for behavior change. MI competence is developed through repeated, reflective interaction, but access to realistic role-play opportunities remains limited in many training environments. Existing methods rely heavily on peer role-play and standardized patients, both of which are resource-intensive.

Recent progress in speech AI and language models enables conversational simulators that can provide scalable and repeatable practice. However, many educational systems remain text-only, and many avatar systems focus on visual novelty rather than pedagogical consistency. This project addresses both issues by integrating a complete educational workflow with a speech-first, visually embodied 2D patient interface.

## 2. Problem Statement

The core problem is to create a scalable, low-cost virtual patient system that supports MI-aligned communication training while preserving:

- real-time turn-taking,
- scenario-specific behavioral control,
- replayable transcript records for reflection and assessment,
- and sufficient visual embodiment to improve learner engagement over text-only chat.

## 3. Contributions

This thesis contributes:

1. **Unified architecture:** Integration of two prior proof-of-concept lines into a single deployable system (`virtual-patient-unified-local`) while preserving lineage.
2. **Voice-first runtime loop:** Microphone input -> Whisper transcription -> LLM response generation -> ElevenLabs synthesis -> viseme cue playback in browser.
3. **SQL-governed prompt policy:** Composition of global and case-level prompts to support reproducible pedagogy and controlled experiments.
4. **2D viseme animation pipeline:** Rhubarb-style mouth cues with static shape assets (`A-H`, `X`, `blink`) rendered by React.
5. **Optional personalized viseme generation:** Local/HuggingFace/Gemini image generation from a base face (`A.png`) with identity-lock prompting and LoRA support hooks.
6. **Research-ready platform operations:** Authentication, case management, assignments, dashboards, transcript persistence, and practice submission states.

## 4. System Architecture

### 4.1 High-level overview

The platform follows a client-server architecture:

- **Frontend:** React + TypeScript application for user authentication, case selection, and live practice sessions.
- **Backend:** FastAPI service with REST APIs and a WebSocket endpoint for low-latency conversation.
- **Data layer:** SQLite by default (configurable via `DATABASE_URL`) with SQLAlchemy models.
- **External AI services:** OpenAI (LLM/STT), ElevenLabs (TTS/alignment), optional diffusion image backends.

### 4.2 Runtime conversation flow

1. User opens a practice case and authenticates via JWT.
2. Browser establishes WebSocket (`/ws/conversation`) and sends auth payload with case context.
3. User sends text or base64 audio.
4. Audio turns are transcribed by Whisper (`stt_service`).
5. Backend builds effective system prompt from global + case prompts.
6. LLM response is streamed to frontend for immediate visual feedback.
7. Response text is chunked and synthesized to audio; each chunk includes mouth cues.
8. Frontend queues audio sequentially and animates the 2D mouth shape timeline.
9. Conversation history is persisted to database and can be submitted/reviewed.

### 4.3 Prompt governance model

Prompt behavior is structured with two policy layers:

- **Global prompt** (`AppSettings` key `global_prompt`): institution-wide MI policy and safety constraints.
- **Case prompt** (`Case.system_prompt`): patient persona and scenario-specific context.

The backend compacts and optionally truncates prompts for latency, then merges them at runtime. This enables consistent pedagogical framing with case-level customization.

## 5. Implementation Details

### 5.1 Backend implementation

The backend is implemented with FastAPI and includes:

- router-based API modules (`auth`, `cases`, `assignments`, `practice`, `settings`, `viseme_generation`),
- startup validation for keys and DB availability,
- optional seed-admin creation from environment variables,
- middleware for CORS and security headers,
- rate-limited health endpoints,
- robust WebSocket handling with authenticated session state.

Conversation turns are managed by asynchronous orchestration:

- streamed token accumulation,
- sentence/chunk scheduling for low perceived latency,
- parallelized bounded-concurrency TTS generation,
- ordered audio emission with synchronized cue arrays,
- persistence and cleanup logic tied to practice status.

### 5.2 Frontend implementation

The frontend (`frontend-react`) provides:

- role-based user journeys (student/admin),
- case loading and session lifecycle management,
- reconnect-aware WebSocket conversation hook,
- audio playback queue and mouth cue synchronization,
- interactive 2D patient view (`PatientAvatar2D`),
- submission workflow and status banners.

Practice mode combines chat UI with audio controls and press-to-record microphone capture. The avatar receives:

- current mouth shape,
- optional generated case-specific shape base URL,
- head/eye motion parameters from `useAvatarMotion` (currently conservative for stability).

### 5.3 Security and operational safeguards

Implemented safeguards include:

- JWT-based auth for API + WebSocket entry,
- token transfer in first WebSocket message rather than query strings,
- payload size checks for audio,
- default security response headers,
- CORS restrictions,
- startup warnings for weak/missing secrets,
- local-only storage fallback for avatar assets if Supabase is not enabled.

## 6. Avatar and Viseme Generation

The system supports two viseme asset strategies:

1. **Static default set:** pre-bundled mouth shape PNGs under `public/static/shapes`.
2. **Generated per-case set:** admin-generated shapes stored under case-specific directories and served to practice sessions.

Generation pipeline:

- produce `A.png` from text prompt (or upload a reference),
- derive `B-H`, `X`, and `blink` via image-to-image with identity-preserving prompts,
- run quality checks/retries in local backend where configured.

Backends:

- `local` (default, diffusion on local machine),
- `hf` (Hugging Face inference providers),
- `gemini` (Google image generation).

Optional LoRA integration (`CUSTOM_LOCAL_LORA_DIR`, `CUSTOM_LOCAL_LORA_SCALE`) allows identity/style tuning for consistent mouth packs.

## 7. Evaluation Perspective (Engineering)

This implementation is validated primarily as an engineering and systems thesis artifact:

- end-to-end conversational loop is functional in browser,
- transcript persistence and workflow state transitions are operational,
- multimodal responses are delivered with aligned cues,
- architecture supports local reproducibility and backend substitution.

Suggested empirical research studies:

- compare MI skill performance vs text-only baseline,
- measure perceived empathy/trust under different TTS style parameters,
- compare personalized vs generic viseme packs for engagement and realism,
- investigate learning retention with repeated practice sessions.

## 8. Limitations

Current limitations include:

- no completed clinical outcomes study in this codebase alone,
- head motion remains intentionally conservative in baseline deployment,
- cloud-service dependence for some AI components unless alternatives are configured,
- possible latency variability from external API round trips.

## 9. Future Work

Recommended next steps:

1. Add structured MI scoring rubrics and automated reflective feedback.
2. Expand emotion/state modeling for patient consistency across long dialogues.
3. Add optional on-device STT/TTS pathways for privacy-sensitive deployments.
4. Run controlled educational studies with pre/post assessment design.
5. Build analytics dashboards for faculty-level cohort insights.

## 10. Conclusion

The Virtual Patient - Unified Local project demonstrates that a practical, low-cost, browser-based MI training simulator can combine pedagogical control, real-time multimodal interaction, and maintainable software architecture in a single platform. By integrating voice dialogue, lip-synced 2D embodiment, and educational workflow tooling, the system offers a strong foundation for both immediate training use and formal research studies.

---

## Technical Documentation

## A. Repository Layout

- `virtual-patient-unified-local/backend`: FastAPI server, routes, services, models, scripts.
- `virtual-patient-unified-local/frontend-react`: React frontend for admin/student workflows and practice UI.
- `virtual-patient-unified-local/docs`: thesis and presentation artifacts.
- `virtual-patient-poc-1`, `virtual-patient-poc-2d`: predecessor repositories preserved for lineage.

## B. Prerequisites

- Python 3.11+
- Node.js 18+
- `ffmpeg`
- Rhubarb Lip Sync binary (configurable path)
- API keys: OpenAI, ElevenLabs (optional Gemini/HuggingFace depending on selected image backend)

## C. Local Setup

### Backend

1. `cd virtual-patient-unified-local/backend`
2. install Python dependencies from `requirements.txt`
3. copy `.env.example` to `.env` at project root and configure secrets
4. run `python3 main.py`

### Frontend

1. `cd virtual-patient-unified-local/frontend-react`
2. `npm install`
3. `npm run dev`

Frontend proxies `/api`, `/ws`, and `/uploads` to backend when `VITE_API_URL` is unset.

## D. Core Runtime APIs

- REST health endpoints: `/health`, `/api/health`
- Auth: `/api/auth/register`, `/api/auth/login`
- Practice WebSocket: `/ws/conversation`
- Viseme generation endpoints under `/api/admin/visemes/*`

## E. Database Notes

- Default DB is SQLite (`backend/aimii.db`) when `DATABASE_URL` is not provided.
- Session transcripts and statuses are persisted per user/case.
- Practice states include `not_started`, `in_progress`, `submitted`.

## F. Environment Configuration (Selected)

- `OPENAI_API_KEY`
- `ELEVEN_LABS_API_KEY`
- `JWT_SECRET`
- `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_ADMIN_DISPLAY_NAME`
- `VISEME_IMAGE_BACKEND` (`local` | `hf` | `gemini`)
- `CUSTOM_LOCAL_LORA_DIR`, `CUSTOM_LOCAL_LORA_SCALE`
- `RHUBARB_PATH`

## G. Operational Tips

- Keep prompts concise for lower latency.
- Use per-case viseme shape directories for better identity consistency.
- Monitor TTS/STT API limits in longer classroom sessions.
- Use submitted session transcripts for supervision and reflective debrief.

## H. Reproducibility Checklist

- Pin Python and Node versions used in experiments.
- Archive `.env` configuration schema (without secrets).
- Export database snapshot for study replication.
- Record prompt versions (global + case) used during data collection.
- Document model/provider versions for LLM, STT, TTS, and image generation.

## References

- Miller, W. R., & Rollnick, S. (2012). *Motivational Interviewing: Helping People Change* (3rd ed.). Guilford Press.
- FastAPI Documentation. [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- React Documentation. [https://react.dev/](https://react.dev/)
- OpenAI API Docs. [https://platform.openai.com/docs](https://platform.openai.com/docs)
- ElevenLabs API Docs. [https://elevenlabs.io/docs](https://elevenlabs.io/docs)
