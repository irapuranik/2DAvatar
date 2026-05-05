"""
Hugging Face image-to-image calls with retries for rate limits and cold-start 503s.
Uses huggingface_hub.InferenceClient (same as manual HTTP to HF Inference, via official client).
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from config import settings

if TYPE_CHECKING:
    from PIL.Image import Image

logger = logging.getLogger(__name__)


def _http_status(exc: BaseException) -> Optional[int]:
    r = getattr(exc, "response", None)
    if r is not None and hasattr(r, "status_code"):
        return int(r.status_code)
    return None


def describe_hf_error(exc: BaseException) -> str:
    """Return a compact, user-facing HF error with common remediation hints."""
    code = _http_status(exc)
    msg = str(exc).strip() or exc.__class__.__name__
    if code == 402:
        return f"{msg} | 402 Payment Required: provider credits are depleted. Try another provider/model."
    if code == 403:
        return (
            f"{msg} | 403 Forbidden: token lacks Inference Providers permission. "
            "Enable 'Make calls to Inference Providers' in HF token settings."
        )
    if code == 404:
        return f"{msg} | 404 Not Found: model/provider route unavailable; switch to another model/provider pair."
    if code == 422:
        return f"{msg} | 422 Validation failed: check inference steps, resolution, and model-specific constraints."
    if code == 429:
        return f"{msg} | 429 Rate limited: retry later or add request delay."
    if code == 503:
        return f"{msg} | 503 Model cold start/unavailable: retry shortly."
    return msg


def image_to_image_with_retry(
    client: Any,
    image_bytes: bytes,
    *,
    prompt: str,
    negative_prompt: str,
    strength: float,
    guidance_scale: float,
    num_inference_steps: int,
) -> "Image":
    """Run InferenceClient.image_to_image with retries on 429 / 503."""
    from huggingface_hub.errors import HfHubHTTPError

    last: Optional[BaseException] = None
    max_t = max(1, settings.hf_max_retries)
    backoff = max(1.0, settings.hf_retry_backoff_s)

    for attempt in range(max_t):
        try:
            return client.image_to_image(
                image_bytes,
                prompt=prompt,
                negative_prompt=negative_prompt,
                strength=strength,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
            )
        except HfHubHTTPError as e:
            last = e
            code = _http_status(e)
            if code in (429, 503) and attempt < max_t - 1:
                wait = backoff * (attempt + 1)
                logger.warning(
                    "HF image_to_image %s (attempt %s/%s), sleeping %.1fs",
                    code,
                    attempt + 1,
                    max_t,
                    wait,
                )
                time.sleep(wait)
                continue
            raise
        except Exception:
            raise


def text_to_image_with_retry(
    client: Any,
    *,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_inference_steps: int,
    guidance_scale: float,
    model: str | None = None,
    seed: int | None = None,
) -> "Image":
    """Run InferenceClient.text_to_image with retries on 429 / 503."""
    from huggingface_hub.errors import HfHubHTTPError

    max_t = max(1, settings.hf_max_retries)
    backoff = max(1.0, settings.hf_retry_backoff_s)

    for attempt in range(max_t):
        try:
            return client.text_to_image(
                prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                model=model,
                seed=seed,
            )
        except HfHubHTTPError as e:
            code = _http_status(e)
            if code in (429, 503) and attempt < max_t - 1:
                wait = backoff * (attempt + 1)
                logger.warning(
                    "HF text_to_image %s (attempt %s/%s), sleeping %.1fs",
                    code,
                    attempt + 1,
                    max_t,
                    wait,
                )
                time.sleep(wait)
                continue
            raise
