"""Storage service — abstracts file storage between local filesystem and Supabase Storage.

When SUPABASE_URL + SUPABASE_SERVICE_KEY are set, uses Supabase Storage.
Otherwise falls back to local filesystem (for Docker / local dev).
"""
import logging
import os
import re
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

# ── Detect which backend to use ──
_USE_SUPABASE = bool(settings.supabase_url and settings.supabase_service_key)

# Local fallback — only create directory if NOT using Supabase
_LOCAL_DIR = Path(os.environ.get(
    "AVATAR_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "uploads" / "avatars"),
))
if not _USE_SUPABASE:
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)

# Lazy-init Supabase client
_supabase_client = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase_client


def get_bucket():
    return settings.supabase_bucket


# ── Public API ──

def list_images() -> list[str]:
    """Return sorted list of image filenames in the library."""
    if _USE_SUPABASE:
        sb = _get_supabase()
        res = sb.storage.from_(get_bucket()).list()
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        return sorted(
            f["name"] for f in res
            if any(f["name"].lower().endswith(e) for e in exts)
        )
    else:
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        return sorted(
            f.name for f in _LOCAL_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in exts
        )


def upload_image(filename: str, content: bytes, content_type: str) -> str:
    """Upload an image. Returns the final filename."""
    # Sanitize filename to prevent path traversal
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w.\-]', '_', filename)
    if not filename:
        filename = "upload.png"
    if _USE_SUPABASE:
        sb = _get_supabase()
        # Supabase upserts by default; add counter to avoid collisions
        existing = {f["name"] for f in sb.storage.from_(get_bucket()).list()}
        final_name = filename
        counter = 1
        stem, ext = os.path.splitext(filename)
        while final_name in existing:
            final_name = f"{stem}-{counter}{ext}"
            counter += 1
        sb.storage.from_(get_bucket()).upload(
            final_name,
            content,
            file_options={"content-type": content_type},
        )
        logger.info(f"Uploaded to Supabase Storage: {final_name}")
        return final_name
    else:
        safe_name = filename.replace(" ", "-")
        dest = _LOCAL_DIR / safe_name
        counter = 1
        stem = dest.stem
        suffix = dest.suffix
        while dest.exists():
            dest = _LOCAL_DIR / f"{stem}-{counter}{suffix}"
            counter += 1
        with open(dest, "wb") as f:
            f.write(content)
        logger.info(f"Saved locally: {dest.name}")
        return dest.name


def delete_image(filename: str) -> None:
    """Delete an image by filename."""
    if _USE_SUPABASE:
        sb = _get_supabase()
        sb.storage.from_(get_bucket()).remove([filename])
        logger.info(f"Deleted from Supabase Storage: {filename}")
    else:
        path = _LOCAL_DIR / filename
        if path.exists() and path.is_file():
            path.unlink()
            logger.info(f"Deleted locally: {filename}")
        else:
            raise FileNotFoundError(f"Image not found: {filename}")


def get_public_url(filename: str) -> str:
    """Get a working URL for an image.

    For Supabase Storage, generates a signed URL (works for both public
    and private buckets). Falls back to a local path for non-Supabase setups.
    """
    if _USE_SUPABASE:
        sb = _get_supabase()
        try:
            res = sb.storage.from_(get_bucket()).create_signed_url(
                filename, 3600  # 1 hour expiry
            )
            # supabase-py returns {"signedURL": "..."} depending on version
            if isinstance(res, dict):
                return res.get("signedURL") or res.get("signedUrl") or res.get("signed_url", "")
            return str(res)
        except Exception as e:
            logger.warning(f"Failed to create signed URL for {filename}: {e}")
            return sb.storage.from_(get_bucket()).get_public_url(filename)
    else:
        return f"/uploads/avatars/{filename}"


def get_signed_urls(filenames: list[str], expires_in: int = 3600) -> dict[str, str]:
    """Get signed URLs for multiple images in a single request (batch).

    Returns a dict mapping filename -> signed URL. For non-Supabase setups,
    returns local paths.
    """
    if not filenames:
        return {}

    if _USE_SUPABASE:
        sb = _get_supabase()
        try:
            res = sb.storage.from_(get_bucket()).create_signed_urls(
                filenames, expires_in
            )
            # Response is a list of dicts: [{"path": "...", "signedURL": "..."}, ...]
            url_map = {}
            if isinstance(res, list):
                for item in res:
                    path = item.get("path", "")
                    url = (
                        item.get("signedURL")
                        or item.get("signedUrl")
                        or item.get("signed_url", "")
                    )
                    # path might be "avatars/patient-01.png" — extract just filename
                    fname = path.rsplit("/", 1)[-1] if "/" in path else path
                    if fname and url:
                        url_map[fname] = url
            # Fill in any missing filenames via individual fallback
            for f in filenames:
                if f not in url_map:
                    url_map[f] = get_public_url(f)
            return url_map
        except Exception as e:
            logger.warning(f"Failed batch signed URLs, falling back to individual: {e}")
            return {f: get_public_url(f) for f in filenames}
    else:
        return {f: f"/uploads/avatars/{f}" for f in filenames}


def is_using_supabase() -> bool:
    return _USE_SUPABASE


def get_local_dir() -> Path:
    """Only valid when NOT using Supabase — returns the local upload directory."""
    return _LOCAL_DIR
