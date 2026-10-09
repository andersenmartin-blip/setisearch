#!/usr/bin/env python3
"""Render visual-only copies from five frozen, precomputed NPZ arrays.

This helper never decodes source HDF5 or reads the raw-power NPZ members.
It does not change any scientific result, selection, center, drift, or score.
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
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

ALLOWED_MEMBERS = (
    "center_minus_flank_each_row",
    "times_seconds_from_reference",
    "mean_fixed_track_frequency_profile",
    "source_channel_offsets",
    "scans",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def padded_range(values):
    """Set display limits only; do not transform the plotted arrays."""
    lower = min(0.0, float(np.min(values)))
    upper = max(0.0, float(np.max(values)))
    margin = max((upper - lower) * 0.08, 0.025)
    return lower - margin, upper + margin


def render(path, arrays, selected, kind):
    scans = arrays["scans"]
    values = arrays[
        "center_minus_flank_each_row" if kind == "time"
        else "mean_fixed_track_frequency_profile"
    ]
    x = arrays[
        "times_seconds_from_reference" if kind == "time"
        else "source_channel_offsets"
    ]
    limits = padded_range(values)
    fig, axes = plt.subplots(3, 2, figsize=(12, 9.6), sharey=True)
    for index, ax in enumerate(axes.flat):
        scan = str(scans[index])
        color = "#1672a7" if scan.endswith("_on") else "#a15428"
        abscissa = x[index] if kind == "time" else x
        ax.plot(abscissa, values[index], color=color, linewidth=1.25,
                marker="o" if kind == "time" else None, markersize=3)
        ax.axhline(0, color="#777777", linewidth=0.65)
        if kind == "mean":
            ax.axvline(0, color="#777777", linewidth=0.65, linestyle=":")
        ax.set_ylim(*limits)
        label = scan.replace("epoch", "Scan ").replace("_", " ").upper()
        if scan == selected["originating_scan"]:
            label += " (origin)"
        ax.set_title(label, fontsize=10, loc="left", pad=7)
        ax.grid(alpha=0.18)
        ax.tick_params(labelsize=9)
        if index % 2 == 0:
            ax.set_ylabel("Power / row median\nminus flank median", fontsize=10,
                          labelpad=10)
        if index >= 4:
            ax.set_xlabel("Time from reference (s)" if kind == "time"
                          else "Channel offset from fixed track", fontsize=10,
                          labelpad=7)
    title = (
        f"{selected['originating_scan']} · {selected['family']} rank "
        f"{selected['display_rank']:02d}\n"
        f"{selected['reference_frequency_hz'] / 1e6:.6f} MHz · "
        f"{selected['drift_hz_s']:+.6f} Hz/s · "
        f"{selected['width_channels']} channel(s) · fixed shift 0"
    )
    fig.suptitle(title, fontsize=12, y=0.97)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.09, top=0.88,
                        hspace=0.40, wspace=0.16)
    fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.2,
                metadata={"Software": "visual-only saved-profile renderer",
                          "Description": "Unchanged precomputed arrays; no source decoding or search"})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-dir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    args = parser.parse_args()
    source = args.profiles_dir.resolve()
    output = args.outdir.resolve()
    if output.exists():
        raise RuntimeError("Output directory must not already exist")
    summary_path = source / "FIXED_TOP3_PROFILES.json"
    records = json.loads(summary_path.read_text())
    if len(records) != 18:
        raise RuntimeError("Expected exactly18 frozen profile records")
    input_paths = sorted(source.iterdir())
    before = {p.name: digest(p) for p in input_paths if p.is_file()}
    output.mkdir(parents=True)
    rendered = []
    for record in records:
        selected = record["selected_track"]
        stem = selected["track_id"]
        npz = source / (stem + ".npz")
        if before[npz.name] != record["patch"]["sha256"]:
            raise RuntimeError("Input NPZ checksum differs from frozen manifest")
        with np.load(npz, allow_pickle=False) as saved:
            arrays = {member: saved[member] for member in ALLOWED_MEMBERS}
        if arrays["scans"].shape != (6,):
            raise RuntimeError("Expected six saved scan labels")
        if arrays["center_minus_flank_each_row"].shape != (6, 16):
            raise RuntimeError("Expected saved6x16 residual array")
        if arrays["times_seconds_from_reference"].shape != (6, 16):
            raise RuntimeError("Expected saved6x16 time array")
        if arrays["mean_fixed_track_frequency_profile"].shape != (6, 129):
            raise RuntimeError("Expected saved6x129 frequency-profile array")
        if arrays["source_channel_offsets"].shape != (129,):
            raise RuntimeError("Expected saved129 channel offsets")
        for member in ALLOWED_MEMBERS[:-1]:
            if not np.all(np.isfinite(arrays[member])):
                raise RuntimeError("Non-finite precomputed display array")
        item = {"track_id": stem, "input_npz": npz.name,
                "input_npz_sha256": before[npz.name], "figures": []}
        original_plot_hashes = {p["path"]: p["sha256"] for p in record["plots"]}
        for kind in ("time", "mean"):
            basename = f"{stem}_{kind}.png"
            original = source / basename
            if before[basename] != original_plot_hashes[basename]:
                raise RuntimeError("Original PNG checksum differs from frozen manifest")
            destination = output / basename
            render(destination, arrays, selected, kind)
            item["figures"].append({
                "original_png": original.name,
                "original_png_sha256": before[basename],
                "presentation_png": destination.name,
                "presentation_png_sha256": digest(destination),
                "bytes": destination.stat().st_size,
            })
        rendered.append(item)
    after = {p.name: digest(p) for p in input_paths if p.is_file()}
    if after != before:
        raise RuntimeError("A frozen input file changed during rendering")

    # A contact sheet for layout inspection, derived solely from these PNG copies.
    thumb_size = (330, 285)
    canvas = Image.new("RGB", (6 * thumb_size[0], 6 * thumb_size[1]), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    for index, item in enumerate(rendered):
        for column, kind in enumerate(("time", "mean")):
            slot = 2 * index + column
            path = output / f"{item['track_id']}_{kind}.png"
            with Image.open(path) as original:
                thumb = original.convert("RGB")
                thumb.thumbnail((thumb_size[0] - 8, thumb_size[1] - 20))
            px, py = (slot % 6) * thumb_size[0], (slot // 6) * thumb_size[1]
            canvas.paste(thumb, (px + 4, py + 18))
            draw.text((px + 4, py + 2), f"{item['track_id']} {kind}", fill="#222222")
    montage = output / "PRESENTATION_CONTACT_SHEET.png"
    canvas.save(montage)
    receipt = {
        "status": "COMPLETE_VISUAL_ONLY_COPIES_36_PLOTS",
        "scope": "Only saved precomputed plot arrays and selected-track labels; no source HTTP, source decoding, scientific search, residual recomputation, or change to frozen results",
        "allowed_npz_members": list(ALLOWED_MEMBERS),
        "source_directory_sha256": before,
        "source_files_byte_unchanged": after == before,
        "script_sha256": digest(Path(__file__)),
        "cpu_cap_seconds": 60,
        "process_cpu_seconds_including_imports": time.process_time() - CPU_START,
        "wall_seconds": time.monotonic() - WALL_START,
        "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__,
        "figures": rendered,
        "contact_sheet": {"path": montage.name, "sha256": digest(montage)},
        "visual_qa": "Pending contact-sheet and representative full-size inspection",
    }
    receipt_path = output / "PRESENTATION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "plots": len(rendered) * 2,
                      "process_cpu_seconds": receipt["process_cpu_seconds_including_imports"],
                      "max_rss_bytes": receipt["max_rss_bytes"],
                      "receipt_sha256": digest(receipt_path),
                      "script_sha256": receipt["script_sha256"]}))


if __name__ == "__main__":
    main()
