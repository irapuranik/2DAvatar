"""
Generate viseme sets for multiple characters to test generalization.
Run from the backend directory:
    python scripts/generate_characters.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.custom_viseme_generator import generate_local_viseme_set

CHARACTERS = [
    ("cartoon_nurse", "cartoon nurse, female, blue scrubs, friendly face, stethoscope"),
    ("anime_student", "anime style student, male, school uniform, short black hair"),
    ("realistic_elderly", "realistic elderly woman, gray hair, glasses, warm smile, cardigan sweater"),
]

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "test_characters"


def progress_cb(viseme: str, step: int, total: int, name: str):
    print(f"  [{name}] {viseme} ({step}/{total})")


def diag_cb(diag: dict, name: str):
    visemes = diag.get("visemes", {})
    for k, v in visemes.items():
        last = v["attempts"][-1] if v["attempts"] else {}
        sc = last.get("scores", {})
        print(
            f"    {k}: id={sc.get('identity','?'):.3f}  mouth={sc.get('mouth_delta','?'):.3f}  "
            f"pass={last.get('pass','?')}  retries={v.get('retry_count', 0)}"
        )


def noop_copy(p: Path):
    pass


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder_name, prompt in CHARACTERS:
        out = OUTPUT_ROOT / folder_name
        out.mkdir(parents=True, exist_ok=True)
        print(f"\n=== Generating: {folder_name} ===")
        print(f"    Prompt: {prompt}")
        print(f"    Output: {out}\n")
        written = generate_local_viseme_set(
            shapes_dir=out,
            merged_prompt=prompt,
            strength_override=None,
            generate_base_from_prompt=True,
            use_copy_default_a_if_missing=False,
            copy_default_a_if_missing_fn=noop_copy,
            on_progress=lambda v, s, t, n=folder_name: progress_cb(v, s, t, n),
            on_diagnostic=lambda d, n=folder_name: diag_cb(d, n),
        )
        print(f"\n  Done: {len(written)} files written for {folder_name}")

    print("\n\n=== All characters complete ===")
    print(f"Results in: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
