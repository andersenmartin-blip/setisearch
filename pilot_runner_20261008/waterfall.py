"""Inert fixed six-panel display helper for one frozen historical visit.

Preparation may read this source or parse its AST; it must not call the helper.
At an admitted runner invocation only, all six already-retained native power
arrays are displayed. This module never opens a source/control array, executes
a detector, selects a candidate/region, or changes input arrays or labels.

Display policy, declared before examining any power values:
* full loaded native interval, every row, six chronological ON/OFF panels;
* frequency groups of eight, maximum power, final partial group retained;
* 10 log10(power / the same native row's full-band median);
* fixed -10 to +20 dB color range, with disclosed color saturation;
* actual integration edges and proportional blank interscan time gaps;
* kHz offsets around the fixed 4096-channel reference-interval center.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from pathlib import Path
from typing import Any


DISPLAY_GROUP_CHANNELS = 8
DISPLAY_MIN_DB = -10.0
DISPLAY_MAX_DB = 20.0
DISPLAY_CMAP = "viridis"
REFERENCE_INTERVAL = (159905792, 159909888)
LOADED_INTERVAL = (159903921, 159911759)
NATIVE_ROWS = 16
NATIVE_COLUMNS = LOADED_INTERVAL[1] - LOADED_INTERVAL[0]
FIGURE_INCHES = (13.0, 15.0)
FIGURE_DPI = 120


def render_waterfall(
    arrays: Sequence[Any], contract: Mapping[str, Any], output_path: str | Path
) -> dict[str, Any]:
    """Render the six retained native arrays and return an explicit display receipt.

``arrays`` must be in the exact order of ``contract['geometry']['scan_metadata']``.
Each scan metadata item supplies ``scan_id``, lower-case ``role``, ``nrows``,
``tstart_mjd``, ``tsamp_s``, ``fch1_hz``, and ``df_hz``. The geometry also supplies
``reference_source_channel_interval`` and ``loaded_source_channel_interval``.

Scientific/plotting imports are intentionally lazy: importing this module is
inert. The helper only accepts retained in-memory arrays; it has no file loader.
The figure is the sole file written. Display reduction/normalization has no
effect on native arrays or detector/classification results.
"""
    geometry = contract["geometry"]
    if tuple(geometry["reference_source_channel_interval"]) != REFERENCE_INTERVAL:
        raise ValueError("Waterfall requires the frozen 4096-channel reference interval")
    if tuple(geometry["loaded_source_channel_interval"]) != LOADED_INTERVAL:
        raise ValueError("Waterfall requires the complete frozen loaded native interval")
    scans = list(geometry["scan_metadata"])
    if len(scans) != 6 or len(arrays) != 6:
        raise ValueError("Waterfall requires all six retained native arrays")
    if [scan["role"] for scan in scans] != ["on", "off"] * 3:
        raise ValueError("Waterfall requires the frozen three ON / three OFF order")
    if len({scan["scan_id"] for scan in scans}) != 6:
        raise ValueError("Waterfall requires six unique scan identifiers")
    output = Path(output_path)
    if output.suffix.lower() != ".png":
        raise ValueError("The single fixed waterfall output must be a PNG")
    if not output.parent.is_dir():
        raise ValueError("Runner must create the waterfall output directory")
    if output.exists():
        raise ValueError("Waterfall refuses to overwrite an existing artifact")

    # Coordinates and scale are fixed from metadata before any power is examined.
    anchor_mjd = float(scans[0]["tstart_mjd"])
    if not math.isfinite(anchor_mjd):
        raise ValueError("Finite scan epochs are required")
    fch1_hz = float(scans[0]["fch1_hz"])
    df_hz = float(scans[0]["df_hz"])
    if not math.isfinite(fch1_hz) or not math.isfinite(df_hz) or df_hz == 0:
        raise ValueError("Finite frequency coordinates and nonzero channel width are required")
    reference_center_source_channel = (REFERENCE_INTERVAL[0] + REFERENCE_INTERVAL[1] - 1) / 2.0
    reference_center_hz = fch1_hz + reference_center_source_channel * df_hz
    scan_geometry = []
    previous_end = None
    for scan in scans:
        if scan["nrows"] != NATIVE_ROWS:
            raise ValueError("All sixteen declared integrations must be displayed")
        if float(scan["fch1_hz"]) != fch1_hz or float(scan["df_hz"]) != df_hz:
            raise ValueError("All six scans must use the frozen common frequency mapping")
        tstart_mjd = float(scan["tstart_mjd"])
        tsamp_s = float(scan["tsamp_s"])
        if not math.isfinite(tstart_mjd) or not math.isfinite(tsamp_s) or tsamp_s <= 0:
            raise ValueError("Finite scan epochs and positive integrations are required")
        start_s = (tstart_mjd - anchor_mjd) * 86400.0
        end_s = start_s + NATIVE_ROWS * tsamp_s
        if previous_end is not None and start_s < previous_end:
            raise ValueError("Scan integration edges must be chronological and nonoverlapping")
        gap_before_s = None if previous_end is None else start_s - previous_end
        scan_geometry.append({
            "scan_id": str(scan["scan_id"]), "role": scan["role"],
            "tstart_mjd": tstart_mjd, "tsamp_s": tsamp_s,
            "start_seconds_from_anchor": start_s,
            "end_seconds_from_anchor": end_s,
            "gap_before_seconds": gap_before_s,
        })
        previous_end = end_s

    # These imports and all value access occur only at the admitted invocation.
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.colors import Normalize
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter

    group_starts = np.arange(0, NATIVE_COLUMNS, DISPLAY_GROUP_CHANNELS, dtype=np.int64)
    group_offsets = np.concatenate((group_starts, np.array([NATIVE_COLUMNS], dtype=np.int64)))
    source_channel_edges = LOADED_INTERVAL[0] - 0.5 + group_offsets
    frequency_edges_hz = fch1_hz + source_channel_edges * df_hz
    frequency_offset_edges_khz = (frequency_edges_hz - reference_center_hz) / 1000.0
    x_limits_khz = sorted([float(frequency_offset_edges_khz[0]),
                           float(frequency_offset_edges_khz[-1])])
    group_sizes = np.diff(group_offsets)
    height_ratios = []
    for index, scan in enumerate(scan_geometry):
        if index:
            height_ratios.append(scan["gap_before_seconds"])
        height_ratios.append(scan["end_seconds_from_anchor"] - scan["start_seconds_from_anchor"])

    figure = Figure(figsize=FIGURE_INCHES, dpi=FIGURE_DPI, facecolor="white")
    canvas = FigureCanvasAgg(figure)
    grid = figure.add_gridspec(11, 1, height_ratios=height_ratios,
                              left=0.20, right=0.87, bottom=0.08, top=0.92,
                              hspace=0.0)
    # Normalize is fixed for every panel; no quantiles or value-derived limits.
    norm = Normalize(vmin=DISPLAY_MIN_DB, vmax=DISPLAY_MAX_DB, clip=False)
    panel_receipts = []
    mesh = None
    try:
        for index, (retained, scan) in enumerate(zip(arrays, scan_geometry)):
            native = np.asarray(retained)
            if native.shape != (NATIVE_ROWS, NATIVE_COLUMNS) or native.dtype.str != "<f4":
                raise ValueError("Every panel requires its complete native 16x7838 little-endian float32 array")
            if not np.isfinite(native).all() or np.any(native < 0):
                raise ValueError("Missing, nonfinite, or negative native power cannot be silently hidden")
            # np.median/reduceat create separate display results; neither writes native.
            row_medians = np.median(native.astype(np.float64, copy=True), axis=1)
            if not np.isfinite(row_medians).all() or np.any(row_medians <= 0):
                raise ValueError("Every full native row must have a finite positive median")
            grouped_power = np.maximum.reduceat(native, group_starts, axis=1).astype(np.float64)
            display_db = np.full(grouped_power.shape, -np.inf, dtype=np.float64)
            positive = grouped_power > 0
            np.log10(grouped_power, out=display_db, where=positive)
            display_db = 10.0 * (display_db - np.log10(row_medians)[:, None])
            # Matplotlib masks -inf automatically. Represent only zero-power groups
            # with an explicit under-range color value so they remain visible; this
            # display-only convention is disclosed in the figure and receipt.
            color_db = np.where(positive, display_db, DISPLAY_MIN_DB - 1.0)
            row_edges_s = scan["start_seconds_from_anchor"] + np.arange(NATIVE_ROWS + 1) * scan["tsamp_s"]
            axis = figure.add_subplot(grid[2 * index, 0])
            mesh = axis.pcolormesh(frequency_offset_edges_khz, row_edges_s, color_db,
                                   cmap=DISPLAY_CMAP, norm=norm, shading="flat",
                                   rasterized=True)
            axis.set_xlim(*x_limits_khz)
            axis.set_ylim(scan["end_seconds_from_anchor"], scan["start_seconds_from_anchor"])
            axis.set_yticks([scan["start_seconds_from_anchor"],
                            (scan["start_seconds_from_anchor"] + scan["end_seconds_from_anchor"]) / 2,
                            scan["end_seconds_from_anchor"]])
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:.1f}"))
            axis.tick_params(axis="both", labelsize=8)
            axis.tick_params(axis="x", labelbottom=index == 5, bottom=index == 5)
            axis.text(-0.15, 0.5,
                      f"{index + 1}/6 {scan['role'].upper()}\n{scan['scan_id']}\nMJD {scan['tstart_mjd']:.9f}",
                      transform=axis.transAxes, ha="right", va="center", fontsize=8)
            if index == 5:
                axis.set_xlabel("Frequency offset from fixed reference-band center (kHz)", fontsize=10)
            panel_receipts.append({
                **scan,
                "native_shape": list(native.shape), "native_dtype": native.dtype.str,
                "row_integration_edges_seconds_from_anchor": row_edges_s.tolist(),
                "row_native_full_band_power_median": row_medians.tolist(),
                "display_shape": list(display_db.shape),
                "zero_power_display_groups": int(np.count_nonzero(~positive)),
                "display_groups_below_fixed_color_min": int(np.count_nonzero(display_db < DISPLAY_MIN_DB)),
                "display_groups_above_fixed_color_max": int(np.count_nonzero(display_db > DISPLAY_MAX_DB)),
            })
        figure.suptitle("ONE historical visit — 3 ON + 3 OFF (3ON3OFF)",
                       fontsize=14, y=0.975)
        figure.text(0.04, 0.5, "Elapsed seconds from first scan start; actual gaps preserved",
                    rotation=90, ha="center", va="center", fontsize=10)
        color_axis = figure.add_axes([0.90, 0.30, 0.018, 0.40])
        colorbar = figure.colorbar(mesh, cax=color_axis, extend="both")
        colorbar.set_label("dB relative to each native row's full-band median", fontsize=9)
        colorbar.ax.tick_params(labelsize=8)
        figure.text(0.20, 0.035,
                    "Display only: maximum of each 8-channel group; final 6-channel group kept. "
                    "Fixed −10…+20 dB colors saturate outside range; zero power uses the low-end color.",
                    ha="left", va="center", fontsize=8)
        canvas.print_png(str(output), metadata={
            "Title": "ONE historical visit — 3 ON + 3 OFF (3ON3OFF)",
            "Description": "Complete frozen six-scan native-band waterfall; fixed display policy.",
            "Software": "pilot_runner_20261008.waterfall",
        })
    finally:
        figure.clear()

    return {
        "status": "FIXED_SIX_PANEL_WATERFALL_RENDERED",
        "output_path": str(output.resolve()),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "historical_visits": 1, "panel_count": 6,
        "panel_roles": [scan["role"] for scan in scan_geometry],
        "chronological_scan_ids": [scan["scan_id"] for scan in scan_geometry],
        "mjd_anchor": anchor_mjd,
        "reference_source_channel_interval_half_open": list(REFERENCE_INTERVAL),
        "loaded_source_channel_interval_half_open": list(LOADED_INTERVAL),
        "reference_center_source_channel": reference_center_source_channel,
        "reference_center_hz": reference_center_hz,
        "x_units": "kHz offset from fixed reference-band center",
        "x_display_limits_khz": x_limits_khz,
        "display_reduction": "maximum power in consecutive groups of eight native frequency channels",
        "display_group_sizes_channels": group_sizes.tolist(),
        "last_partial_group_retained": True,
        "row_normalization": "10 log10(group maximum power / full loaded native row median)",
        "fixed_color_min_db": DISPLAY_MIN_DB, "fixed_color_max_db": DISPLAY_MAX_DB,
        "fixed_colormap": DISPLAY_CMAP,
        "color_saturation_outside_fixed_range": True,
        "zero_power_display": "under-range color; original dB remains negative infinity",
        "row_edges_are_actual_integrations": True,
        "blank_gap_heights_proportional_to_actual_seconds": True,
        "native_arrays_mutated": False, "classification_mutated": False,
        "all_native_rows_and_channels_displayed": True,
        "candidate_region_selection_or_overlays": False,
        "figure_pixel_size": [int(FIGURE_INCHES[0] * FIGURE_DPI), int(FIGURE_INCHES[1] * FIGURE_DPI)],
        "panels": panel_receipts,
    }
