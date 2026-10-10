#!/usr/bin/env python3
"""Repair three summary plot layouts using saved120-case JSON values only.

Preserves the selected cases, original role/width groups, values, boxplot
definitions and titles. Only the canvas, margins and x-axis display limits
change. No source decoding, new scientific measurements or rescoring.
"""
import argparse
import hashlib
import json
import os
import resource
import time
from pathlib import Path

CPU_START = time.process_time()
WALL_START = time.monotonic()
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SPECIFICATIONS = (
    (["mean_center_minus_flank"], "ORIGIN_MEAN_BY_ROLE_WIDTH.png",
     "Mean by original role and width"),
    (["minimum_of_half_means"], "ORIGIN_MIN_HALF_BY_ROLE_WIDTH.png",
     "Lower of fixed first/last half means"),
    (["channel0_minus_immediate_neighbor_mean",
      "selected_width_center_minus_outer_neighbor_mean"],
     "ORIGIN_SHAPE_BY_ROLE_WIDTH.png",
     "Fixed central and neighboring-channel shape"),
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement-dir", required=True, type=Path)
    args = parser.parse_args()
    source = args.measurement_dir.resolve()
    output = source / "presentation"
    if output.exists():
        raise RuntimeError("Presentation directory must not already exist")
    frozen_files = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
    case_path = source / "ALL_120_STATIONARY_CASES.json"
    cases = json.loads(case_path.read_text())
    if len(cases) != 120:
        raise RuntimeError("Expected120 saved cases")
    groups = [(role, width) for width in (1, 3) for role in ("ON", "OFF")]
    counts = [sum(r["origin_role"] == role and r["original_selected_width"] == width
                  for r in cases) for role, width in groups]
    if counts != [58, 60, 2, 0]:
        raise RuntimeError("Saved role/width groups differ from expected frozen groups")
    output.mkdir()
    plots = []
    for keys, name, title in SPECIFICATIONS:
        fig, axes = plt.subplots(1, len(keys), figsize=(7.2 * len(keys), 5.6),
                                 squeeze=False)
        for ax, key in zip(axes.flat, keys):
            values = [[r["origin_measurements"][key] for r in cases
                       if r["origin_role"] == role
                       and r["original_selected_width"] == width]
                      for role, width in groups]
            for index, group_values in enumerate(values, 1):
                if group_values:
                    # The same boxplot definition as the original scientific PNG.
                    ax.boxplot([group_values], positions=[index], widths=.45,
                               tick_labels=[""])
            ax.set_xticks(range(1, 5), [
                f"{role}, w{width}\nn={len(v)}" + (" (empty)" if not v else "")
                for (role, width), v in zip(groups, values)])
            ax.set_xlim(.5, 4.5)
            ax.axhline(0, color="gray", linewidth=.7)
            ax.set_title(key.replace("_", " ")
                         .replace("selected width center minus outer neighbor mean",
                                  "Selected box minus outer neighbors")
                         .replace("channel0 minus immediate neighbor mean",
                                  "Channel 0 minus nearest neighbors"),
                         fontsize=10, wrap=True)
            ax.set_ylabel("Additive row-normalized units")
            ax.grid(alpha=.2, axis="y")
        fig.suptitle(title + "\nOriginal selected top20 family; descriptive",
                     fontsize=12)
        fig.subplots_adjust(left=.15 if len(keys) == 1 else .08, right=.97,
                            bottom=.18, top=.78, wspace=.35)
        path = output / name
        fig.savefig(path, dpi=120, bbox_inches="tight", pad_inches=.2,
                    metadata={"Software": "Saved-case summary layout renderer",
                              "Description": "Same saved values and boxplot definitions; display repair only"})
        plt.close(fig)
        plots.append({"original_png": name,
                      "original_png_sha256": frozen_files[name],
                      "presentation_png": name,
                      "presentation_png_sha256": digest(path),
                      "bytes": path.stat().st_size,
                      "saved_metric_keys": keys})
    after = {p.name: digest(p) for p in source.iterdir() if p.is_file()}
    if after != frozen_files:
        raise RuntimeError("An original measurement file changed")
    receipt = {
        "status": "COMPLETE_THREE_VISUAL_ONLY_SUMMARY_COPIES",
        "scope": __doc__,
        "input_case_json_sha256": frozen_files[case_path.name],
        "all_original_measurement_file_sha256": frozen_files,
        "original_measurement_files_byte_unchanged": after == frozen_files,
        "unique_plot_definition_count_unchanged": 10,
        "role_width_groups": [list(group) for group in groups],
        "role_width_counts": counts,
        "display_changes": ["Explicit xlim0.5..4.5 includes empty fourth group",
                            "Wider canvas and increased left/right margins",
                            "bbox_inches tight with0.2inch padding"],
        "process_cpu_seconds_including_imports": time.process_time() - CPU_START,
        "wall_seconds": time.monotonic() - WALL_START,
        "cpu_cap_seconds": 10,
        "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "renderer_sha256": digest(Path(__file__)),
        "matplotlib_version": matplotlib.__version__,
        "plots": plots,
        "visual_qa": "Pending original-detail image inspection",
    }
    receipt_path = output / "SUMMARY_PRESENTATION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"],
                      "cpu_seconds": receipt["process_cpu_seconds_including_imports"],
                      "renderer_sha256": receipt["renderer_sha256"],
                      "receipt_sha256": digest(receipt_path)}))


if __name__ == "__main__":
    main()
