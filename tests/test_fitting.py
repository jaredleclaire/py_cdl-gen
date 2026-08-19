import numpy as np

from cdl_gen.fitting import apply_saturation, apply_sop, fit_cdl, fit_saturation, fit_sop


def _make_source_image(seed: int = 42, size: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((size, size, 3))


def test_fit_sop_recovers_known_parameters():
    source = _make_source_image()
    true_slope = np.array([1.2, 0.9, 1.05])
    true_offset = np.array([0.05, -0.02, 0.01])
    true_power = np.array([0.9, 1.1, 1.0])

    target = apply_sop(source, true_slope, true_offset, true_power)

    slope, offset, power = fit_sop(source, target, max_samples=4096)

    assert np.allclose(slope, true_slope, atol=1e-2)
    assert np.allclose(offset, true_offset, atol=1e-2)
    assert np.allclose(power, true_power, atol=1e-2)


def test_fit_saturation_recovers_known_value():
    source = _make_source_image()
    true_sat = 0.6

    target = apply_saturation(source, true_sat)

    sat = fit_saturation(source, target)

    assert abs(sat - true_sat) < 1e-6


def test_identity_transform_yields_identity_parameters():
    source = _make_source_image()

    slope, offset, power = fit_sop(source, source, max_samples=4096)
    sop_output = apply_sop(source, slope, offset, power)
    sat = fit_saturation(sop_output, source)

    assert np.allclose(slope, 1.0, atol=1e-2)
    assert np.allclose(offset, 0.0, atol=1e-2)
    assert np.allclose(power, 1.0, atol=1e-2)
    assert abs(sat - 1.0) < 1e-2


def test_fit_cdl_recovers_combined_sop_and_saturation():
    # Target = Sat(SOP(source)); fitting SOP against the raw target directly
    # would be biased since Sat mixes channels via luma, so fit_cdl must
    # iteratively separate the two operators.
    source = _make_source_image()
    true_slope = np.array([1.15, 0.95, 1.05])
    true_offset = np.array([0.03, -0.01, 0.02])
    true_power = np.array([0.9, 1.0, 1.1])
    true_sat = 0.7

    sop_out = apply_sop(source, true_slope, true_offset, true_power)
    target = apply_saturation(sop_out, true_sat)

    slope, offset, power, sat = fit_cdl(source, target, max_samples=4096, iterations=12)

    assert np.allclose(slope, true_slope, atol=1e-2)
    assert np.allclose(offset, true_offset, atol=1e-2)
    assert np.allclose(power, true_power, atol=1e-2)
    assert abs(sat - true_sat) < 1e-2

