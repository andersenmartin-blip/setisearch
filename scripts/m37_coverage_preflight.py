#!/usr/bin/env python3
"""Prove M37 extraction coverage from frozen metadata only.

The normative guard covers every circular-orbit phase and every projected
scale in [0, 1]. A previously frozen 21-template bank is replayed only as a
non-normative regression. This program opens no remote object and reads no
spectral sample.
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
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from seti_repeater.orbit import (
    AU_M,
    C_M_S,
    DAY_S,
    celestial_frequency_factor,
    make_location,
    make_target,
)
from seti_repeater.search import make_rest_grid, make_subsets
from seti_repeater.spectral import validate_widths


LEGACY_TEMPLATES = tuple(
    [(0.0, 0.0)]
    + [
        (scale, phase)
        for scale in (0.25, 0.5, 0.75, 1.0)
        for phase in (-0.2, -0.1, 0.0, 0.1, 0.2)
    ]
)
LEGACY_WIDTHS = (1, 3, 5, 9, 17, 33, 65, 129)
SOURCE_PATHS = {
    "target_selection": Path("MILESTONE_37_TARGET_SELECTION.md"),
    "selected_metadata": Path("results_m37_selected_metadata/hd156668b.json"),
    "selected_metadata_manifest": Path(
        "RESULTS_MANIFEST_M37_SELECTED_METADATA.sha256"
    ),
    "selected_metadata_provenance": Path(
        "MILESTONE_37_SELECTED_METADATA_PROVENANCE.json"
    ),
    "header_screen": Path("results_m36_header_screen/header_screen.json"),
    "header_screen_manifest": Path("RESULTS_MANIFEST_M36_HEADER_SCREEN.sha256"),
    "discovery": Path("results_m16_discovery/discovery.json"),
    "milestone_36_verification_receipt": Path(
        "MILESTONE_36_PUBLICATION_VERIFICATION.json"
    ),
    "legacy_m36_preflight_config": Path("config/hip48714b_m36_preflight.json"),
    "orbit_module": Path("src/seti_repeater/orbit.py"),
    "search_module": Path("src/seti_repeater/search.py"),
    "hdf5_extractor": Path("scripts/m13_hdf5_extract.py"),
}


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} changed: {actual!r} != {expected!r}")


def validate_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    expected = config["project"]["source_hashes"]
    if set(expected) != set(SOURCE_PATHS):
        raise ValueError("M37 source-hash inventory changed")
    actual = {name: sha256(path) for name, path in SOURCE_PATHS.items()}
    for name in sorted(expected):
        require_equal(actual[name], expected[name], f"source hash {name}")
    return actual


def validate_selected_metadata(config: dict[str, Any]) -> None:
    selected = load_json(SOURCE_PATHS["selected_metadata"])
    provenance = load_json(SOURCE_PATHS["selected_metadata_provenance"])
    record = selected["record"]
    target = config["target"]
    orbit = config["orbit"]

    for flag in (
        "spectral_payload_inspected",
        "spectral_dataset_values_read",
        "telescope_remote_request_made",
    ):
        require_equal(selected[flag], False, f"selected metadata {flag}")
        require_equal(provenance[flag], False, f"selected provenance {flag}")
    require_equal(provenance["github_run_id"], 33007853035, "metadata run")
    require_equal(provenance["artifact_id"], 9621276239, "metadata artifact")
    require_equal(
        provenance["artifact_digest"],
        "785fb05c22c20777d26a5367a3a8e9ceb9c135cd1b3c306b57462df67eed1d61",
        "metadata artifact digest",
    )
    require_equal(
        provenance["source_commit"],
        "c37c828a88ddc7a30a49a3f8d5c5d93371f2ad34",
        "metadata source commit",
    )
    require_equal(
        config["project"]["selected_metadata_result_commit"],
        "269c213f256a48bc7f76ae042b98eaa85bf76008",
        "selected-metadata result boundary",
    )

    pairs = {
        "ra": (target["ra"], record["rastr"]),
        "dec": (target["dec"], record["decstr"]),
        "ra_deg": (target["ra_deg"], record["ra"]),
        "dec_deg": (target["dec_deg"], record["dec"]),
        "distance_pc": (target["distance_pc"], record["sy_dist"]),
        "parallax_mas": (target["parallax_mas"], record["sy_plx"]),
        "pm_ra_cosdec_mas_yr": (
            target["pm_ra_cosdec_mas_yr"],
            record["sy_pmra"],
        ),
        "pm_dec_mas_yr": (target["pm_dec_mas_yr"], record["sy_pmdec"]),
        "radial_velocity_km_s": (
            target["radial_velocity_km_s"],
            record["st_radv"],
        ),
        "period_days": (orbit["period_days"], record["pl_orbper"]),
        "semi_major_axis_au": (
            orbit["semi_major_axis_au"],
            record["pl_orbsmax"],
        ),
        "eccentricity": (orbit["eccentricity"], record["pl_orbeccen"]),
        "t_periastron_bjd_tdb": (
            orbit["t_periastron_bjd_tdb"],
            record["pl_orbtper"],
        ),
        "omega_rad": (
            orbit["omega_rad"],
            math.radians(record["pl_orblper"]),
        ),
    }
    for label, (actual, expected) in pairs.items():
        require_equal(actual, expected, f"official metadata {label}")
    require_equal(record["pl_name"], "HD 156668 b", "planet identity")
    require_equal(record["hostname"], "HD 156668", "host identity")
    require_equal(record["hip_name"], "HIP 84607", "HIP identity")
    require_equal(target["name"], "HIP 84607", "configured target identity")


def rank37_headers() -> list[dict[str, Any]]:
    screen = load_json(SOURCE_PATHS["header_screen"])
    require_equal(screen["spectral_payload_inspected"], False, "header flag")
    require_equal(
        screen["spectral_dataset_values_read"], False, "header value-read flag"
    )
    targets = {item["rank"]: item for item in screen["screened_targets"]}
    require_equal(sorted(targets), [36, 37, 38, 39, 40], "screened ranks")
    target = targets[37]
    require_equal(target["archive_target"], "HIP84607", "rank-37 target")
    require_equal(target["planet_name"], "HD 156668 b", "rank-37 planet")
    require_equal(target["qualifying_count"], 1, "rank-37 cadence count")
    require_equal(len(target["cadences"]), 1, "rank-37 catalogue cadence count")
    cadence = target["cadences"][0]
    qualified = cadence["qualifying_hdf5_abacad_cadences"]
    require_equal(len(qualified), 1, "rank-37 qualified cadence count")
    require_equal(
        cadence["cadence_url"].rsplit("/", 1)[-1],
        "--85168",
        "rank-37 cadence",
    )
    headers = qualified[0]["headers"]
    require_equal(cadence["hdf5_headers"], headers, "duplicated header ledger")
    require_equal(len(headers), 6, "rank-37 header count")
    return headers


def validate_scan_headers(config: dict[str, Any]) -> None:
    headers = rank37_headers()
    scans = config["scans"]
    require_equal(len(scans), 6, "configured scan count")
    require_equal(
        [(scan["epoch"], scan["kind"], scan["label"]) for scan in scans],
        [
            (1, "on", "epoch1_on"),
            (1, "off", "epoch1_off"),
            (2, "on", "epoch2_on"),
            (2, "off", "epoch2_off"),
            (3, "on", "epoch3_on"),
            (3, "off", "epoch3_off"),
        ],
        "ABABAB scan order",
    )
    require_equal(len({scan["url"] for scan in scans}), 6, "unique scan URLs")

    for scan, published in zip(scans, headers, strict=True):
        expected = scan["expected_header"]
        attributes = published["data_attributes"]
        pairs = {
            "url": (scan["url"], published["url"]),
            "remote size": (
                scan["expected_remote_size_bytes"],
                published["remote_size_bytes"],
            ),
            "ETag": (scan["expected_etag"], published["etag"]),
            "source": (expected["source_name"], published["source_name"]),
            "tstart": (expected["tstart_mjd"], published["tstart_mjd"]),
            "tsamp": (expected["tsamp_s"], published["tsamp_s"]),
            "shape": (expected["dataset_shape"], published["dataset_shape"]),
            "dtype": (expected["dataset_dtype"], published["dataset_dtype"]),
            "fch1": (expected["fch1_mhz"], published["fch1_mhz"]),
            "foff": (expected["foff_mhz"], published["foff_mhz"]),
            "src_raj": (expected["src_raj_hours"], attributes["src_raj"]),
            "src_dej": (expected["src_dej_deg"], attributes["src_dej"]),
        }
        for label, (actual, frozen) in pairs.items():
            require_equal(actual, frozen, f"{scan['label']} {label}")
        require_equal(published["http_status"], 200, "published header status")
        require_equal(
            published["spectral_dataset_values_read"],
            False,
            "published spectral read flag",
        )
        frozen_time = Time(expected["tstart_mjd"], format="mjd", scale="utc")
        labelled_time = Time(scan["hdf5_header_utc"], format="isot", scale="utc")
        if abs((frozen_time - labelled_time).to_value("s")) > 1e-6:
            raise ValueError(f"{scan['label']} HDF5 UTC label changed")


def validate_windows(config: dict[str, Any]) -> None:
    require_equal(
        [
            (
                item["id"],
                item["fmin_mhz"],
                item["fmax_mhz"],
                item["rest_center_mhz"],
                item["rest_half_width_khz"],
            )
            for item in config["windows"]
        ],
        [
            ("m37_1400p5", 1399.2, 1401.8, 1400.5, 500),
            ("m37_1406p5", 1405.2, 1407.8, 1406.5, 500),
            ("m37_1412p5", 1411.2, 1413.8, 1412.5, 500),
            ("m37_1418p5", 1417.2, 1419.8, 1418.5, 500),
            ("m37_1425p0", 1423.7, 1426.3, 1425.0, 500),
        ],
        "five-window geometry",
    )


def validate_legacy_regression_source(config: dict[str, Any]) -> None:
    frozen = load_json(SOURCE_PATHS["legacy_m36_preflight_config"])
    frozen_search = frozen["search"]
    frozen_templates = tuple(
        [(0.0, 0.0)]
        + [
            (float(scale), float(phase))
            for scale in frozen_search["projected_scales"]
            if float(scale) != 0.0
            for phase in frozen_search["phase_offsets_cycles"]
        ]
    )
    require_equal(frozen_templates, LEGACY_TEMPLATES, "legacy M36 template bank")
    require_equal(
        tuple(frozen_search["spectral_widths_channels"]),
        LEGACY_WIDTHS,
        "legacy M36 width bank",
    )
    require_equal(
        config["legacy_regression_reference"]["template_count"],
        len(frozen_templates),
        "legacy regression template count",
    )
    require_equal(
        config["legacy_regression_reference"]["spectral_width_count"],
        len(LEGACY_WIDTHS),
        "legacy regression width count",
    )


def channel_bounds(
    fch1_mhz: float,
    foff_mhz: float,
    nchans: int,
    fmin_mhz: float,
    fmax_mhz: float,
) -> tuple[int, int]:
    """Return the exact native-channel slice used by the HDF5 adapter."""
    low_index = int(np.ceil((fmin_mhz - fch1_mhz) / foff_mhz))
    high_index = int(np.floor((fmax_mhz - fch1_mhz) / foff_mhz))
    channel_start, channel_stop = sorted((low_index, high_index))
    channel_start = max(0, channel_start)
    channel_stop = min(nchans - 1, channel_stop) + 1
    if channel_start >= channel_stop:
        raise ValueError("Requested frequency window is outside the HDF5 file")
    return channel_start, channel_stop


def extraction_geometry(scan: dict[str, Any], window: dict[str, Any]) -> dict:
    header = scan["expected_header"]
    fch1 = float(header["fch1_mhz"])
    foff = float(header["foff_mhz"])
    nchans = int(header["dataset_shape"][-1])
    start, stop = channel_bounds(
        fch1,
        foff,
        nchans,
        float(window["fmin_mhz"]),
        float(window["fmax_mhz"]),
    )
    first = fch1 + start * foff
    last = fch1 + (stop - 1) * foff
    low, high = sorted((first, last))
    return {
        "channel_start": start,
        "channel_stop": stop,
        "channel_count": stop - start,
        "frequency_low_mhz": low,
        "frequency_high_mhz": high,
        "channel_width_mhz": abs(foff),
    }


def integration_times(header: dict[str, Any]) -> Time:
    return Time(
        float(header["tstart_mjd"])
        + (np.arange(int(header["dataset_shape"][0])) + 0.5)
        * float(header["tsamp_s"])
        / DAY_S,
        format="mjd",
        scale="utc",
    )


def rounded_difference_bound(delta_channels: float) -> int:
    """Bound abs(rint(x + delta) - rint(x)), including ties-to-even."""
    if not math.isfinite(delta_channels) or delta_channels < 0:
        raise ValueError("channel displacement must be finite and nonnegative")
    if delta_channels == 0.0:
        return 0
    return math.floor(math.nextafter(delta_channels, math.inf)) + 1


def continuous_circular_envelope(
    config: dict[str, Any],
    scan: dict[str, Any],
    window: dict[str, Any],
    target: SkyCoord,
    location: Any,
    spectral_rest_half_width: int,
) -> dict[str, Any]:
    """Bound every scale and phase analytically for an eccentricity-zero orbit."""
    domain = config["coverage_domain"]
    if float(config["orbit"]["eccentricity"]) != 0.0:
        raise ValueError("The analytic M37 envelope requires eccentricity == 0")
    require_equal(domain["projected_scale_min"], 0.0, "scale-domain minimum")
    require_equal(domain["projected_scale_max"], 1.0, "scale-domain maximum")
    require_equal(domain["phase_cycles"], "all_modulo_one", "phase domain")
    require_equal(
        domain["nearest_channel_rounding_guard_channels"],
        1,
        "nearest-channel rounding rule",
    )

    header = scan["expected_header"]
    geometry = extraction_geometry(scan, window)
    times = integration_times(header)
    stationary_factor, observer, _ = celestial_frequency_factor(
        times,
        0.0,
        0.0,
        target,
        location,
        config["orbit"],
    )
    observer_factor = 1.0 + observer / C_M_S
    if not np.array_equal(stationary_factor, observer_factor):
        raise AssertionError("Observer-only factor identity changed")

    # For e=0 the unknown scale/phase is a coefficient vector in a unit disk.
    # The norm below is the exact phase maximum and uses a cancellation-stable
    # representation of |A_i e(theta_i) - A_0 e(theta_0)|.
    period_days = float(config["orbit"]["period_days"])
    circular_speed = (
        2.0
        * math.pi
        * float(config["orbit"]["semi_major_axis_au"])
        * AU_M
        / (period_days * DAY_S)
    )
    delta_theta = (
        2.0
        * math.pi
        * (times.tdb - times.tdb[0]).to_value("day")
        / period_days
    )
    deterministic_delta = stationary_factor - stationary_factor[0]
    maximum_orbital_delta = circular_speed / C_M_S * np.hypot(
        observer_factor * np.cos(delta_theta) - observer_factor[0],
        observer_factor * np.sin(delta_theta),
    )
    maximum_factor_delta = np.abs(deterministic_delta) + maximum_orbital_delta

    df_mhz = float(geometry["channel_width_mhz"])
    reference_hz = float(window["rest_center_mhz"]) * 1e6
    maximum_track_delta_channels = float(
        np.max(reference_hz * maximum_factor_delta / (df_mhz * 1e6))
    )
    dedoppler_margin = rounded_difference_bound(maximum_track_delta_channels)

    rest_grid = make_rest_grid(window, df_mhz)
    factor_start_radius = float(observer_factor[0] * circular_speed / C_M_S)
    factor_start_low = math.nextafter(
        float(stationary_factor[0] - factor_start_radius), -math.inf
    )
    factor_start_high = math.nextafter(
        float(stationary_factor[0] + factor_start_radius), math.inf
    )
    if factor_start_low <= 0.0:
        raise AssertionError("Observed/rest factor envelope is not positive")
    spectral_support_margin = rounded_difference_bound(
        spectral_rest_half_width * max(abs(factor_start_low), abs(factor_start_high))
    )
    total_margin = dedoppler_margin + spectral_support_margin
    observed_min = math.nextafter(float(rest_grid[0] * factor_start_low), -math.inf)
    observed_max = math.nextafter(float(rest_grid[-1] * factor_start_high), math.inf)
    zero = float(geometry["frequency_low_mhz"])
    nfreq = int(geometry["channel_count"])
    minimum_index_real = (observed_min - zero) / df_mhz
    maximum_index_real = (observed_max - zero) / df_mhz
    # Deliberately loose endpoint bounds include every np.rint outcome.
    minimum_index_bound = math.floor(
        math.nextafter(minimum_index_real - 0.5, -math.inf)
    )
    maximum_index_bound = math.ceil(
        math.nextafter(maximum_index_real + 0.5, math.inf)
    )
    lower_headroom = minimum_index_bound - total_margin
    upper_headroom = nfreq - 1 - maximum_index_bound - total_margin
    passed = lower_headroom >= 0 and upper_headroom >= 0

    return {
        "scan_label": scan["label"],
        "source_name": header["source_name"],
        "window_id": window["id"],
        "integration_count": len(times),
        "parameter_domain": {
            "projected_scale_min": 0.0,
            "projected_scale_max": 1.0,
            "phase_cycles": "all modulo one",
            "eccentricity": 0.0,
        },
        "proof": (
            "exact circular coefficient-disk envelope with a stable analytic "
            "phase maximum plus outward endpoint and nearest-channel bounds"
        ),
        "extraction_geometry": geometry,
        "circular_orbital_speed_m_s": circular_speed,
        "factor_start_low": factor_start_low,
        "factor_start_high": factor_start_high,
        "maximum_continuous_track_delta_channels": maximum_track_delta_channels,
        "dedoppler_margin_channels": dedoppler_margin,
        "spectral_rest_half_width_channels": spectral_rest_half_width,
        "spectral_mapped_support_margin_channels": spectral_support_margin,
        "total_margin_channels": total_margin,
        "minimum_rest_mapping_index_bound": minimum_index_bound,
        "maximum_rest_mapping_index_bound": maximum_index_bound,
        "lower_headroom_channels": lower_headroom,
        "upper_headroom_channels": upper_headroom,
        "passed": bool(passed),
    }


def exact_template_regression(
    config: dict[str, Any],
    scan: dict[str, Any],
    window: dict[str, Any],
    target: SkyCoord,
    location: Any,
    spectral_half_width: int,
) -> list[dict[str, Any]]:
    header = scan["expected_header"]
    geometry = extraction_geometry(scan, window)
    df_mhz = float(geometry["channel_width_mhz"])
    zero = float(geometry["frequency_low_mhz"])
    nfreq = int(geometry["channel_count"])
    rest_grid = make_rest_grid(window, df_mhz)
    times = integration_times(header)
    records = []
    for template_index, (scale, phase) in enumerate(LEGACY_TEMPLATES):
        factor, _, _ = celestial_frequency_factor(
            times, scale, phase, target, location, config["orbit"]
        )
        observed_track = float(window["rest_center_mhz"]) * factor
        reference_indices = np.rint((observed_track - zero) / df_mhz).astype(int)
        shifts = reference_indices - reference_indices[0]
        dedoppler_margin = int(np.max(np.abs(shifts)))
        total_margin = dedoppler_margin + spectral_half_width
        observed_needed = rest_grid * factor[0]
        indices = np.rint((observed_needed - zero) / df_mhz).astype(int)
        lower_headroom = int(indices.min() - total_margin)
        upper_headroom = int(nfreq - total_margin - 1 - indices.max())
        records.append({
            "template_index": template_index,
            "projected_scale": scale,
            "phase_offset_cycles": phase,
            "dedoppler_margin_channels": dedoppler_margin,
            "spectral_half_width_channels": spectral_half_width,
            "total_margin_channels": total_margin,
            "lower_headroom_channels": lower_headroom,
            "upper_headroom_channels": upper_headroom,
            "passed": lower_headroom >= 0 and upper_headroom >= 0,
        })
    return records


def literal_tolerance(channel_width_hz: float, tolerance_hz: float) -> dict:
    bins = int(math.floor((tolerance_hz + 1e-9) / channel_width_hz))
    radius = bins * channel_width_hz
    next_radius = (bins + 1) * channel_width_hz
    if radius > tolerance_hz + 1e-6 or next_radius <= tolerance_hz - 1e-6:
        raise AssertionError("Literal tolerance radius is not maximal")
    return {
        "configured_tolerance_hz": tolerance_hz,
        "radius_channels": bins,
        "radius_hz": radius,
        "next_channel_radius_hz": next_radius,
        "next_channel_exceeds_tolerance": next_radius > tolerance_hz,
        "normative_retention_set_defined_here": False,
    }


def control_geometry(config: dict[str, Any]) -> dict[str, Any]:
    on = [scan for scan in config["scans"] if scan["kind"] == "on"]
    off = [scan for scan in config["scans"] if scan["kind"] == "off"]

    def coordinate(scan: dict[str, Any]) -> SkyCoord:
        header = scan["expected_header"]
        return SkyCoord(
            ra=float(header["src_raj_hours"]) * u.hourangle,
            dec=float(header["src_dej_deg"]) * u.deg,
            frame="icrs",
        )

    on_coordinates = [coordinate(scan) for scan in on]
    off_coordinates = [coordinate(scan) for scan in off]
    off_pair_separations = [
        float(off_coordinates[left].separation(off_coordinates[right]).arcsec)
        for left in range(len(off_coordinates))
        for right in range(left + 1, len(off_coordinates))
    ]
    on_off_separations = [
        float(on_coordinates[index].separation(off_coordinates[index]).deg)
        for index in range(3)
    ]
    sources = sorted({scan["expected_header"]["source_name"] for scan in off})
    repeated = len(sources) == 1 and max(off_pair_separations) < 1.0
    return {
        "on_scan_count": len(on),
        "off_scan_count": len(off),
        "distinct_off_source_names": sources,
        "distinct_off_source_name_count": len(sources),
        "maximum_off_pointing_spread_arcsec": max(off_pair_separations),
        "paired_on_off_separation_deg": on_off_separations,
        "one_repeated_control_direction": repeated,
        "temporal_control_measurements": 3,
        "distinct_spatial_control_directions": 1,
        "interpretation": (
            "three temporal OFF measurements at one repeated sky direction, "
            "not three independent spatial controls"
        ),
    }


def check_config(config: dict[str, Any]) -> dict[str, Any]:
    require_equal(
        config["project"]["status"],
        "metadata_only_before_spectral_contact",
        "preflight status",
    )
    require_equal(config["project"]["selected_extension_rank"], 37, "rank")
    require_equal(
        config["project"]["selected_archive_target"], "HIP84607", "target"
    )
    require_equal(config["project"]["selected_cadence"], "--85168", "cadence")
    source_hashes = validate_source_hashes(config)
    validate_selected_metadata(config)
    validate_scan_headers(config)
    validate_windows(config)
    validate_legacy_regression_source(config)

    domain = config["coverage_domain"]
    require_equal(domain["projected_scale_min"], 0.0, "scale minimum")
    require_equal(domain["projected_scale_max"], 1.0, "scale maximum")
    require_equal(domain["phase_cycles"], "all_modulo_one", "phase domain")
    require_equal(
        domain["requires_exact_zero_eccentricity"], True, "circular requirement"
    )
    require_equal(
        domain["orbital_parameter_uncertainties_covered"],
        False,
        "orbital-uncertainty scope",
    )
    require_equal(config["orbit"]["eccentricity"], 0.0, "eccentricity")
    require_equal(
        domain["maximum_spectral_width_channels"], 129, "maximum width guard"
    )

    legacy = config["legacy_regression_reference"]
    require_equal(legacy["enabled"], True, "legacy regression switch")
    require_equal(legacy["template_count"], len(LEGACY_TEMPLATES), "legacy templates")
    widths = validate_widths(LEGACY_WIDTHS)
    require_equal(legacy["spectral_width_count"], len(widths), "legacy widths")
    require_equal(max(widths), domain["maximum_spectral_width_channels"], "width guard")
    spectral_half_width = max(widths) // 2

    dimensions = config["conditional_search_dimensions"]
    on_count = sum(scan["kind"] == "on" for scan in config["scans"])
    off_count = sum(scan["kind"] == "off" for scan in config["scans"])
    require_equal((on_count, off_count), (3, 3), "ON/OFF counts")
    require_equal(dimensions["on_epoch_count"], on_count, "conditional ON count")
    subsets = make_subsets(on_count, int(dimensions["minimum_active_epochs"]))
    require_equal(
        subsets,
        [(0, 1), (0, 2), (1, 2), (0, 1, 2)],
        "activity subsets",
    )
    require_equal(dimensions["activity_subset_count"], len(subsets), "subset count")
    require_equal(
        dimensions["legacy_template_count"], len(LEGACY_TEMPLATES), "template count"
    )
    require_equal(
        dimensions["legacy_spectral_width_count"], len(widths), "width count"
    )

    channel_widths = {
        abs(float(scan["expected_header"]["foff_mhz"])) * 1e6
        for scan in config["scans"]
    }
    require_equal(len(channel_widths), 1, "scan channel-width count")
    channel_width_hz = channel_widths.pop()
    tolerance = literal_tolerance(
        channel_width_hz,
        float(config["candidate_geometry_reference"][
            "literal_frequency_tolerance_hz"
        ]),
    )

    period_s = float(config["orbit"]["period_days"]) * DAY_S
    circular_speed = (
        2.0
        * math.pi
        * float(config["orbit"]["semi_major_axis_au"])
        * AU_M
        / period_s
    )
    maximum_acceleration = 2.0 * math.pi * circular_speed / period_s
    derived_proxy = 1425e6 * maximum_acceleration / C_M_S
    proxy = float(config["project"]["design_drift_proxy_hz_s_at_1425_mhz"])
    require_equal(derived_proxy, proxy, "derived drift proxy")
    maximum_tsamp = max(
        float(scan["expected_header"]["tsamp_s"])
        for scan in config["scans"]
    )
    proxy_sweep_hz = proxy * maximum_tsamp
    proxy_sweep_channels = proxy_sweep_hz / channel_width_hz
    first_covering_width = next(
        width for width in widths if width >= math.ceil(proxy_sweep_channels)
    )

    target = make_target(config["target"])
    location = make_location(config["observatory"])
    envelope_records = []
    regression_records = []
    rest_bins_by_window: dict[str, int] = {}
    for window in config["windows"]:
        rest_grid = make_rest_grid(window, channel_width_hz / 1e6)
        rest_bins_by_window[window["id"]] = int(rest_grid.size)
        for scan in config["scans"]:
            envelope_records.append(
                continuous_circular_envelope(
                    config,
                    scan,
                    window,
                    target,
                    location,
                    spectral_half_width,
                )
            )
            exact = exact_template_regression(
                config,
                scan,
                window,
                target,
                location,
                spectral_half_width,
            )
            regression_records.append({
                "scan_label": scan["label"],
                "window_id": window["id"],
                "templates": exact,
                "passed": all(record["passed"] for record in exact),
            })

    hypotheses_per_window = len(LEGACY_TEMPLATES) * len(subsets) * len(widths)
    score_cells_by_window = {
        key: hypotheses_per_window * value
        for key, value in rest_bins_by_window.items()
    }
    controls = control_geometry(config)
    width_passed = max(widths) >= math.ceil(proxy_sweep_channels)
    all_passed = (
        all(record["passed"] for record in envelope_records)
        and all(record["passed"] for record in regression_records)
        and width_passed
        and controls["one_repeated_control_direction"]
    )
    minimum_headroom_channels = min(
        min(record["lower_headroom_channels"], record["upper_headroom_channels"])
        for record in envelope_records
    )
    return {
        "purpose": (
            "M37 metadata-only continuous circular motion, spectral-width, "
            "and extraction-coverage proof"
        ),
        "spectral_payload_inspected": False,
        "spectral_dataset_values_read": False,
        "remote_files_opened": False,
        "telescope_remote_request_made": False,
        "network_access_required": False,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "astropy": importlib.metadata.version("astropy"),
            "astropy_iers_data": importlib.metadata.version("astropy-iers-data"),
            "pyerfa": importlib.metadata.version("pyerfa"),
        },
        "source_hashes": source_hashes,
        "passed": bool(all_passed),
        "continuous_circular_orbit_envelope": {
            "is_normative_extraction_guard_proof": True,
            "does_not_freeze_detector_v0p6": True,
            "does_not_claim_continuous_search_sensitivity": True,
            "projected_scale_min": 0.0,
            "projected_scale_max": 1.0,
            "phase_cycles": "all modulo one",
            "checks": len(envelope_records),
            "scan_window_integration_evaluations": sum(
                record["integration_count"] for record in envelope_records
            ),
            "minimum_lower_headroom_channels": min(
                record["lower_headroom_channels"] for record in envelope_records
            ),
            "minimum_upper_headroom_channels": min(
                record["upper_headroom_channels"] for record in envelope_records
            ),
            "minimum_any_edge_headroom_channels": minimum_headroom_channels,
            "minimum_any_edge_headroom_hz": (
                minimum_headroom_channels * channel_width_hz
            ),
            "maximum_dedoppler_margin_channels": max(
                record["dedoppler_margin_channels"] for record in envelope_records
            ),
            "maximum_mapped_spectral_support_margin_channels": max(
                record["spectral_mapped_support_margin_channels"]
                for record in envelope_records
            ),
            "records": envelope_records,
        },
        "legacy_m36_v0p5_21_template_regression": {
            "is_normative_extraction_guard_proof": False,
            "scope": (
                "exact historical discrete templates only; regression and "
                "conditional resource arithmetic, with no continuum claim"
            ),
            "template_count": len(LEGACY_TEMPLATES),
            "checks": sum(
                len(record["templates"]) for record in regression_records
            ),
            "minimum_any_edge_headroom_channels": min(
                min(item["lower_headroom_channels"], item["upper_headroom_channels"])
                for record in regression_records
                for item in record["templates"]
            ),
            "maximum_dedoppler_margin_channels": max(
                item["dedoppler_margin_channels"]
                for record in regression_records
                for item in record["templates"]
            ),
            "passed": all(record["passed"] for record in regression_records),
            "records": regression_records,
        },
        "width_envelope": {
            "legacy_width_bank_channels": list(widths),
            "maximum_width_extraction_support_guard_channels": max(widths),
            "spectral_rest_half_width_channels": spectral_half_width,
            "maximum_mapped_extraction_support_margin_channels": max(
                record["spectral_mapped_support_margin_channels"]
                for record in envelope_records
            ),
            "circular_orbital_speed_m_s": circular_speed,
            "maximum_circular_acceleration_m_s2": maximum_acceleration,
            "derived_drift_proxy_hz_s_at_1425_mhz": derived_proxy,
            "maximum_integration_seconds": maximum_tsamp,
            "proxy_sweep_hz_per_integration": proxy_sweep_hz,
            "proxy_sweep_channels_per_integration": proxy_sweep_channels,
            "first_legacy_width_covering_proxy_sweep_channels": first_covering_width,
            "all_legacy_rest_grid_bins_finite_claim": False,
            "v0p5_ordering_caveat": (
                "v0.5 filters after mapping to the one-MHz rest grid, so a "
                "width-129 vector has 64 NaN edge bins; v0.6 ordering and its "
                "finite normative domain must be frozen separately"
            ),
            "passed": width_passed,
        },
        "literal_frequency_tolerance": tolerance,
        "conditional_search_dimensions_for_legacy_21_template_bank": {
            "not_a_detector_freeze": True,
            "nominal_score_tensor_cells_label": (
                "includes v0.5 boxcar edge positions that are NaN at width > 1"
            ),
            "templates": len(LEGACY_TEMPLATES),
            "activity_subsets": len(subsets),
            "spectral_widths": len(widths),
            "hypotheses_per_window": hypotheses_per_window,
            "rest_bins_by_window": rest_bins_by_window,
            "nominal_score_tensor_cells_by_window": score_cells_by_window,
            "nominal_score_tensor_cells_total": sum(score_cells_by_window.values()),
            "normative_retention_record_set": (
                "not frozen by this geometry preflight"
            ),
        },
        "control_geometry": controls,
        "phase_scope": {
            "composite_eccentricity": float(config["orbit"]["eccentricity"]),
            "periastron_epoch_and_angle_physically_unique": False,
            "normative_extraction_phase_domain": "all modulo one",
            "m37_v0p6_template_bank": "not frozen",
            "orbital_parameter_uncertainties_covered": False,
            "full_orbit_search_sensitivity_claim": False,
            "allowed_future_claim": (
                "exact preregistered finite template bank only unless a "
                "separate certified track-space sensitivity cover is frozen"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    result = check_config(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(json.dumps({
        "passed": result["passed"],
        "continuous_checks": result[
            "continuous_circular_orbit_envelope"
        ]["checks"],
        "scan_window_integration_evaluations": result[
            "continuous_circular_orbit_envelope"
        ]["scan_window_integration_evaluations"],
        "legacy_regression_checks": result[
            "legacy_m36_v0p5_21_template_regression"
        ]["checks"],
        "minimum_any_edge_headroom_channels": result[
            "continuous_circular_orbit_envelope"
        ]["minimum_any_edge_headroom_channels"],
        "maximum_dedoppler_margin_channels": result[
            "continuous_circular_orbit_envelope"
        ]["maximum_dedoppler_margin_channels"],
        "conditional_nominal_score_cells_total": result[
            "conditional_search_dimensions_for_legacy_21_template_bank"
        ]["nominal_score_tensor_cells_total"],
    }, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit("M37 metadata-only extraction coverage failed")


if __name__ == "__main__":
    main()
