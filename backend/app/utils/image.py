"""
Image Security & Sanitization Utilities — Raw Port Defense.

Implements defense-in-depth image intake security:
1. Binary Magic-Byte Inspection (prevents extension spoofing / non-image payloads).
2. Decompression Bomb Guard (caps max allowed pixels at 25 MP to protect VPS RAM).
3. EXIF Orientation Normalization.
4. Total Metadata Erasure: Strips GPS coordinates, device tags, and camera serials.
"""

import io
import logging
from typing import Tuple
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger("tursathi.utils.image")

# Maximum allowed pixels (25 MP) prevents memory-exhaustion decompression attacks on VPS RAM
MAX_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_magic_bytes(header: bytes) -> str:
    """
    Validates binary file signature (magic bytes) before file decoding.
    Rejects disguised non-image files before PIL or OpenCV parses them.
    """
    if len(header) < 4:
        raise ValueError("File too small to contain valid image headers.")

    # JPEG standard signature: 0xFF, 0xD8, 0xFF
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    # PNG standard signature: 0x89, 'P', 'N', 'G', \r, \n, 0x1A, \n
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    # WebP: 'RIFF' .... 'WEBP'
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "WEBP"

    # HEIC / HEIF ISO Base Media container signature
    if len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in {
        b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"
    }:
        return "HEIC"

    raise ValueError("File content does not match allowed image signatures (JPEG, PNG, WebP).")


def load_and_sanitize_image(image_bytes: bytes) -> Tuple[np.ndarray, int, int]:
    """
    Ingests raw image bytes, verifies magic bytes, transposes EXIF orientation,
    checks dimension bounds, and strips all EXIF/GPS/device metadata into a clean
    NumPy RGB pixel buffer [H, W, 3].

    Returns
    -------
    (image_rgb, width, height)
        image_rgb: np.ndarray uint8 of shape (H, W, 3) with zero surviving metadata.
        width: original image width in pixels.
        height: original image height in pixels.
    """
    # 1. Magic byte binary check
    validate_magic_bytes(image_bytes[:16])

    # 2. Decode under strict 25 MP pixel cap
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError:
        raise ValueError("Image exceeds maximum decompression pixel limits (decompression bomb detected).")
    except Exception as exc:
        raise ValueError(f"Corrupt or unreadable image payload: {exc}")

    if pil_image.format not in ALLOWED_FORMATS:
        format_name = pil_image.format
        pil_image.close()
        raise ValueError(f"Disallowed image format '{format_name}'. Allowed: JPEG, PNG, WEBP.")

    # 3. Safe EXIF orientation transpose with fallback
    try:
        pil_image = ImageOps.exif_transpose(pil_image)
    except Exception:
        pass  # Malformed EXIF tags ignored safely

    orig_w, orig_h = pil_image.size
    if orig_w < 1 or orig_h < 1 or orig_w > 8192 or orig_h > 8192:
        pil_image.close()
        raise ValueError(f"Image dimensions ({orig_w}x{orig_h}) out of safe bounds (1-8192 px).")

    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    # 4. Total metadata erasure: convert to raw NumPy pixel array [H, W, 3]
    # No EXIF, GPS, camera serials, or embedded strings survive this step
    image_rgb = np.array(pil_image, dtype=np.uint8)
    pil_image.close()

    return image_rgb, orig_w, orig_h
