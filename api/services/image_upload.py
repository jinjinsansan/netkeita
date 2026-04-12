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

BUCKET_NAME         = "article-images"
AVATAR_BUCKET_NAME  = "user-avatars"

# Cap uploaded images at 5 MB.
MAX_IMAGE_BYTES  = 5 * 1024 * 1024
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # same cap for avatars

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


def _ensure_bucket_exists(bucket: str = BUCKET_NAME) -> None:
    """Idempotently create a public bucket on first call."""
    try:
        client = get_client()
        existing = client.storage.list_buckets() or []
        names = {b.name if hasattr(b, "name") else b.get("name") for b in existing}
        if bucket in names:
            return
        client.storage.create_bucket(bucket, options={"public": True})
        logger.info(f"image_upload: created Supabase bucket '{bucket}'")
    except Exception as exc:
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

    _ensure_bucket_exists(BUCKET_NAME)
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


def upload_avatar(data: bytes, content_type: str) -> str:
    """Upload a user avatar image to the user-avatars bucket.

    Accepts JPEG / PNG / WebP / GIF up to MAX_AVATAR_BYTES.
    Returns the public URL.
    """
    if not data:
        raise ImageUploadError("ファイルが空です")
    if len(data) > MAX_AVATAR_BYTES:
        raise ImageUploadError(
            f"ファイルサイズが大きすぎます (最大 {MAX_AVATAR_BYTES // (1024 * 1024)}MB)"
        )

    normalised = (content_type or "").split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(normalised)
    if not ext:
        raise ImageUploadError(
            "サポートされていない画像形式です (JPEG / PNG / WebP / GIF のみ)"
        )

    _ensure_bucket_exists(AVATAR_BUCKET_NAME)
    object_name = _generate_object_name(ext)

    try:
        client = get_client()
        client.storage.from_(AVATAR_BUCKET_NAME).upload(
            object_name,
            data,
            {
                "content-type": normalised,
                "cache-control": "public, max-age=31536000, immutable",
                "upsert": "false",
            },
        )
    except Exception as exc:
        logger.exception("image_upload: avatar upload failed")
        raise ImageUploadError(f"アップロードに失敗しました: {exc}") from exc

    try:
        public_url = client.storage.from_(AVATAR_BUCKET_NAME).get_public_url(object_name)
    except Exception as exc:
        logger.exception("image_upload: avatar public url lookup failed")
        raise ImageUploadError(f"公開URLの取得に失敗しました: {exc}") from exc

    return public_url.rstrip("?")


__all__ = [
    "upload_image", "upload_avatar",
    "ImageUploadError", "BUCKET_NAME", "AVATAR_BUCKET_NAME",
    "MAX_IMAGE_BYTES", "MAX_AVATAR_BYTES",
]
