import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings

_logger = logging.getLogger(__name__)

# backend/ lives next to frontend-react/ at the monorepo root (not backend/frontend-react/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_PUBLIC_DIR = PROJECT_ROOT / "frontend-react" / "public"

_ENV_FILE = PROJECT_ROOT / ".env"
if not _ENV_FILE.exists():
    _ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    openai_api_key: str = ""
    eleven_labs_api_key: str = ""
    # Alias for Gemini-backed "Nano Banana" viseme generation.
    # If set, it will be used as GEMINI_API_KEY when VISEME_IMAGE_BACKEND=gemini.
    nanobanana_api_key: str = ""

    # gpt-4o-mini is much faster TTFT than gpt-4o; override with OPENAI_MODEL=gpt-4o if needed.
    openai_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"

    # LLM latency: long global prompts + full history increase time-to-first-token.
    # Only the last N messages are sent to OpenAI; full history remains in the DB.
    llm_history_max_messages: int = 12
    llm_max_tokens: int = 80
    llm_temperature: float = 0.45
    # 0 = no limit. Set e.g. 6000 if admins paste huge globals.
    global_prompt_max_chars: int = 0

    default_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    # Expressive default for stronger emotional contrast in patient speech.
    eleven_labs_model: str = "eleven_multilingual_v2"
    # Smaller MP3 = faster TTS + Rhubarb. Valid: mp3_22050_32, mp3_44100_64, mp3_44100_128, …
    eleven_labs_output_format: str = "mp3_22050_32"

    default_stability: float = 0.4
    default_similarity_boost: float = 0.75
    default_style: float = 0.5

    # Local JWT auth (required for unified-local)
    jwt_secret: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_expire_days: int = 7

    # Optional: promote this email to admin on register/login sync
    admin_email: str = ""

    database_url: str = ""

    # Optional Supabase Storage for avatars / image library (leave empty for local files only)
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "avatars"

    frontend_url: str = ""

    # Legacy Supabase JWT verification (only if you set supabase_jwt_secret + supabase_url)
    supabase_jwt_secret: str = ""
    jwt_secret_legacy: str = ""

    # Rhubarb lip-sync (see README); override with RHUBARB_PATH in .env
    rhubarb_path: str = (
        "/Users/irapuranik/Downloads/rhubarb-lip-sync-1.14.0-osx/"
        "Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb"
    )

    # Optional one-shot admin seed (local dev)
    seed_admin_email: str = ""
    seed_admin_password: str = ""
    seed_admin_display_name: str = "Admin"

    # Hugging Face Inference — routed via router.huggingface.co.
    # Token needs "Make calls to Inference Providers" enabled.
    huggingface_api_token: str = ""
    hf_inference_timeout_s: int = 300
    hf_request_delay_s: float = 2.0
    hf_max_retries: int = 3
    hf_retry_backoff_s: float = 8.0

    # FLUX.2 cloud generation (HF router providers). Keep providers configurable because
    # model/provider availability can vary by account and month-to-month limits.
    hf_flux2_txt2img_provider: str = "hf-inference"
    hf_flux2_txt2img_provider_fallbacks: str = "replicate"
    # HF router currently exposes FLUX.2 primarily for editing tasks; use FLUX.1-schnell
    # for A.png text bootstrap, then FLUX.2 for reference-preserving edits.
    hf_flux2_txt2img_model: str = "black-forest-labs/FLUX.1-schnell"
    hf_flux2_txt2img_model_fallbacks: str = ""
    hf_flux2_txt2img_width: int = 512
    hf_flux2_txt2img_height: int = 512
    hf_flux2_txt2img_steps: int = 4
    hf_flux2_txt2img_guidance_scale: float = 7.5

    hf_flux2_img2img_provider: str = "hf-inference"
    hf_flux2_img2img_provider_fallbacks: str = "replicate"
    hf_flux2_img2img_model: str = "black-forest-labs/FLUX.2-klein-4B"
    hf_flux2_img2img_model_fallbacks: str = "black-forest-labs/FLUX.2-dev"
    hf_img2img_strength: float = 0.42
    hf_img2img_guidance_scale: float = 7.5
    hf_img2img_steps: int = 4

    # Deprecated FLUX.1-era keys (kept for backward-compatible env files).
    hf_txt2img_provider: str = ""
    hf_txt2img_model: str = ""
    hf_img2img_provider: str = ""
    hf_img2img_model: str = ""

    # Viseme image backend: "local" (on-device), "hf" (HF providers), or "gemini" (Google Gemini API).
    viseme_image_backend: str = "local"
    # Use SD 1.5 locally for stronger controllable mouth edits on Apple Silicon.
    local_txt2img_model: str = "runwayml/stable-diffusion-v1-5"
    local_img2img_model: str = "runwayml/stable-diffusion-v1-5"
    local_txt2img_width: int = 512
    local_txt2img_height: int = 512
    local_txt2img_steps: int = 30
    local_txt2img_guidance_scale: float = 7.5
    local_img2img_steps: int = 35
    local_img2img_guidance_scale: float = 8.0
    local_img2img_strength: float = 0.62
    custom_local_max_retries: int = 2
    custom_local_retry_strength_step: float = 0.08
    custom_local_retry_guidance_step: float = 0.5
    custom_local_request_delay_s: float = 0.0
    custom_local_identity_threshold: float = 0.84
    custom_local_background_threshold: float = 0.85
    custom_local_mouth_delta_threshold: float = 0.055
    custom_local_blink_eye_delta_threshold: float = 0.035
    custom_local_x_mouth_max_delta: float = 0.08
    custom_local_lora_dir: str = ""
    custom_local_lora_scale: float = 0.8

    # Gemini image generation backend (google-genai SDK, model: gemini-3.1-flash-image-preview).
    gemini_api_key: str = ""
    gemini_image_model: str = "gemini-3.1-flash-image-preview"
    gemini_image_width: int = 512
    gemini_image_height: int = 512
    gemini_request_delay_s: float = 1.0
    gemini_max_retries: int = 3
    gemini_retry_backoff_s: float = 5.0

    model_config = {
        "env_file": str(_ENV_FILE) if _ENV_FILE.exists() else None,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
