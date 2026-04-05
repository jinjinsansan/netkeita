"""Image upload service for article authoring.

Stores uploaded images in a public Supabase Storage bucket called
``article-images`` and returns the public URL so the admin editor can
insert a Markdown image reference right away.

Security:
    - Mime type whitelist (jpeg / png / webp / gif) — no svg (XSS via script)
    - Hard size cap (5 MB) — anything bigger is rejected
    - File names are generated server-side (timestamp + random) so the
      caller can never influence the final path
    - Bucket is created on first upload with public-read access so the
      public URL works without signed-URL gymnastics
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from services.supabase_client import get_client

logger = logging.getLogger(__name__)

BUCKET_NAME = "article-images"

# Cap uploaded images at 5 MB to keep the editor snappy and Supabase
# storage cheap. Anything over this gets a clean 413 error.
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Allowed mime types → file extension. SVG deliberately excluded (XSS).
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class ImageUploadError(Exception):
    """Raised when the upload cannot proceed (validation or storage failure)."""


def _ensure_bucket_exists() -> None:
    """Idempotently create the public bucket on first call."""
    try:
        client = get_client()
        # list_buckets returns a list of BucketResponse objects
        existing = client.storage.list_buckets() or []
        names = {b.name if hasattr(b, "name") else b.get("name") for b in existing}
        if BUCKET_NAME in names:
            return
        client.storage.create_bucket(
            BUCKET_NAME,
            options={"public": True},
        )
        logger.info(f"image_upload: created Supabase bucket '{BUCKET_NAME}'")
    except Exception as exc:
        # Creating a bucket that already exists races with other workers —
        # just log and continue; the upload itself will surface real errors.
        logger.warning(f"image_upload: bucket ensure failed (may already exist): {exc}")


def _generate_object_name(extension: str) -> str:
    # Partition by date so the Supabase dashboard stays navigable.
    now = datetime.now(timezone.utc)
    prefix = now.strftime("%Y/%m")
    stamp = now.strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(6)
    return f"{prefix}/{stamp}-{token}.{extension}"


def upload_image(data: bytes, content_type: str) -> str:
    """Validate and upload a single image. Returns the public URL.

    Raises:
        ImageUploadError with a user-safe message on any validation failure
        or Supabase error.
    """
    if not data:
        raise ImageUploadError("ファイルが空です")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageUploadError(
            f"ファイルサイズが大きすぎます (最大 {MAX_IMAGE_BYTES // (1024 * 1024)}MB)"
        )

    normalised = (content_type or "").split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(normalised)
    if not ext:
        raise ImageUploadError(
            "サポートされていない画像形式です (JPEG / PNG / WebP / GIF のみ)"
        )

    _ensure_bucket_exists()
    object_name = _generate_object_name(ext)

    try:
        client = get_client()
        client.storage.from_(BUCKET_NAME).upload(
            object_name,
            data,
            {
                "content-type": normalised,
                # 1 year CDN cache — the object name is unique so we never
                # need to bust the cache.
                "cache-control": "public, max-age=31536000, immutable",
                "upsert": "false",
            },
        )
    except Exception as exc:
        logger.exception("image_upload: supabase upload failed")
        raise ImageUploadError(f"アップロードに失敗しました: {exc}") from exc

    try:
        public_url = client.storage.from_(BUCKET_NAME).get_public_url(object_name)
    except Exception as exc:
        logger.exception("image_upload: public url lookup failed")
        raise ImageUploadError(f"公開URLの取得に失敗しました: {exc}") from exc

    # Supabase returns URLs with trailing '?' in some SDK versions; strip it.
    return public_url.rstrip("?")


__all__ = ["upload_image", "ImageUploadError", "BUCKET_NAME", "MAX_IMAGE_BYTES"]
