from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import FRONTEND_PUBLIC_DIR
from services.viseme_layer_service import VISEME_KEYS, generate_layer_assets_for_shapes_dir


def _is_shapes_dir(path: Path) -> bool:
    return all((path / f"{k}.png").is_file() for k in VISEME_KEYS)


def main() -> None:
    public_dir = FRONTEND_PUBLIC_DIR
    candidates: list[Path] = []

    static_shapes = public_dir / "static" / "shapes"
    if _is_shapes_dir(static_shapes):
        candidates.append(static_shapes)

    generated_cases = public_dir / "generated" / "cases"
    if generated_cases.is_dir():
        for case_dir in generated_cases.iterdir():
            if not case_dir.is_dir():
                continue
            shapes_dir = case_dir / "shapes"
            if _is_shapes_dir(shapes_dir):
                candidates.append(shapes_dir)

    if not candidates:
        print("No viseme shape directories found.")
        return

    for shapes_dir in candidates:
        written = generate_layer_assets_for_shapes_dir(shapes_dir)
        print(f"{shapes_dir}: wrote {len(written)} layer files")


if __name__ == "__main__":
    main()
