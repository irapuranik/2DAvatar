"""
Viseme generation orchestration.

- Local custom path: quality-scored/retried viseme generation.
- HF path: provider/model fallback over router providers.
"""
from __future__ import annotations

import hashlib
import io
import logging
import time
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image

from config import FRONTEND_PUBLIC_DIR, settings
from services.custom_viseme_generator import generate_local_viseme_set
from services.hf_image_service import describe_hf_error, image_to_image_with_retry, text_to_image_with_retry

logger = logging.getLogger(__name__)

_IMG2IMG_GLOBAL = (
    "Generate a cartoon avatar image. Use the reference image. Same character, same pose, same camera framing, "
    "same lighting, same colors. Do not move the head/eyes/hair at all. "
    "Transparent background (PNG). Exact same canvas size as reference. "
    "Only change the mouth/eyes as instructed below."
)

_IMG2IMG_NEGATIVE = (
    "realistic person, different person, different face, different hair, different clothes, "
    "two people, crowd, side view, profile, new background, zoom, crop change, "
    "deformed, blurry, low quality, watermark, text"
)

_VISEME_CUES: dict[str, str] = {
    # Mouth shape instructions (prompt-engineered) for each 2D viseme PNG.
    "B": "Slightly open mouth with clenched teeth. Used for most consonants (e.g. “K”, “S”, “T”, etc.). Also used for some vowels such as the “EE” sound in bee.",
    "C": "Open mouth. Used for vowels like “EH” as in men and “AE” as in bat. Also used for some consonants, depending on context.",
    "D": "Wide open mouth. Used for vowels like “AA” as in father.",
    "E": "Slightly rounded mouth. Used for vowels like “AO” as in off and “ER” as in bird. This shape is also used as an in-between when animating from C or D to F. Make sure the mouth isn’t wider open than for C. Both C E F and D E F should result in smooth animation.",
    "F": "Puckered lips. Used for “UW” as in you, “OW” as in show, and “W” as in way.",
    "G": "Upper teeth touching the lower lip for “F” as in for and “V” as in very.",
    "H": "Used for long “L” sounds, with the tongue raised behind the upper teeth. The mouth should be at least far open as in C, but not quite as far as in D.",
    "X": "Idle position. Used for pauses in speech. This should be the same mouth drawing used when the character is walking around without talking. Almost identical to A, but with slightly less pressure between the lips: for X.png, the lips should be closed but relaxed.",
    "blink": "Closed-eyes state of A.png (eyes fully closed). Mouth should match A.png (closed mouth for P/B/M sounds with ever-so-slight pressure between the lips)."
}


def _gemini_client():
    from google import genai  # pyright: ignore[reportMissingImports]
    # "Nano Banana" alias: support NANOBANANA_API_KEY without forcing users to rename env vars.
    api_key = (settings.gemini_api_key or settings.nanobanana_api_key or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY (or NANOBANANA_API_KEY) is required when VISEME_IMAGE_BACKEND=gemini.")
    return genai.Client(api_key=api_key)


def _gemini_base_prompt(character_desc: str) -> str:
    return (
        "Generate a single stylized 2D cartoon portrait for a virtual patient avatar. "
        "Requirements: exactly one person, frontal view only, head and shoulders centered, "
        "eyes open looking directly at camera, transparent background (PNG), soft even lighting, no props, no text, no watermarks. "
        "Mouth shape for the “P”, “B”, and “M” sounds: closed mouth with ever-so-slight pressure between the lips. "
        "This is almost identical to X.png, but with slightly more pressure between the lips. "
        "Same lighting, same style, and a fixed, neutral head/eye/hair placement (no camera motion). "
        "Square canvas composition. "
        f"Character description: {character_desc}."
    )


def _gemini_viseme_prompt(*, character_desc: str, viseme_key: str) -> str:
    cue = _VISEME_CUES[viseme_key]
    return (
        "Edit this avatar image. "
        # Global constraints (verbatim intent from the request).
        "Global constraints: Same character, same pose, same camera framing, same lighting, same colors. "
        "Do not move head/eyes/hair at all. Transparent background (PNG). Exact same canvas size as reference. "
        "Preserve everything exactly: identity, face shape, skin tone, hairstyle, hair color, eye color, clothing, "
        "background, framing, lighting, scale, and pose. "
        "Do NOT add watermarks, text, or change the art style. "
        "Per-frame instruction (ONLY this change): "
        f"{cue}"
    )


def _gemini_extract_image(response: Any) -> bytes:
    """Extract the first inline image bytes from a Gemini generateContent response."""
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data
    raise RuntimeError("Gemini response did not contain an image. Check model and API key support.")


def _gemini_generate_text_to_image(client: Any, prompt: str, model: str) -> bytes:
    from google.genai import types  # pyright: ignore[reportMissingImports]
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )
    return _gemini_extract_image(response)


def _gemini_generate_image_to_image(client: Any, prompt: str, ref_image: Any, model: str) -> bytes:
    """ref_image is a PIL.Image.Image."""
    from google.genai import types  # pyright: ignore[reportMissingImports]
    response = client.models.generate_content(
        model=model,
        contents=[prompt, ref_image],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )
    return _gemini_extract_image(response)


def _run_gemini_generation(
    *,
    shapes_dir: Path,
    merged_prompt: str,
    strength: Optional[float],
    generate_base_from_prompt: bool,
    use_copy_default_a_if_missing: bool,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> list[str]:
    _ = strength  # Gemini editing doesn't use a numeric strength param.
    model = (settings.gemini_image_model or "gemini-3.1-flash-image-preview").strip()
    retries = max(1, int(settings.gemini_max_retries))
    backoff = max(1.0, float(settings.gemini_retry_backoff_s))
    delay = max(0.0, float(settings.gemini_request_delay_s))
    target_w = int(settings.gemini_image_width)
    target_h = int(settings.gemini_image_height)

    shapes_dir.mkdir(parents=True, exist_ok=True)
    desc = (merged_prompt or "").strip()
    a_path = shapes_dir / "A.png"
    written: list[str] = []
    viseme_keys = list(_VISEME_CUES.keys())
    total = len(viseme_keys) + (1 if generate_base_from_prompt else 0)
    step = 0

    client = _gemini_client()

    if generate_base_from_prompt:
        if not desc:
            raise ValueError("Provide a character description to generate the base face.")
        step += 1
        if on_progress:
            on_progress("A", step, total)
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                img_bytes = _gemini_generate_text_to_image(client, _gemini_base_prompt(desc), model)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                img.save(a_path, format="PNG")
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    logger.warning("Gemini A.png attempt %s/%s failed: %s", attempt + 1, retries, exc)
                    time.sleep(backoff * (attempt + 1))
        if last_exc is not None:
            raise RuntimeError(f"Gemini failed to generate A.png: {last_exc}") from last_exc
        written.append("A.png")
        if delay > 0:
            time.sleep(delay)
    else:
        if use_copy_default_a_if_missing:
            copy_default_a_if_missing(shapes_dir)
        elif not a_path.is_file():
            raise FileNotFoundError(f"Reference A.png not found at {a_path}")

    ref_img = Image.open(a_path).convert("RGB")
    ref_size = ref_img.size

    for idx, key in enumerate(viseme_keys):
        step += 1
        if on_progress:
            on_progress(key, step, total)
        out_path = shapes_dir / f"{key}.png"
        prompt = _gemini_viseme_prompt(character_desc=desc or "same character", viseme_key=key)
        last_exc = None
        for attempt in range(retries):
            try:
                img_bytes = _gemini_generate_image_to_image(client, prompt, ref_img, model)
                out = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                if out.size != ref_size:
                    out = out.resize(ref_size, Image.Resampling.LANCZOS)
                out.save(out_path, format="PNG")
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    logger.warning("Gemini viseme %s attempt %s/%s failed: %s", key, attempt + 1, retries, exc)
                    time.sleep(backoff * (attempt + 1))
        if last_exc is not None:
            raise RuntimeError(f"Gemini failed to generate {key}.png: {last_exc}") from last_exc
        written.append(f"{key}.png")
        if idx < len(viseme_keys) - 1 and delay > 0:
            time.sleep(delay)

    return written


def _csv_list(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _unique_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _txt2img_providers() -> list[str]:
    values = [
        settings.hf_flux2_txt2img_provider,
        *_csv_list(settings.hf_flux2_txt2img_provider_fallbacks),
        settings.hf_txt2img_provider,
    ]
    return _unique_ordered([v for v in values if v])


def _txt2img_models() -> list[str]:
    values = [
        settings.hf_flux2_txt2img_model,
        *_csv_list(settings.hf_flux2_txt2img_model_fallbacks),
        settings.hf_txt2img_model,
    ]
    return _unique_ordered([v for v in values if v])


def _img2img_providers() -> list[str]:
    values = [
        settings.hf_flux2_img2img_provider,
        *_csv_list(settings.hf_flux2_img2img_provider_fallbacks),
        settings.hf_img2img_provider,
    ]
    return _unique_ordered([v for v in values if v])


def _img2img_models() -> list[str]:
    values = [
        settings.hf_flux2_img2img_model,
        *_csv_list(settings.hf_flux2_img2img_model_fallbacks),
        settings.hf_img2img_model,
    ]
    return _unique_ordered([v for v in values if v])


def _iter_stage_candidates(providers: list[str], models: list[str]) -> list[tuple[str, str]]:
    return [(provider, model) for provider in providers for model in models]


def _build_client(*, provider: str, model: str) -> Any:
    from huggingface_hub import InferenceClient

    return InferenceClient(
        provider=provider,
        model=model,
        token=settings.huggingface_api_token.strip(),
        timeout=settings.hf_inference_timeout_s,
    )


def _public_root() -> Path:
    return FRONTEND_PUBLIC_DIR


def get_default_shapes_dir() -> Path:
    return _public_root() / "static" / "shapes"


def get_case_shapes_dir(case_id: str) -> Path:
    return _public_root() / "generated" / "cases" / case_id / "shapes"


def ensure_case_shapes_dir(case_id: str) -> Path:
    d = get_case_shapes_dir(case_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def copy_default_a_if_missing(shapes_dir: Path) -> None:
    target = shapes_dir / "A.png"
    if target.is_file():
        return
    src = get_default_shapes_dir() / "A.png"
    if not src.is_file():
        raise FileNotFoundError(
            f"No A.png in {shapes_dir} and no template at {src}. "
            "Upload a reference A.png or add frontend-react/public/static/shapes/A.png."
        )
    import shutil

    shutil.copy2(src, target)


def _deterministic_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _generate_a_png(client: Any, character_desc: str, out_path: Path, seed: int, model: str) -> None:
    prompt = (
        "Solo, one person only, single subject, close-up portrait, centered in frame, "
        "front facing camera, head and shoulders, looking straight at the viewer, "
        "soft even studio lighting, plain solid white background, no other people. "
        f"{character_desc}. Neutral relaxed expression, mouth gently closed, eyes open."
    )
    img = text_to_image_with_retry(
        client,
        prompt=prompt,
        negative_prompt="",
        width=settings.hf_flux2_txt2img_width,
        height=settings.hf_flux2_txt2img_height,
        num_inference_steps=settings.hf_flux2_txt2img_steps,
        guidance_scale=settings.hf_flux2_txt2img_guidance_scale,
        model=model,
        seed=seed,
    )
    img.convert("RGB").save(out_path, format="PNG")


def _generate_viseme_from_ref(
    client: Any,
    ref_bytes: bytes,
    ref_size: tuple[int, int],
    viseme_key: str,
    out_path: Path,
    strength: float,
) -> None:
    cue = _VISEME_CUES[viseme_key]
    prompt = f"{_IMG2IMG_GLOBAL} {cue}"
    out = image_to_image_with_retry(
        client,
        ref_bytes,
        prompt=prompt,
        negative_prompt=_IMG2IMG_NEGATIVE,
        strength=strength,
        guidance_scale=settings.hf_img2img_guidance_scale,
        num_inference_steps=settings.hf_img2img_steps,
    )
    out = out.convert("RGB")
    if out.size != ref_size:
        out = out.resize(ref_size, Image.Resampling.LANCZOS)
    out.save(out_path, format="PNG")


def _run_hf_generation(
    *,
    shapes_dir: Path,
    merged_prompt: str,
    strength: Optional[float],
    generate_base_from_prompt: bool,
    use_copy_default_a_if_missing: bool,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> list[str]:
    if not settings.huggingface_api_token or not settings.huggingface_api_token.strip():
        raise ValueError("HUGGINGFACE_API_TOKEN is not set; set token or switch VISEME_IMAGE_BACKEND=local")

    shapes_dir.mkdir(parents=True, exist_ok=True)
    desc = (merged_prompt or "").strip()
    a_path = shapes_dir / "A.png"
    written: list[str] = []
    viseme_keys = list(_VISEME_CUES.keys())
    total = len(viseme_keys) + (1 if generate_base_from_prompt else 0)
    step = 0

    txt2img_candidates = _iter_stage_candidates(_txt2img_providers(), _txt2img_models())
    img2img_candidates = _iter_stage_candidates(_img2img_providers(), _img2img_models())
    if not txt2img_candidates:
        raise ValueError("No FLUX txt2img providers/models configured.")
    if not img2img_candidates:
        raise ValueError("No FLUX img2img providers/models configured.")

    if generate_base_from_prompt:
        if not desc:
            raise ValueError("Provide prompt and/or character_hint to generate the base face.")
        step += 1
        if on_progress:
            on_progress("A", step, total)
        seed = _deterministic_seed(desc)
        last_exc: Optional[Exception] = None
        for provider, model in txt2img_candidates:
            try:
                txt_client = _build_client(provider=provider, model=model)
                _generate_a_png(txt_client, desc, a_path, seed, model)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("A.png failed provider=%s model=%s: %s", provider, model, describe_hf_error(exc))
        if last_exc is not None:
            raise RuntimeError(f"Failed generating A.png with all FLUX candidates: {describe_hf_error(last_exc)}") from last_exc
        written.append("A.png")
        if settings.hf_request_delay_s > 0:
            time.sleep(settings.hf_request_delay_s)
    else:
        if use_copy_default_a_if_missing:
            copy_default_a_if_missing(shapes_dir)
        elif not a_path.is_file():
            raise FileNotFoundError(f"Reference A.png not found at {a_path}")

    ref_img = Image.open(a_path).convert("RGB")
    ref_size = ref_img.size
    buf = io.BytesIO()
    ref_img.save(buf, format="PNG")
    ref_bytes = buf.getvalue()

    effective_strength = settings.hf_img2img_strength
    if strength is not None:
        effective_strength = max(0.05, min(0.95, float(strength)))

    for i, key in enumerate(viseme_keys):
        step += 1
        if on_progress:
            on_progress(key, step, total)
        out_path = shapes_dir / f"{key}.png"
        last_exc: Optional[Exception] = None
        for provider, model in img2img_candidates:
            try:
                img2img_client = _build_client(provider=provider, model=model)
                _generate_viseme_from_ref(img2img_client, ref_bytes, ref_size, key, out_path, effective_strength)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("Viseme %s failed provider=%s model=%s: %s", key, provider, model, describe_hf_error(exc))
        if last_exc is not None:
            raise RuntimeError(f"Failed to generate {key}.png with all FLUX candidates: {describe_hf_error(last_exc)}") from last_exc
        written.append(f"{key}.png")
        if i < len(viseme_keys) - 1 and settings.hf_request_delay_s > 0:
            time.sleep(settings.hf_request_delay_s)

    return written


def run_full_viseme_generation(
    *,
    shapes_dir: Path,
    merged_prompt: str,
    strength: Optional[float],
    generate_base_from_prompt: bool,
    use_copy_default_a_if_missing: bool,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
    on_diagnostic: Optional[Callable[[dict[str, Any]], None]] = None,
) -> list[str]:
    backend = (settings.viseme_image_backend or "local").strip().lower()
    if backend == "local":
        return generate_local_viseme_set(
            shapes_dir=shapes_dir,
            merged_prompt=merged_prompt,
            strength_override=strength,
            generate_base_from_prompt=generate_base_from_prompt,
            use_copy_default_a_if_missing=use_copy_default_a_if_missing,
            copy_default_a_if_missing_fn=copy_default_a_if_missing,
            on_progress=on_progress,
            on_diagnostic=on_diagnostic,
        )
    if backend == "hf":
        return _run_hf_generation(
            shapes_dir=shapes_dir,
            merged_prompt=merged_prompt,
            strength=strength,
            generate_base_from_prompt=generate_base_from_prompt,
            use_copy_default_a_if_missing=use_copy_default_a_if_missing,
            on_progress=on_progress,
        )
    if backend == "gemini":
        return _run_gemini_generation(
            shapes_dir=shapes_dir,
            merged_prompt=merged_prompt,
            strength=strength,
            generate_base_from_prompt=generate_base_from_prompt,
            use_copy_default_a_if_missing=use_copy_default_a_if_missing,
            on_progress=on_progress,
        )
    raise ValueError("VISEME_IMAGE_BACKEND must be 'local', 'hf', or 'gemini'.")
