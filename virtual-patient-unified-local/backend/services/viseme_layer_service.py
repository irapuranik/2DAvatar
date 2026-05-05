from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter


VISEME_KEYS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "X", "blink")


def _make_masks(size: tuple[int, int]) -> tuple[Image.Image, Image.Image, Image.Image]:
    """
    Create coarse semantic masks (head / neck / mouth) for the current avatar framing.
    The masks are deterministic and intentionally conservative to avoid edge artifacts.
    """
    w, h = size

    head_mask = Image.new("L", (w, h), 0)
    neck_mask = Image.new("L", (w, h), 0)
    mouth_mask = Image.new("L", (w, h), 0)

    head = ImageDraw.Draw(head_mask)
    neck = ImageDraw.Draw(neck_mask)
    mouth = ImageDraw.Draw(mouth_mask)

    # Head + hair silhouette (upper region, rounded).
    head.ellipse(
        (
            int(w * 0.14),
            int(h * 0.01),
            int(w * 0.86),
            int(h * 0.72),
        ),
        fill=255,
    )
    # Extend through braided sides so side hair stays in head layer.
    head.polygon(
        [
            (int(w * 0.19), int(h * 0.56)),
            (int(w * 0.15), int(h * 0.84)),
            (int(w * 0.34), int(h * 0.84)),
            (int(w * 0.35), int(h * 0.60)),
        ],
        fill=255,
    )
    head.polygon(
        [
            (int(w * 0.81), int(h * 0.56)),
            (int(w * 0.65), int(h * 0.60)),
            (int(w * 0.66), int(h * 0.84)),
            (int(w * 0.85), int(h * 0.84)),
        ],
        fill=255,
    )

    # Neck-only region (avoid broad trapezoid to prevent visible hard mask edges).
    neck.rounded_rectangle(
        (
            int(w * 0.39),
            int(h * 0.56),
            int(w * 0.61),
            int(h * 0.93),
        ),
        radius=max(8, w // 30),
        fill=255,
    )

    # Mouth region (viseme articulation area) - useful for future overlays.
    mouth.ellipse(
        (
            int(w * 0.36),
            int(h * 0.53),
            int(w * 0.64),
            int(h * 0.74),
        ),
        fill=255,
    )

    # Force a clean neck/head split by cutting neck area out of head.
    head_mask = ImageChops.subtract(head_mask, neck_mask)

    return head_mask, neck_mask, mouth_mask


def _alpha_silhouette_mask(img: Image.Image) -> Image.Image:
    """Binary foreground mask from alpha channel; falls back to opaque full-frame."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    # Keep low threshold so anti-aliased edges remain part of the silhouette.
    silhouette = alpha.point(lambda p: 255 if p > 8 else 0, mode="L")
    if silhouette.getbbox() is None:
        return Image.new("L", rgba.size, 255)
    return silhouette


def _intersect(a: Image.Image, b: Image.Image) -> Image.Image:
    """Mask intersection for L-mode images."""
    return ImageChops.multiply(a, b)


def _make_masks_from_reference(reference_png: Path) -> tuple[Image.Image, Image.Image, Image.Image]:
    """
    Build canonical head/neck/mouth masks from A.png once, then reuse for all visemes.
    This keeps seam alignment stable frame-to-frame.
    """
    ref = Image.open(reference_png).convert("RGBA")
    w, h = ref.size
    silhouette = _alpha_silhouette_mask(ref)
    bbox = silhouette.getbbox()
    if bbox is None:
        return _make_masks((w, h))
    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)

    split_y = y1 + int(bh * 0.62)
    neck_bottom = min(h - 1, y2 + int(h * 0.04))
    neck_half_w = max(int(bw * 0.16), max(10, w // 18))
    cx = x1 + (bw // 2)

    neck_core = Image.new("L", (w, h), 0)
    neck = ImageDraw.Draw(neck_core)
    neck.rounded_rectangle(
        (
            max(0, cx - neck_half_w),
            max(0, split_y - int(bh * 0.02)),
            min(w - 1, cx + neck_half_w),
            max(0, neck_bottom),
        ),
        radius=max(6, w // 30),
        fill=255,
    )
    neck_core = _intersect(neck_core, silhouette)

    # Add a shared soft seam band to both head and neck to hide visible cut lines.
    seam_band = Image.new("L", (w, h), 0)
    seam = ImageDraw.Draw(seam_band)
    seam.rectangle(
        (
            max(0, x1),
            max(0, split_y - max(2, h // 200)),
            min(w - 1, x2),
            min(h - 1, split_y + max(4, h // 140)),
        ),
        fill=255,
    )
    seam_band = _intersect(seam_band, silhouette)

    head_mask = ImageChops.subtract(silhouette, neck_core)
    head_mask = ImageChops.lighter(head_mask, seam_band)
    neck_mask = ImageChops.lighter(neck_core, seam_band)

    blur_r = max(1, w // 220)
    head_mask = head_mask.filter(ImageFilter.GaussianBlur(radius=blur_r))
    neck_mask = neck_mask.filter(ImageFilter.GaussianBlur(radius=blur_r))

    # Mouth region based on face bbox proportions from reference framing.
    mouth_mask = Image.new("L", (w, h), 0)
    mouth = ImageDraw.Draw(mouth_mask)
    mouth.ellipse(
        (
            int(x1 + bw * 0.31),
            int(y1 + bh * 0.54),
            int(x1 + bw * 0.69),
            int(y1 + bh * 0.79),
        ),
        fill=255,
    )
    mouth_mask = _intersect(mouth_mask, silhouette)

    return head_mask, neck_mask, mouth_mask


def _apply_mask(src: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = src.convert("RGBA")
    out = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    out.paste(rgba, (0, 0), mask=mask)
    return out


def _write_layer_set(
    source_png: Path,
    layers_dir: Path,
    canonical_masks: tuple[Image.Image, Image.Image, Image.Image] | None = None,
) -> None:
    img = Image.open(source_png).convert("RGBA")
    head_mask, neck_mask, mouth_mask = canonical_masks or _make_masks(img.size)

    (layers_dir / "head.png").parent.mkdir(parents=True, exist_ok=True)
    _apply_mask(img, head_mask).save(layers_dir / "head.png", format="PNG")
    _apply_mask(img, neck_mask).save(layers_dir / "neck.png", format="PNG")
    _apply_mask(img, mouth_mask).save(layers_dir / "mouth.png", format="PNG")


def generate_layer_assets_for_shapes_dir(shapes_dir: Path, viseme_keys: Iterable[str] = VISEME_KEYS) -> list[str]:
    """
    Produce per-viseme semantic layer PNGs:
      {shapes_dir}/layers/{viseme}/{head|neck|mouth}.png
    """
    written: list[str] = []
    canonical_masks: tuple[Image.Image, Image.Image, Image.Image] | None = None
    ref_a = shapes_dir / "A.png"
    if ref_a.is_file():
        canonical_masks = _make_masks_from_reference(ref_a)

    for key in viseme_keys:
        src = shapes_dir / f"{key}.png"
        if not src.is_file():
            continue
        dst = shapes_dir / "layers" / key
        _write_layer_set(src, dst, canonical_masks=canonical_masks)
        written.extend(
            [
                f"layers/{key}/head.png",
                f"layers/{key}/neck.png",
                f"layers/{key}/mouth.png",
            ]
        )
    return written
