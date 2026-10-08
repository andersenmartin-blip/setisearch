"""Prospective synthetic radio controls; importing does not create random values.

Only build_manifests() is used before the public freeze. generate_case() is for
an explicitly admitted DEV or validation invocation after that freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

SUBSETS = ((0,), (2,), (4,), (0, 2), (0, 4), (2, 4), (0, 2, 4))
NOISE_LAWS = ("gamma16", "gaussian", "rowgain_gamma16", "frequency_ar1_gaussian")


def _case(panel, family, serial, **fields):
    identity = f"SETI_RADIO_PILOT_20261008_{panel}:{family}:{serial:03d}"
    return {"case_id": identity, "panel": panel, "family": family,
            "seed_sha256": hashlib.sha256(identity.encode("ascii")).hexdigest(),
            "eligibility_case": family in {"strong", "operating", "matched_rfi", "noise"},
            **fields}


def _placement(serial, nchan):
    # Coordinates are native-channel positions at the global reference time.
    # Quarter-channel offsets are inward at the two carrier-band boundaries.
    bases = (0.0, float(nchan - 1), 1024.0, float(nchan - 1025))
    base = bases[serial % 4]
    offset = .25 if base == 0 else -.25 if base == nchan - 1 else (.25 if serial % 2 == 0 else -.25)
    return base + offset


def full_panel(panel, nchan=4096):
    cases = []
    for serial, (active, drift) in enumerate(itertools.product(SUBSETS, (-4., 4.))):
        cases.append(_case(panel, "strong", serial, active_scan_indices=list(active),
                           drift_hz_s=drift, intrinsic_width_channels=1 if serial % 2 == 0 else 3,
                           nominal_ideal_box_score=24., reference_native_offset=_placement(serial, nchan),
                           noise_law="gamma16"))
    for serial, (active, drift, width) in enumerate(itertools.product(SUBSETS[:6], (-4., -1.25, 1.25, 4.), (1, 3))):
        cases.append(_case(panel, "operating", serial, active_scan_indices=list(active),
                           drift_hz_s=drift, intrinsic_width_channels=width,
                           nominal_ideal_box_score=12., reference_native_offset=_placement(serial, nchan),
                           noise_law="gamma16"))
    for serial, (drift, width, level, location) in enumerate(itertools.product((-4., 0., 4.), (1, 3), (12., 24.), (0, 1))):
        fields = dict(active_scan_indices=list(range(6)), drift_hz_s=drift,
                      intrinsic_width_channels=width, nominal_ideal_box_score=level,
                      reference_native_offset=1024.25 if location == 0 else nchan - 1025.25,
                      noise_law="gamma16")
        if serial in (0, 7, 16, 23):
            fields["off_only_nuisance"] = {"drift_hz_s": -3. if drift >= 0 else 3.,
                                           "nominal_ideal_box_score": 48.,
                                           "intrinsic_width_channels": 1}
        cases.append(_case(panel, "matched_rfi", serial, **fields))
    for serial, (law, repeat) in enumerate(itertools.product(NOISE_LAWS, range(8))):
        cases.append(_case(panel, "noise", serial, active_scan_indices=[], noise_law=law,
                           noise_repeat_index=repeat))
    for serial, (on_scan, row, width) in enumerate(itertools.product((0, 2, 4), (0, 15), (1, 3))):
        cases.append(_case(panel, "single_row_transient", serial,
                           active_scan_indices=[on_scan], transient_row=row, drift_hz_s=(-4., 4.)[serial % 2],
                           intrinsic_width_channels=width, nominal_ideal_box_score=24.,
                           reference_native_offset=_placement(serial, nchan), noise_law="gamma16"))
    for serial, (on_scan, width, offset) in enumerate(itertools.product((0, 2, 4), (1, 3), (2., 8.))):
        cases.append(_case(panel, "near_off_contamination", serial,
                           active_scan_indices=[on_scan], drift_hz_s=0.,
                           intrinsic_width_channels=width, nominal_ideal_box_score=12.,
                           reference_native_offset=_placement(serial + 2, nchan), noise_law="gamma16",
                           diagnostic_off_frequency_offset_channels=offset,
                           diagnostic_off_nominal_ideal_box_score=24.))
    return cases


def development_panel(nchan=4096):
    all_cases = full_panel("DEV", nchan)
    keep = {"strong": {0, 3, 10, 13}, "operating": {0, 7, 8, 15, 24, 31, 40, 47},
            "matched_rfi": {0, 3, 6, 7, 12, 16, 20, 23}, "noise": {0, 8, 16, 24}}
    return [c for c in all_cases if c["family"] in keep and int(c["case_id"].rsplit(":", 1)[1]) in keep[c["family"]]]


def make_contract(source_manifest, source_bytes_sha256):
    source = source_manifest
    c0, c1 = source["frequency_reference_channel_interval"]
    scans = []
    for item in source["all_six_scan_metadata"]:
        h = item["expected_header"]
        scans.append({"scan_id": item["label"], "role": item["role"],
                      "nrows": h["dataset_shape"][0], "tsamp_s": h["tsamp_s"],
                      "tstart_mjd": h["tstart_mjd"], "fch1_hz": h["fch1_mhz"] * 1e6,
                      "df_hz": h["foff_mhz"] * 1e6})
    first = scans[0]["tstart_mjd"]
    mids = [((s["tstart_mjd"] - first) * 86400 + (i + .5) * s["tsamp_s"])
            for s in scans for i in range(s["nrows"])]
    tref_relative_s = .5 * (min(mids) + max(mids))
    edges = [((s["tstart_mjd"] - first) * 86400 + i * s["tsamp_s"])
             for s in scans for i in (0, s["nrows"])]
    max_motion_channels = 4. * max(abs(t - tref_relative_s) for t in mids) / min(abs(s["df_hz"]) for s in scans)
    # Match the production full-OFF reference halo and 501-channel normalizer.
    guard = math.ceil(max_motion_channels) + 250 + 16 + 250 + 1
    return {"schema": "prospective-synthetic-controls-v1", "source_manifest_sha256": source_bytes_sha256,
            "source_metadata_status": "historical-metadata-template; current-source-admission-separate",
            "synthetic_values_status": "NOT_GENERATED", "pilot_values_status": "NOT_OPENED",
            "geometry": {"reference_source_channel_interval": [c0, c1],
                         "loaded_source_channel_interval": [c0 - guard, c1 + guard],
                         "guard_channels_each_side": guard, "tref_relative_first_scan_start_s": tref_relative_s,
                         "guard_components": {"midpoint_drift": math.ceil(max_motion_channels),
                                               "compatible_OFF_reference_halo": 250,
                                               "largest_box_halfwidth": 16,
                                               "normalization_halfwidth": 250, "rounding": 1},
                         "first_scan_start_mjd": first, "scan_metadata": scans},
            "box_width_bank": [1, 3, 9, 33],
            "signal_profile": "unit-area intrinsic uniform top-hat convolved with uniform frequency sweep during each integration; exact bin CDF differences",
            "amplitude_definition": "per active scan A=nominal_ideal_box_score*sigma_raw/B; B=max_width(sum of exact profile in true-centred integer box over active rows)/sqrt(nrows*width). A is the mean-integration frequency-summed positive power before preprocessing; nominal score is only a declared-law ideal projection, not detector SNR or flux.",
            "ideal_box_center_rounding": "numpy.rint on ABSOLUTE source channel index; ties to even before subtracting loaded source_channel0",
            "noise_laws": {"gamma16": {"mean": 1., "shape": 16., "scale": .0625, "sigma_raw": .25},
                           "gaussian": {"mean": 1., "sigma_raw": .05},
                           "rowgain_gamma16": {"mean": "g_row", "shape": 16., "scale": ".0625*g_row", "sigma_raw": ".25*g_row", "g_row": "1+.1*sin(2*pi*(row+.5)/16+scan_index*pi/3)"},
                           "frequency_ar1_gaussian": {"mean": 1., "sigma_raw": .05, "rho": .25, "row_initial_state": "stationary N(0,1)", "cross_row_independence": True}},
            "positivity": "All main controls use positive Gamma power. Gaussian diagnostic draws must be finite and positive; failure closes the case, without clipping or re-drawing.",
            "rng": "numpy.Generator(PCG64(integer_from_full_SHA256_case_identity)); NumPy version pinned by admitted run",
            "recovery_definition": "Every active ON must retain a localized hit after full OFF comparison; also report any-active recovery. First/last integration-centre trajectory mismatch must be <=(2+max(winning_width,injection_oracle_width)/2)*abs(df_hz).",
            "gates": {"strong_all": 14, "operating_at_least": 44, "operating_each_activity_at_least": 7,
                      "operating_each_drift_at_least": 10, "operating_each_width_at_least": 22,
                      "matched_rfi_maximum_surviving_cadences": 0, "noise_maximum_surviving_cadences": 1},
            "panel_counts": {"DEV": 24, "VAL_A": 142, "VAL_B": 142},
            "authority": "Definitions only; no DEV/VAL invocation authorized by this file"}


def build_manifests(source_path, output_dir):
    raw = Path(source_path).read_bytes()
    contract = make_contract(json.loads(raw), hashlib.sha256(raw).hexdigest())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    documents = {"control_contract.json": contract,
                 "development_cases.json": development_panel(),
                 "validation_a_cases.json": full_panel("VAL_A"),
                 "validation_b_cases.json": full_panel("VAL_B")}
    for filename, value in documents.items():
        (output / filename).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in documents}


def _uniform_convolution_cdf(x, intrinsic_width, sweep_width):
    import numpy as np
    a, b = float(intrinsic_width), float(sweep_width)
    x = np.asarray(x, dtype=np.float64)
    if b == 0:
        return np.clip((x + a / 2) / a, 0., 1.)
    h = (a + b) / 2
    y = np.clip(x, -h, h)
    positive_square = lambda z: np.maximum(z, 0.) ** 2
    out = (positive_square(y + h) - positive_square(y + (b - a) / 2)
           - positive_square(y + (a - b) / 2) + positive_square(y - h)) / (2 * a * b)
    return np.where(x <= -h, 0., np.where(x >= h, 1., np.clip(out, 0., 1.)))


def _profile(case, scan, geometry, *, drift=None, offset=None, width=None, rows=None):
    import numpy as np
    rate = float(case["drift_hz_s"] if drift is None else drift)
    native_offset = float(case["reference_native_offset"] if offset is None else offset)
    intrinsic = int(case["intrinsic_width_channels"] if width is None else width)
    c0 = geometry["reference_source_channel_interval"][0]
    loaded0, loaded1 = geometry["loaded_source_channel_interval"]
    relative_start = (scan["tstart_mjd"] - geometry["first_scan_start_mjd"]) * 86400
    times = relative_start + (np.arange(scan["nrows"]) + .5) * scan["tsamp_s"]
    # signed df retains the native descending frequency orientation.
    centers = c0 + native_offset + rate * (times - geometry["tref_relative_first_scan_start_s"]) / scan["df_hz"]
    channels = np.arange(loaded0, loaded1, dtype=np.float64)
    x = channels[None, :] - centers[:, None]
    sweep = abs(rate) * scan["tsamp_s"] / abs(scan["df_hz"])
    profile = (_uniform_convolution_cdf(x + .5, intrinsic, sweep)
               - _uniform_convolution_cdf(x - .5, intrinsic, sweep))
    if rows is not None:
        keep = np.zeros(scan["nrows"], dtype=bool)
        keep[rows] = True
        profile[~keep] = 0.
    if not np.allclose(profile.sum(axis=1)[profile.sum(axis=1) > 0], 1., atol=1e-11, rtol=0):
        raise ValueError("Synthetic profile falls outside the declared loaded context")
    return profile, centers


def _ideal_projection(profile, centers, geometry, widths):
    import numpy as np
    channels = np.arange(*geometry["loaded_source_channel_interval"])
    nearest = np.rint(centers).astype(np.int64)
    nrows = profile.shape[0]
    projections = []
    for width in widths:
        select = abs(channels[None, :] - nearest[:, None]) <= width // 2
        projections.append(float(profile[select].sum() / math.sqrt(nrows * width)))
    winner = int(np.argmax(projections))
    return {"maximum": projections[winner], "oracle_width_channels": widths[winner],
            "by_width": dict(zip(map(str, widths), projections))}


def generate_case(case, contract):
    """Return six native-order float64 power arrays and explicit synthetic truth.

    Caller admission and frozen seed membership are compulsory external gates.
    This function is intentionally not exposed by the command-line interface.
    """
    import numpy as np
    geometry = contract["geometry"]
    nchan = geometry["loaded_source_channel_interval"][1] - geometry["loaded_source_channel_interval"][0]
    arrays, fluxes = [], {}
    law = case["noise_law"]
    # Compute geometry and flux without observing any noise or search result.
    injections = {}
    for index, scan in enumerate(geometry["scan_metadata"]):
        layers = []
        if index in case.get("active_scan_indices", []):
            rows = [case["transient_row"]] if case["family"] == "single_row_transient" else None
            profile, centers = _profile(case, scan, geometry, rows=rows)
            projection = _ideal_projection(profile, centers, geometry, contract["box_width_bank"])
            flux = case["nominal_ideal_box_score"] * .25 / projection["maximum"]
            layers.append(flux * profile)
            fluxes[scan["scan_id"]] = {"mean_integration_frequency_summed_power": flux,
                                       "ideal_box_projection_per_unit_power": projection["maximum"],
                                       "injection_oracle_width_channels": projection["oracle_width_channels"],
                                       "ideal_box_projection_by_width": projection["by_width"]}
        if scan["role"] == "off" and "off_only_nuisance" in case:
            nuisance = case["off_only_nuisance"]
            profile, centers = _profile(case, scan, geometry, drift=nuisance["drift_hz_s"], width=nuisance["intrinsic_width_channels"])
            projection = _ideal_projection(profile, centers, geometry, contract["box_width_bank"])
            layers.append(nuisance["nominal_ideal_box_score"] * .25 / projection["maximum"] * profile)
        if case["family"] == "near_off_contamination" and index - 1 in case["active_scan_indices"]:
            profile, centers = _profile(case, scan, geometry, offset=case["reference_native_offset"] + case["diagnostic_off_frequency_offset_channels"])
            projection = _ideal_projection(profile, centers, geometry, contract["box_width_bank"])
            layers.append(case["diagnostic_off_nominal_ideal_box_score"] * .25 / projection["maximum"] * profile)
        injections[index] = layers
    rng = np.random.Generator(np.random.PCG64(int(case["seed_sha256"], 16)))
    for index, scan in enumerate(geometry["scan_metadata"]):
        shape = (scan["nrows"], nchan)
        if law in {"gamma16", "rowgain_gamma16"}:
            power = rng.gamma(shape=16., scale=.0625, size=shape)
            if law == "rowgain_gamma16":
                gain = 1 + .1 * np.sin(2 * np.pi * (np.arange(shape[0]) + .5) / shape[0] + index * np.pi / 3)
                power *= gain[:, None]
        elif law == "gaussian":
            power = 1 + .05 * rng.standard_normal(shape)
        elif law == "frequency_ar1_gaussian":
            innovations = rng.standard_normal(shape)
            process = np.empty(shape)
            process[:, 0] = innovations[:, 0]
            for col in range(1, nchan):
                process[:, col] = .25 * process[:, col - 1] + math.sqrt(1 - .25 ** 2) * innovations[:, col]
            power = 1 + .05 * process
        else:
            raise ValueError(f"Unknown declared noise law: {law}")
        for injection in injections[index]:
            power += injection
        if not np.isfinite(power).all() or (power <= 0).any():
            raise ValueError("Declared synthetic power law failed finite-positive check; no redraw")
        arrays.append(power)
    truth = {"case_id": case["case_id"], "synthetic": True, "family": case["family"],
             "seed_sha256": case["seed_sha256"], "noise_law": law, "flux_by_scan": fluxes,
             "active_scan_indices": case["active_scan_indices"],
             "active_ON_scan_ids": [geometry["scan_metadata"][i]["scan_id"] for i in case["active_scan_indices"]
                                    if geometry["scan_metadata"][i]["role"] == "on"]}
    if "drift_hz_s" in case:
        scan0 = geometry["scan_metadata"][0]
        source_channel = geometry["reference_source_channel_interval"][0] + case["reference_native_offset"]
        truth.update(reference_frequency_hz=scan0["fch1_hz"] + source_channel * scan0["df_hz"],
                     reference_source_channel=source_channel, drift_hz_s=case["drift_hz_s"],
                     intrinsic_width_channels=case["intrinsic_width_channels"])
    return arrays, truth


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write case/seed definitions only; no random values")
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(build_manifests(args.source_manifest, args.output_dir), indent=2))
