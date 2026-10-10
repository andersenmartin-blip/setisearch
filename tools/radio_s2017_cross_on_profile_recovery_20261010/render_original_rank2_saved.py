"""One saved-only display of the preselected original cross-ON rank 2.

No scientific producer/QA module is imported. Only four arrays from the new
already-QA-admitted NPZ are decoded: geometry index, logical time, residual,
and scan labels. No normalization, median, matching, fit, ranking or source
HDF5 operation occurs. Each displayed coordinate is a saved float64 value.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

FAMILY = "radio_s2017_cross_on_profile_recovery_20261010"
CPU_CAP = 30
WALL_CAP = 120
MEMORY_CAP = 1073741824
EXPECTED_QA_SHA = "542659607565595ec77074fadcd98d236eda8b126da8a09414c8696baa0fd7dc"
EXPECTED_SCOPE_SHA = "ba699556755e7b0621c8972e61f609f62f8b87ca8e37c6c7c9d8cb4242df8506"
EXPECTED_FREEZE = "afa74530e81fad064bf97d60bbc501696377009a"
EXPECTED_PUBLISHER_SHA = "98330391a76d1fa9b0138f1ecd62be1ef0c5a4c3ac3bdc2a5963538c5aa9434a"
ARRAYS = ("logical_geometry_indices", "logical_times_seconds_from_original_reference",
          "geometry_center_minus_flank_rows", "scans")


def main():
    start_wall = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 2))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("Finite display wall limit")))
    signal.alarm(WALL_CAP)
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    stage = root / "results" / FAMILY
    tools = root / "tools" / FAMILY
    outdir = stage / "presentation"
    outdir.mkdir(exist_ok=True)
    marker = outdir / "RANK2_RENDER_STARTED_ONCE.json"
    script_pin = {"path": str(Path(__file__).resolve()),
                  "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "bytes": Path(__file__).stat().st_size}
    with marker.open("x") as stream:
        json.dump({"scope": "One original rank2 saved-residual figure, no retry",
                   "script_pin": script_pin, "CPU_cap_s": CPU_CAP,
                   "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP}, stream)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pins = {}

    def read_pin(path, expected=None, decode_json=True):
        path = Path(path)
        raw = path.read_bytes()
        pin = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if expected is not None and pin != expected:
            raise ValueError("Saved input byte pin differs: " + str(path))
        pins[str(path)] = pin
        return json.loads(raw) if decode_json else pin

    qa = read_pin(stage / "review/QA_RECEIPT.json")
    assert pins[str(stage / "review/QA_RECEIPT.json")]["sha256"] == EXPECTED_QA_SHA
    scope = read_pin(tools / "scope.json")
    assert pins[str(tools / "scope.json")]["sha256"] == EXPECTED_SCOPE_SHA
    execution = read_pin(stage / "measurement/EXECUTION_RECEIPT.json")
    outer = read_pin(stage / "ROOT_OUTER_EXECUTION_RECEIPT.json")
    index = read_pin(stage / "measurement/FIXED_ALL_SIX_PROFILES.json")
    assert qa["status"] == "PASS_635_TRIPLES_11430_FIXED_PROFILE_OUTPUTS_AND23465616_RAW_CELL_OCCURRENCE_DIGESTS"
    assert execution["status"] == "COMPLETE_635_S2017_MATCHED_TRIPLES_ALL_SIX_FIXED_PROFILES_EXPLORATORY_ONLY"
    assert outer["status"] == "PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS" and outer["child_exit_code"] == 0
    assert qa["execution_receipt_sha256"] == outer["inner_terminal_sha256"] == pins[str(stage / "measurement/EXECUTION_RECEIPT.json")]["sha256"]
    assert qa["outer_execution_receipt_sha256"] == pins[str(stage / "ROOT_OUTER_EXECUTION_RECEIPT.json")]["sha256"]
    assert qa["scope_sha256"] == execution["scope_sha256"] == EXPECTED_SCOPE_SHA
    assert qa["public_profile_freeze_commit"] == execution["public_freeze_commit"] == outer["freeze_commit"] == EXPECTED_FREEZE
    qa_pins = {p["path"]: p for p in qa["all_input_byte_pins"]}
    assert len(qa_pins) == len(qa["all_input_byte_pins"])
    assert qa_pins[str(stage / "measurement/FIXED_ALL_SIX_PROFILES.json")] == pins[str(stage / "measurement/FIXED_ALL_SIX_PROFILES.json")]
    records = []
    for member_file in index["origin_record_files"]:
        assert qa_pins[member_file["file_pin"]["path"]] == member_file["file_pin"]
        member_json = read_pin(member_file["file_pin"]["path"], member_file["file_pin"])
        chosen = [x for x in member_json["records"] if x["original_display_rank"] == 2]
        assert len(chosen) == 1
        records.append(chosen[0])
    assert [x["member_scan_id"] for x in records] == scope["scans"][::2]
    assert [x["logical_member_index"] for x in records] == [0, 1, 2]
    assert len({x["match_id"] for x in records}) == 1
    original_top = read_pin(scope["matching_TOP_pin"]["path"], scope["matching_TOP_pin"])
    top_rank2 = [x for x in original_top["records"] if x["display_rank"] == 2]
    assert len(top_rank2) == 1 and top_rank2[0]["match_id"] == records[0]["match_id"]
    assert top_rank2[0]["members"] == [x["original_member"] for x in records]
    npz_pin = index["compact_arrays_pin"]
    assert qa_pins[npz_pin["path"]] == npz_pin
    read_pin(npz_pin["path"], npz_pin, decode_json=False)
    publisher = tools / "rank2_png_publish.py"
    publisher_pin = read_pin(publisher, decode_json=False)
    assert publisher_pin["sha256"] == EXPECTED_PUBLISHER_SHA
    spec = importlib.util.spec_from_file_location("rank2_display_png_publish", publisher)
    publication = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publication)
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import MaxNLocator
    with np.load(npz_pin["path"], allow_pickle=False) as saved:
        logical = saved[ARRAYS[0]]
        times = saved[ARRAYS[1]]
        residuals = saved[ARRAYS[2]]
        scans = saved[ARRAYS[3]]
    assert logical.shape == (1905, 6) and logical.dtype.str == "<i4"
    assert times.shape == (1905, 6, 16) and times.dtype.str == "<f8"
    assert residuals.shape == (11369, 16) and residuals.dtype.str == "<f8"
    assert scans.shape == (6,) and scans.tolist() == scope["scans"]
    plotted = []
    fig, axes = plt.subplots(3, 6, figsize=(19.2, 9.6), dpi=120, sharey="row")
    fig.subplots_adjust(left=0.067, right=0.986, bottom=0.177, top=0.805, wspace=0.15, hspace=0.61)
    fig.suptitle("Original cross-ON rank 2 — three unchanged member paths, all six scans", x=0.067, y=0.971, ha="left", fontsize=17, weight="bold")
    fig.text(0.067, 0.927, "Same visit: 28 April 2017  |  Posthoc ON selection  |  16 saved integration residuals in every panel", fontsize=11)
    fig.text(0.067, 0.902, "ON: solid blue  ·  OFF: dashed orange  ·  Shaded panel: this path's original ON  ·  Dotted horizontal line: saved scan mean", fontsize=10, color="#444444")
    scan_names = ["ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3"]
    for ri, record in enumerate(records):
        member_index = record["logical_member_index"]
        source = record["original_member"]
        key = source["original_key"]
        expected_indices = [s["geometry_index"] for s in record["scan_profiles"]]
        assert logical[member_index].tolist() == expected_indices
        row_values = residuals[logical[member_index]]
        row_times = times[member_index]
        assert np.isfinite(row_values).all() and np.isfinite(row_times).all()
        low = min(0.0, float(row_values.min()))
        high = max(0.0, float(row_values.max()))
        padding = max((high - low) * 0.12, 0.01)
        row_y_range = [low - padding, high + padding]
        row_top = axes[ri, 0].get_position().y1
        description = (f"Path from {scan_names[ri * 2]}:  f at its original reference = {source['original_reference_frequency_hz'] / 1e6:.9f} MHz"
                       f"   |   drift = {key['drift_hz_s']:+.9f} Hz/s   |   width = {key['width_channels']} channel")
        fig.text(0.067, row_top + 0.050, description, fontsize=11, weight="bold")
        for si, ax in enumerate(axes[ri]):
            scan_record = record["scan_profiles"][si]
            assert scan_record["scan_id"] == scans[si]
            g = scan_record["geometry_index"]
            assert scan_record["row_array_ref"] == {"file": "COMPACT_FIXED_PROFILES.npz", "array": ARRAYS[2], "index": g}
            values, x = row_values[si], row_times[si]
            assert np.all(np.diff(x) > 0)
            assert math.isclose(float(values.mean()), scan_record["metrics"]["mean"], rel_tol=1e-12, abs_tol=1e-12)
            origin = si == 2 * ri
            color = "#125da5" if si % 2 == 0 else "#b65c16"
            ax.plot(x, values, color=color, linestyle="-" if si % 2 == 0 else "--",
                    marker="o" if si % 2 == 0 else "s", markersize=3.2, linewidth=1.1)
            ax.axhline(0, color="#505050", linewidth=0.65, zorder=0)
            ax.axhline(scan_record["metrics"]["mean"], color=color, linestyle=":", linewidth=0.8)
            ax.set_ylim(*row_y_range)
            ax.set_xlim(float(x[0]) - 10, float(x[-1]) + 10)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.tick_params(labelsize=9)
            ax.grid(axis="y", color="#dddddd", linewidth=0.5, alpha=0.8)
            ax.set_title(f"{scan_names[si]}{' (origin)' if origin else ''}\nmean {scan_record['metrics']['mean']:+.5f}", fontsize=10, color=color, pad=6)
            if origin:
                ax.set_facecolor("#edf4fa")
                for spine in ax.spines.values():
                    spine.set_linewidth(1.35)
                    spine.set_edgecolor(color)
            if si == 0:
                ax.set_ylabel("Power / saved row median\nminus flank median", fontsize=10)
            plotted.append({"logical_member_index": member_index, "original_member_scan_id": record["member_scan_id"],
                            "scan_id": str(scans[si]), "geometry_index": g,
                            "x_exact_saved_float64_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
                            "y_exact_saved_float64_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
                            "saved_mean": scan_record["metrics"]["mean"], "row_y_axis_range": row_y_range,
                            "saved_time_range_seconds": [float(x[0]), float(x[-1])]})
    fig.text(0.53, 0.127, "Seconds from this path's original ON first-integration midpoint — each row retains its own zero", ha="center", fontsize=11)
    fig.text(0.067, 0.080, "Descriptive signed normalized residuals; these are not calibrated SNR. ON/OFF comparisons are within each fixed member path.", fontsize=10)
    fig.text(0.067, 0.052, "Posthoc same-visit selection is biased and correlated. Transported OFF residuals do not rule out nearby OFF structure or establish an origin.", fontsize=10)
    fig.text(0.067, 0.025, "Exact saved 288 values shown; no refit, new normalization, median, score, matching, selection, or raw-source read. Y range is shared across six panels within each row.", fontsize=9, color="#444444")
    figure_path = outdir / "ORIGINAL_CROSS_ON_RANK2_ALL_SIX_SAVED_RESIDUALS.png"
    verified = publication.save_figure_atomic(fig, figure_path, dpi=120, facecolor="white")
    plt.close(fig)
    for pin in pins.values():
        assert Path(pin["path"]).stat().st_size == pin["bytes"]
        assert hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest() == pin["sha256"]
    assert script_pin["sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    cpu = time.process_time()
    elapsed = time.monotonic() - start_wall
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    caps = cpu <= CPU_CAP and elapsed <= WALL_CAP and rss <= MEMORY_CAP
    receipt = {"status": "COMPLETE_ONE_ORIGINAL_RANK2_SAVED_ONLY_FIGURE" if caps else "COMPLETE_DISPLAY_RESOURCE_CAP_EXCEEDED_NO_RETRY",
               "script_pin": script_pin, "input_pins": list(pins.values()),
               "profile_public_freeze_commit": EXPECTED_FREEZE, "profile_scope_sha256": EXPECTED_SCOPE_SHA,
               "QA_receipt_sha256": EXPECTED_QA_SHA, "preselected_original_rank": 2,
               "preselected_match_id": records[0]["match_id"], "source_arrays_decoded": list(ARRAYS),
               "saved_values_plotted": 288, "plotted_panels": plotted,
               "output": {"path": str(figure_path), **verified}, "all_input_end_readbacks_exact": True,
               "profiles_remeasured": False, "normalization_or_medians_recomputed": False,
               "matching_or_detector_or_fitting_or_ranking_reexecuted": False, "H5_source_opened": False,
               "new_HTTP_requests": 0, "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP,
               "memory_cap_bytes": MEMORY_CAP, "process_CPU_seconds_including_imports": cpu,
               "wall_seconds": elapsed, "peak_RSS_bytes": rss, "resource_caps_satisfied": caps,
               "visual_QA": "Pending actual image view; independent receipt follows",
               "limitations": index["limitations"]}
    with (outdir / "RANK2_PLOTTING_RECEIPT.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "output": receipt["output"],
                      "process_CPU_seconds": cpu, "resource_caps_satisfied": caps}))


if __name__ == "__main__":
    main()
