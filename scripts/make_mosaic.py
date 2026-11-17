"""Build a mosaic from a base photo and a folder of tiles: uv run poe mosaic BASE TILES OUT."""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from mosaic_core import (
    Grid,
    MatchOptions,
    SignatureSpec,
    base_signatures,
    cell_size,
    default_rows,
    index_tiles,
    match,
    open_image,
    render_mosaic,
    tile_features,
)


def main() -> int:
    defaults = MatchOptions()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("base", type=Path)
    p.add_argument("tiles", type=Path, help="folder of tile photos (searched recursively)")
    p.add_argument("out", type=Path, help="output image (.jpg or .png)")
    p.add_argument("--cols", type=int, default=50)
    p.add_argument("--rows", type=int, help="default: square cells")
    p.add_argument("--cell-px", type=int, default=64, help="output cell width in pixels")
    p.add_argument("--lambda-seam", type=float, default=defaults.lambda_seam)
    p.add_argument("--lambda-self", type=float, default=defaults.lambda_self)
    p.add_argument("--top-k", type=int, default=defaults.top_k)
    p.add_argument("--max-iters", type=int, default=defaults.max_iters)
    p.add_argument("--signature-grid", type=int, default=SignatureSpec().grid)
    p.add_argument("--keep-near-duplicates", action="store_true")
    p.add_argument("--report", type=Path, help="write stats as JSON")
    args = p.parse_args()

    t0 = time.perf_counter()
    base = open_image(args.base)
    grid = Grid(args.cols, args.rows or default_rows(base.width, base.height, args.cols))
    aspect = grid.cell_aspect(base.width, base.height)

    files = sorted(f for f in args.tiles.rglob("*") if f.is_file() and not f.name.startswith("."))
    index = index_tiles(
        ((str(f), f) for f in files), collapse_near_duplicates=not args.keep_near_duplicates
    )
    t_index = time.perf_counter()
    skipped = Counter(s.reason.value for s in index.skipped)
    print(f"indexed {len(index.tiles)} tiles, skipped {dict(skipped)} in {t_index - t0:.1f}s")
    if not index.tiles:
        print("no usable tiles", file=sys.stderr)
        return 1

    spec = SignatureSpec(grid=args.signature_grid)
    features = tile_features([t.thumb for t in index.tiles], aspect, spec)
    cells = base_signatures(base, grid, spec)
    options = MatchOptions(
        lambda_seam=args.lambda_seam,
        lambda_self=args.lambda_self,
        top_k=args.top_k,
        max_iters=args.max_iters,
    )
    result = match(cells, features, options)
    t_match = time.perf_counter()
    print(
        f"matched {grid.cols}x{grid.rows} in {t_match - t_index:.1f}s "
        f"({result.iterations} iterations, converged={result.converged})"
    )
    print(json.dumps(vars(result.stats), indent=2))

    min_side = max(cell_size(args.cell_px, aspect))
    image = render_mosaic(
        result.tiles,
        lambda i: open_image(Path(index.tiles[i].key), min_side=min_side),
        cell_width=args.cell_px,
        cell_aspect=aspect,
    )
    if args.out.suffix.lower() in (".jpg", ".jpeg"):
        image.save(args.out, quality=92)
    else:
        image.save(args.out)
    t_render = time.perf_counter()
    print(f"wrote {args.out} ({image.width}x{image.height}) in {t_render - t_match:.1f}s")

    if args.report:
        report = {
            "grid": [grid.cols, grid.rows],
            "tiles": len(index.tiles),
            "skipped": dict(skipped),
            "options": vars(options),
            "stats": vars(result.stats),
            "iterations": result.iterations,
            "seconds": {
                "index": t_index - t0,
                "match": t_match - t_index,
                "render": t_render - t_match,
            },
        }
        args.report.write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
