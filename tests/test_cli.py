import numpy as np
import pytest
from PIL import Image

from cdl_gen.__main__ import main


@pytest.fixture
def image_pair(tmp_path):
    rng = np.random.default_rng(3)
    source = (rng.random((32, 32, 3)) * 255).astype(np.uint8)
    target = np.clip(source.astype(np.int16) + 20, 0, 255).astype(np.uint8)
    Image.fromarray(source).save(tmp_path / "src.png")
    Image.fromarray(target).save(tmp_path / "tgt.png")
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
