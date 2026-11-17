"""Colour signatures (architecture §4.3). All values are CIELAB."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from mosaic_core.color import to_lab
from mosaic_core.grid import Grid

TOP, RIGHT, BOTTOM, LEFT = range(4)


@dataclass(frozen=True)
class SignatureSpec:
    grid: int = 6
    """Fit signature resolution: each cell/tile becomes a ``grid x grid`` Lab grid."""
    edge_segments: int = 4
    """Segments per side in an edge strip (seam term)."""
    edge_depth: float = 0.08
    """Edge strip thickness as a fraction of the tile side."""

    def __post_init__(self) -> None:
        if self.grid < 1 or self.edge_segments < 1 or not 0 < self.edge_depth <= 0.5:
            raise ValueError("invalid signature spec")

    @property
    def work_size(self) -> int:
        step = math.lcm(self.grid, self.edge_segments)
        return step * math.ceil(32 / step)


@dataclass(frozen=True)
class TileFeatures:
    fit: NDArray[np.float32]
    """(tiles, grid*grid, 3) Lab grid of each tile cropped to the cell aspect."""
    edges: NDArray[np.float32]
    """(tiles, 4, edge_segments, 3) mean Lab per segment; sides TOP, RIGHT, BOTTOM, LEFT.
    Top/bottom segments run left to right; left/right segments run top to bottom."""

    def __len__(self) -> int:
        return int(self.fit.shape[0])


@dataclass(frozen=True)
class BaseSignatures:
    fit: NDArray[np.float32]
    """(rows, cols, grid*grid, 3) Lab grid per cell."""
    edges: NDArray[np.float32]
    """(rows, cols, 4, edge_segments, 3) Lab edge strips per cell, same layout as tiles."""

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.fit.shape[0]), int(self.fit.shape[1])


def center_crop_box(width: int, height: int, aspect: float) -> tuple[float, float, float, float]:
    """Largest centred box with ``width / height == aspect``."""
    if width / height > aspect:
        w = height * aspect
        x = (width - w) / 2
        return (x, 0.0, x + w, float(height))
    h = width / aspect
    y = (height - h) / 2
    return (0.0, y, float(width), y + h)


def tile_features(
    thumbs: Sequence[Image.Image], aspect: float, spec: SignatureSpec | None = None
) -> TileFeatures:
    spec = spec or SignatureSpec()
    n = len(thumbs)
    size = spec.work_size
    fit = np.empty((n, spec.grid * spec.grid, 3), dtype=np.float32)
    edges = np.empty((n, 4, spec.edge_segments, 3), dtype=np.float32)
    for i, thumb in enumerate(thumbs):
        box = center_crop_box(thumb.width, thumb.height, aspect)
        lab = to_lab(thumb.convert("RGB").resize((size, size), Image.Resampling.BOX, box=box))
        fit[i] = _block_mean(lab, spec.grid).reshape(-1, 3)
        edges[i] = _edge_strips(lab, spec)
    return TileFeatures(fit=fit, edges=edges)


def base_signatures(
    base: Image.Image, grid: Grid, spec: SignatureSpec | None = None
) -> BaseSignatures:
    """Per-cell fit grids and edge strips. The base is resampled, not cropped (ADR 0002)."""
    spec = spec or SignatureSpec()
    g = spec.grid
    rgb = base.convert("RGB")
    small = rgb.resize((grid.cols * g, grid.rows * g), Image.Resampling.BOX)
    lab = to_lab(small).reshape(grid.rows, g, grid.cols, g, 3).transpose(0, 2, 1, 3, 4)
    e = 2 * spec.edge_segments
    edge_img = rgb.resize((grid.cols * e, grid.rows * e), Image.Resampling.BOX)
    edge_lab = to_lab(edge_img).reshape(grid.rows, e, grid.cols, e, 3).transpose(0, 2, 1, 3, 4)
    return BaseSignatures(
        fit=np.ascontiguousarray(lab.reshape(grid.rows, grid.cols, g * g, 3)),
        edges=_edge_strips(edge_lab, spec),
    )


def _block_mean(lab: NDArray[np.float32], blocks: int) -> NDArray[np.float32]:
    s = lab.shape[0] // blocks
    return np.asarray(lab.reshape(blocks, s, blocks, s, 3).mean(axis=(1, 3)), dtype=np.float32)


def _edge_strips(lab: NDArray[np.float32], spec: SignatureSpec) -> NDArray[np.float32]:
    """``lab`` (..., S, S, 3) -> (..., 4, edge_segments, 3)."""
    size = lab.shape[-2]
    depth = max(1, round(size * spec.edge_depth))
    seg = spec.edge_segments
    strips = (
        lab[..., :depth, :, :].mean(axis=-3),
        lab[..., :, -depth:, :].mean(axis=-2),
        lab[..., -depth:, :, :].mean(axis=-3),
        lab[..., :, :depth, :].mean(axis=-2),
    )
    lead = lab.shape[:-3]
    segments = [s.reshape(*lead, seg, size // seg, 3).mean(axis=-2) for s in strips]
    return np.stack(segments, axis=-3).astype(np.float32)
