"""Mosaic engine. Only names exported here are public; other packages must not import submodules."""

from mosaic_core.decode import open_image
from mosaic_core.errors import DecodeError
from mosaic_core.features import (
    BaseSignatures,
    SignatureSpec,
    TileFeatures,
    base_signatures,
    tile_features,
)
from mosaic_core.grid import Grid, default_rows
from mosaic_core.index import IndexedTile, SkippedTile, SkipReason, TileIndex, index_tiles
from mosaic_core.matching import MatchOptions, MatchResult, MatchStats, match
from mosaic_core.render import cell_size, render_mosaic

__version__ = "0.1.0"

__all__ = [
    "BaseSignatures",
    "DecodeError",
    "Grid",
    "IndexedTile",
    "MatchOptions",
    "MatchResult",
    "MatchStats",
    "SignatureSpec",
    "SkipReason",
    "SkippedTile",
    "TileFeatures",
    "TileIndex",
    "__version__",
    "base_signatures",
    "cell_size",
    "default_rows",
    "index_tiles",
    "match",
    "open_image",
    "render_mosaic",
    "tile_features",
]
