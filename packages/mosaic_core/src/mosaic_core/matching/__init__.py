"""Assign a tile to every cell: cell fit + neighbour seams + self-adjacency penalty (ADR 0003)."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mosaic_core.features import BOTTOM, LEFT, RIGHT, TOP, BaseSignatures, TileFeatures
from mosaic_core.matching.candidates import fit_costs, top_k
from mosaic_core.matching.local_search import improve


@dataclass(frozen=True)
class MatchOptions:
    """Free reuse (ADR 0004). λ defaults are provisional until tuned on real photos."""

    lambda_seam: float = 0.5
    lambda_self: float = 8.0
    top_k: int = 32
    max_iters: int = 30

    def __post_init__(self) -> None:
        if self.lambda_seam < 0 or self.lambda_self < 0 or self.top_k < 1 or self.max_iters < 0:
            raise ValueError("invalid match options")


@dataclass(frozen=True)
class MatchStats:
    mean_fit_de: float
    mean_seam_de: float
    adjacent_repeats: int
    distinct_tiles: int
    total_cost: float


@dataclass(frozen=True)
class MatchResult:
    tiles: NDArray[np.intp]
    """(rows, cols) index into the ``TileFeatures`` the match was run with."""
    fit_cost: NDArray[np.float32]
    """(rows, cols) fit ΔE of each assigned tile."""
    stats: MatchStats
    iterations: int
    converged: bool


def match(
    base: BaseSignatures,
    features: TileFeatures,
    options: MatchOptions | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> MatchResult:
    """``features`` must be computed for the same cell aspect as ``base``."""
    options = options or MatchOptions()
    if len(features) == 0:
        raise ValueError("no tiles to match")
    rows, cols = base.shape
    costs = fit_costs(base.fit.reshape(rows * cols, *base.fit.shape[2:]), features.fit)
    cand, cand_fit = top_k(costs, options.top_k)
    k = cand.shape[1]
    cand = cand.reshape(rows, cols, k)
    cand_fit = cand_fit.reshape(rows, cols, k)
    search = improve(
        cand,
        cand_fit,
        features.edges,
        base.edges,
        lambda_seam=options.lambda_seam,
        lambda_self=options.lambda_self,
        max_iters=options.max_iters,
        progress=progress,
    )
    pick = search.choice[..., None]
    tiles = np.take_along_axis(cand, pick, axis=2)[..., 0]
    fit = np.take_along_axis(cand_fit, pick, axis=2)[..., 0]
    return MatchResult(
        tiles=tiles,
        fit_cost=fit,
        stats=assignment_stats(tiles, fit, features.edges, base.edges, options),
        iterations=search.iterations,
        converged=search.converged,
    )


def seam_costs(
    tiles: NDArray[np.intp], edges: NDArray[np.float32], base_edges: NDArray[np.float32]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Seam ΔE for every horizontal (rows, cols-1) and vertical (rows-1, cols) neighbour pair.

    A seam costs how far the colour step between two tiles differs from the step the base photo
    has at that boundary: tiles blend where the photo is smooth and keep its real edges.
    """
    horiz = (edges[tiles[:, :-1], RIGHT] - edges[tiles[:, 1:], LEFT]) - (
        base_edges[:, :-1, RIGHT] - base_edges[:, 1:, LEFT]
    )
    vert = (edges[tiles[:-1], BOTTOM] - edges[tiles[1:], TOP]) - (
        base_edges[:-1, :, BOTTOM] - base_edges[1:, :, TOP]
    )
    return (
        np.linalg.norm(horiz, axis=-1).mean(axis=-1).astype(np.float64),
        np.linalg.norm(vert, axis=-1).mean(axis=-1).astype(np.float64),
    )


def assignment_stats(
    tiles: NDArray[np.intp],
    fit: NDArray[np.float32],
    edges: NDArray[np.float32],
    base_edges: NDArray[np.float32],
    options: MatchOptions,
) -> MatchStats:
    horiz, vert = seam_costs(tiles, edges, base_edges)
    pairs = horiz.size + vert.size
    seam_total = float(horiz.sum() + vert.sum())
    repeats = int((tiles[:, :-1] == tiles[:, 1:]).sum() + (tiles[:-1] == tiles[1:]).sum())
    fit_total = float(fit.sum())
    return MatchStats(
        mean_fit_de=fit_total / fit.size,
        mean_seam_de=seam_total / pairs if pairs else 0.0,
        adjacent_repeats=repeats,
        distinct_tiles=int(np.unique(tiles).size),
        total_cost=fit_total + options.lambda_seam * seam_total + options.lambda_self * repeats,
    )
