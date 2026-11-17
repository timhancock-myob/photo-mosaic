"""Synthetic test images."""

from io import BytesIO

import numpy as np
from PIL import Image


def solid(colour: tuple[int, int, int], size: tuple[int, int] = (64, 64)) -> Image.Image:
    return Image.new("RGB", size, colour)


def smooth_noise(seed: int, size: tuple[int, int] = (200, 160)) -> Image.Image:
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 256, (6, 8, 3), dtype=np.uint8)
    return Image.fromarray(small).resize(size, Image.Resampling.BILINEAR)


def encode(img: Image.Image, fmt: str = "PNG", **kwargs: object) -> bytes:
    buf = BytesIO()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()
