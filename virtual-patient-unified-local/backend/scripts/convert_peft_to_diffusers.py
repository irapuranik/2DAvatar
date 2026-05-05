"""
Convert PEFT-format LoRA weights to diffusers-compatible format.

Usage:
    python scripts/convert_peft_to_diffusers.py [--input lora_weights/final] [--output lora_weights/diffusers]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from safetensors.torch import load_file, save_file


def convert_key(peft_key: str) -> str | None:
    """Convert a PEFT LoRA key to diffusers format."""
    m = re.match(r"base_model\.model\.(.*?)\.lora_(A|B)\.weight$", peft_key)
    if not m:
        return None
    layer_path = m.group(1)
    ab = "down" if m.group(2) == "A" else "up"
    return f"unet.{layer_path}.lora_linear_layer.{ab}.weight"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, default="lora_weights/final")
    p.add_argument("--output", type=str, default="lora_weights/diffusers")
    args = p.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = in_dir / "adapter_model.safetensors"
    if not src.is_file():
        print(f"Not found: {src}")
        return

    state_dict = load_file(str(src))
    new_dict = {}
    skipped = 0

    for k, v in state_dict.items():
        new_key = convert_key(k)
        if new_key is None:
            skipped += 1
            continue
        new_dict[new_key] = v

    dst = out_dir / "pytorch_lora_weights.safetensors"
    save_file(new_dict, str(dst))
    print(f"Converted {len(new_dict)} keys ({skipped} skipped)")
    print(f"Saved to: {dst}")
    print(f"\nUpdate .env:")
    print(f"  CUSTOM_LOCAL_LORA_DIR={out_dir.resolve()}")


if __name__ == "__main__":
    main()
