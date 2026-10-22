import numpy as np
import OpenImageIO as oiio
import pytest

from cdl_gen.__main__ import main


def _write_png(path, pixels: np.ndarray) -> None:
    h, w, c = pixels.shape
    out = oiio.ImageOutput.create(str(path))
    assert out is not None, oiio.geterror()
    assert out.open(str(path), oiio.ImageSpec(w, h, c, oiio.UINT8)), out.geterror()
    assert out.write_image(pixels), out.geterror()
    out.close()


@pytest.fixture
def image_pair(tmp_path):
    rng = np.random.default_rng(3)
    source = (rng.random((32, 32, 3)) * 255).astype(np.uint8)
    target = np.clip(source.astype(np.int16) + 20, 0, 255).astype(np.uint8)
    _write_png(tmp_path / "src.png", source)
    _write_png(tmp_path / "tgt.png", target)
    return tmp_path / "src.png", tmp_path / "tgt.png"


@pytest.mark.parametrize("extra_args", [[], ["--no-progress"]])
def test_cli_writes_cc_and_keeps_stdout_clean(image_pair, tmp_path, capsys, extra_args):
    src, tgt = image_pair
    out = tmp_path / "out.cc"

    assert main([str(src), str(tgt), "-o", str(out), "--iterations", "3", *extra_args]) == 0

    assert "<ColorCorrection" in out.read_text()
    stdout = capsys.readouterr().out
    assert "Loading images" not in stdout
    assert "Fitting CDL" not in stdout
    assert "Saturation:" in stdout


@pytest.mark.parametrize("name", ["identity.cc", "identity.cdl"])
def test_cli_identity_writes_bypass_values(tmp_path, name):
    out = tmp_path / name

    assert main(["--identity", "-o", str(out), "--id", "bypass"]) == 0

    text = out.read_text()
    assert 'id="bypass"' in text
    assert "<Slope>1.000000 1.000000 1.000000</Slope>" in text
    assert "<Offset>0.000000 0.000000 0.000000</Offset>" in text
    assert "<Power>1.000000 1.000000 1.000000</Power>" in text
    assert "<Saturation>1.000000</Saturation>" in text


def test_cli_requires_images_without_identity():
    with pytest.raises(SystemExit):
        main([])


def test_cli_identity_rejects_images(image_pair):
    src, tgt = image_pair
    with pytest.raises(SystemExit):
        main(["--identity", str(src), str(tgt)])
