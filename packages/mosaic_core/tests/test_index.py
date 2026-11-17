from pathlib import Path

import pytest
from images import encode, smooth_noise, solid
from PIL import Image, ImageEnhance

from mosaic_core import SkipReason, index_tiles


def test_index_skips_with_reasons(tmp_path: Path) -> None:
    a = encode(smooth_noise(1), "JPEG", quality=95)
    near = encode(ImageEnhance.Brightness(smooth_noise(1)).enhance(1.03), "JPEG", quality=80)
    path = tmp_path / "b.png"
    path.write_bytes(encode(smooth_noise(2)))
    index = index_tiles(
        [
            ("a", a),
            ("b", path),
            ("a-copy", a),
            ("a-near", near),
            ("broken", b"\x00not an image"),
            ("tiny", encode(smooth_noise(3, (40, 30)))),
            ("missing", tmp_path / "nope.jpg"),
        ]
    )
    assert [t.key for t in index.tiles] == ["a", "b"]
    reasons = {s.key: (s.reason, s.duplicate_of) for s in index.skipped}
    assert reasons == {
        "a-copy": (SkipReason.DUPLICATE, "a"),
        "a-near": (SkipReason.NEAR_DUPLICATE, "a"),
        "broken": (SkipReason.UNREADABLE, None),
        "tiny": (SkipReason.TOO_SMALL, None),
        "missing": (SkipReason.UNREADABLE, None),
    }


def test_decompression_bomb_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    index = index_tiles([("big", encode(solid((1, 2, 3), (100, 100))))])
    assert index.tiles == []
    assert index.skipped[0].reason == SkipReason.UNREADABLE


def test_near_duplicates_can_be_kept() -> None:
    a = smooth_noise(1)
    near = ImageEnhance.Brightness(a).enhance(1.03)
    index = index_tiles([("a", encode(a)), ("n", encode(near))], collapse_near_duplicates=False)
    assert len(index.tiles) == 2


def test_flat_photos_of_different_colours_are_not_duplicates() -> None:
    index = index_tiles([("r", encode(solid((200, 0, 0)))), ("b", encode(solid((0, 0, 200))))])
    assert len(index.tiles) == 2


def test_thumbnail_and_upright_size() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6
    data = encode(smooth_noise(4, (800, 400)), "JPEG", exif=exif)
    (tile,) = index_tiles([("p", data)]).tiles
    assert (tile.width, tile.height) == (400, 800)
    assert min(tile.thumb.size) == 128
    assert tile.thumb.height > tile.thumb.width
