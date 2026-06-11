import io

from PIL import Image

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DIMENSION = 4096
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_MIME_MAP = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_SAVE_KWARGS: dict[str, dict] = {
    "JPEG": {"quality": 85, "optimize": True},
    "PNG": {"optimize": True},
    "WEBP": {"quality": 85},
}


def sanitize_image(data: bytes) -> tuple[bytes, str]:
    """Validate, strip EXIF metadata, and re-encode an image.

    Raises ValueError with a human-readable message on any validation failure.
    Returns (sanitized_bytes, content_type).
    """
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit")

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise ValueError("File is not a valid image")

    # verify() exhausts the stream — re-open before using the image
    img = Image.open(io.BytesIO(data))

    fmt = img.format
    if fmt not in _ALLOWED_FORMATS:
        allowed = ", ".join(sorted(_ALLOWED_FORMATS))
        raise ValueError(f"Image format {fmt!r} is not allowed; accepted formats: {allowed}")

    if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # Convert to RGB — strips EXIF, alpha channel, and palette data
    img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format=fmt, **_SAVE_KWARGS[fmt])
    return buf.getvalue(), _MIME_MAP[fmt]
