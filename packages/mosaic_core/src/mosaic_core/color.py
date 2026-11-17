import numpy as np
from numpy.typing import NDArray
from PIL import Image
from skimage.color import rgb2lab


def to_lab(img: Image.Image) -> NDArray[np.float32]:
    """RGB image -> CIELAB array of shape (h, w, 3)."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return np.asarray(rgb2lab(rgb), dtype=np.float32)
