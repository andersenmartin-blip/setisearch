"""Realistic fractional-bin, intra-integration-smeared signal injections."""

from __future__ import annotations

import numpy as np

from .orbit import celestial_frequency_factor, make_location, make_target


def smeared_signal_vector(
    scan: dict,
    rest_frequency_grid_mhz: np.ndarray,
    reference_frequency_mhz: float,
    truth_rest_frequency_mhz: float,
    projected_scale: float,
    phase_offset_cycles: float,
    ideal_single_epoch_snr: float,
    config: dict,
    subintegrations: int = 32,
) -> tuple[np.ndarray, dict]:
    """Signal response after exact dedoppler, without allocating a full waterfall.

    The signal power follows sinc-squared channel leakage and sweeps linearly at
    the instantaneous model drift during each recorded integration. The supplied
    S/N is what a stationary, bin-centred one-channel tone would have produced.
    """
    target = make_target(config["target"])
    location = make_location(config["observatory"])
    factor, _, _ = celestial_frequency_factor(
        scan["times"], projected_scale, phase_offset_cycles,
        target, location, config["orbit"],
    )
    frequencies_mhz = scan["frequency_mhz"]
    f0_hz = float(frequencies_mhz[0] * 1e6)
    df_hz = float((frequencies_mhz[1] - frequencies_mhz[0]) * 1e6)
    tsamp_s = float(scan["header"]["tsamp"])
    ntime = scan["normalized"].shape[0]

    reference_track_mhz = reference_frequency_mhz * factor
    reference_indices = np.rint(
        (reference_track_mhz - frequencies_mhz[0]) / (df_hz / 1e6)
    ).astype(int)
    shifts = reference_indices - reference_indices[0]
    output_indices = np.rint(
        (rest_frequency_grid_mhz * factor[0] - frequencies_mhz[0]) / (df_hz / 1e6)
    ).astype(int)

    observed_hz = truth_rest_frequency_mhz * 1e6 * factor
    drift_hz_s = np.gradient(observed_hz, tsamp_s)
    midpoint_channels = (observed_hz - f0_hz) / df_hz
    sweep_channels = drift_hz_s * tsamp_s / df_hz
    truth_index = int(np.argmin(np.abs(rest_frequency_grid_mhz - truth_rest_frequency_mhz)))
    support = max(32, int(np.ceil(np.max(np.abs(sweep_channels)))) + 16)
    lo = max(0, truth_index - support)
    hi = min(rest_frequency_grid_mhz.size, truth_index + support + 1)
    vector = np.zeros(rest_frequency_grid_mhz.size, dtype=np.float32)
    subtime = (np.arange(subintegrations) + 0.5) / subintegrations - 0.5

    for row in range(ntime):
        instantaneous = midpoint_channels[row] + sweep_channels[row] * subtime
        sampled_channels = output_indices[lo:hi] + shifts[row]
        response = np.mean(
            np.sinc(sampled_channels[:, None] - instantaneous[None, :]) ** 2,
            axis=1,
        )
        norm_channels = np.arange(
            int(np.floor(np.min(instantaneous))) - support,
            int(np.ceil(np.max(instantaneous))) + support + 1,
        )
        normalization = np.sum(np.mean(
            np.sinc(norm_channels[:, None] - instantaneous[None, :]) ** 2,
            axis=1,
        ))
        vector[lo:hi] += (
            ideal_single_epoch_snr / ntime * response / normalization
        ).astype(np.float32)

    diagnostics = {
        "truth_rest_frequency_mhz": float(truth_rest_frequency_mhz),
        "truth_frequency_index": truth_index,
        "mean_absolute_drift_hz_s": float(np.mean(np.abs(drift_hz_s))),
        "max_absolute_drift_hz_s": float(np.max(np.abs(drift_hz_s))),
        "mean_bins_swept_per_integration": float(np.mean(np.abs(sweep_channels))),
        "max_bins_swept_per_integration": float(np.max(np.abs(sweep_channels))),
        "subintegrations": int(subintegrations),
        "response_model": "time-averaged sinc-squared channel power",
    }
    return vector, diagnostics

