import numpy as np
import pytest
from images import smooth_noise, solid
from numpy.typing import NDArray
from PIL import Image

from mosaic_core import Grid, SignatureSpec, base_signatures, tile_features
from mosaic_core.color import to_lab
from mosaic_core.features import BOTTOM, LEFT, TOP, center_crop_box
from mosaic_core.matching.candidates import fit_costs


def lab_of(colour: tuple[int, int, int]) -> NDArray[np.float32]:
    lab: NDArray[np.float32] = to_lab(solid(colour, (1, 1)))[0, 0]
    return lab


def split(size: tuple[int, int] = (64, 64)) -> Image.Image:
    img = solid((0, 0, 0), size)
    img.paste((255, 255, 255), (size[0] // 2, 0, size[0], size[1]))
    return img


def test_center_crop_box() -> None:
    assert center_crop_box(200, 100, 1.0) == (50.0, 0.0, 150.0, 100.0)
    assert center_crop_box(100, 200, 2.0) == (0.0, 75.0, 100.0, 125.0)


def test_fit_signature_keeps_structure() -> None:
    feats = tile_features([split(), solid((119, 119, 119))], aspect=1.0)
    cells = base_signatures(split((120, 120)), Grid(1, 1)).fit
    costs = fit_costs(cells.reshape(1, *cells.shape[2:]), feats.fit)
    assert costs[0, 0] < costs[0, 1] / 4


def test_edge_strips_follow_sides() -> None:
    img = solid((220, 20, 20))
    img.paste((20, 20, 220), (0, 32, 64, 64))
    edges = tile_features([img], aspect=1.0).edges[0]
    red, blue = lab_of((220, 20, 20)), lab_of((20, 20, 220))
    assert np.linalg.norm(edges[TOP] - red, axis=1).max() < 2
    assert np.linalg.norm(edges[BOTTOM] - blue, axis=1).max() < 2
    assert np.linalg.norm(edges[LEFT][0] - red) < 2  # left side runs top to bottom
    assert np.linalg.norm(edges[LEFT][-1] - blue) < 2


def test_tile_is_cropped_to_cell_aspect() -> None:
    wide = solid((255, 0, 0), (300, 100))
    wide.paste((0, 0, 255), (100, 0, 200, 100))  # blue centre third
    fit = tile_features([wide], aspect=1.0).fit[0]
    assert np.linalg.norm(fit - lab_of((0, 0, 255)), axis=1).max() < 2


def test_identical_textured_tile_ranks_first() -> None:
    texture = smooth_noise(3, (60, 60))
    mean_rgb = np.asarray(texture).reshape(-1, 3).mean(axis=0)
    flat = solid((int(mean_rgb[0]), int(mean_rgb[1]), int(mean_rgb[2])), (60, 60))
    feats = tile_features([flat, texture], aspect=1.0, spec=SignatureSpec(grid=1))
    base = base_signatures(texture, Grid(1, 1), SignatureSpec(grid=1))
    costs = fit_costs(base.fit.reshape(1, 1, 3), feats.fit)[0]
    assert costs[1] < 0.01
    assert costs[1] < costs[0]
    assert np.abs(base.edges[0, 0] - tile_features([texture], 1.0).edges[0]).max() < 0.01


def test_base_signatures_shape_and_colour() -> None:
    base = solid((255, 0, 0), (90, 40))
    base.paste((0, 255, 0), (60, 20, 90, 40))
    spec = SignatureSpec(grid=4)
    base_sig = base_signatures(base, Grid(3, 2), spec)
    sig = base_sig.fit
    assert sig.shape == (2, 3, 16, 3)
    assert base_sig.edges.shape == (2, 3, 4, 4, 3)
    assert np.linalg.norm(base_sig.edges[1, 2] - lab_of((0, 255, 0)), axis=-1).max() < 1
    assert np.linalg.norm(sig[1, 2] - lab_of((0, 255, 0)), axis=1).max() < 1
    assert np.linalg.norm(sig[0, 0] - lab_of((255, 0, 0)), axis=1).max() < 1


def test_invalid_spec() -> None:
    with pytest.raises(ValueError):
        SignatureSpec(edge_depth=0)
