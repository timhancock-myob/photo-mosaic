"""Tile indexing (architecture §4.2): decode, thumbnail, hash, skip with reasons."""

import hashlib
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from mosaic_core.color import to_lab
from mosaic_core.decode import open_image, read_bytes
from mosaic_core.errors import DecodeError

THUMB_SIDE = 128
MIN_SIDE = 64
NEAR_DUPLICATE_BITS = 4
NEAR_DUPLICATE_DE = 8.0
_EXIF_ORIENTATION = 0x0112


class SkipReason(StrEnum):
    UNREADABLE = "unreadable"
    TOO_SMALL = "too_small"
    DUPLICATE = "duplicate"
    NEAR_DUPLICATE = "near_duplicate"


@dataclass(frozen=True)
class IndexedTile:
    key: str
    """Caller's identifier (path, provider item id)."""
    content_hash: str
    width: int
    height: int
    thumb: Image.Image
    """Working thumbnail: ``THUMB_SIDE`` px on the short side, uncropped, sRGB."""
    dhash: int
    mean_lab: tuple[float, float, float]


@dataclass(frozen=True)
class SkippedTile:
    key: str
    reason: SkipReason
    detail: str = ""
    duplicate_of: str | None = None


@dataclass
class TileIndex:
    tiles: list[IndexedTile] = field(default_factory=list)
    skipped: list[SkippedTile] = field(default_factory=list)


class _Skip(Exception):
    def __init__(self, reason: SkipReason, detail: str = "") -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def dhash(img: Image.Image) -> int:
    """64-bit difference hash; near-identical photos differ in only a few bits."""
    px = np.asarray(img.convert("L").resize((9, 8), Image.Resampling.BOX), dtype=np.int16)
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def index_tile(
    key: str, source: Path | bytes, *, thumb_side: int = THUMB_SIDE, min_side: int = MIN_SIDE
) -> IndexedTile:
    try:
        data = read_bytes(source)
        with Image.open(BytesIO(data)) as probe:
            width, height = probe.size
            if probe.getexif().get(_EXIF_ORIENTATION, 1) in (5, 6, 7, 8):
                width, height = height, width
        img = open_image(data, min_side=thumb_side)
    except (DecodeError, OSError, ValueError) as exc:
        raise _Skip(SkipReason.UNREADABLE, str(exc)) from exc
    if min(width, height) < min_side:
        raise _Skip(SkipReason.TOO_SMALL, f"{width}x{height}")
    scale = thumb_side / min(img.size)
    if scale < 1:
        img = img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.Resampling.LANCZOS,
        )
    return IndexedTile(
        key=key,
        content_hash=hashlib.sha256(data).hexdigest(),
        width=width,
        height=height,
        thumb=img,
        dhash=dhash(img),
        mean_lab=_mean_lab(img),
    )


def _mean_lab(img: Image.Image) -> tuple[float, float, float]:
    lightness, a, b = (float(v) for v in to_lab(img).reshape(-1, 3).mean(axis=0))
    return (lightness, a, b)


def index_tiles(
    sources: Iterable[tuple[str, Path | bytes]],
    *,
    collapse_near_duplicates: bool = True,
    near_duplicate_bits: int = NEAR_DUPLICATE_BITS,
    workers: int = 4,
) -> TileIndex:
    """Index ``(key, path-or-bytes)`` pairs in order; the first copy of a duplicate wins.

    Near-duplicates have a similar structure (dHash within ``near_duplicate_bits``) *and* a
    similar mean colour, so differently coloured flat photos are not collapsed.
    """
    items = list(sources)
    result = TileIndex()

    def work(item: tuple[str, Path | bytes]) -> IndexedTile | SkippedTile:
        key, src = item
        try:
            return index_tile(key, src)
        except _Skip as skip:
            return SkippedTile(key=key, reason=skip.reason, detail=skip.detail)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        outcomes = list(pool.map(work, items))

    by_hash: dict[str, str] = {}
    kept_hashes: list[int] = []
    kept_labs: list[tuple[float, float, float]] = []
    for outcome in outcomes:
        if isinstance(outcome, SkippedTile):
            result.skipped.append(outcome)
            continue
        if outcome.content_hash in by_hash:
            result.skipped.append(
                SkippedTile(
                    outcome.key, SkipReason.DUPLICATE, duplicate_of=by_hash[outcome.content_hash]
                )
            )
            continue
        if collapse_near_duplicates and kept_hashes:
            dist = np.bitwise_count(
                np.array(kept_hashes, dtype=np.uint64) ^ np.uint64(outcome.dhash)
            ).astype(np.float64)
            colour = np.linalg.norm(np.array(kept_labs) - np.array(outcome.mean_lab), axis=1)
            dist[colour > NEAR_DUPLICATE_DE] = np.inf
            nearest = int(np.argmin(dist))
            if dist[nearest] <= near_duplicate_bits:
                result.skipped.append(
                    SkippedTile(
                        outcome.key,
                        SkipReason.NEAR_DUPLICATE,
                        detail=f"{int(dist[nearest])} bits",
                        duplicate_of=result.tiles[nearest].key,
                    )
                )
                continue
        by_hash[outcome.content_hash] = outcome.key
        kept_hashes.append(outcome.dhash)
        kept_labs.append(outcome.mean_lab)
        result.tiles.append(outcome)
    return result
