import re

import numpy as np
import OpenImageIO as oiio
import pytest

from cdl_gen.__main__ import main
from cdl_gen.fitting import apply_saturation, apply_sop
from cdl_gen.io_utils import load_image


def _make_image(seed: int = 7, size: int = 32) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((size, size, 3)).astype(np.float32)


def _write(path, pixels: np.ndarray, fmt) -> None:
    h, w, c = pixels.shape
    spec = oiio.ImageSpec(w, h, c, fmt)
    out = oiio.ImageOutput.create(str(path))
    assert out is not None, oiio.geterror()
    assert out.open(str(path), spec), out.geterror()
    assert out.write_image(pixels), out.geterror()
    out.close()


@pytest.mark.parametrize(
    "suffix, fmt, atol",
    [
        (".png", oiio.UINT8, 1 / 255),
        (".png", oiio.UINT16, 1 / 65535),
        (".tif", oiio.UINT16, 1 / 65535),
        (".tif", oiio.FLOAT, 1e-6),
        (".exr", oiio.HALF, 1e-3),
        (".exr", oiio.FLOAT, 1e-6),
        (".dpx", oiio.UINT16, 1 / 1023),  # DPX defaults to 10-bit
    ],
)
def test_load_image_round_trips_formats(tmp_path, suffix, fmt, atol):
    pixels = _make_image()
    path = tmp_path / f"img{suffix}"
    _write(path, pixels, fmt)

    loaded = load_image(path)

    assert loaded.shape == pixels.shape
    assert loaded.dtype == np.float64
    assert np.allclose(loaded, pixels, atol=atol)


def test_load_image_drops_alpha_and_expands_gray(tmp_path):
    rgba = np.concatenate([_make_image(), np.ones((32, 32, 1), np.float32)], axis=-1)
    _write(tmp_path / "rgba.exr", rgba, oiio.FLOAT)
    assert load_image(tmp_path / "rgba.exr").shape == (32, 32, 3)

    gray = _make_image()[..., :1]
    _write(tmp_path / "gray.tif", gray, oiio.UINT16)
    loaded = load_image(tmp_path / "gray.tif")
    assert loaded.shape == (32, 32, 3)
    assert np.allclose(loaded[..., 0], loaded[..., 2])


def test_load_image_clips_scene_linear_values(tmp_path):
    pixels = np.full((4, 4, 3), [2.5, -0.5, 0.25], np.float32)
    _write(tmp_path / "hdr.exr", pixels, oiio.FLOAT)

    loaded = load_image(tmp_path / "hdr.exr")

    assert np.allclose(loaded[0, 0], [1.0, 0.0, 0.25])


def test_load_image_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        load_image(tmp_path / "nope.exr")


def test_cli_fits_cdl_from_exr_pair(tmp_path):
    source = _make_image(size=64)
    target = apply_saturation(
        apply_sop(source, np.array([1.1, 0.95, 1.0]), np.array([0.02, 0.0, -0.01]),
                  np.array([0.95, 1.0, 1.05])),
        0.8,
    ).astype(np.float32)
    _write(tmp_path / "src.exr", source, oiio.FLOAT)
    _write(tmp_path / "tgt.exr", target, oiio.FLOAT)
    out = tmp_path / "out.cc"

    assert main([str(tmp_path / "src.exr"), str(tmp_path / "tgt.exr"), "-o", str(out)]) == 0
    sat = float(re.search(r"<Saturation>([-\d.]+)</Saturation>", out.read_text()).group(1))
    assert abs(sat - 0.8) < 1e-2
