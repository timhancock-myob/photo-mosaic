import numpy as np
import pytest
from images import solid
from PIL import Image

from mosaic_core import cell_size, render_mosaic

COLOURS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def test_render_places_each_tile_and_loads_once() -> None:
    loads: list[int] = []

    def load(i: int) -> Image.Image:
        loads.append(i)
        return solid(COLOURS[i], (300, 200))

    tiles = np.array([[0, 1, 2], [2, 2, 0]])
    out = render_mosaic(tiles, load, cell_width=20, cell_aspect=2.0)
    assert out.size == (60, 20)
    assert cell_size(20, 2.0) == (20, 10)
    for r in range(2):
        for c in range(3):
            assert out.getpixel((c * 20 + 10, r * 10 + 5)) == COLOURS[tiles[r, c]]
    assert sorted(loads) == [0, 1, 2]


def test_render_refuses_oversized_output() -> None:
    with pytest.raises(ValueError):
        render_mosaic(
            np.zeros((10, 10), dtype=np.intp),
            lambda i: solid((0, 0, 0)),
            cell_width=100,
            cell_aspect=1.0,
            max_pixels=1000,
        )
