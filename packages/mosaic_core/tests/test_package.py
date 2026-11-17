import mosaic_core


def test_version_is_exposed() -> None:
    assert mosaic_core.__version__
