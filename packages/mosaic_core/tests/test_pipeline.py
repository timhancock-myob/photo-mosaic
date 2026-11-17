import numpy as np
from images import smooth_noise, solid
from PIL import Image

from mosaic_core import Grid, MatchOptions, base_signatures, match, render_mosaic, tile_features

PALETTE = [(230, 40, 40), (40, 200, 60), (40, 60, 220), (240, 220, 50), (30, 30, 30)]


def test_mosaic_reproduces_a_block_image() -> None:
    layout = np.array([[0, 1, 2, 3], [4, 0, 1, 2], [3, 4, 0, 1]])
    base = Image.new("RGB", (400, 300))
    for (r, c), i in np.ndenumerate(layout):
        base.paste(PALETTE[i], (c * 100, r * 100, c * 100 + 100, r * 100 + 100))
    tiles = [solid(colour, (120, 90)) for colour in PALETTE] + [smooth_noise(s) for s in range(20)]
    grid = Grid(4, 3)
    aspect = grid.cell_aspect(*base.size)
    result = match(base_signatures(base, grid), tile_features(tiles, aspect), MatchOptions())
    np.testing.assert_array_equal(result.tiles, layout)
    out = render_mosaic(result.tiles, lambda i: tiles[i], cell_width=10, cell_aspect=aspect)
    assert out.getpixel((15, 15)) == PALETTE[layout[1, 1]]
