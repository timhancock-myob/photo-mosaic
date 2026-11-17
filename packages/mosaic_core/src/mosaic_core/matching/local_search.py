"""Iterated conditional modes over the grid (ADR 0003), updated as a checkerboard.

Cells of one colour never touch each other, so all of them can take their best response to
the (fixed) other colour at once. Each accepted change strictly lowers the total cost.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mosaic_core.features import BOTTOM, LEFT, RIGHT, TOP

# (row offset, col offset, this cell's side, neighbour's facing side)
_NEIGHBOURS = ((-1, 0, TOP, BOTTOM), (0, 1, RIGHT, LEFT), (1, 0, BOTTOM, TOP), (0, -1, LEFT, RIGHT))
_EPS = 1e-6


@dataclass(frozen=True)
class SearchResult:
    choice: NDArray[np.intp]
    """(rows, cols) index into each cell's candidate list."""
    iterations: int
    converged: bool


def improve(
    cand: NDArray[np.intp],
    cand_fit: NDArray[np.float32],
    edges: NDArray[np.float32],
    base_edges: NDArray[np.float32],
    *,
    lambda_seam: float,
    lambda_self: float,
    max_iters: int,
    progress: Callable[[int, int], None] | None = None,
) -> SearchResult:
    """``cand``/``cand_fit``: (rows, cols, K) tile ids and fit costs, best first.

    ``base_edges`` (rows, cols, 4, segments, 3) sets the colour step each seam should show.
    """
    rows, cols, _ = cand.shape
    choice = np.zeros((rows, cols), dtype=np.intp)
    rr, cc = np.indices((rows, cols))
    parity = (rr + cc) % 2
    for iteration in range(1, max_iters + 1):
        changed = 0
        for colour in (0, 1):
            mask = parity == colour
            changed += _sweep(
                cand,
                cand_fit,
                edges,
                base_edges,
                choice,
                rr[mask],
                cc[mask],
                lambda_seam,
                lambda_self,
            )
        if progress is not None:
            progress(iteration, max_iters)
        if changed == 0:
            return SearchResult(choice, iteration, True)
    return SearchResult(choice, max_iters, False)


def _sweep(
    cand: NDArray[np.intp],
    cand_fit: NDArray[np.float32],
    edges: NDArray[np.float32],
    base_edges: NDArray[np.float32],
    choice: NDArray[np.intp],
    r: NDArray[np.intp],
    c: NDArray[np.intp],
    lambda_seam: float,
    lambda_self: float,
) -> int:
    if r.size == 0:
        return 0
    rows, cols, _ = cand.shape
    options = cand[r, c]
    cost = cand_fit[r, c].astype(np.float64)
    tiles = np.take_along_axis(cand, choice[..., None], axis=2)[..., 0]
    for dr, dc, side, facing in _NEIGHBOURS:
        nr, nc = r + dr, c + dc
        ok = (nr >= 0) & (nr < rows) & (nc >= 0) & (nc < cols)
        if not ok.any():
            continue
        neighbour = tiles[nr[ok], nc[ok]]
        step = edges[options[ok], side] - edges[neighbour, facing][:, None]
        target = base_edges[r[ok], c[ok], side] - base_edges[nr[ok], nc[ok], facing]
        seam = np.linalg.norm(step - target[:, None], axis=-1).mean(axis=-1)
        cost[ok] += lambda_seam * seam + lambda_self * (options[ok] == neighbour[:, None])
    best = np.argmin(cost, axis=1)
    idx = np.arange(r.size)
    now = choice[r, c]
    better = cost[idx, best] < cost[idx, now] - _EPS
    choice[r[better], c[better]] = best[better]
    return int(better.sum())
