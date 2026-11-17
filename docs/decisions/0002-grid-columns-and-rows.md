# 0002. Grid: user sets columns and rows independently

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

The brief says "e.g. 20x20, 50x50". The initial system description changed this so the user picks columns and rows are derived to keep cells square. We needed to decide what the grid controls mean.

## Decision

The user sets **columns and rows independently**. Cell shape follows: `cell_aspect = (base_width / cols) / (base_height / rows)`.

- The UI pre-fills rows with the value that gives square cells (`rows = round(cols * base_height / base_width)`) as a sensible default. The user can change it.
- Tiles are cropped to the cell aspect ratio (centre crop by default; crop window adjustable as an extra).

## Consequences

- Tile signatures depend on cell aspect. The engine stores a working thumbnail per tile and computes signatures per aspect ratio on demand, caching by `(tile, aspect)`, rather than precomputing one square signature at index time.
- Very elongated cells crop away most of each tile. The UI warns when `cell_aspect` is outside roughly 1:2 to 2:1.
- The base photo is resampled to `(cols * n, rows * n)` for signature extraction, not cropped to an exact multiple, so no edge pixels are lost.
