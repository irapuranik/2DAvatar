"""
Local image generation helpers (no cloud credits).

Uses diffusers pipelines on Apple Silicon (MPS) or CPU.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_txt2img_pipe = None
_img2img_pipe = None
_runtime_device: str | None = None
_txt2img_lora_key: str | None = None
_img2img_lora_key: str | None = None


def _torch():
    try:
        import torch
    except Exception as e:  # pragma: no cover - runtime environment dependent
        raise RuntimeError(
            "Local image generation requires torch + diffusers. "
            "Run: pip install -r backend/requirements.txt"
        ) from e
    return torch


def _detect_device() -> str:
    global _runtime_device
    if _runtime_device:
        return _runtime_device
    torch = _torch()
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        _runtime_device = "mps"
    else:
        _runtime_device = "cpu"
    return _runtime_device


def _dtype():
    torch = _torch()
    return torch.float16 if _detect_device() == "mps" else torch.float32


def _load_txt2img(model_id: str):
    global _txt2img_pipe
    if _txt2img_pipe is not None:
        return _txt2img_pipe

    try:
        from diffusers import AutoPipelineForText2Image
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Local image generation requires diffusers. "
            "Run: pip install -r backend/requirements.txt"
        ) from e

    _txt2img_pipe = AutoPipelineForText2Image.from_pretrained(
        model_id,
        torch_dtype=_dtype(),
        use_safetensors=True,
    )
    # Apple Silicon memory safeguards: reduce peak VRAM during UNet/VAE passes.
    if hasattr(_txt2img_pipe, "enable_attention_slicing"):
        _txt2img_pipe.enable_attention_slicing()
    if hasattr(_txt2img_pipe, "enable_vae_slicing"):
        _txt2img_pipe.enable_vae_slicing()
    if hasattr(_txt2img_pipe, "enable_vae_tiling"):
        _txt2img_pipe.enable_vae_tiling()
    if hasattr(_txt2img_pipe, "safety_checker"):
        _txt2img_pipe.safety_checker = None
    if hasattr(_txt2img_pipe, "config") and hasattr(_txt2img_pipe.config, "requires_safety_checker"):
        _txt2img_pipe.config.requires_safety_checker = False
    _txt2img_pipe = _txt2img_pipe.to(_detect_device())
    logger.info("Loaded local txt2img pipeline model=%s device=%s", model_id, _detect_device())
    return _txt2img_pipe


def _load_img2img(model_id: str):
    global _img2img_pipe
    if _img2img_pipe is not None:
        return _img2img_pipe

    try:
        from diffusers import AutoPipelineForImage2Image
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Local image generation requires diffusers. "
            "Run: pip install -r backend/requirements.txt"
        ) from e

    _img2img_pipe = AutoPipelineForImage2Image.from_pretrained(
        model_id,
        torch_dtype=_dtype(),
        use_safetensors=True,
    )
    # Apple Silicon memory safeguards: reduce peak VRAM during img2img VAE encode.
    if hasattr(_img2img_pipe, "enable_attention_slicing"):
        _img2img_pipe.enable_attention_slicing()
    if hasattr(_img2img_pipe, "enable_vae_slicing"):
        _img2img_pipe.enable_vae_slicing()
    if hasattr(_img2img_pipe, "enable_vae_tiling"):
        _img2img_pipe.enable_vae_tiling()
    if hasattr(_img2img_pipe, "safety_checker"):
        _img2img_pipe.safety_checker = None
    if hasattr(_img2img_pipe, "config") and hasattr(_img2img_pipe.config, "requires_safety_checker"):
        _img2img_pipe.config.requires_safety_checker = False
    _img2img_pipe = _img2img_pipe.to(_detect_device())
    logger.info("Loaded local img2img pipeline model=%s device=%s", model_id, _detect_device())
    return _img2img_pipe


def _seed_generator(seed: Optional[int]):
    torch = _torch()
    if seed is None:
        return None
    gen = torch.Generator(device="cpu")
    gen.manual_seed(int(seed))
    return gen


def _maybe_clear_mps_cache() -> None:
    torch = _torch()
    if _detect_device() == "mps":
        try:
            torch.mps.empty_cache()
        except Exception:
            pass


def _maybe_apply_lora(pipe, *, lora_dir: str | None, lora_scale: float | None, stage: str):
    global _txt2img_lora_key, _img2img_lora_key
    if not lora_dir:
        return
    key = f"{lora_dir}:{lora_scale}"
    loaded_key = _txt2img_lora_key if stage == "txt2img" else _img2img_lora_key
    if loaded_key == key:
        return
    try:
        from peft import PeftModel
        import os

        adapter_cfg = os.path.join(lora_dir, "adapter_config.json")
        if os.path.isfile(adapter_cfg):
            pipe.unet = PeftModel.from_pretrained(pipe.unet, lora_dir)
            pipe.unet.eval()
            if lora_scale is not None and lora_scale != 1.0:
                pipe.unet.set_adapter("default")
            logger.info("Loaded LoRA (PEFT) for %s from %s", stage, lora_dir)
        else:
            pipe.load_lora_weights(lora_dir)
            if lora_scale is not None:
                try:
                    pipe.fuse_lora(lora_scale=lora_scale)
                except Exception:
                    pass
            logger.info("Loaded LoRA (diffusers) for %s from %s", stage, lora_dir)

        if stage == "txt2img":
            _txt2img_lora_key = key
        else:
            _img2img_lora_key = key
    except Exception as e:
        logger.warning("Failed to load LoRA from %s: %s — continuing without LoRA", lora_dir, e)
        if stage == "txt2img":
            _txt2img_lora_key = key
        else:
            _img2img_lora_key = key


def local_text_to_image(
    *,
    model_id: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_inference_steps: int,
    guidance_scale: float,
    seed: int | None,
    lora_dir: str | None = None,
    lora_scale: float | None = None,
):
    pipe = _load_txt2img(model_id)
    _maybe_clear_mps_cache()
    _maybe_apply_lora(pipe, lora_dir=lora_dir, lora_scale=lora_scale, stage="txt2img")
    out = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        width=width,
        height=height,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=_seed_generator(seed),
    )
    return out.images[0]


def local_image_to_image(
    *,
    model_id: str,
    image,
    prompt: str,
    negative_prompt: str,
    strength: float,
    num_inference_steps: int,
    guidance_scale: float,
    seed: int | None = None,
    lora_dir: str | None = None,
    lora_scale: float | None = None,
):
    pipe = _load_img2img(model_id)
    _maybe_clear_mps_cache()
    _maybe_apply_lora(pipe, lora_dir=lora_dir, lora_scale=lora_scale, stage="img2img")
    out = pipe(
        image=image,
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        strength=strength,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        generator=_seed_generator(seed),
    )
    return out.images[0]
