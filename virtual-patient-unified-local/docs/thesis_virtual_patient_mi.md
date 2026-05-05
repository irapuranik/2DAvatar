---
title: "A Real-Time 2D Virtual Patient for Motivational Interviewing Training"
subtitle: "Multimodal Architecture, SQL-Governed Prompting, and LoRA-Driven Viseme Personalization"
author: "Thesis manuscript (synthesized from project research materials)"
date: "April 29, 2026"
abstract: |
  Motivational interviewing (MI) is effective but difficult to practice at scale because human standardized-patient resources are limited and expensive. This work presents a browser-deployable virtual patient system that closes a speech loop from user microphone input through automatic speech recognition, large-language-model dialogue guided by MI-oriented prompts, text-to-speech with temporal alignment, and two-dimensional mouth animation driven by Rhubarb-style viseme cues. The platform merges administrative and educational workflows (authentication, cases, assignments, transcripts) with a low-cost 2D avatar representation that avoids photograph-based avatars in the primary practice mode. Optional diffusion-based pipelines (local, Hugging Face, or Gemini backends) generate identity-consistent viseme image sets, with an optional Stable Diffusion 1.5 LoRA hook for improved articulation and identity lock. We summarize the end-to-end architecture, implementation anchors, limitations, and a roadmap for empirical studies on skill transfer, perceived empathy, and engagement. Full project documentation is reproduced in the appendices via included source files.
keywords:
  - Motivational interviewing
  - Virtual patient
  - Speech-to-text
  - Text-to-speech
  - Lip synchronization
  - Low-rank adaptation
header-includes:
  - \usepackage{microtype}
  - \usepackage{enumitem}
  - \usepackage{verbatim}
  - \setlist{nosep}
---

# Introduction

Motivational interviewing is a collaborative, person-centered counseling style that strengthens intrinsic motivation for change (Miller \& Rollnick, 2012). Training clinicians to use MI well requires repeated practice with realistic interpersonal feedback. Conventional approaches rely on role-play with peers, standardized patients, or supervisors. While high in fidelity, these methods scale poorly across cohorts and schedules.

Interactive simulation and virtual standardized patients have long been proposed to complement human training; recent systematic reviews in health professions education emphasize outcome measurement, fidelity, and instructional design when evaluating such systems. Advances in automatic speech recognition (ASR), generative language models, and neural text-to-speech (TTS) make continuous, voice-first conversation technically feasible in a web browser. However, many educational chat systems remain text-centric, and many avatar prototypes prioritize entertainment visuals over behaviorally grounded clinical pedagogy.

This manuscript synthesizes the design rationale, system architecture, and technical documentation of the **Virtual Patient — Unified Local** codebase: a merged application combining an earlier React-based platform (cases, admin, practice, assignments, transcripts, image library, global prompt, voice chat) with a two-dimensional mouth-shape pipeline inspired by a prior proof-of-concept using Rhubarb lip-sync, without requiring a user-uploaded photo avatar in the primary practice flow.

# Problem Statement and Contributions

## Clinical training problem

Learners need **safe, repeatable** conversation practice that preserves the rhythm and prosody of real dialogue. Text-only interfaces under-embody the interaction; purely passive video lacks the adaptive back-and-forth that MI emphasizes.

## Research gaps

Three gaps motivate the present work:

1. **MI systems are often text-centric**, with limited embodied feedback during rehearsal.
2. **Avatar systems are often visual demonstrations** rather than integrated training stacks with scenario governance, transcripts, and assignment workflows.
3. **Few low-cost 2D pipelines** unify MI-specific prompt composition, a real-time speech loop, and **personalized** viseme assets suitable for educational deployment.

## Contributions

This work contributes an **integrated, modular** educational stack:

- **SQL-governed prompt composition** merging a global MI policy with per-case system prompts for reproducibility and controlled interventions.
- A **closed speech loop**: browser capture $\rightarrow$ Whisper transcription $\rightarrow$ dialogue generation $\rightarrow$ ElevenLabs TTS with alignment $\rightarrow$ **mouth cues** consumed by the frontend.
- **Personalized 2D viseme generation** (optional) via text-to-image and image-to-image diffusion, with documented **LoRA** dataset conventions for local identity-consistent mouth packs.
- A **research-ready web application** (auth, dashboards, live practice) suitable for studies on communication training at scale.

# System Overview

## End-to-end runtime pipeline

The runtime path can be summarized as follows:

1. The learner speaks into the browser microphone; audio is encoded and sent over a WebSocket.
2. The backend transcribes audio using OpenAI Whisper (`whisper-1` by default).
3. The backend composes the final system behavior policy from persisted **global** and **case-level** prompts, then obtains a model response (streaming).
4. Spoken patient output is synthesized with ElevenLabs; alignment metadata is transformed into a time-ordered **cue** sequence (Rhubarb `mouthCues` semantics).
5. The frontend queues audio chunks, plays them sequentially, and drives the **2D avatar** by swapping PNG mouth shapes (`A`--`H`, `X`, `blink`) according to cue timestamps.

WebSocket events coordinate turns so that perceived latency remains manageable while preserving transcript traceability for downstream assessment.

## Repository lineage

The **unified-local** project intentionally preserves sibling folders for earlier proofs of concept (`virtual-patient-poc-1`, `virtual-patient-poc-2d`) while integrating their capabilities into a single deployable tree. Prerequisites include Python 3.11+, Node.js 18+, `ffmpeg`, the Rhubarb Lip Sync binary (path configurable), and API credentials for cloud services where used.

# Methodology and Subsystems

## Prompt orchestration via SQL

A global behavioral prompt is stored as an application setting (`global_prompt`). Each training case stores a case-level system prompt. Session logic **merges** global and case prompts to form the effective policy. Faculty can update one global MI guideline consistently across cohorts while preserving scenario-specific nuance—supporting **experimental reproducibility** when prompt wording is an independent variable.

## Speech-to-text

Whisper-based transcription treats STT as a first-class stage in the turn loop rather than an optional accessory. The transcript is shown in the user interface and fed forward to dialogue generation, enabling both voice-first interaction and text-based review.

## Text-to-speech and alignment

ElevenLabs synthesis returns audio together with **alignment** information. The backend maps alignment to discrete mouth states for lip-sync. Configuration exposes voice parameters such as **stability** (prosodic consistency), **similarity_boost** (adherence to a reference voice identity), and **style** (expressive coloration). These parameters are positioned for controlled studies on perceived empathy, consistency, and realism; Appendix C reproduces concrete preset values for calm, anxious, defensive, and other affective regimes from the project documentation.

## Lip synchronization and 2D rendering

**Separation of concerns** is explicit: the backend determines cue timing; the frontend renders frames. `audio_chunk` messages carry encoded audio plus the cue array. The React component `PatientAvatar2D` resolves a base URL for viseme PNGs (default static assets or per-case generated folders), selects the active shape including a **blink** overlay with guards to avoid replacing wide-open speech visemes during playback, and applies optional **head** transforms (yaw `rotateY`, pitch `rotateX`, roll `rotate`) and **eye** offsets via `object-position`. The current baseline uses static head motion (zeros) for stability; the transform interface is already present for future prosody-driven motion models.

## Optional viseme personalization (diffusion + LoRA)

The viseme pipeline supports three backends (`local`, `hf`, `gemini`) selected by `VISEME_IMAGE_BACKEND`. A common flow generates a base face `A.png` (text-to-image), then derives remaining shapes (`B`--`H`, `X`, `blink`) via image-to-image passes with **identity-lock** prompts. Local generation can load optional LoRA weights via `CUSTOM_LOCAL_LORA_DIR` and `CUSTOM_LOCAL_LORA_SCALE`. Dataset layout, caption schema, and collection heuristics are specified in Appendix B.

# User Interface and Educational Workflow

The unified frontend provides registration and login backed by JWT authentication, role-based dashboards (administrator, student), case editing (including viseme reference upload or prompt-driven base-face generation), assignments, and a **live practice session** pairing transcript, voice controls, and the animated 2D patient. This yields a **browser-only** rehearsal workflow appropriate for institutions that cannot rely on specialized client installations.

# Limitations and Future Work

Known limitations include: static head motion in the current baseline; opportunity to expand per-case viseme URL wiring in all runtime paths; and the need for **clinical validation** and learner-outcome studies beyond engineering feasibility.

Recommended empirical directions:

- Compare MI skill gains against a **text-only** baseline.
- Manipulate TTS slider settings and measure **perceived empathy** and trust.
- Contrast **personalized** viseme packs against generic packs on engagement and subjective realism.

# Conclusion

The unified virtual patient platform addresses a practical bottleneck in MI education by combining scalable voice dialogue with low-cost 2D articulation and administratively complete training workflows. Its modular architecture allows independent substitution of ASR, dialogue models, TTS providers, cue generators, and renderers—supporting both deployment and controlled research.

# References

Miller, W. R., \& Rollnick, S. (2012). *Motivational interviewing: Helping people change* (3rd ed.). Guilford Press.

```{=latex}
\newpage
\appendix
\section*{Appendix A: Virtual Patient — Unified Local (README)}
\addcontentsline{toc}{section}{Appendix A: Virtual Patient — Unified Local (README)}
\vspace{0.5em}
\hrule
\vspace{0.5em}
\verbatiminput{../README.md}
\newpage
\section*{Appendix B: Viseme LoRA Dataset Specification}
\addcontentsline{toc}{section}{Appendix B: Viseme LoRA Dataset Specification}
\vspace{0.5em}
\hrule
\vspace{0.5em}
\verbatiminput{../backend/docs/viseme_lora_dataset.md}
\newpage
\section*{Appendix C: ElevenLabs Mood and Slider Examples}
\addcontentsline{toc}{section}{Appendix C: ElevenLabs Mood and Slider Examples}
\vspace{0.5em}
\hrule
\vspace{0.5em}
\verbatiminput{presentation/elevenlabs_mood_examples_3.md}
```
