"""Image loading helpers.

Images are loaded as float64 arrays in [0, 1], shape (H, W, 3), RGB order.
"""
from __future__ import annotations

import numpy as np
import OpenImageIO as oiio


def load_image(path: str) -> np.ndarray:
    """Load an image from disk and return a normalized float RGB array.

    Integer formats (8/10/12/16-bit) are scaled to [0, 1] by OpenImageIO.
    Float formats such as EXR are read as-is and then clipped to [0, 1],
    matching the ASC CDL's clamped working range.
    """
    buf = oiio.ImageBuf(str(path))
    # Reads only the first subimage / MIP level.
    if not buf.read():
        raise OSError(f"Could not read image {str(path)!r}: {buf.geterror()}")
    arr = buf.get_pixels(oiio.FLOAT)
    if arr is None:
        raise OSError(f"Could not read image {str(path)!r}: {buf.geterror()}")

    if arr.ndim == 2:
        arr = arr[..., np.newaxis]

    nchannels = arr.shape[-1]
    if nchannels == 1:
        arr = np.repeat(arr, 3, axis=-1)
    elif nchannels == 2:
        # Luminance + alpha
        arr = np.repeat(arr[..., :1], 3, axis=-1)
    else:
        arr = arr[..., :3]

    arr = np.nan_to_num(arr.astype(np.float64), nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(arr, 0.0, 1.0)
