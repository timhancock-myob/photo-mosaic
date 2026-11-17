"""Compose the export from original-resolution tiles (architecture §4.10)."""

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from mosaic_core.features import center_crop_box

MAX_OUTPUT_PIXELS = 200_000_000


def cell_size(cell_width: int, cell_aspect: float) -> tuple[int, int]:
    return cell_width, max(1, round(cell_width / cell_aspect))


def render_mosaic(
    tiles: NDArray[np.intp],
    load_tile: Callable[[int], Image.Image],
    *,
    cell_width: int,
    cell_aspect: float,
    max_pixels: int = MAX_OUTPUT_PIXELS,
    progress: Callable[[int, int], None] | None = None,
) -> Image.Image:
    """``load_tile(i)`` returns tile ``i`` upright in sRGB, at least cell-sized if possible.

    Each distinct tile is loaded and centre-cropped once, then pasted into every cell using it.
    """
    rows, cols = tiles.shape
    cw, ch = cell_size(cell_width, cell_aspect)
    if cols * cw * rows * ch > max_pixels:
        raise ValueError(f"output {cols * cw}x{rows * ch} exceeds {max_pixels} pixels")
    out = Image.new("RGB", (cols * cw, rows * ch))
    cells: dict[int, Image.Image] = {}
    for r in range(rows):
        for c in range(cols):
            t = int(tiles[r, c])
            if t not in cells:
                src = load_tile(t).convert("RGB")
                box = center_crop_box(src.width, src.height, cell_aspect)
                cells[t] = src.resize((cw, ch), Image.Resampling.LANCZOS, box=box)
            out.paste(cells[t], (c * cw, r * ch))
        if progress is not None:
            progress(r + 1, rows)
    return out
