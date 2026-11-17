# 0003. Matching: cell fit plus neighbour seam blending

- **Status:** Accepted (seam definition refined by [0007](0007-seams-relative-to-base.md))
- **Date:** 2026-11-17

## Context

The brief says the best tile is "determined by the general color profile of the photo, especially around the edges". The initial system description read this as "a tile's edges should match the edges of the base cell it replaces". The alternative reading is that adjacent tiles should blend into each other at their shared borders.

## Decision

"Edges" means **neighbouring tiles blend into each other**. Each tile must still match its base cell's overall colour, otherwise the mosaic would not resemble the base. The objective for a full assignment `A` is:

```
total_cost(A) = Σ_cells  fit(cell, A[cell])                       # tile vs base cell colour
              + λ_seam  * Σ_adjacent (c1,c2) seam(A[c1], A[c2], side)  # shared-border mismatch
              + λ_self  * Σ_adjacent [A[c1] == A[c2]]               # same tile touching itself
```

- `fit` compares the tile's colour signature with the base cell's (CIELAB, small downsampled grid).
- `seam` compares the facing edge strips of two adjacent tiles (right edge of left tile vs left edge of right tile, and so on).
- `λ_self` stops the optimiser tiling one photo next to itself, which would otherwise score a perfect seam (see ADR 0004).

**Algorithm.** The pairwise term makes this a grid labelling problem, not a per-cell lookup. v1:
1. Initialise each cell with its lowest-`fit` tile (vectorised cost matrix).
2. Improve with local search, e.g. iterated conditional modes: revisit each cell and pick the tile that minimises fit plus seams with its current neighbours, using the top-K candidates by `fit`. Repeat until there is no improvement or the iteration cap is hit.
3. Optionally finish with simulated annealing if quality needs it.

`λ_seam`, `λ_self`, K and the iteration cap are configurable and tuned in `notebooks/`.

## Consequences

- Matching is no longer a single `argmin` per cell. Expect seconds rather than milliseconds for large grids. It runs as a background job with progress.
- Tile features need both a full-tile signature (for `fit`) and per-side edge strips (for `seam`).
- Swapping one tile changes the seam cost of its neighbours. The alternatives panel ranks by `fit + seams with current neighbours`, and can offer a local re-optimise of the neighbourhood.
- A no-repeats constraint plus pairwise terms is a quadratic assignment problem. That mode uses heuristics (constrained local search), not the Hungarian algorithm alone.
