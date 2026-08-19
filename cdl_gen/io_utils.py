"""Image loading helpers.

Images are loaded as float64 arrays in [0, 1], shape (H, W, 3), RGB order.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def load_image(path: str) -> np.ndarray:
    """Load an image from disk and return a normalized float RGB array."""
    img = Image.open(path)

    if img.mode not in ("RGB", "RGBA", "I;16", "I"):
        img = img.convert("RGB")

    arr = np.asarray(img)

    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    elif arr.shape[-1] == 4:
        arr = arr[..., :3]

    if arr.dtype == np.uint8:
        arr = arr.astype(np.float64) / 255.0
    elif arr.dtype == np.uint16:
        arr = arr.astype(np.float64) / 65535.0
    else:
        arr = arr.astype(np.float64)
        max_val = arr.max() if arr.size else 1.0
        if max_val > 1.0:
            arr = arr / 255.0

    return np.clip(arr, 0.0, 1.0)
