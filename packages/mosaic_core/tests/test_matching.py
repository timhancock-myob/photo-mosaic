import numpy as np
import pytest

from mosaic_core import BaseSignatures, MatchOptions, TileFeatures, match
from mosaic_core.matching import assignment_stats
from mosaic_core.matching.candidates import fit_costs, top_k

RNG = np.random.default_rng(0)


def features(fit: list[list[float]] | np.ndarray, edges: np.ndarray | None = None) -> TileFeatures:
    f = np.asarray(fit, dtype=np.float32).reshape(len(fit), 1, 3)
    e = edges if edges is not None else np.zeros((len(fit), 4, 1, 3), dtype=np.float32)
    return TileFeatures(fit=f, edges=e.astype(np.float32))


def cells(values: list[list[list[float]]], segments: int = 1) -> BaseSignatures:
    fit = np.asarray(values, dtype=np.float32)[:, :, None, :]
    rows, cols = fit.shape[:2]
    return BaseSignatures(fit=fit, edges=np.zeros((rows, cols, 4, segments, 3), np.float32))


def random_base(rows: int, cols: int, points: int, segments: int) -> BaseSignatures:
    return BaseSignatures(
        fit=(RNG.normal(size=(rows, cols, points, 3)) * 20).astype(np.float32),
        edges=(RNG.normal(size=(rows, cols, 4, segments, 3)) * 20).astype(np.float32),
    )


def test_fit_costs_match_brute_force() -> None:
    c = RNG.normal(size=(5, 4, 3)).astype(np.float32)
    t = RNG.normal(size=(7, 4, 3)).astype(np.float32)
    expected = np.linalg.norm(c[:, None] - t[None], axis=-1).mean(axis=-1)
    np.testing.assert_allclose(fit_costs(c, t), expected, rtol=1e-5)


def test_top_k_sorted() -> None:
    idx, cost = top_k(np.array([[3.0, 1.0, 2.0, 0.5]], dtype=np.float32), 3)
    assert idx.tolist() == [[3, 1, 2]]
    assert cost.tolist() == [[0.5, 1.0, 2.0]]


def test_without_pairwise_terms_each_cell_takes_best_fit() -> None:
    c = random_base(4, 5, 6, 2)
    feats = TileFeatures(
        fit=RNG.normal(size=(20, 6, 3)).astype(np.float32),
        edges=RNG.normal(size=(20, 4, 2, 3)).astype(np.float32),
    )
    result = match(c, feats, MatchOptions(lambda_seam=0, lambda_self=0))
    best = fit_costs(c.fit.reshape(20, 6, 3), feats.fit).argmin(axis=1).reshape(4, 5)
    np.testing.assert_array_equal(result.tiles, best)
    assert result.converged


def test_seam_term_prefers_blending_neighbour() -> None:
    # Cell 0 wants tile 0 (right edge = 50). Cell 1 slightly prefers tile 1 (left edge 0)
    # over tile 2 (left edge 50, which blends with tile 0).
    edges = np.zeros((3, 4, 1, 3), dtype=np.float32)
    edges[0, 1] = 50
    edges[2, 3] = 50
    feats = features([[0, 0, 0], [100, 0, 0], [101, 0, 0]], edges)
    c = cells([[[0, 0, 0], [100, 0, 0]]])
    assert match(c, feats, MatchOptions(lambda_seam=0)).tiles.tolist() == [[0, 1]]
    assert match(c, feats, MatchOptions(lambda_seam=0.5)).tiles.tolist() == [[0, 2]]


def test_self_penalty_avoids_repeats() -> None:
    feats = features([[0, 0, 0], [2, 0, 0]])
    c = cells([[[0, 0, 0], [0, 0, 0]]])
    assert match(c, feats, MatchOptions(lambda_self=0)).tiles.tolist() == [[0, 0]]
    result = match(c, feats, MatchOptions(lambda_self=8))
    assert sorted(result.tiles[0].tolist()) == [0, 1]
    assert result.stats.adjacent_repeats == 0


def test_local_search_lowers_total_cost_and_is_deterministic() -> None:
    c = random_base(12, 15, 4, 3)
    feats = TileFeatures(
        fit=(RNG.normal(size=(60, 4, 3)) * 20).astype(np.float32),
        edges=(RNG.normal(size=(60, 4, 3, 3)) * 20).astype(np.float32),
    )
    opts = MatchOptions(lambda_seam=1.0, lambda_self=10.0)
    result = match(c, feats, opts)
    costs = fit_costs(c.fit.reshape(-1, 4, 3), feats.fit)
    init = costs.argmin(axis=1).reshape(12, 15)
    init_fit = costs.min(axis=1).reshape(12, 15)
    init_stats = assignment_stats(init, init_fit, feats.edges, c.edges, opts)
    assert result.stats.total_cost < init_stats.total_cost
    np.testing.assert_array_equal(match(c, feats, opts).tiles, result.tiles)


def test_seams_keep_the_base_photos_edges() -> None:
    # The base steps from dark to light between the cells, so a matching step between the
    # tiles is free and a blended pair is penalised.
    base = cells([[[50, 0, 0], [50, 0, 0]]])
    base.edges[0, 0, 1] = 20  # right side of the left cell
    base.edges[0, 1, 3] = 80  # left side of the right cell
    edges = np.zeros((3, 4, 1, 3), dtype=np.float32)
    edges[:, :] = [[[50, 0, 0]]]
    edges[1, 1], edges[2, 3] = 20, 80  # tiles 1 + 2 reproduce the step
    feats = features([[50, 0, 0], [52, 0, 0], [52, 0, 0]], edges)
    result = match(base, feats, MatchOptions(lambda_seam=1.0, lambda_self=0))
    assert result.tiles.tolist() == [[1, 2]]


def test_rejects_empty_tile_set() -> None:
    with pytest.raises(ValueError):
        match(cells([[[0, 0, 0]]]), features(np.zeros((0, 3))))
