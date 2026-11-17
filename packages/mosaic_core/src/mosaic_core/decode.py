"""Decode any supported image to an upright sRGB RGB Pillow image."""

from io import BytesIO
from pathlib import Path

import pillow_heif
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from mosaic_core.errors import DecodeError

pillow_heif.register_heif_opener()

MAX_FILE_BYTES = 200 * 1024 * 1024
MAX_PIXELS = 100_000_000

_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


def read_bytes(source: Path | bytes, *, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    if isinstance(source, bytes):
        data = source
    else:
        try:
            if source.stat().st_size > max_bytes:
                raise DecodeError(f"file larger than {max_bytes} bytes")
            data = source.read_bytes()
        except OSError as exc:
            raise DecodeError(f"cannot read file: {exc}") from exc
    if len(data) > max_bytes:
        raise DecodeError(f"file larger than {max_bytes} bytes")
    return data


def open_image(
    source: Path | bytes,
    *,
    min_side: int | None = None,
    max_bytes: int = MAX_FILE_BYTES,
    max_pixels: int = MAX_PIXELS,
) -> Image.Image:
    """Return the image upright (EXIF orientation applied), converted to sRGB, mode RGB.

    ``min_side`` lets JPEG decoding use draft mode: the result keeps at least that many
    pixels on each side (or the full size if smaller), which is much faster for thumbnails.
    """
    data = read_bytes(source, max_bytes=max_bytes)
    try:
        img: Image.Image = Image.open(BytesIO(data))
        if img.width * img.height > max_pixels:
            raise DecodeError(f"image has more than {max_pixels} pixels")
        if min_side is not None and img.format == "JPEG":
            img.draft("RGB", (min_side, min_side))
        img = ImageOps.exif_transpose(img)
        return _to_srgb(img)
    except DecodeError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise DecodeError(f"unreadable image: {exc}") from exc


def _to_srgb(img: Image.Image) -> Image.Image:
    icc = img.info.get("icc_profile")
    if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
        img = _flatten_alpha(img)
    elif img.mode not in ("RGB", "CMYK", "L"):
        img = img.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(BytesIO(icc))
            converted = ImageCms.profileToProfile(img, src, _SRGB, outputMode="RGB")
            if converted is not None:
                return converted
        except (ImageCms.PyCMSError, OSError, ValueError):
            pass
    return img.convert("RGB")


def _flatten_alpha(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(background, rgba).convert("RGB")
    if "icc_profile" in img.info:
        flat.info["icc_profile"] = img.info["icc_profile"]
    return flat
