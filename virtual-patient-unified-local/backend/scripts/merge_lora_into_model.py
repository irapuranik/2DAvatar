"""
Merge trained LoRA weights into the base SD1.5 model and save a single checkpoint.

This eliminates the ~3x inference overhead from PeftModel wrapping on MPS.

Usage:
    python scripts/merge_lora_into_model.py [--lora-dir lora_weights/final] [--output models/sd15-viseme-merged]
"""
from __future__ import annotations

import argparse
import gc
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_MODEL = "runwayml/stable-diffusion-v1-5"
BACKEND_DIR = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-model", type=str, default=BASE_MODEL)
    p.add_argument("--lora-dir", type=str, default=str(BACKEND_DIR / "lora_weights" / "final"))
    p.add_argument("--output", type=str, default=str(BACKEND_DIR / "models" / "sd15-viseme-merged"))
    args = p.parse_args()

    import torch
    from diffusers import StableDiffusionPipeline
    from peft import PeftModel

    device = "cpu"
    dtype = torch.float32

    logger.info(f"Loading base model: {args.base_model}")
    pipe = StableDiffusionPipeline.from_pretrained(
        args.base_model,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )

    logger.info(f"Loading LoRA from: {args.lora_dir}")
    pipe.unet = PeftModel.from_pretrained(pipe.unet, args.lora_dir)

    logger.info("Merging LoRA into base weights...")
    pipe.unet = pipe.unet.merge_and_unload()

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving merged model to: {output_path}")
    pipe.save_pretrained(str(output_path))

    del pipe
    gc.collect()

    logger.info("Done! Merged model saved.")
    print(f"\nTo use this model, set in .env:")
    print(f"  LOCAL_TXT2IMG_MODEL={output_path.resolve()}")
    print(f"  LOCAL_IMG2IMG_MODEL={output_path.resolve()}")
    print(f"  CUSTOM_LOCAL_LORA_DIR=")
    print(f"  (clear LORA_DIR so the separate LoRA loading is skipped)")


if __name__ == "__main__":
    main()
