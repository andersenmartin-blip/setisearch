"""Transparent approximations for two important unresolved-tone losses."""

from __future__ import annotations

import numpy as np


def one_bin_leakage_fraction(fractional_bin_offset: np.ndarray | float):
    """Central-bin power fraction for a rectangular-window unresolved tone."""
    return np.sinc(fractional_bin_offset) ** 2


def leakage_summary(samples: int = 200_001) -> dict:
    offsets = np.linspace(-0.5, 0.5, samples)
    fractions = one_bin_leakage_fraction(offsets)
    return {
        "model": "rectangular FFT window; one-bin power statistic",
        "mean_retained_fraction_uniform_bin_phase": float(np.mean(fractions)),
        "worst_retained_fraction_half_bin": float(one_bin_leakage_fraction(0.5)),
        "best_retained_fraction_bin_center": 1.0,
    }


def acceleration_smearing(drift_hz_s: float, tsamp_s: float, channel_width_hz: float) -> dict:
    """Incoherent-averaging approximation for drift within one integration."""
    bins_crossed = abs(drift_hz_s) * tsamp_s / abs(channel_width_hz)
    peak_fraction = min(1.0, 1.0 / max(bins_crossed, 1.0))
    return {
        "drift_hz_s": float(drift_hz_s),
        "bins_crossed_per_integration": float(bins_crossed),
        "approx_peak_retained_fraction": float(peak_fraction),
        "approx_flux_penalty": float(1.0 / peak_fraction),
        "model": "uniform power across bins traversed during one integration",
    }


def smearing_table(tsamp_s: float, channel_width_hz: float) -> list[dict]:
    return [
        acceleration_smearing(rate, tsamp_s, channel_width_hz)
        for rate in (0.0, 0.1, 0.25, 0.5, 1.0, 2.0)
    ]
