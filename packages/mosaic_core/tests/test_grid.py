import pytest

from mosaic_core import Grid, default_rows


def test_default_rows_gives_square_cells() -> None:
    assert default_rows(3000, 2000, 50) == 33
    assert Grid(50, 33).cell_aspect(3000, 2000) == pytest.approx(0.99, abs=0.01)


def test_independent_rows_change_cell_shape() -> None:
    assert Grid(10, 20).cell_aspect(1000, 1000) == pytest.approx(2.0)


def test_rejects_empty_grid() -> None:
    with pytest.raises(ValueError):
        Grid(0, 5)
