"""
Custom local viseme generator with quality checks + retries.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image

from config import settings
from services.local_image_service import local_image_to_image, local_text_to_image

_SOLO = (
    "single person portrait, centered, front-facing, head-and-shoulders, "
    "white background, same camera and lighting"
)

_GLOBAL = (
    "Use reference image. Same character, same pose, same camera framing, same lighting, same colors. "
    "Do not move the head/eyes/hair at all. "
    "Transparent background (PNG). Exact same canvas size as reference. "
    "Only change the mouth/eyes as instructed below."
)

_NEGATIVE = (
    "different person, different face, different hair, different clothes, two people, crowd, side view, profile, "
    "new background, zoom, crop change, deformed, blurry, low quality, watermark, text"
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
    "X": "Idle position. Used for pauses in speech. Same mouth drawing used when the character is walking around without talking. Almost identical to A, but with slightly less pressure between the lips: for X.png, the lips should be closed but relaxed.",
    "blink": "Closed-eyes state of A.png (eyes fully closed). Mouth should match A.png (closed mouth for P/B/M sounds with ever-so-slight pressure between the lips).",
}

_DEFAULT_STRENGTH: dict[str, float] = {
    "B": 0.48,
    "C": 0.52,
    "D": 0.55,
    "E": 0.52,
    "F": 0.65,
    "G": 0.60,
    "H": 0.62,
    "X": 0.42,
    "blink": 0.45,
}

_MAX_STRENGTH: dict[str, float] = {
    "B": 0.62,
    "C": 0.68,
    "D": 0.70,
    "E": 0.68,
    "F": 0.82,
    "G": 0.78,
    "H": 0.78,
    "X": 0.55,
    "blink": 0.58,
}

_DEFAULT_GUIDANCE: dict[str, float] = {
    "B": 8.0,
    "C": 8.5,
    "D": 8.8,
    "E": 8.0,
    "F": 9.5,
    "G": 9.2,
    "H": 9.2,
    "X": 7.5,
    "blink": 7.2,
}


@dataclass
class QualityScores:
    identity: float
    mouth_delta: float
    eye_delta: float
    background: float


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _as_np(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32)


def _region(arr: np.ndarray, top: float, bottom: float, left: float, right: float) -> np.ndarray:
    h, w = arr.shape[:2]
    y1, y2 = int(h * top), int(h * bottom)
    x1, x2 = int(w * left), int(w * right)
    return arr[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]


def _identity_score(ref: np.ndarray, cur: np.ndarray) -> float:
    # Use upper-face region to avoid penalizing mouth articulation.
    r = _region(ref, 0.08, 0.62, 0.20, 0.80)
    c = _region(cur, 0.08, 0.62, 0.20, 0.80)
    mad = float(np.mean(np.abs(r - c)))
    return max(0.0, 1.0 - (mad / 255.0))


def _mouth_delta(ref: np.ndarray, cur: np.ndarray) -> float:
    r = _region(ref, 0.55, 0.88, 0.27, 0.73)
    c = _region(cur, 0.55, 0.88, 0.27, 0.73)
    return float(np.mean(np.abs(r - c)) / 255.0)


def _eye_delta(ref: np.ndarray, cur: np.ndarray) -> float:
    r = _region(ref, 0.28, 0.50, 0.22, 0.78)
    c = _region(cur, 0.28, 0.50, 0.22, 0.78)
    return float(np.mean(np.abs(r - c)) / 255.0)


def _background_score(cur: np.ndarray) -> float:
    h, w = cur.shape[:2]
    border = np.concatenate(
        [
            cur[: int(h * 0.08), :, :].reshape(-1, 3),
            cur[int(h * 0.92):, :, :].reshape(-1, 3),
            cur[:, : int(w * 0.06), :].reshape(-1, 3),
            cur[:, int(w * 0.94):, :].reshape(-1, 3),
        ],
        axis=0,
    )
    bright = np.mean(border, axis=1)
    return float(np.mean(bright > 235.0))


def _score_frame(ref_img: Image.Image, cur_img: Image.Image) -> QualityScores:
    ref = _as_np(ref_img)
    cur = _as_np(cur_img)
    return QualityScores(
        identity=_identity_score(ref, cur),
        mouth_delta=_mouth_delta(ref, cur),
        eye_delta=_eye_delta(ref, cur),
        background=_background_score(cur),
    )


def _passes_thresholds(viseme_key: str, score: QualityScores) -> tuple[bool, str]:
    if score.identity < settings.custom_local_identity_threshold:
        return False, f"identity_low:{score.identity:.3f}"
    if score.background < settings.custom_local_background_threshold:
        return False, f"background_low:{score.background:.3f}"
    if viseme_key == "blink":
        if score.eye_delta < settings.custom_local_blink_eye_delta_threshold:
            return False, f"blink_eye_delta_low:{score.eye_delta:.3f}"
        return True, "ok"
    if viseme_key == "X":
        if score.mouth_delta > settings.custom_local_x_mouth_max_delta:
            return False, f"x_mouth_too_large:{score.mouth_delta:.3f}"
        return True, "ok"
    if score.mouth_delta < settings.custom_local_mouth_delta_threshold:
        return False, f"mouth_delta_low:{score.mouth_delta:.3f}"
    return True, "ok"


def _with_lora_kwargs() -> dict[str, Any]:
    if not settings.custom_local_lora_dir.strip():
        return {}
    return {
        "lora_dir": settings.custom_local_lora_dir.strip(),
        "lora_scale": settings.custom_local_lora_scale,
    }


def _build_a_prompt(desc: str) -> str:
    words = (desc or "").split()
    short_desc = " ".join(words[:16])
    return (
        f"{_SOLO}. {short_desc}. "
        "Mouth shape for the “P”, “B”, and “M” sounds: closed mouth with ever-so-slight pressure between the lips. "
        "This is almost identical to X.png, but with slightly more pressure between the lips. "
        "Eyes open looking directly at camera. "
        "Transparent background (PNG)."
    )


def _build_viseme_prompt(desc: str, key: str) -> str:
    words = (desc or "").split()
    short_desc = " ".join(words[:16])
    return f"{_GLOBAL} {short_desc}. {_VISEME_CUES[key]}"


def generate_local_viseme_set(
    *,
    shapes_dir: Path,
    merged_prompt: str,
    strength_override: float | None,
    generate_base_from_prompt: bool,
    use_copy_default_a_if_missing: bool,
    copy_default_a_if_missing_fn: Callable[[Path], None],
    on_progress: Callable[[str, int, int], None] | None,
    on_diagnostic: Callable[[dict[str, Any]], None] | None,
) -> list[str]:
    shapes_dir.mkdir(parents=True, exist_ok=True)
    desc = (merged_prompt or "").strip()
    a_path = shapes_dir / "A.png"
    written: list[str] = []
    viseme_keys = list(_VISEME_CUES.keys())
    total = len(viseme_keys) + (1 if generate_base_from_prompt else 0)
    step = 0
    diagnostics: dict[str, Any] = {"backend": "custom_local", "visemes": {}}

    if generate_base_from_prompt:
        if not desc:
            raise ValueError("Provide prompt and/or character_hint to generate the base face.")
        step += 1
        if on_progress:
            on_progress("A", step, total)
        a_seed = _seed(f"{desc}:A")
        a_img = local_text_to_image(
            model_id=settings.local_txt2img_model,
            prompt=_build_a_prompt(desc),
            negative_prompt=_NEGATIVE,
            width=settings.local_txt2img_width,
            height=settings.local_txt2img_height,
            num_inference_steps=settings.local_txt2img_steps,
            guidance_scale=settings.local_txt2img_guidance_scale,
            seed=a_seed,
            **_with_lora_kwargs(),
        )
        a_img.convert("RGB").save(a_path, format="PNG")
        written.append("A.png")
    else:
        if use_copy_default_a_if_missing:
            copy_default_a_if_missing_fn(shapes_dir)
        elif not a_path.is_file():
            raise FileNotFoundError(f"Reference A.png not found at {a_path}")

    ref_img = Image.open(a_path).convert("RGB")
    ref_size = ref_img.size

    for idx, key in enumerate(viseme_keys):
        step += 1
        if on_progress:
            on_progress(key, step, total)

        base_strength = strength_override if strength_override is not None else _DEFAULT_STRENGTH[key]
        base_guidance = _DEFAULT_GUIDANCE[key]
        max_retries = max(0, settings.custom_local_max_retries)
        viseme_diag = {"attempts": []}
        out_path = shapes_dir / f"{key}.png"
        success = False
        fail_reason = "unknown"

        for attempt in range(max_retries + 1):
            cap = _MAX_STRENGTH.get(key, 0.85)
            attempt_strength = min(cap, base_strength + (attempt * settings.custom_local_retry_strength_step))
            attempt_guidance = min(12.0, base_guidance + (attempt * settings.custom_local_retry_guidance_step))
            img = local_image_to_image(
                model_id=settings.local_img2img_model,
                image=ref_img,
                prompt=_build_viseme_prompt(desc, key),
                negative_prompt=_NEGATIVE,
                strength=attempt_strength,
                num_inference_steps=settings.local_img2img_steps,
                guidance_scale=attempt_guidance,
                seed=_seed(f"{desc}:{key}:{attempt}"),
                **_with_lora_kwargs(),
            )
            img = img.convert("RGB")
            if img.size != ref_size:
                img = img.resize(ref_size, Image.Resampling.LANCZOS)
            score = _score_frame(ref_img, img)
            ok, reason = _passes_thresholds(key, score)
            viseme_diag["attempts"].append(
                {
                    "attempt": attempt + 1,
                    "strength": round(attempt_strength, 4),
                    "guidance": round(attempt_guidance, 4),
                    "scores": {
                        "identity": round(score.identity, 4),
                        "mouth_delta": round(score.mouth_delta, 4),
                        "eye_delta": round(score.eye_delta, 4),
                        "background": round(score.background, 4),
                    },
                    "pass": ok,
                    "reason": reason,
                }
            )
            if ok:
                img.save(out_path, format="PNG")
                success = True
                break
            fail_reason = reason

        viseme_diag["retry_count"] = max(0, len(viseme_diag["attempts"]) - 1)
        viseme_diag["status"] = "passed" if success else "failed"
        viseme_diag["final_reason"] = "ok" if success else fail_reason
        diagnostics["visemes"][key] = viseme_diag
        if on_diagnostic:
            on_diagnostic(diagnostics)

        if not success:
            raise RuntimeError(f"Local generation failed for {key}.png: {fail_reason}")

        written.append(f"{key}.png")
        if idx < len(viseme_keys) - 1 and settings.custom_local_request_delay_s > 0:
            import time

            time.sleep(settings.custom_local_request_delay_s)

    diagnostics["status"] = "completed"
    if on_diagnostic:
        on_diagnostic(diagnostics)
    return written
