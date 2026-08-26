#!/usr/bin/env python3
"""Certify the prospective M37 v0.6 bank without reading spectral data.

The proof is specific to the direct multiplicative track contract

    P_v_i(q) = q * F_v_i

and includes the finite proxy-carrier lattice.  It deliberately does not
implement or freeze detector v0.6 and never opens a remote telescope object.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np
from astropy.time import Time

from seti_repeater.orbit import (
    AU_M,
    C_M_S,
    DAY_S,
    celestial_frequency_factor,
    make_location,
    make_target,
)
from seti_repeater.search import make_subsets
from seti_repeater.spectral import validate_widths


UPSTREAM_CONFIG = Path("config/hd156668b_m37_preflight.json")
SOURCE_PATHS = {
    "continuous_preflight_config": UPSTREAM_CONFIG,
    "continuous_preflight_result": Path("results_m37_preflight/coverage.json"),
    "continuous_preflight_provenance": Path(
        "MILESTONE_37_COVERAGE_PREFLIGHT_PROVENANCE.json"
    ),
    "continuous_preflight_manifest": Path(
        "RESULTS_MANIFEST_M37_COVERAGE_PREFLIGHT.sha256"
    ),
    "continuous_preflight_plan": Path("MILESTONE_37_COVERAGE_PREFLIGHT_PLAN.md"),
    "continuous_preflight_script": Path("scripts/m37_coverage_preflight.py"),
    "orbit_module": Path("src/seti_repeater/orbit.py"),
    "search_module": Path("src/seti_repeater/search.py"),
    "spectral_module": Path("src/seti_repeater/spectral.py"),
}


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} changed: {actual!r} != {expected!r}")


def require_frozen_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a frozen lowercase SHA-256 digest")
    return value


def verify_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    expected = config["project"]["source_hashes"]
    require_equal(set(expected), set(SOURCE_PATHS), "source-hash inventory")
    observed = {name: sha256(path) for name, path in SOURCE_PATHS.items()}
    for name in sorted(expected):
        require_equal(observed[name], expected[name], f"source hash {name}")
    return observed


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def integration_times(upstream: dict[str, Any]) -> tuple[Time, list[dict[str, Any]]]:
    values = []
    labels = []
    for scan_index, scan in enumerate(upstream["scans"]):
        header = scan["expected_header"]
        count = int(header["dataset_shape"][0])
        times = Time(
            float(header["tstart_mjd"])
            + (np.arange(count) + 0.5) * float(header["tsamp_s"]) / DAY_S,
            format="mjd",
            scale="utc",
        )
        values.extend(times)
        labels.extend(
            {
                "scan_index": scan_index,
                "scan_label": scan["label"],
                "integration_index": integration_index,
            }
            for integration_index in range(count)
        )
    return Time(values), labels


def factor_basis(
    upstream: dict[str, Any],
) -> tuple[Time, list[dict[str, Any]], np.ndarray, np.ndarray, str]:
    times, labels = integration_times(upstream)
    target = make_target(upstream["target"])
    location = make_location(upstream["observatory"])
    baseline = celestial_frequency_factor(
        times, 0.0, 0.0, target, location, upstream["orbit"]
    )[0]
    phase_zero = celestial_frequency_factor(
        times, 1.0, 0.0, target, location, upstream["orbit"]
    )[0]
    phase_quarter = celestial_frequency_factor(
        times, 1.0, 0.25, target, location, upstream["orbit"]
    )[0]
    orbital = np.column_stack(
        (phase_zero - baseline, phase_quarter - baseline)
    )
    payload = b"".join(
        np.ascontiguousarray(item, dtype="<f8").tobytes()
        for item in (times.utc.mjd, baseline, orbital)
    )
    return times, labels, baseline, orbital, hashlib.sha256(payload).hexdigest()


def bank_direction(config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    bank = config["template_bank"]
    direction = np.array(
        [float(bank["direction_x"]), float(bank["direction_y"])],
        dtype=np.float64,
    )
    norm = float(np.linalg.norm(direction))
    if abs(norm - 1.0) > 2e-15:
        raise ValueError(f"bank direction is not unit length: {norm}")
    direction /= norm
    perpendicular = np.array([-direction[1], direction[0]], dtype=np.float64)
    phase = math.atan2(direction[1], direction[0]) / (2.0 * math.pi) % 1.0
    if abs(phase - float(bank["direction_phase_cycles"])) > 2e-15:
        raise ValueError("bank direction phase changed")
    return direction, perpendicular


def make_bank(config: dict[str, Any]) -> list[dict[str, Any]]:
    bank = config["template_bank"]
    count = int(bank["selected_odd_count"])
    if count % 2 != 1:
        raise ValueError("the centered bank count must be odd")
    half = (count - 1) // 2
    require_equal(bank["index_min"], -half, "bank minimum line index")
    require_equal(bank["index_max"], half, "bank maximum line index")
    direction, _ = bank_direction(config)
    line_indices = [0] + [value for m in range(1, half + 1) for value in (m, -m)]
    records = []
    base_phase = float(bank["direction_phase_cycles"])
    for template_index, line_index in enumerate(line_indices):
        coefficient = 2.0 * line_index / count
        vector = coefficient * direction
        records.append(
            {
                "template_index": template_index,
                "line_index": line_index,
                "line_coefficient": coefficient,
                "coefficient_x": float(vector[0]),
                "coefficient_y": float(vector[1]),
                "projected_scale": abs(coefficient),
                "phase_cycles": (
                    0.0
                    if line_index == 0
                    else base_phase if line_index > 0 else (base_phase + 0.5) % 1.0
                ),
            }
        )
    require_equal(len(records), count, "template count")
    require_equal(len({item["line_index"] for item in records}), count, "line IDs")
    return records


def bank_sha256(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(records)).hexdigest()


def _maximum_linear_on_disk_strip(
    along: np.ndarray,
    across: np.ndarray,
    lower: float,
    upper: float,
) -> np.ndarray:
    """Maximize along*x + across*y on x^2+y^2<=1, lower<=x<=upper."""
    norm = np.hypot(along, across)
    unconstrained_x = np.divide(
        along,
        norm,
        out=np.zeros_like(along, dtype=np.float64),
        where=norm != 0.0,
    )
    result = np.where(
        (unconstrained_x >= lower) & (unconstrained_x <= upper),
        norm,
        -np.inf,
    )
    for boundary in (lower, upper):
        vertical = math.sqrt(max(0.0, 1.0 - boundary * boundary))
        result = np.maximum(
            result,
            along * boundary + np.abs(across) * vertical,
        )
    return np.where(norm == 0.0, 0.0, result)


def linear_extrema_on_disk_strip(
    constant: np.ndarray,
    along: np.ndarray,
    across: np.ndarray,
    lower: float,
    upper: float,
) -> tuple[np.ndarray, np.ndarray]:
    maximum = _maximum_linear_on_disk_strip(along, across, lower, upper)
    minimum = -_maximum_linear_on_disk_strip(-along, -across, lower, upper)
    return constant + minimum, constant + maximum


def certify_odd_bank(
    count: int,
    center_hz: float,
    physical_half_width_hz: float,
    error_budget_hz: float,
    baseline: np.ndarray,
    orbital: np.ndarray,
    direction: np.ndarray,
    perpendicular: np.ndarray,
) -> dict[str, Any]:
    """Exact analytic strip extrema for the direct q*F_v track family.

    For a fixed template v and truth u, define r_i=f*F_u_i/F_v_i.  The
    feasible proxy-carrier interval is

        [max_i(r_i-E/F_v_i), min_i(r_i+E/F_v_i)].

    Pairwise interval margins are affine in u inside each Voronoi disk strip.
    Their extrema are therefore attained at the unconstrained disk support
    point or one of the two strip boundaries, all evaluated below.
    """
    if count % 2 != 1:
        raise ValueError("only centered odd line banks are certified here")
    f_low = center_hz - physical_half_width_hz
    f_high = center_hz + physical_half_width_hz
    half = (count - 1) // 2
    minimum_interval_width = math.inf
    maximum_lower = -math.inf
    minimum_upper = math.inf
    maximum_half_pair_range = -math.inf
    worst: dict[str, Any] | None = None
    extrema_checks = 0

    for line_index in range(-half, half + 1):
        coefficient = 2.0 * line_index / count
        lower = max(-1.0, (2.0 * line_index - 1.0) / count)
        upper = min(1.0, (2.0 * line_index + 1.0) / count)
        template_factor = baseline + orbital @ (coefficient * direction)
        if np.any(template_factor <= 0.0):
            raise AssertionError("template factor is not strictly positive")

        constant = baseline / template_factor
        vector = orbital / template_factor[:, None]
        minimum, maximum = linear_extrema_on_disk_strip(
            constant,
            vector @ direction,
            vector @ perpendicular,
            lower,
            upper,
        )
        possible = np.stack(
            (f_low * minimum, f_high * minimum, f_low * maximum, f_high * maximum)
        )
        r_minimum = np.min(possible, axis=0)
        r_maximum = np.max(possible, axis=0)
        maximum_lower = max(
            maximum_lower,
            float(np.max(r_maximum - error_budget_hz / template_factor)),
        )
        minimum_upper = min(
            minimum_upper,
            float(np.min(r_minimum + error_budget_hz / template_factor)),
        )

        pair_constant = constant[:, None] - constant[None, :]
        pair_vector = vector[:, None, :] - vector[None, :, :]
        pair_minimum, pair_maximum = linear_extrema_on_disk_strip(
            pair_constant,
            pair_vector @ direction,
            pair_vector @ perpendicular,
            lower,
            upper,
        )
        pair_possible = np.stack(
            (
                f_low * pair_minimum,
                f_high * pair_minimum,
                f_low * pair_maximum,
                f_high * pair_maximum,
            )
        )
        maximum_oriented_difference = np.max(pair_possible, axis=0)
        margins = (
            error_budget_hz / template_factor[:, None]
            + error_budget_hz / template_factor[None, :]
            - maximum_oriented_difference
        )
        np.fill_diagonal(margins, np.inf)
        flat = int(np.argmin(margins))
        local_width = float(margins.flat[flat])
        if local_width < minimum_interval_width:
            left, right = np.unravel_index(flat, margins.shape)
            minimum_interval_width = local_width
            worst = {
                "line_index": line_index,
                "strip_lower": lower,
                "strip_upper": upper,
                "left_time_index": int(left),
                "right_time_index": int(right),
                "maximum_oriented_pair_difference_hz": float(
                    maximum_oriented_difference[left, right]
                ),
                "left_template_factor": float(template_factor[left]),
                "right_template_factor": float(template_factor[right]),
            }
        maximum_half_pair_range = max(
            maximum_half_pair_range,
            float(np.max(maximum_oriented_difference) / 2.0),
        )
        extrema_checks += int(baseline.size * (baseline.size - 1))

    assert worst is not None
    return {
        "template_count": count,
        "physical_center_hz": center_hz,
        "physical_half_width_hz": physical_half_width_hz,
        "error_budget_hz": error_budget_hz,
        "voronoi_disk_strips": count,
        "ordered_time_pair_extrema_checks": extrema_checks,
        "minimum_feasible_interval_width_hz": minimum_interval_width,
        "maximum_feasible_lower_endpoint_hz": maximum_lower,
        "minimum_feasible_upper_endpoint_hz": minimum_upper,
        "maximum_half_pair_range_hz": maximum_half_pair_range,
        "worst_interval_witness": worst,
    }


def integration_endpoint_smear(
    upstream: dict[str, Any], physical_frequency_hz: float
) -> dict[str, Any]:
    target = make_target(upstream["target"])
    location = make_location(upstream["observatory"])
    maximum = -math.inf
    witness: dict[str, Any] | None = None
    evaluations = 0
    for scan in upstream["scans"]:
        header = scan["expected_header"]
        count = int(header["dataset_shape"][0])
        centers = Time(
            float(header["tstart_mjd"])
            + (np.arange(count) + 0.5) * float(header["tsamp_s"]) / DAY_S,
            format="mjd",
            scale="utc",
        )
        for endpoint_sign in (-0.5, 0.5):
            endpoints = Time(
                centers.utc.mjd
                + endpoint_sign * float(header["tsamp_s"]) / DAY_S,
                format="mjd",
                scale="utc",
            )
            joined = Time(
                np.column_stack((centers.utc.mjd, endpoints.utc.mjd)).ravel(),
                format="mjd",
                scale="utc",
            )
            baseline = celestial_frequency_factor(
                joined, 0.0, 0.0, target, location, upstream["orbit"]
            )[0].reshape(count, 2)
            phase_zero = celestial_frequency_factor(
                joined, 1.0, 0.0, target, location, upstream["orbit"]
            )[0].reshape(count, 2)
            phase_quarter = celestial_frequency_factor(
                joined, 1.0, 0.25, target, location, upstream["orbit"]
            )[0].reshape(count, 2)
            delta_baseline = baseline[:, 1] - baseline[:, 0]
            delta_orbital = np.column_stack(
                (
                    (phase_zero[:, 1] - baseline[:, 1])
                    - (phase_zero[:, 0] - baseline[:, 0]),
                    (phase_quarter[:, 1] - baseline[:, 1])
                    - (phase_quarter[:, 0] - baseline[:, 0]),
                )
            )
            envelope = physical_frequency_hz * (
                np.abs(delta_baseline) + np.linalg.norm(delta_orbital, axis=1)
            )
            index = int(np.argmax(envelope))
            value = float(envelope[index])
            if value > maximum:
                maximum = value
                witness = {
                    "scan_label": scan["label"],
                    "integration_index": index,
                    "endpoint_sign_half_integration": endpoint_sign,
                    "smear_hz": value,
                }
            evaluations += count
    assert witness is not None
    return {
        "maximum_center_to_endpoint_smear_hz": maximum,
        "physical_frequency_hz": physical_frequency_hz,
        "endpoint_evaluations": evaluations,
        "witness": witness,
    }


def continuous_integration_smear_bound(
    config: dict[str, Any],
    upstream: dict[str, Any],
    physical_frequency_hz: float,
) -> dict[str, Any]:
    """Bound center-to-any-time motion from global velocity derivatives.

    For F=(1+v_observer/c)(1-v_planet/c), the absolute derivative is bounded
    by

      a_observer/c * (1 + |v_planet|/c)
      + (1 + |v_observer|/c) * a_planet/c.

    The circular planet speed and acceleration follow exactly from the frozen
    working orbit.  The observer bounds deliberately exceed the sum of GBT
    rotational and Earth/Solar-System orbital terms; they are frozen design
    bounds rather than measurements from the selected spectra.
    """
    spectral = config["spectral_support"]
    period_s = float(upstream["orbit"]["period_days"]) * DAY_S
    circular_speed = (
        2.0
        * math.pi
        * float(upstream["orbit"]["semi_major_axis_au"])
        * AU_M
        / period_s
    )
    circular_acceleration = 2.0 * math.pi * circular_speed / period_s
    observer_acceleration = float(
        spectral["observer_radial_acceleration_bound_m_s2"]
    )
    observer_velocity = float(
        spectral["observer_radial_velocity_abs_bound_m_s"]
    )
    if observer_acceleration < 0.05:
        raise ValueError("observer acceleration bound was weakened")
    if observer_velocity < 50_000.0:
        raise ValueError("observer velocity bound was weakened")
    factor_rate = (
        observer_acceleration / C_M_S * (1.0 + circular_speed / C_M_S)
        + (1.0 + observer_velocity / C_M_S)
        * circular_acceleration
        / C_M_S
    )
    maximum_tsamp = max(
        float(scan["expected_header"]["tsamp_s"])
        for scan in upstream["scans"]
    )
    smear = physical_frequency_hz * maximum_tsamp / 2.0 * factor_rate
    return {
        "method": "global derivative bound over every integration interior",
        "physical_frequency_hz": physical_frequency_hz,
        "maximum_integration_seconds": maximum_tsamp,
        "circular_orbital_speed_m_s": circular_speed,
        "circular_orbital_acceleration_m_s2": circular_acceleration,
        "observer_radial_velocity_abs_bound_m_s": observer_velocity,
        "observer_radial_acceleration_bound_m_s2": observer_acceleration,
        "maximum_factor_rate_abs_s_inverse": factor_rate,
        "maximum_center_to_any_integration_time_smear_hz": smear,
    }


def channel_bounds(
    fch1_mhz: float,
    foff_mhz: float,
    nchans: int,
    fmin_mhz: float,
    fmax_mhz: float,
) -> tuple[int, int]:
    low_index = int(np.ceil((fmin_mhz - fch1_mhz) / foff_mhz))
    high_index = int(np.floor((fmax_mhz - fch1_mhz) / foff_mhz))
    start, stop = sorted((low_index, high_index))
    start = max(0, start)
    stop = min(nchans - 1, stop) + 1
    if start >= stop:
        raise ValueError("requested extraction is outside the HDF5 geometry")
    return start, stop


def extraction_geometry(scan: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
    header = scan["expected_header"]
    fch1 = float(header["fch1_mhz"])
    foff = float(header["foff_mhz"])
    start, stop = channel_bounds(
        fch1,
        foff,
        int(header["dataset_shape"][-1]),
        float(window["fmin_mhz"]),
        float(window["fmax_mhz"]),
    )
    endpoints = [fch1 + start * foff, fch1 + (stop - 1) * foff]
    return {
        "channel_start": start,
        "channel_stop": stop,
        "channel_count": stop - start,
        "frequency_low_mhz": min(endpoints),
        "frequency_high_mhz": max(endpoints),
        "channel_width_mhz": abs(foff),
    }


def rounded_difference_bound(delta_channels: float) -> int:
    """Bound abs(rint(x + delta) - rint(x)), including ties-to-even."""
    if not math.isfinite(delta_channels) or delta_channels < 0.0:
        raise ValueError("channel displacement must be finite and nonnegative")
    if delta_channels == 0.0:
        return 0
    return math.floor(math.nextafter(delta_channels, math.inf)) + 1


def extraction_certificate(
    config: dict[str, Any],
    upstream: dict[str, Any],
    baseline: np.ndarray,
    orbital: np.ndarray,
    labels: list[dict[str, Any]],
    direction: np.ndarray,
) -> dict[str, Any]:
    bank_count = int(config["template_bank"]["selected_odd_count"])
    bank_half = (bank_count - 1) // 2
    carrier = config["proxy_carrier_grid"]
    channel_width_hz = float(config["spectral_support"]["channel_width_hz"])
    raw_filter_radius = int(
        config["spectral_support"]["maximum_half_width_channels"]
    )
    support_half = int(carrier["support_half_bins"])
    integration_motion_margin = rounded_difference_bound(
        float(config["spectral_support"][
            "maximum_center_to_any_integration_time_smear_hz"
        ])
        / channel_width_hz
    )
    records = []
    minimum_proxy_headroom = math.inf
    minimum_proxy_native_filter_headroom = math.inf
    minimum_truth_headroom = math.inf
    minimum_truth_integration_headroom = math.inf

    for window in upstream["windows"]:
        center_hz = float(window["rest_center_mhz"]) * 1e6
        q_low = center_hz - support_half * channel_width_hz
        q_high = center_hz + support_half * channel_width_hz
        physical_low = center_hz - float(
            config["truth_domain"]["physical_frequency_half_width_hz"]
        )
        physical_high = center_hz + float(
            config["truth_domain"]["physical_frequency_half_width_hz"]
        )
        for scan_index, scan in enumerate(upstream["scans"]):
            geometry = extraction_geometry(scan, window)
            zero_hz = float(geometry["frequency_low_mhz"]) * 1e6
            native_df_hz = float(geometry["channel_width_mhz"]) * 1e6
            count = int(geometry["channel_count"])
            selected = [
                index
                for index, label in enumerate(labels)
                if int(label["scan_index"]) == scan_index
            ]
            local_baseline = baseline[selected]
            local_orbital = orbital[selected]

            proxy_minimum = math.inf
            proxy_maximum = -math.inf
            for line_index in range(-bank_half, bank_half + 1):
                factor = local_baseline + local_orbital @ (
                    2.0 * line_index / bank_count * direction
                )
                proxy_minimum = min(proxy_minimum, float(np.min(q_low * factor)))
                proxy_maximum = max(proxy_maximum, float(np.max(q_high * factor)))
            proxy_minimum_index = int(
                np.rint((proxy_minimum - zero_hz) / native_df_hz)
            )
            proxy_maximum_index = int(
                np.rint((proxy_maximum - zero_hz) / native_df_hz)
            )
            proxy_lower_headroom = proxy_minimum_index
            proxy_upper_headroom = count - 1 - proxy_maximum_index

            amplitude = np.linalg.norm(local_orbital, axis=1)
            factor_low = local_baseline - amplitude
            factor_high = local_baseline + amplitude
            truth_possible = np.stack(
                (
                    physical_low * factor_low,
                    physical_high * factor_low,
                    physical_low * factor_high,
                    physical_high * factor_high,
                )
            )
            truth_minimum = float(np.min(truth_possible))
            truth_maximum = float(np.max(truth_possible))
            truth_minimum_index = int(
                np.rint((truth_minimum - zero_hz) / native_df_hz)
            )
            truth_maximum_index = int(
                np.rint((truth_maximum - zero_hz) / native_df_hz)
            )
            truth_lower_headroom = truth_minimum_index
            truth_upper_headroom = count - 1 - truth_maximum_index
            proxy_any = min(proxy_lower_headroom, proxy_upper_headroom)
            proxy_native_filter_any = proxy_any - raw_filter_radius
            truth_any = min(truth_lower_headroom, truth_upper_headroom)
            truth_integration_any = truth_any - integration_motion_margin
            minimum_proxy_headroom = min(minimum_proxy_headroom, proxy_any)
            minimum_proxy_native_filter_headroom = min(
                minimum_proxy_native_filter_headroom,
                proxy_native_filter_any,
            )
            minimum_truth_headroom = min(minimum_truth_headroom, truth_any)
            minimum_truth_integration_headroom = min(
                minimum_truth_integration_headroom, truth_integration_any
            )
            records.append(
                {
                    "window_id": window["id"],
                    "scan_label": scan["label"],
                    "extraction_geometry": geometry,
                    "proxy_support_frequency_low_mhz": proxy_minimum / 1e6,
                    "proxy_support_frequency_high_mhz": proxy_maximum / 1e6,
                    "proxy_lower_headroom_channels": proxy_lower_headroom,
                    "proxy_upper_headroom_channels": proxy_upper_headroom,
                    "native_raw_filter_radius_channels": raw_filter_radius,
                    "proxy_support_with_native_filter_headroom_channels": (
                        proxy_native_filter_any
                    ),
                    "truth_frequency_low_mhz": truth_minimum / 1e6,
                    "truth_frequency_high_mhz": truth_maximum / 1e6,
                    "truth_lower_headroom_channels": truth_lower_headroom,
                    "truth_upper_headroom_channels": truth_upper_headroom,
                    "truth_integration_motion_margin_channels": (
                        integration_motion_margin
                    ),
                    "truth_any_integration_time_headroom_channels": (
                        truth_integration_any
                    ),
                    "passed": (
                        proxy_native_filter_any >= 1
                        and truth_integration_any >= 1
                    ),
                }
            )
    return {
        "checks": len(records),
        "score_grid_bins": int(carrier["score_bin_count"]),
        "q_support_guard_bins_each_edge": int(
            carrier["q_support_guard_bins_each_edge"]
        ),
        "support_grid_bins": int(carrier["support_bin_count"]),
        "minimum_proxy_support_headroom_channels": int(minimum_proxy_headroom),
        "native_raw_filter_radius_channels": raw_filter_radius,
        "minimum_proxy_support_with_native_filter_headroom_channels": int(
            minimum_proxy_native_filter_headroom
        ),
        "minimum_truth_headroom_channels": int(minimum_truth_headroom),
        "truth_integration_motion_margin_channels": integration_motion_margin,
        "minimum_truth_any_integration_time_headroom_channels": int(
            minimum_truth_integration_headroom
        ),
        "records": records,
        "passed": all(item["passed"] for item in records),
    }


def q_to_raw_mapping_diagnostic(
    config: dict[str, Any],
    upstream: dict[str, Any],
    baseline: np.ndarray,
    orbital: np.ndarray,
    labels: list[dict[str, Any]],
    direction: np.ndarray,
) -> dict[str, Any]:
    """Diagnose why filtering must precede q-track gathering.

    Every frozen template factor is slightly above one, so nearest-channel
    q-to-raw mappings are injective but not surjective.  A q-domain boxcar can
    therefore omit a native raw channel even when its raw-index distance is
    within the nominal radius.  The mandatory native-raw filter avoids that
    gap.  Endpoint arithmetic also verifies that the redundant q-support guard
    supplies at least one native filter radius at both extraction edges.
    """
    bank_count = int(config["template_bank"]["selected_odd_count"])
    bank_half = (bank_count - 1) // 2
    carrier = config["proxy_carrier_grid"]
    q_df_hz = float(config["spectral_support"]["channel_width_hz"])
    score_half = int(carrier["score_half_bins"])
    support_half = int(carrier["support_half_bins"])
    support_bins = int(carrier["support_bin_count"])
    raw_filter_radius = int(
        config["spectral_support"]["maximum_half_width_channels"]
    )

    minimum_factor = math.inf
    maximum_factor = -math.inf
    minimum_step_ratio = math.inf
    maximum_step_ratio = -math.inf
    minimum_skipped = math.inf
    maximum_skipped = -math.inf
    minimum_guard_margin = math.inf
    maximum_guard_margin = -math.inf
    skipped_histogram: dict[int, int] = {}
    minimum_skipped_witness: dict[str, Any] | None = None
    maximum_skipped_witness: dict[str, Any] | None = None
    evaluations = 0

    for window in upstream["windows"]:
        center_hz = float(window["rest_center_mhz"]) * 1e6
        q_support_low = center_hz - support_half * q_df_hz
        q_score_low = center_hz - score_half * q_df_hz
        q_score_high = center_hz + score_half * q_df_hz
        q_support_high = center_hz + support_half * q_df_hz
        for scan_index, scan in enumerate(upstream["scans"]):
            geometry = extraction_geometry(scan, window)
            raw_zero_hz = float(geometry["frequency_low_mhz"]) * 1e6
            raw_df_hz = float(geometry["channel_width_mhz"]) * 1e6
            selected = [
                index
                for index, label in enumerate(labels)
                if int(label["scan_index"]) == scan_index
            ]
            for time_index in selected:
                for line_index in range(-bank_half, bank_half + 1):
                    factor = float(
                        baseline[time_index]
                        + orbital[time_index]
                        @ (2.0 * line_index / bank_count * direction)
                    )
                    step_ratio = factor * q_df_hz / raw_df_hz
                    raw_indices = [
                        int(np.rint((frequency * factor - raw_zero_hz) / raw_df_hz))
                        for frequency in (
                            q_support_low,
                            q_score_low,
                            q_score_high,
                            q_support_high,
                        )
                    ]
                    mapped_span = raw_indices[3] - raw_indices[0] + 1
                    skipped = mapped_span - support_bins
                    lower_guard = raw_indices[1] - raw_indices[0]
                    upper_guard = raw_indices[3] - raw_indices[2]
                    guard_margin = min(lower_guard, upper_guard)
                    maximum_local_guard_margin = max(lower_guard, upper_guard)
                    witness = {
                        "window_id": window["id"],
                        "scan_label": scan["label"],
                        "integration_index": int(
                            labels[time_index]["integration_index"]
                        ),
                        "line_index": line_index,
                        "template_factor": factor,
                        "q_to_raw_step_ratio": step_ratio,
                        "skipped_raw_channels_over_support": skipped,
                    }
                    if skipped < minimum_skipped:
                        minimum_skipped = skipped
                        minimum_skipped_witness = witness
                    if skipped > maximum_skipped:
                        maximum_skipped = skipped
                        maximum_skipped_witness = witness
                    minimum_factor = min(minimum_factor, factor)
                    maximum_factor = max(maximum_factor, factor)
                    minimum_step_ratio = min(minimum_step_ratio, step_ratio)
                    maximum_step_ratio = max(maximum_step_ratio, step_ratio)
                    minimum_guard_margin = min(minimum_guard_margin, guard_margin)
                    maximum_guard_margin = max(
                        maximum_guard_margin, maximum_local_guard_margin
                    )
                    skipped_histogram[skipped] = skipped_histogram.get(skipped, 0) + 1
                    evaluations += 1

    assert minimum_skipped_witness is not None
    assert maximum_skipped_witness is not None
    all_injective = minimum_step_ratio > 1.0 and maximum_step_ratio < 2.0
    all_non_surjective = minimum_skipped > 0
    guard_covers_native_filter = minimum_guard_margin >= raw_filter_radius
    return {
        "mapping_evaluations": evaluations,
        "support_q_bins_per_mapping": support_bins,
        "minimum_template_factor": minimum_factor,
        "maximum_template_factor": maximum_factor,
        "minimum_q_to_raw_step_ratio": minimum_step_ratio,
        "maximum_q_to_raw_step_ratio": maximum_step_ratio,
        "all_nearest_channel_mappings_injective": all_injective,
        "all_nearest_channel_mappings_non_surjective": all_non_surjective,
        "minimum_skipped_raw_channels_over_support": int(minimum_skipped),
        "maximum_skipped_raw_channels_over_support": int(maximum_skipped),
        "skipped_raw_channel_histogram": {
            str(key): skipped_histogram[key] for key in sorted(skipped_histogram)
        },
        "minimum_skipped_witness": minimum_skipped_witness,
        "maximum_skipped_witness": maximum_skipped_witness,
        "q_domain_boxcar_permitted": False,
        "required_filter_coordinate": config["spectral_support"][
            "filter_coordinate"
        ],
        "native_raw_filter_radius_channels": raw_filter_radius,
        "minimum_native_raw_channels_supplied_by_q_support_guard": int(
            minimum_guard_margin
        ),
        "maximum_native_raw_channels_supplied_by_q_support_guard": int(
            maximum_guard_margin
        ),
        "q_support_guard_covers_native_filter_radius": guard_covers_native_filter,
        "native_filter_contract_requires_future_implementation_verification": True,
        "passed": bool(
            all_injective and all_non_surjective and guard_covers_native_filter
        ),
    }


def capacity_certificate(config: dict[str, Any]) -> dict[str, Any]:
    dimensions = config["search_dimensions"]
    bank = int(config["template_bank"]["selected_odd_count"])
    widths = len(validate_widths(config["spectral_support"]["widths_channels"]))
    subsets = make_subsets(
        int(dimensions["on_epoch_count"]),
        int(dimensions["minimum_active_epochs"]),
    )
    score_bins = int(config["proxy_carrier_grid"]["score_bin_count"])
    support_bins = int(config["proxy_carrier_grid"]["support_bin_count"])
    windows = int(dimensions["window_count"])
    scrambles = int(dimensions["scramble_count"])
    hypotheses = bank * widths * len(subsets)
    per_window = hypotheses * score_bins
    total = per_window * windows
    null_total = total * scrambles
    expected = {
        "template_count": bank,
        "spectral_width_count": widths,
        "activity_subset_count": len(subsets),
        "hypotheses_per_window": hypotheses,
        "score_cells_per_window": per_window,
        "score_cells_total": total,
        "null_score_cells_total": null_total,
    }
    for key, value in expected.items():
        require_equal(dimensions[key], value, f"search dimension {key}")

    capacity = config["retention_capacity"]
    evidence_bound = (
        int(capacity["maximum_above_threshold_records_per_window"])
        * int(capacity["maximum_record_canonical_bytes"])
        + int(capacity["maximum_clusters_per_window"])
        * int(capacity["maximum_cluster_summary_canonical_bytes"])
        + hypotheses
        * int(capacity["maximum_hypothesis_certificate_canonical_bytes"])
        + int(capacity["maximum_misc_canonical_bytes_per_window"])
    )
    if evidence_bound > int(
        capacity["maximum_retention_evidence_canonical_bytes_per_window"]
    ):
        raise ValueError("retention evidence bound exceeds its fail-closed cap")
    if int(capacity["maximum_retention_evidence_canonical_bytes_total"]) != (
        windows
        * int(capacity["maximum_retention_evidence_canonical_bytes_per_window"])
    ):
        raise ValueError("run-wide retention capacity is not five window caps")

    full_spectral_bank_bytes_per_kind = (
        widths * bank * int(dimensions["on_epoch_count"]) * score_bins * 4
    )
    core_streaming_array_bytes = (
        2 * int(dimensions["on_epoch_count"]) * support_bins * 4
        + int(dimensions["on_epoch_count"]) * score_bins
        + score_bins * 4
    )
    return {
        **expected,
        "score_cells_observed_plus_null_total": total * (scrambles + 1),
        "full_spectral_bank_bytes_per_kind_per_window": (
            full_spectral_bank_bytes_per_kind
        ),
        "core_streaming_array_bytes_per_template": core_streaming_array_bytes,
        "core_streaming_array_definition": (
            "three unfiltered q-gather float32 support vectors, three q-gather "
            "vectors obtained after native-raw filtering, one three-epoch "
            "boolean score mask, and one float32 score vector"
        ),
        "core_streaming_arrays_below_live_cap": core_streaming_array_bytes
        < int(capacity["maximum_live_ndarray_bytes"]),
        "maximum_evidence_canonical_bytes_derived_per_window": evidence_bound,
        "retention_cap_is_not_a_mathematical_record_bound": True,
        "capacity_overflow_outcome": capacity["capacity_failure_outcome"],
        "truncation_permitted": capacity["truncation_permitted"],
    }


def validate_config(config: dict[str, Any], upstream: dict[str, Any]) -> None:
    require_equal(
        config["project"]["status"],
        "metadata_only_before_spectral_contact",
        "project status",
    )
    require_equal(
        config["project"]["upstream_publication_commit"],
        "4439c9833984128b79a1dd8ac6b8151d0670fa2c",
        "upstream publication boundary",
    )
    require_equal(
        config["project"]["does_not_freeze_detector_v0p6_implementation"],
        True,
        "implementation boundary",
    )
    require_equal(
        config["project"]["does_not_authorize_spectral_access"],
        True,
        "spectral-access boundary",
    )
    require_equal(
        config["project"][
            "raw_channel_inclusion_is_conditional_on_native_filter_contract"
        ],
        True,
        "raw-channel inclusion scope",
    )
    require_equal(
        config["project"]["does_not_claim_search_sensitivity"],
        True,
        "sensitivity scope",
    )
    require_equal(upstream["orbit"]["eccentricity"], 0.0, "upstream eccentricity")
    require_equal(config["truth_domain"]["eccentricity"], 0.0, "truth eccentricity")
    require_equal(len(upstream["scans"]), 6, "scan count")
    require_equal(
        [scan["kind"] for scan in upstream["scans"]],
        ["on", "off", "on", "off", "on", "off"],
        "ABABAB order",
    )
    require_equal(len(upstream["windows"]), 5, "window count")
    truth = config["truth_domain"]
    require_equal(truth["coefficient_disk"], "x^2 + y^2 <= 1", "truth coefficient disk")
    require_equal(
        truth["physical_frequency_half_width_hz"],
        500000.0,
        "physical truth half-width",
    )
    require_equal(
        truth["time_domain"],
        "all 96 integration midpoints in the six frozen ABABAB scans",
        "truth time domain",
    )
    require_equal(
        truth["orbital_parameter_uncertainties_covered"],
        False,
        "orbit-uncertainty scope",
    )
    require_equal(
        truth["physical_frequency_scope"],
        "five frozen central one-MHz bands",
        "physical truth scope",
    )
    for window in upstream["windows"]:
        require_equal(
            float(window["rest_half_width_khz"]) * 1000.0,
            float(truth["physical_frequency_half_width_hz"]),
            f"physical truth half-width {window['id']}",
        )

    track = config["track_contract"]
    require_equal(
        track["name"],
        "direct_multiplicative_proxy_carrier",
        "track contract",
    )
    require_equal(track["formula"], "P_v_i(q) = q * F_v_i", "track formula")
    require_equal(track["truth_formula"], "Y_i(u,f) = f * F_u_i", "truth formula")
    require_equal(track["legacy_v0p5_equivalent"], False, "v0.5 equivalence")
    require_equal(
        track["carrier_restarts_between_scans"],
        False,
        "carrier restart semantics",
    )
    require_equal(
        track["proxy_carrier_is_physical_rest_frequency"],
        False,
        "proxy carrier semantics",
    )
    require_equal(track["candidate_axis_label"], "proxy_carrier_mhz", "candidate axis")
    require_equal(track["forbidden_candidate_axis_label"], "frequency_mhz", "forbidden axis")

    bank = config["template_bank"]
    require_equal(
        bank["family"],
        "centered_uniform_line_in_circular_coefficient_disk",
        "bank family",
    )
    require_equal(bank["coefficient_formula"], "v_m = (2*m/93) * direction", "bank formula")
    require_equal(
        bank["template_order"],
        "m=0, then m=+1,-1,+2,-2,...,+46,-46",
        "bank order contract",
    )
    require_equal(
        bank["assignment"],
        "nearest line coefficient with Voronoi strips clipped to the unit disk",
        "bank assignment",
    )
    require_equal(
        bank["tie_rule"],
        "larger integer line index at an exact midpoint; both adjacent closed Voronoi strips are certified",
        "bank tie rule",
    )
    require_equal(
        config["proxy_carrier_grid"]["all_score_cells_normative"],
        True,
        "normative score cells",
    )
    require_equal(
        config["proxy_carrier_grid"]["support_guard_cells_normative"],
        False,
        "q-support guard semantics",
    )
    retention = config["retention_capacity"]
    require_equal(
        retention,
        {
            "threshold_comparison": "finite score >= final calibrated threshold",
            "maximum_above_threshold_records_per_window": 10000,
            "maximum_receiver_alias_records_per_window": 10000,
            "maximum_alias_bucket_entries_per_window": 30000,
            "maximum_alias_neighbor_candidate_visits_per_window": 5000000,
            "maximum_clusters_per_window": 10000,
            "maximum_record_canonical_bytes": 6144,
            "maximum_cluster_summary_canonical_bytes": 2048,
            "maximum_hypothesis_certificate_canonical_bytes": 1024,
            "maximum_misc_canonical_bytes_per_window": 5000000,
            "maximum_retention_evidence_canonical_bytes_per_window": 96000000,
            "maximum_retention_evidence_canonical_bytes_total": 480000000,
            "maximum_single_compressed_output_file_bytes": 95000000,
            "maximum_live_ndarray_bytes": 536870912,
            "truncation_permitted": False,
            "threshold_adaptation_permitted": False,
            "capacity_failure_outcome": "M37_INVALID_NO_CONCLUSION",
        },
        "retention capacity contract",
    )
    require_equal(
        retention["capacity_failure_outcome"],
        config["outcomes"]["invalid"],
        "capacity failure outcome",
    )
    require_equal(
        config["outcomes"],
        {
            "closed": "PRIMARY_CADENCE_NULL_AFTER_COMPLETE_V0P6_RETENTION",
            "open": "UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE",
            "invalid": "M37_INVALID_NO_CONCLUSION",
        },
        "outcome vocabulary",
    )
    require_equal(
        config["streaming_contract"],
        {
            "full_template_bank_materialization_permitted": False,
            "template_at_a_time": True,
            "width_at_a_time": True,
            "native_raw_filter_before_q_gather": True,
            "q_domain_boxcar_permitted": False,
            "raw_filter_then_q_gather_then_crop_support_guard": True,
            "two_pass_mask_then_score": True,
            "calibration_before_retention": True,
            "complete_threshold_replay_required": True,
            "nms_is_normative": False,
            "clustering_is_normative": False,
            "member_level_disposition_required": True,
            "atomic_final_publication_required": True,
        },
        "streaming contract",
    )

    spectral = config["spectral_support"]
    widths = validate_widths(spectral["widths_channels"])
    require_equal(widths, (1, 3, 5, 9, 17, 33, 65, 129), "width bank")
    require_equal(max(widths), spectral["maximum_width_channels"], "maximum width")
    require_equal(max(widths) // 2, spectral["maximum_half_width_channels"], "half width")
    require_equal(
        spectral["composed_nearest_channel_reserve_channels"],
        2,
        "nearest-channel reserve",
    )
    require_equal(
        spectral["observer_radial_acceleration_bound_m_s2"],
        0.05,
        "observer acceleration design bound",
    )
    require_equal(
        spectral["observer_radial_velocity_abs_bound_m_s"],
        50000.0,
        "observer velocity design bound",
    )
    require_equal(
        spectral["observer_motion_bounds_are_frozen_design_assumptions"],
        True,
        "observer-bound semantics",
    )
    require_equal(spectral["numeric_outward_guard_hz"], 0.01, "numeric guard")
    require_equal(
        spectral["floating_point_roundoff_operation_budget"],
        4096,
        "roundoff operation budget",
    )
    require_equal(
        spectral["q_to_raw_nearest_channel_mapping_surjectivity_assumed"],
        False,
        "q-to-raw surjectivity assumption",
    )
    require_equal(
        spectral["filter_coordinate"],
        "native_raw_channel_axis_before_q_track_gather",
        "spectral filter coordinate",
    )
    require_equal(
        spectral["q_domain_boxcar_permitted"],
        False,
        "q-domain boxcar contract",
    )
    require_equal(
        spectral["native_filter_contract_requires_future_implementation_verification"],
        True,
        "native-filter implementation gate",
    )
    channel_widths = {
        abs(float(scan["expected_header"]["foff_mhz"])) * 1e6
        for scan in upstream["scans"]
    }
    require_equal(len(channel_widths), 1, "native channel-width count")
    require_equal(channel_widths.pop(), spectral["channel_width_hz"], "channel width")

    carrier = config["proxy_carrier_grid"]
    require_equal(carrier["nuisance_recenter_guard_hz"], 560000.0, "q-grid guard")
    require_equal(
        carrier["grid_formula"],
        "q[k] = window_center_hz + k * channel_width_hz",
        "q-grid formula",
    )
    require_equal(
        float(carrier["physical_plus_guard_half_width_hz"]),
        float(truth["physical_frequency_half_width_hz"])
        + float(carrier["nuisance_recenter_guard_hz"]),
        "q-grid physical-plus-guard half-width",
    )
    required_half = float(carrier["physical_plus_guard_half_width_hz"])
    calculated_half_bins = math.ceil(required_half / float(spectral["channel_width_hz"]))
    require_equal(calculated_half_bins, carrier["score_half_bins"], "score half bins")
    require_equal(2 * calculated_half_bins + 1, carrier["score_bin_count"], "score bins")
    support_guard = int(carrier["q_support_guard_bins_each_edge"])
    require_equal(
        support_guard,
        spectral["maximum_half_width_channels"],
        "q-support guard",
    )
    require_equal(
        calculated_half_bins + support_guard,
        carrier["support_half_bins"],
        "support half bins",
    )
    require_equal(
        2 * (calculated_half_bins + support_guard) + 1,
        carrier["support_bin_count"],
        "support bins",
    )
    require_equal(
        carrier["score_index_domain"],
        "-373832 <= k <= 373832",
        "score-index domain",
    )
    require_equal(
        carrier["support_index_domain"],
        "-373896 <= k <= 373896",
        "support-index domain",
    )

    dimensions = config["search_dimensions"]
    require_equal(dimensions["window_count"], len(upstream["windows"]), "dimension windows")
    require_equal(dimensions["on_epoch_count"], 3, "dimension ON epochs")
    require_equal(dimensions["minimum_active_epochs"], 2, "dimension active epochs")
    require_equal(dimensions["scramble_count"], 256, "dimension scrambles")


def check_config(config: dict[str, Any]) -> dict[str, Any]:
    source_hashes = verify_source_hashes(config)
    upstream = load_json(UPSTREAM_CONFIG)
    validate_config(config, upstream)
    times, labels, baseline, orbital, basis_hash = factor_basis(upstream)
    require_equal(len(times), 96, "integration midpoint count")
    direction, perpendicular = bank_direction(config)
    bank = make_bank(config)
    bank_hash = bank_sha256(bank)
    expected_bank_hash = require_frozen_sha256(
        config["template_bank"]["expected_bank_sha256"], "bank hash"
    )
    expected_basis_hash = require_frozen_sha256(
        config["template_bank"]["expected_factor_basis_sha256"],
        "factor-basis hash",
    )
    require_equal(bank_hash, expected_bank_hash, "bank hash")
    require_equal(basis_hash, expected_basis_hash, "factor-basis hash")

    # Direct orbit evaluations are checked against the frozen linear circular
    # basis.  This is diagnostic only; the prospective v0.6 kernel will use the
    # explicit coefficient basis rather than phase arithmetic at large BJD.
    target = make_target(upstream["target"])
    location = make_location(upstream["observatory"])
    maximum_basis_residual = 0.0
    for scale in (0.0, 0.37, 1.0):
        for phase in (0.0, 0.137, 0.25, 0.3638531880461531, 0.75):
            vector = scale * np.array(
                [math.cos(2.0 * math.pi * phase), math.sin(2.0 * math.pi * phase)]
            )
            constructed = baseline + orbital @ vector
            direct = celestial_frequency_factor(
                times, scale, phase, target, location, upstream["orbit"]
            )[0]
            maximum_basis_residual = max(
                maximum_basis_residual,
                float(np.max(np.abs(direct - constructed))),
            )
    if maximum_basis_residual > 2e-12:
        raise AssertionError("circular factor basis no longer reconstructs the orbit")

    maximum_physical_frequency = max(
        float(window["rest_center_mhz"]) * 1e6
        + float(config["truth_domain"]["physical_frequency_half_width_hz"])
        for window in upstream["windows"]
    )
    endpoint_diagnostic = integration_endpoint_smear(
        upstream, maximum_physical_frequency
    )
    smear = continuous_integration_smear_bound(
        config, upstream, maximum_physical_frequency
    )
    spectral = config["spectral_support"]
    require_equal(
        endpoint_diagnostic["maximum_center_to_endpoint_smear_hz"],
        spectral["sampled_endpoint_diagnostic_hz"],
        "sampled endpoint diagnostic",
    )
    require_equal(
        smear["maximum_center_to_any_integration_time_smear_hz"],
        spectral["maximum_center_to_any_integration_time_smear_hz"],
        "continuous integration smear bound",
    )
    if (
        smear["maximum_center_to_any_integration_time_smear_hz"]
        < endpoint_diagnostic["maximum_center_to_endpoint_smear_hz"]
    ):
        raise AssertionError("continuous smear bound does not dominate endpoints")
    derived_error_budget = (
        int(spectral["maximum_half_width_channels"])
        - int(spectral["composed_nearest_channel_reserve_channels"])
    ) * float(spectral["channel_width_hz"]) - float(
        smear["maximum_center_to_any_integration_time_smear_hz"]
    )
    require_equal(
        derived_error_budget,
        spectral["center_track_error_budget_hz"],
        "center-track error budget",
    )

    numeric_guard = float(spectral["numeric_outward_guard_hz"])
    roundoff_operation_budget = int(
        spectral["floating_point_roundoff_operation_budget"]
    )
    minimum_factor = float(np.min(baseline - np.linalg.norm(orbital, axis=1)))
    if minimum_factor <= 0.0:
        raise AssertionError("continuous truth-factor envelope is not positive")
    numeric_error_bound = (
        roundoff_operation_budget
        * np.finfo(np.float64).eps
        * maximum_physical_frequency
        / minimum_factor**2
        + maximum_basis_residual * maximum_physical_frequency
    )
    if 2.0 * numeric_error_bound >= numeric_guard:
        raise AssertionError(
            "numeric guard does not dominate both endpoint-error envelopes"
        )
    channel_width_hz = float(spectral["channel_width_hz"])
    physical_half = float(config["truth_domain"]["physical_frequency_half_width_hz"])
    selected_count = int(config["template_bank"]["selected_odd_count"])
    evaluated_counts = [int(value) for value in config["template_bank"]["evaluated_odd_counts"]]
    require_equal(evaluated_counts, [89, 91, 93], "evaluated odd-bank counts")
    require_equal(selected_count, 93, "selected bank count")

    center_track_rint_bound = rounded_difference_bound(
        derived_error_budget / channel_width_hz
    )
    integration_motion_rint_bound = rounded_difference_bound(
        smear["maximum_center_to_any_integration_time_smear_hz"]
        / channel_width_hz
    )
    if center_track_rint_bound + integration_motion_rint_bound > int(
        spectral["maximum_half_width_channels"]
    ):
        raise AssertionError("composed nearest-channel bounds exceed width-129 radius")

    records = []
    diagnostics: dict[str, list[dict[str, Any]]] = {
        str(count): [] for count in evaluated_counts if count < selected_count
    }
    carrier = config["proxy_carrier_grid"]
    score_half = int(carrier["score_half_bins"])
    grid_extent_hz = score_half * channel_width_hz
    for window in upstream["windows"]:
        center_hz = float(window["rest_center_mhz"]) * 1e6
        selected = certify_odd_bank(
            selected_count,
            center_hz,
            physical_half,
            derived_error_budget,
            baseline,
            orbital,
            direction,
            perpendicular,
        )
        selected["window_id"] = window["id"]
        selected["guarded_minimum_feasible_interval_width_hz"] = (
            selected["minimum_feasible_interval_width_hz"] - 2.0 * numeric_guard
        )
        selected["lattice_spacing_hz"] = channel_width_hz
        selected["lattice_point_guaranteed"] = (
            selected["guarded_minimum_feasible_interval_width_hz"]
            >= channel_width_hz
        )
        selected["proxy_grid_low_hz"] = center_hz - grid_extent_hz
        selected["proxy_grid_high_hz"] = center_hz + grid_extent_hz
        selected["guarded_maximum_lower_endpoint_hz"] = (
            selected["maximum_feasible_lower_endpoint_hz"] + numeric_guard
        )
        selected["guarded_minimum_upper_endpoint_hz"] = (
            selected["minimum_feasible_upper_endpoint_hz"] - numeric_guard
        )
        selected["finite_grid_containment_guaranteed"] = (
            selected["guarded_maximum_lower_endpoint_hz"]
            <= selected["proxy_grid_high_hz"]
            and selected["guarded_minimum_upper_endpoint_hz"]
            >= selected["proxy_grid_low_hz"]
        )
        selected["passed"] = bool(
            selected["lattice_point_guaranteed"]
            and selected["finite_grid_containment_guaranteed"]
        )
        records.append(selected)

        for diagnostic_count in evaluated_counts:
            if diagnostic_count >= selected_count:
                continue
            diagnostic = certify_odd_bank(
                diagnostic_count,
                center_hz,
                physical_half,
                derived_error_budget,
                baseline,
                orbital,
                direction,
                perpendicular,
            )
            diagnostic["window_id"] = window["id"]
            diagnostic["guarded_minimum_feasible_interval_width_hz"] = (
                diagnostic["minimum_feasible_interval_width_hz"]
                - 2.0 * numeric_guard
            )
            diagnostic["lattice_spacing_hz"] = channel_width_hz
            diagnostic["certified_for_discrete_lattice"] = (
                diagnostic["guarded_minimum_feasible_interval_width_hz"]
                >= channel_width_hz
            )
            diagnostics[str(diagnostic_count)].append(diagnostic)

    extraction = extraction_certificate(
        config, upstream, baseline, orbital, labels, direction
    )
    raw_mapping = q_to_raw_mapping_diagnostic(
        config, upstream, baseline, orbital, labels, direction
    )
    capacity = capacity_certificate(config)
    selected_passed = all(item["passed"] for item in records)
    all_smaller_counts_fail = all(
        any(not item["certified_for_discrete_lattice"] for item in items)
        for items in diagnostics.values()
    )
    all_passed = (
        selected_passed
        and all_smaller_counts_fail
        and extraction["passed"]
        and raw_mapping["passed"]
        and capacity["core_streaming_arrays_below_live_cap"]
    )
    return {
        "purpose": "M37 metadata-only detector-v0.6 discrete bank and capacity preflight",
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "remote_files_opened": False,
        "telescope_remote_request_made": False,
        "network_access_required": False,
        "detector_v0p6_implementation_frozen": False,
        "spectral_access_authorized": False,
        "search_sensitivity_claimed": False,
        "native_raw_filter_implementation_verified": False,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "astropy": importlib.metadata.version("astropy"),
            "astropy_iers_data": importlib.metadata.version("astropy-iers-data"),
            "pyerfa": importlib.metadata.version("pyerfa"),
        },
        "source_hashes": source_hashes,
        "passed": bool(all_passed),
        "factor_basis": {
            "integration_midpoints": len(times),
            "scan_count": len(upstream["scans"]),
            "basis_sha256": basis_hash,
            "maximum_direct_orbit_reconstruction_residual": maximum_basis_residual,
            "minimum_baseline_factor": float(np.min(baseline)),
            "maximum_baseline_factor": float(np.max(baseline)),
        },
        "template_bank": {
            "count": len(bank),
            "canonical_sha256": bank_hash,
            "direction": direction.tolist(),
            "perpendicular": perpendicular.tolist(),
            "order": config["template_bank"]["template_order"],
            "records": bank,
        },
        "spectral_budget": {
            "maximum_width_channels": spectral["maximum_width_channels"],
            "half_width_channels": spectral["maximum_half_width_channels"],
            "composed_nearest_channel_reserve_channels": spectral[
                "composed_nearest_channel_reserve_channels"
            ],
            "reserve_derivation": spectral["reserve_derivation"],
            "channel_width_hz": channel_width_hz,
            "sampled_endpoint_diagnostic": endpoint_diagnostic,
            "continuous_integration_smear_bound": smear,
            "center_track_error_budget_hz": derived_error_budget,
            "numeric_outward_guard_hz": numeric_guard,
            "floating_point_roundoff_operation_budget": roundoff_operation_budget,
            "derived_numeric_error_bound_hz": numeric_error_bound,
            "twice_derived_numeric_error_bound_hz": 2.0 * numeric_error_bound,
            "numeric_guard_dominates_error_bound": True,
            "center_track_rint_bound_channels": center_track_rint_bound,
            "integration_motion_rint_bound_channels": (
                integration_motion_rint_bound
            ),
            "composed_rint_bound_channels": (
                center_track_rint_bound + integration_motion_rint_bound
            ),
            "composed_rint_bound_within_filter_radius": True,
            "filter_coordinate": spectral["filter_coordinate"],
            "q_domain_boxcar_permitted": False,
            "raw_channel_inclusion_geometry_certified": True,
            "native_filter_contract_requires_future_implementation_verification": True,
        },
        "selected_93_template_discrete_cover": {
            "track_contract": config["track_contract"]["formula"],
            "truth_contract": config["track_contract"]["truth_formula"],
            "coefficient_domain": config["truth_domain"]["coefficient_disk"],
            "physical_frequency_half_width_hz": physical_half,
            "proof": (
                "exact support-function extrema on every clipped Voronoi disk "
                "strip; interval length at least one q-lattice spacing plus "
                "finite endpoint containment, after a frozen outward guard"
            ),
            "records": records,
            "minimum_guarded_interval_width_hz": min(
                item["guarded_minimum_feasible_interval_width_hz"]
                for item in records
            ),
            "minimum_interval_excess_over_lattice_hz": min(
                item["guarded_minimum_feasible_interval_width_hz"]
                - channel_width_hz
                for item in records
            ),
            "minimum_upper_grid_headroom_hz": min(
                item["proxy_grid_high_hz"]
                - item["guarded_maximum_lower_endpoint_hz"]
                for item in records
            ),
            "minimum_lower_grid_headroom_hz": min(
                item["guarded_minimum_upper_endpoint_hz"]
                - item["proxy_grid_low_hz"]
                for item in records
            ),
            "passed": selected_passed,
        },
        "smaller_bank_discrete_lattice_diagnostics": {
            "is_normative": False,
            "reason": (
                "each evaluated smaller uniform-line bank fails to guarantee "
                "one discrete q-lattice spacing in at least one window under "
                "the same production q*F_v contract"
            ),
            "evaluated_counts": [int(key) for key in diagnostics],
            "records_by_count": diagnostics,
            "all_smaller_counts_fail_at_least_one_window": (
                all_smaller_counts_fail
            ),
        },
        "proxy_carrier_semantics": {
            "axis_label": config["track_contract"]["candidate_axis_label"],
            "is_physical_rest_frequency": False,
            "score_half_bins": carrier["score_half_bins"],
            "score_bin_count": carrier["score_bin_count"],
            "q_support_guard_bins_each_edge": carrier[
                "q_support_guard_bins_each_edge"
            ],
            "support_bin_count": carrier["support_bin_count"],
            "all_widened_score_cells_enter_observed_null_and_retention": True,
            "support_guard_cells_are_cropped_before_scoring": True,
            "scope_note": carrier["scope_note"],
        },
        "extraction_coverage": extraction,
        "q_to_raw_mapping_diagnostic": raw_mapping,
        "capacity": capacity,
        "remaining_gates": [
            "implement native-raw width filtering before direct q*F_v gathering beside unchanged detector v0.5, with q-domain boxcars forbidden",
            "prove streaming output bitwise equal to a materialized reference",
            "freeze scramble shifts, OFF track-distance semantics, completeness, and seeds",
            "benchmark exact-grid memory and throughput under the live-array cap",
            "publish and verify the complete detector-v0.6 preregistration before spectral access",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_json(args.config)
    result = check_config(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "templates": result["template_bank"]["count"],
                "score_bins": result["proxy_carrier_semantics"]["score_bin_count"],
                "minimum_discrete_interval_excess_hz": result[
                    "selected_93_template_discrete_cover"
                ]["minimum_interval_excess_over_lattice_hz"],
                "minimum_proxy_extraction_headroom_channels": result[
                    "extraction_coverage"
                ]["minimum_proxy_support_headroom_channels"],
                "score_cells_total": result["capacity"]["score_cells_total"],
            },
            indent=2,
        ),
        flush=True,
    )
    if not result["passed"]:
        raise SystemExit("M37 v0.6 bank preflight failed")


if __name__ == "__main__":
    main()
