import numpy as np
from numpy.typing import NDArray
from scipy.spatial.distance import cdist


def fit_costs(cells: NDArray[np.float32], tiles: NDArray[np.float32]) -> NDArray[np.float32]:
    """Mean CIE76 ΔE over grid points: ``cells`` (C, P, 3) x ``tiles`` (N, P, 3) -> (C, N)."""
    if cells.shape[1:] != tiles.shape[1:]:
        raise ValueError("cell and tile signatures have different shapes")
    points = cells.shape[1]
    out = np.zeros((cells.shape[0], tiles.shape[0]), dtype=np.float64)
    for p in range(points):
        out += cdist(cells[:, p], tiles[:, p])
    result: NDArray[np.float32] = (out / points).astype(np.float32)
    return result


def top_k(costs: NDArray[np.float32], k: int) -> tuple[NDArray[np.intp], NDArray[np.float32]]:
    """Per row, the ``k`` lowest-cost columns sorted ascending, and their costs."""
    k = min(k, costs.shape[1])
    idx = np.argpartition(costs, k - 1, axis=1)[:, :k]
    part = np.take_along_axis(costs, idx, axis=1)
    order = np.argsort(part, axis=1, kind="stable")
    return np.take_along_axis(idx, order, axis=1), np.take_along_axis(part, order, axis=1)
