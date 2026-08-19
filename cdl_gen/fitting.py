"""Core fitting logic for recovering ASC CDL Slope/Offset/Power/Saturation
values that map a source (ungraded) image onto a target (graded) image.

Both images must be pixel-aligned and depict the same content.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit

# Rec.709 luma weights, as specified by the ASC CDL for the Sat operator.
LUMA_WEIGHTS = np.array([0.2126, 0.7152, 0.0722])


def _sop_model(x: np.ndarray, slope: float, offset: float, power: float) -> np.ndarray:
    y = np.clip(x * slope + offset, 0.0, 1.0)
    return np.power(y, power)


def fit_sop(
    source: np.ndarray,
    target: np.ndarray,
    max_samples: int = 200_000,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit per-channel Slope/Offset/Power mapping `source` onto `target`.

    Returns three (3,) arrays: slope, offset, power (order R, G, B).
    """
    src_flat = source.reshape(-1, 3)
    tgt_flat = target.reshape(-1, 3)
    n = src_flat.shape[0]

    if n > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(n, size=max_samples, replace=False)
        src_flat = src_flat[idx]
        tgt_flat = tgt_flat[idx]

    slope = np.ones(3)
    offset = np.zeros(3)
    power = np.ones(3)

    for c in range(3):
        x = src_flat[:, c]
        y = tgt_flat[:, c]
        try:
            popt, _ = curve_fit(
                _sop_model,
                x,
                y,
                p0=[1.0, 0.0, 1.0],
                bounds=([0.01, -1.0, 0.01], [10.0, 1.0, 10.0]),
                maxfev=10000,
            )
            slope[c], offset[c], power[c] = popt
        except RuntimeError:
            # Keep identity defaults for this channel if the fit fails to converge.
            pass

    return slope, offset, power


def apply_sop(image: np.ndarray, slope: np.ndarray, offset: np.ndarray, power: np.ndarray) -> np.ndarray:
    """Apply the ASC CDL SOP (Slope/Offset/Power) operator to an image."""
    out = np.clip(image * slope + offset, 0.0, 1.0)
    return np.power(out, power)


def fit_saturation(
    sop_output: np.ndarray,
    target: np.ndarray,
    luma_weights: np.ndarray = LUMA_WEIGHTS,
) -> float:
    """Closed-form least-squares fit of a single saturation scalar.

    The ASC CDL Sat operator is `out = luma + sat * (color - luma)`, which is
    linear in `sat`, so the optimal value has a direct least-squares solution.
    """
    luma = np.tensordot(sop_output, luma_weights, axes=([2], [0]))[..., None]
    diff_pred = sop_output - luma
    diff_target = target - luma

    denominator = np.sum(diff_pred * diff_pred)
    if denominator < 1e-8:
        return 1.0

    numerator = np.sum(diff_pred * diff_target)
    sat = numerator / denominator
    return float(np.clip(sat, 0.0, 4.0))


def apply_saturation(image: np.ndarray, saturation: float, luma_weights: np.ndarray = LUMA_WEIGHTS) -> np.ndarray:
    """Apply the ASC CDL Sat operator to an image."""
    luma = np.tensordot(image, luma_weights, axes=([2], [0]))[..., None]
    return luma + saturation * (image - luma)


def invert_saturation(image: np.ndarray, saturation: float, luma_weights: np.ndarray = LUMA_WEIGHTS) -> np.ndarray:
    """Approximately undo the Sat operator (ignoring any [0, 1] clipping)."""
    if abs(saturation) < 1e-6:
        return image
    luma = np.tensordot(image, luma_weights, axes=([2], [0]))[..., None]
    return luma + (image - luma) / saturation


def fit_cdl(
    source: np.ndarray,
    target: np.ndarray,
    max_samples: int = 200_000,
    seed: int = 0,
    iterations: int = 8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Jointly recover Slope/Offset/Power/Saturation mapping `source` to `target`.

    The real pipeline is `target = Sat(SOP(source))`, so SOP and Sat can't be
    fit independently against the final target: Sat mixes channels via luma,
    which biases a naive per-channel SOP fit. This alternates between
    desaturating the target with the current Sat estimate (fitting SOP against
    that), then re-fitting Sat from the new SOP output, until it converges.
    """
    saturation = 1.0
    slope = np.ones(3)
    offset = np.zeros(3)
    power = np.ones(3)

    for _ in range(iterations):
        desaturated_target = invert_saturation(target, saturation)
        slope, offset, power = fit_sop(source, desaturated_target, max_samples=max_samples, seed=seed)
        sop_output = apply_sop(source, slope, offset, power)
        saturation = fit_saturation(sop_output, target)

    return slope, offset, power, saturation
