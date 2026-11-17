import pytest
from images import encode, solid
from PIL import Image, ImageCms

from mosaic_core import DecodeError, open_image


def test_exif_orientation_is_applied() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° CW on display
    data = encode(solid((200, 30, 30), (40, 20)), "JPEG", exif=exif)
    assert open_image(data).size == (20, 40)


@pytest.mark.parametrize("mode", ["L", "P", "CMYK"])
def test_modes_become_rgb(mode: str) -> None:
    fmt = "JPEG" if mode == "CMYK" else "PNG"
    img = open_image(encode(solid((10, 120, 200)).convert(mode), fmt))
    assert img.mode == "RGB"


def test_transparency_is_flattened_on_white() -> None:
    img = open_image(encode(Image.new("RGBA", (8, 8), (255, 0, 0, 0))))
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_embedded_srgb_profile_keeps_colour() -> None:
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    img = open_image(encode(solid((10, 120, 200)), icc_profile=icc))
    r, g, b = img.getpixel((0, 0))  # type: ignore[misc]
    assert abs(r - 10) <= 2 and abs(g - 120) <= 2 and abs(b - 200) <= 2


def test_heic_is_supported() -> None:
    img = open_image(encode(solid((20, 160, 60), (64, 48)), "HEIF"))
    assert img.size == (64, 48)
    assert abs(img.getpixel((32, 24))[1] - 160) < 10  # type: ignore[index]


def test_jpeg_draft_keeps_min_side() -> None:
    img = open_image(encode(solid((1, 2, 3), (1600, 1200)), "JPEG"), min_side=100)
    assert 100 <= min(img.size) < 1200


@pytest.mark.parametrize(
    ("data", "kwargs"),
    [
        (b"not an image", {}),
        (encode(solid((0, 0, 0), (20, 20))), {"max_pixels": 100}),
        (encode(solid((0, 0, 0), (20, 20))), {"max_bytes": 10}),
    ],
)
def test_rejects_bad_input(data: bytes, kwargs: dict[str, int]) -> None:
    with pytest.raises(DecodeError):
        open_image(data, **kwargs)
