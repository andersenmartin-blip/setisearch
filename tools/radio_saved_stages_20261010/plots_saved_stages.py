#!/usr/bin/env python3
"""Two pinned saved-JSON figures for an originally COMPLETE future stage.

Root GO and an exact prospective POSTPROCESSING_SCOPE pin are required before
opening any outcome. Both rolling155157 and native158 keep chunk/batch/ON
selections separate. Every original numerical job, acquisition QA, output QA
and source-cell audit must pass the configured COMPLETE-only contracts.
No current exceptional-output admission, HDF5/NPZ access, numerical search,
residual recomputation, new selection, or cross-batch reranking is inherited.
Rendering preserves the prior saved-profile display: six stable scan columns,
signed annotations, and one shared actual symmetric color scale.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import time

WALL_START = time.monotonic()
CPU_CAP = 60
MEMORY_CAP = 4 * 1024**3
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP))
resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np
import common_json as saved
import summarize_saved as contracts
import png_publish

PROTECTED_RENDERER = "tools/radio_next_bands_20261010/plots_qualified_saved.py"
PROTECTED_RENDERER_SHA256 = "f122449e317d90b8c08f7c259e193c014022b76c44828f470942551b39564f3c"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_complete_stage(reader, stage_id, expected_post_sha):
    post, config, chunks = contracts.configure(reader, stage_id, expected_post_sha)
    for module_path in (Path(__file__), Path(saved.__file__), Path(contracts.__file__),
                        Path(png_publish.__file__)):
        relative = str(module_path.resolve().relative_to(reader.root))
        if post["pinned_dependency_files"].get(relative) != digest(module_path):
            raise ValueError("This exact renderer and all saved-contract/PNG helper modules must be public-scope pinned")
    required = contracts.required_inputs(config, chunks)
    if set(reader.pins) != required:
        raise ValueError("Exact finite prospective saved-JSON index required")
    activation = reader.load(config["activation_path"])
    scope = reader.load(config["numerical_scope_path"])
    if (reader.pins[config["numerical_scope_path"]] != config["numerical_scope_sha256"]
            or scope["script_sha256"] != config["numerical_wrapper_sha256"]):
        raise ValueError("Original numeric scope/wrapper differs from the fixed stage configuration")
    selection = contracts.geometry(activation, scope, config, chunks)
    acquisitions = {str(c): saved.acquisition_metadata(reader, scope, c) for c in chunks}
    batches = [saved.load_batch(reader, scope, c, b, selection, acquisitions[str(c)])
               for c in chunks for b in (1, 2)]
    expected_jobs = [(c, b) for c in chunks for b in (1, 2)]
    if [(j["source_chunk_id"], j["batch_id"]) for j in config["jobs"]] != expected_jobs:
        raise ValueError("Configured future stage jobs differ from the fixed chunk/batch inventory")
    for batch, job in zip(batches, config["jobs"]):
        prefix = (f'{config["results_directory"]}/chunk{batch["source_chunk_id"]}/'
                  f'batch_{batch["batch_id"]:02d}/measurement/')
        if (job["measurement_directory"] != prefix.rstrip("/")
                or job["QA_receipt_path"] != prefix + "QA_RECEIPT.json"
                or job["required_original_status"] != saved.COMPLETE_STATUS
                or job["required_QA_status"] != "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
                or job["fixed_batch_q"] != selection["batch_q"][batch["batch_id"] - 1]):
            raise ValueError("Prospective job paths/status gates/core selections changed")
        reader.load(prefix + "NORMALIZATION.json")
        execution = reader.load(prefix + "EXECUTION_RECEIPT.json")
        qa = reader.load(prefix + "QA_RECEIPT.json")
        if (not batch["execution_complete"] or not batch["checkpoint_all_tiles_present"]
                or batch["completed_scan_tiles"] != 381 or batch["profile_count"] != 9
                or batch["status"] != job["required_original_status"]
                or batch["QA_status"] != job["required_QA_status"]
                or execution["saved_normalization_sha256"] != reader.pins[prefix + "NORMALIZATION.json"]
                or qa["qa_script_sha256"] != config["local_QA_script_sha256"]):
            raise ValueError("Every original COMPLETE and actual matching saved-output QA is required")
    if any(a["acquisition_source_QA_status"] != "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
           for a in acquisitions.values()):
        raise ValueError("Every actual acquisition/source QA must pass before rendering")
    profiles = [p for batch in batches for p in batch["profiles"]]
    if (len(profiles) != 18 * len(chunks)
            or len({tuple(p["identity"]) for p in profiles}) != len(profiles)):
        raise ValueError("All fixed profile composite identities must be present and unique")
    audit = contracts.source_audit(reader, scope, config, profiles, chunks)
    if set(reader.opened) != required:
        raise ValueError("Every required saved-JSON input must be read and pinned")
    expected_paths = [config["results_directory"] + "/figures/STAGE_COVERAGE.png",
                      config["results_directory"] + "/figures/STAGE_FIXED_PROFILE_MEANS.png"]
    if config["figure_paths"] != expected_paths:
        raise ValueError("Figure paths must remain separate inside the configured stage")
    return post, config, chunks, batches, profiles, audit


def plot_coverage(path, chunks, batches, stage_id):
    row_count = 3 * len(chunks)
    raster = np.full((row_count, 256), 3, dtype=np.int8)
    raster[:, [0, 255]] = 0
    by_job = {(b["source_chunk_id"], b["batch_id"]): b for b in batches}
    counts, labels = [], []
    for row, (chunk, scan) in enumerate((c, s) for c in chunks for s in saved.ONS):
        actual = set()
        for batch_id in (1, 2):
            q = by_job[(chunk, batch_id)]["completed_q_by_ON"][scan]
            raster[row, q] = batch_id
            actual.update(q)
        count = len(actual)
        labels.append(f"Chunk{chunk} {saved.SHORT[scan]}\n{count}/256 cores ({count / 256:.5%})")
        counts.append({"source_chunk_id": chunk, "scan_id": scan,
                       "actual_completed_core_q": sorted(actual),
                       "completed_core_count": count, "reference_channels": count * 4096,
                       "native_chunk_fraction": count / 256})
    colors = ["#292f36", "#197fa3", "#cf7b27", "#f0f0f0"]
    cmap = ListedColormap(colors)
    fig, ax = plt.subplots(figsize=(14.8, 6.8 if len(chunks) == 1 else 8.5))
    ax.imshow(raster, cmap=cmap, norm=BoundaryNorm(np.arange(-.5, 4.5), cmap.N),
              interpolation="nearest", aspect="auto", extent=(-.5, 255.5, row_count - .5, -.5))
    ax.set_yticks(range(row_count), labels, fontsize=10)
    ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
    ax.set_xlim(-.5, 255.5)
    ax.set_ylim(row_count - .5, -.5)
    ax.set_xlabel("Reference core q (4096 native channels per core)", fontsize=11, labelpad=10)
    ax.axvline(127.5, color="black", linewidth=.6, alpha=.45)
    for row in range(3, row_count, 3):
        ax.axhline(row - .5, color="black", linewidth=1.3, linestyle="--")
    ax.set_title(f"{stage_id}: exact reference-carrier coverage\n"
                 "Actual completed ON/core receipts · all original executions COMPLETE", fontsize=13, pad=17)
    legend = [Patch(facecolor=c, edgecolor="#555555", linewidth=.5, label=l)
              for c, l in zip(colors, ("Excluded edge cores", "Batch 01 completed",
                                       "Batch 02 completed", "No completed map receipt"))]
    fig.legend(handles=legend, loc="upper center", bbox_to_anchor=(.55, .855),
               ncol=4, frameon=False, fontsize=9)
    lines = [f"C{b['source_chunk_id']} B{b['batch_id']:02d}: "
             f"{b['completed_scan_tiles']}/381 map receipts · original COMPLETE · saved/source QA PASS"
             for b in batches]
    fig.text(.55, .135, "\n".join(lines), ha="center", va="center", fontsize=9)
    fig.text(.55, .050,
             "254/256 reference cores = 99.21875% per native band for this fixed drift grid and widths1/3.\n"
             "One historical visit · coverage is not survey or sensitivity completeness.\n"
             "Two edge cores excluded per band · read/trajectory halos may overlap.",
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.20, right=.98, top=.75, bottom=.255)
    publication = png_publish.save_figure_atomic(fig, path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned COMPLETE-only saved-stage renderer",
                          "Description": "Actual saved ON/core receipt metadata; no numerical rerun"})
    plt.close(fig)
    return {"coverage_by_chunk_ON": counts, "raster_int8_sha256": hashlib.sha256(raster.tobytes()).hexdigest(),
            "coverage_basis": "Actual checkpoint completed_receipts, checked by the pinned saved-JSON contract",
            "reference_core_denominator_per_native_chunk": 256, "core_channel_count": 4096,
            "PNG_atomic_publication": publication}


def plot_means(path, profiles, stage_id):
    means = np.asarray([[p["all_six_fixed_scan_measures"][s]["mean_center_minus_flank"]
                         for s in saved.SCANS] for p in profiles], dtype=np.float64)
    if not np.isfinite(means).all():
        raise ValueError("Every saved fixed-profile mean must be finite")
    limit = max(float(np.max(np.abs(means))) * 1.05, 1e-9)
    labels = [f"C{p['source_chunk_id']} B{p['batch_id']:02d} "
              f"{saved.SHORT[p['originating_scan']]} r{p['display_rank_within_batch_and_ON']}\n"
              f"{p['reference_frequency_hz'] / 1e6:.6f} MHz · {p['drift_hz_s']:+.6f} Hz/s · "
              f"w{p['width_channels']} · q{p['reference_core_q']}" for p in profiles]
    n = len(profiles)
    fig, ax = plt.subplots(figsize=(14.6, max(10.2, .62 * n + 3.1)))
    im = ax.imshow(means, cmap="RdBu_r", vmin=-limit, vmax=limit,
                   interpolation="nearest", aspect="auto")
    ax.set_xticks(range(6), [saved.SHORT[s] for s in saved.SCANS], fontsize=11)
    ax.set_yticks(range(n), labels, fontsize=9)
    ax.set_xlim(-.5, 5.5)
    ax.set_ylim(n - .5, -.5)
    ax.set_xlabel("Scan evaluated on the same saved fixed path (all six scans)", fontsize=10, labelpad=12)
    for row in range(n):
        if row and profiles[row]["source_chunk_id"] != profiles[row - 1]["source_chunk_id"]:
            ax.axhline(row - .5, color="#222222", linewidth=2.1)
        elif row and profiles[row]["batch_id"] != profiles[row - 1]["batch_id"]:
            ax.axhline(row - .5, color="#333333", linewidth=1.4, linestyle="--")
        for col in range(6):
            rgba = im.cmap(im.norm(means[row, col]))
            luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
            ax.text(col, row, f"{means[row, col]:+.3f}", ha="center", va="center", fontsize=10,
                    color="black" if luminance > .55 else "white")
    color = fig.colorbar(im, ax=ax, fraction=.038, pad=.028)
    color.set_label("Saved mean center minus fixed flank\n(row-normalized power; not SNR)",
                    fontsize=10, labelpad=11)
    ax.set_title(f"{stage_id}: saved fixed-profile means across all six scans\n"
                 f"{n} selected paths · original top3 perON within each chunk/batch · one historical visit",
                 fontsize=12, pad=17)
    fig.text(.56, .030,
             "Chunk/batch-specific display ranks · no global reranking · fixed shift0 · post-selection description.\n"
             "All six exact-path means retained; adjacent OFF controls are described in the report/JSON.\n"
             "No OFF veto or origin classification; small exact-path OFF means do not rule out nearby features.",
             ha="center", va="center", fontsize=9)
    fig.subplots_adjust(left=.36, right=.90, top=.905, bottom=.105)
    publication = png_publish.save_figure_atomic(fig, path, dpi=125, bbox_inches="tight", pad_inches=.2,
                metadata={"Software": "Pinned COMPLETE-only saved-stage renderer",
                          "Description": "Unchanged saved six-scan means; separate chunk/batch/ON ranks"})
    plt.close(fig)
    return {"saved_mean_count_displayed": int(means.size),
            "symmetric_color_limits": [-limit, limit],
            "actual_minimum_saved_mean": float(np.min(means)), "actual_maximum_saved_mean": float(np.max(means)),
            "all_actual_saved_means_inside_color_limits": bool(np.all(np.abs(means) < limit)),
            "saved_means_float64_sha256": hashlib.sha256(means.tobytes()).hexdigest(),
            "case_identities_in_saved_order": [p["identity"] for p in profiles], "global_reranking": False,
            "PNG_atomic_publication": publication}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--stage-id", choices=sorted(contracts.ALLOWED), required=True)
    parser.add_argument("--pins", required=True, type=Path)
    parser.add_argument("--expected-postprocessing-scope-sha256", required=True)
    parser.add_argument("--postprocessing-freeze-commit", required=True)
    parser.add_argument("--root-authorized-plot-read", action="store_true")
    args = parser.parse_args()
    if not args.root_authorized_plot_read:
        raise SystemExit("Public prospective scope and root GO required before outcome reads")
    if (len(args.postprocessing_freeze_commit) != 40
            or any(c not in "0123456789abcdef" for c in args.postprocessing_freeze_commit)):
        raise ValueError("Exact public prospective postprocessing commit required")
    root = args.root.resolve()
    if digest(root / PROTECTED_RENDERER) != PROTECTED_RENDERER_SHA256:
        raise ValueError("Current exceptional-output renderer must remain byte-unchanged")
    reader = saved.PinnedJSON(root, args.pins)
    post, config, chunks, batches, profiles, audit = read_complete_stage(
        reader, args.stage_id, args.expected_postprocessing_scope_sha256)
    paths = [(root / name).resolve() for name in config["figure_paths"]]
    output = paths[0].parent
    if (any(not p.is_relative_to(root) or p.parent != output for p in paths)
            or output.exists()):
        raise ValueError("New separate configured stage figure directory required; no overwrite/retry")
    reader.unchanged()
    output.mkdir(parents=True, exist_ok=False)
    details = [plot_coverage(paths[0], chunks, batches, args.stage_id),
               plot_means(paths[1], profiles, args.stage_id)]
    reader.unchanged()
    if digest(root / PROTECTED_RENDERER) != PROTECTED_RENDERER_SHA256:
        raise ValueError("Current exceptional-output renderer changed during future stage rendering")
    cpu = time.process_time()
    cap_pass = cpu <= CPU_CAP
    receipt = {
        "schema": "SETI_CONFIGURED_ORIGINAL_COMPLETE_SAVED_PLOTTING_V1",
        "status": ("COMPLETE_TWO_ORIGINAL_COMPLETE_SAVED_JSON_FIGURES" if cap_pass else
                   "COMPLETE_TWO_FIGURES_PLOTTING_CPU_CAP_EXCEEDED_NO_RETRY"),
        "stage_id": args.stage_id, "source_chunk_ids": list(chunks),
        "all_original_numeric_executions_COMPLETE": True, "original_execution_statuses_rewritten": False,
        "acquisition_source_QA_passed": True, "all_saved_output_QA_passed": True,
        "source_cell_audit": audit, "script_sha256": digest(Path(__file__)),
        "postprocessing_scope_sha256": reader.pins[contracts.POST_SCOPE],
        "postprocessing_freeze_commit": args.postprocessing_freeze_commit,
        "numerical_scope_sha256": config["numerical_scope_sha256"],
        "numerical_wrapper_sha256": config["numerical_wrapper_sha256"],
        "original_scientific_freeze_commit": config["original_scientific_freeze_commit"],
        "pinned_postprocessing_dependencies": post["pinned_dependency_files"],
        "input_pins_sha256": reader.pins_sha, "opened_input_JSON": reader.opened,
        "all_opened_input_JSON_byte_unchanged": True,
        "protected_current_renderer_sha256": PROTECTED_RENDERER_SHA256,
        "protected_current_renderer_byte_unchanged": True,
        "case_count": len(profiles), "scan_mean_count": 6 * len(profiles),
        "actual_completed_map_receipts": sum(b["completed_scan_tiles"] for b in batches),
        "scientific_rerun_or_residual_recomputation": False, "HDF5_or_NPZ_opened": False,
        "global_reranking": False, "one_historical_visit": True,
        "OFF_veto": False, "origin_classification": False,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "process_CPU_seconds_including_imports": cpu, "cpu_cap_seconds": CPU_CAP,
        "measured_CPU_within_cap": cap_pass, "CPU_excess_seconds": max(0.0, cpu - CPU_CAP),
        "OS_RLIMIT_CPU_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
        "wall_seconds_including_imports": time.monotonic() - WALL_START,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "matplotlib_version": matplotlib.__version__, "numpy_version": np.__version__,
        "plots": [{"path": str(path.relative_to(root)), "sha256": digest(path),
                   "bytes": path.stat().st_size, **detail} for path, detail in zip(paths, details)],
        "visual_QA": "Pending separate original-detail inspection of both actual saved PNGs",
        "limitations": ["Reference-carrier coverage is specific to the fixed grid/widths in these bands",
                        "All scans are one historical visit; selected profiles are not counts of independent signals",
                        "Small exact-path OFF means do not establish absence of nearby OFF features",
                        "Source and output QA receipts were read; no raw-source audit was rerun by this renderer"],
    }
    receipt_path = output / "PLOTTING_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "stage_id": args.stage_id,
                      "case_count": len(profiles), "process_CPU_seconds": cpu,
                      "measured_CPU_within_cap": cap_pass, "receipt_sha256": digest(receipt_path),
                      "plots": [str(p.relative_to(root)) for p in paths]}))


if __name__ == "__main__":
    main()
