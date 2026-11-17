# 0004. Default reuse policy: reuse freely

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

A few hundred tiles cannot fill a large grid without repeats (50x50 is 2,500 cells). We needed a default policy, while keeping the brief's optional "no photo used twice".

## Decision

The default is **reuse freely**: each cell takes whichever tile minimises the objective in ADR 0003. There is no cap on uses.

Two more policies are available as options:
- **Even spread:** each tile is used at most `ceil(cells / tiles)` times, with a minimum spacing between repeats.
- **No repeats:** each tile is used at most once. Requires `tiles >= cells`; the UI blocks larger grids and suggests one that fits.

## Consequences

- Free reuse plus seam blending makes the same tile cluster, because it matches its own edges perfectly. The `λ_self` penalty in ADR 0003 discourages adjacent repeats. It is on by default.
- The Grid step shows "N cells / M tiles" and, when a constrained policy is selected and impossible, explains why.
- Near-duplicate tiles (bursts, edited copies) make even free reuse look repetitive. Indexing records a perceptual hash so near-duplicates can be collapsed.
