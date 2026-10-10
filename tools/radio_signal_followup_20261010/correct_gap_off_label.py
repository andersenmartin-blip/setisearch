#!/usr/bin/env python3
"""Correct only the saved-row publication figure's following-OFF labels.

Calls the original JSON-only visual renderer with the same saved values,
then changes text artists immediately before saving. No scientific job,
new measurements, optimization, source decoding, or selection changes.
"""
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

CPU_START = time.process_time()
WALL_START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
import plot_saved_gap_profiles as original
from matplotlib.figure import Figure
from matplotlib.text import Text


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement-dir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.measurement_dir.resolve(), args.outdir.resolve()
    correction_receipt_path = output / "WORDING_CORRECTION_RECEIPT.json"
    if correction_receipt_path.exists():
        raise ValueError("This display correction has already run; no rerun")
    receipt_path = output / "PLOTTING_RECEIPT.json"
    previous_receipt_sha = digest(receipt_path)
    previous = json.loads(receipt_path.read_text())
    pinned, means, rows, labels, cases = original.load_contract(source)
    if previous["input_json_sha256"] != pinned:
        raise ValueError("Scientific JSON pins differ from original plot inputs")
    for plot in previous["plots"]:
        if digest(output / plot["path"]) != plot["sha256"]:
            raise ValueError("Original publication PNG differs from plotting receipt")
    initial_row = next(plot for plot in previous["plots"]
                       if plot["path"] == "GAP_ORIGIN_PAIRED_OFF_ROWS.png")
    heatmap = next(plot for plot in previous["plots"]
                  if plot["path"] == "GAP_FIXED_PROFILE_MEANS.png")
    counts = {"main_title": 0, "legend": 0, "panel_titles": 0, "footer": 0}
    real_save = Figure.savefig

    def label_then_save(fig, filename, **kwargs):
        for text in fig.findobj(Text):
            content = text.get_text()
            if content == ("Gap drift: all16 saved rows in origin ON and paired OFF\n"
                           "Nine post-selected fixed profiles · one historical visit"):
                text.set_text("Gap drift: all 16 saved rows in origin ON and following OFF\n"
                              "Nine post-selected fixed profiles · one historical visit")
                counts["main_title"] += 1
            elif content == "Paired OFF":
                text.set_text("Following OFF (same epoch label)")
                counts["legend"] += 1
            elif " · paired OFF" in content:
                text.set_text(content.replace(" · paired OFF", " · following OFF"))
                counts["panel_titles"] += 1
            elif content == ("Each scan has its own row sequence · common y scale · descriptive comparison"):
                text.set_text("Following OFF uses the same epoch label; preceding OFF controls for ON2/ON3 are in the six-scan matrix/JSON\n"
                              "Each scan has its own row sequence · common y scale · descriptive comparison")
                counts["footer"] += 1
        if counts != {"main_title": 1, "legend": 1, "panel_titles": 9, "footer": 1}:
            raise ValueError("Expected text-only display corrections were not all matched")
        real_save(fig, filename, **kwargs)

    Figure.savefig = label_then_save
    try:
        path, details = original.plot_rows(output, rows, cases)
    finally:
        Figure.savefig = real_save
    if digest(output / heatmap["path"]) != heatmap["sha256"]:
        raise ValueError("Six-scan matrix PNG changed during row-label correction")
    if pinned != {name: digest(source / name) for name in pinned}:
        raise ValueError("Saved scientific JSON changed during display correction")
    if details != {key: initial_row[key] for key in details}:
        raise ValueError("Saved-row plot value hash or common-axis contract changed")
    script_sha = digest(Path(__file__))
    correction = {
        "status": "COMPLETE_TEXT_ONLY_FOLLOWING_OFF_LABEL_CORRECTION",
        "scope": __doc__, "original_renderer_sha256": digest(Path(original.__file__)),
        "correction_script_sha256": script_sha,
        "previous_plotting_receipt_sha256": previous_receipt_sha,
        "input_json_sha256": pinned, "input_json_byte_unchanged": True,
        "six_scan_matrix_PNG_byte_unchanged": True,
        "same288_saved_residual_values_and_common_y_limits": True,
        "old_row_PNG_sha256": initial_row["sha256"],
        "corrected_row_PNG_sha256": digest(path),
        "corrected_row_PNG_bytes": path.stat().st_size,
        "text_artist_replacements": counts,
        "following_OFF_definition": "The OFF scan with the same epoch label follows the originating ON; preceding OFF controls for ON2/ON3 are displayed in the all-six-scan mean matrix and retained JSON",
        "cpu_cap_seconds": 10,
        "process_CPU_seconds_including_imports": time.process_time() - CPU_START,
        "wall_seconds": time.monotonic() - WALL_START,
        "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "visual_QA": "Pending original-detail view of corrected PNG",
    }
    correction_receipt_path.write_text(json.dumps(correction, indent=2) + "\n")
    for plot in previous["plots"]:
        if plot["path"] == path.name:
            plot["initial_publication_render_sha256"] = plot["sha256"]
            plot["sha256"] = digest(path)
            plot["bytes"] = path.stat().st_size
            plot["text_only_correction_script_sha256"] = script_sha
    previous["wording_correction"] = {
        "receipt_path": correction_receipt_path.name,
        "receipt_sha256": digest(correction_receipt_path),
        "process_CPU_seconds_including_imports": correction["process_CPU_seconds_including_imports"],
    }
    receipt_path.write_text(json.dumps(previous, indent=2) + "\n")
    print(json.dumps({"status": correction["status"],
                      "process_CPU_seconds": correction["process_CPU_seconds_including_imports"],
                      "correction_script_sha256": script_sha,
                      "corrected_row_PNG_sha256": digest(path),
                      "correction_receipt_sha256": digest(correction_receipt_path),
                      "updated_plotting_receipt_sha256": digest(receipt_path)}))


if __name__ == "__main__":
    main()
