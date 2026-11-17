from dataclasses import dataclass


@dataclass(frozen=True)
class Grid:
    """Columns x rows laid over the base photo (ADR 0002)."""

    cols: int
    rows: int

    def __post_init__(self) -> None:
        if self.cols < 1 or self.rows < 1:
            raise ValueError("cols and rows must be at least 1")

    @property
    def cells(self) -> int:
        return self.cols * self.rows

    def cell_aspect(self, base_width: int, base_height: int) -> float:
        """Cell width / height in base-photo pixels."""
        return (base_width / self.cols) / (base_height / self.rows)


def default_rows(base_width: int, base_height: int, cols: int) -> int:
    """Row count that gives approximately square cells."""
    return max(1, round(cols * base_height / base_width))
