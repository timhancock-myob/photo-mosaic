# 0007. Seams are measured against the base photo's own edges

- **Status:** Accepted
- **Date:** 2026-11-17
- **Refines:** [0003](0003-neighbour-seam-matching.md) (definition of `seam` only)

## Context

ADR 0003 defines `seam(A[c1], A[c2], side)` as the difference between the facing edge strips of two neighbouring tiles. Implemented literally, that term pushes every neighbour pair towards the same colour, including across real edges in the base photo (a dark building against a bright sky). In a synthetic test with hard colour blocks, the plain seam term replaced a third of the exactly matching tiles with blurrier ones.

## Decision

A seam costs how far the colour **step** between two tiles differs from the step the base photo has at that boundary:

```
seam(c1, c2) = mean over segments ‖ (tile_edge(A[c1], side) − tile_edge(A[c2], facing))
                                   − (base_edge(c1, side) − base_edge(c2, facing)) ‖
```

Where the base is smooth, the base step is about zero and this is the ADR 0003 term unchanged: neighbours blend. Where the base has an edge, tiles that reproduce that edge are not penalised.

Base edge strips are computed per cell, the same way as tile edge strips (mean Lab of `s` segments along each side).

## Consequences

- Seam blending no longer fights fidelity at genuine edges, so `λ_seam` can be set higher before the mosaic loses the base's shapes.
- The engine computes edge strips for the base cells as well as the tiles. That is cheap: one extra resample of the base.
- The objective in ADR 0003 is unchanged apart from the seam definition; ICM, `λ_self` and the reuse policies are unaffected.
