"""
Build a LoRA training dataset from generated viseme sets.

Scans test_characters/ (and optionally the default shapes dir) and assembles
a HuggingFace-compatible image/text dataset with metadata.jsonl.

Usage:
    python scripts/build_lora_dataset.py [--include-default]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VISEME_CAPTIONS: dict[str, str] = {
    "A": "neutral face, closed mouth, eyes open",
    "B": "viseme B, lips pressed tightly together for M/B/P sound",
    "C": "viseme C, upper front teeth touching lower lip for F/V sound",
    "D": "viseme D, tongue tip visible between slightly open lips for L sound",
    "E": "viseme E, stretched smile shape for E sound, corners pulled sideways",
    "F": "viseme F, jaw dropped wide open for AI sound, large vertical opening",
    "G": "viseme G, rounded medium-open mouth for O sound, oval opening",
    "H": "viseme H, small tight rounded puckered lips for U/W sound",
    "X": "viseme X, neutral rest, relaxed closed mouth",
    "blink": "both eyes fully closed in natural blink, mouth gently closed",
}

IDENTITY_TEMPLATE = (
    "single person portrait, centered, front-facing, head-and-shoulders, "
    "white background, same camera and lighting. {character}. {viseme_caption}"
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_CHARS_DIR = BACKEND_DIR / "test_characters"
DEFAULT_SHAPES_DIR = BACKEND_DIR.parent / "frontend-react" / "public" / "static" / "shapes"
OUTPUT_DIR = BACKEND_DIR / "viseme_lora_dataset"


def collect_character_dirs(include_default: bool) -> list[tuple[str, Path]]:
    dirs: list[tuple[str, Path]] = []
    if TEST_CHARS_DIR.is_dir():
        for d in sorted(TEST_CHARS_DIR.iterdir()):
            if d.is_dir() and (d / "A.png").is_file():
                dirs.append((d.name, d))
    if include_default and DEFAULT_SHAPES_DIR.is_dir() and (DEFAULT_SHAPES_DIR / "A.png").is_file():
        dirs.append(("default_doctor", DEFAULT_SHAPES_DIR))
    return dirs


def build_dataset(include_default: bool):
    chars = collect_character_dirs(include_default)
    if not chars:
        print("No character directories found. Generate some first with generate_characters.py")
        sys.exit(1)

    images_dir = OUTPUT_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    metadata: list[dict] = []
    count = 0

    for identity_id, src_dir in chars:
        print(f"Processing {identity_id} from {src_dir}")
        for viseme_key, caption in VISEME_CAPTIONS.items():
            src_file = src_dir / f"{viseme_key}.png"
            if not src_file.is_file():
                print(f"  SKIP {viseme_key}.png (not found)")
                continue

            dest_name = f"{identity_id}_{viseme_key}.png"
            dest_path = images_dir / dest_name
            shutil.copy2(src_file, dest_path)

            character_hint = identity_id.replace("_", " ")
            full_caption = IDENTITY_TEMPLATE.format(
                character=character_hint,
                viseme_caption=caption,
            )

            metadata.append({
                "file_name": f"images/{dest_name}",
                "text": full_caption,
                "viseme": viseme_key,
                "identity_id": identity_id,
            })
            count += 1

    meta_path = OUTPUT_DIR / "metadata.jsonl"
    with open(meta_path, "w") as f:
        for entry in metadata:
            f.write(json.dumps(entry) + "\n")

    print(f"\nDataset built: {count} images from {len(chars)} characters")
    print(f"  Images: {images_dir}")
    print(f"  Metadata: {meta_path}")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-default", action="store_true",
                        help="Include the default shapes dir (cartoon doctor)")
    args = parser.parse_args()
    build_dataset(args.include_default)
