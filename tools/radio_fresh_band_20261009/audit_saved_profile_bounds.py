#!/usr/bin/env python3
"""Audit visual text bounds without writing or changing any profile PNG.

Rebuilds only the saved-array display layout. The PNG save operation is
intercepted to inspect title, axis-label, and tick-label bounds instead.
No source decoding, search, residual computation, or scientific selection.
"""
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

CPU_START = time.process_time()
WALL_START = time.monotonic()

import render_saved_profiles as display
from matplotlib.figure import Figure
from PIL import Image

resource.setrlimit(resource.RLIMIT_CPU, (22, 22))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-dir", required=True, type=Path)
    parser.add_argument("--presentation-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise RuntimeError("Audit receipt must not already exist")
    profiles = args.profiles_dir.resolve()
    presentation = args.presentation_dir.resolve()
    plot_records = json.loads((profiles / "FIXED_TOP3_PROFILES.json").read_text())
    render_receipt_path = presentation / "PRESENTATION_RECEIPT.json"
    render_receipt = json.loads(render_receipt_path.read_text())
    input_hashes = {p.name: digest(p) for p in profiles.iterdir() if p.is_file()}
    output_hashes = {p.name: digest(p) for p in presentation.iterdir() if p.is_file()}
    expected_png = {f["presentation_png"]: f["presentation_png_sha256"]
                    for r in render_receipt["figures"] for f in r["figures"]}
    bounds = []

    def inspect_instead_of_saving(fig, filename, **kwargs):
        fig.set_dpi(kwargs["dpi"])
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        tight = fig.get_tightbbox(renderer)
        pad = float(kwargs["pad_inches"])
        # Figure tight bounding boxes use inches; artist boxes use display pixels.
        dpi = fig.dpi
        canvas = ((tight.x0 - pad) * dpi, (tight.y0 - pad) * dpi,
                  (tight.x1 + pad) * dpi, (tight.y1 + pad) * dpi)
        # Text artists for unused ticks can report visible=True but are excluded
        # by Matplotlib's axis drawing when their locations lie outside view.
        # Inspect only labels which participate in the actual drawn figure.
        drawn_texts = list(fig.texts)
        for axis_panel in fig.axes:
            drawn_texts += [axis_panel.title, axis_panel._left_title,
                            axis_panel._right_title]
            drawn_texts += list(axis_panel.texts)
            for axis in (axis_panel.xaxis, axis_panel.yaxis):
                drawn_texts += [axis.label, axis.get_offset_text()]
                low, high = sorted(axis.get_view_interval())
                for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                    if low - 1e-8 <= tick.get_loc() <= high + 1e-8:
                        drawn_texts += [tick.label1, tick.label2]
        texts = []
        for artist in drawn_texts:
            if not artist.get_visible() or not artist.get_text():
                continue
            bbox = artist.get_window_extent(renderer)
            edges = [bbox.x0 - canvas[0], bbox.y0 - canvas[1],
                     canvas[2] - bbox.x1, canvas[3] - bbox.y1]
            texts.append({"text": artist.get_text(),
                          "bounds_display_pixels": list(bbox.extents),
                          "minimum_canvas_margin_display_pixels": min(edges),
                          "inside_export_canvas": all(edge >= -1e-7 for edge in edges)})
        path = Path(filename)
        if digest(path) != expected_png[path.name]:
            raise RuntimeError("Presentation PNG checksum changed")
        with Image.open(path) as png:
            size = list(png.size)
        predicted = [(canvas[2] - canvas[0]) * kwargs["dpi"] / dpi,
                     (canvas[3] - canvas[1]) * kwargs["dpi"] / dpi]
        bounds.append({"path": path.name, "sha256": digest(path),
                       "png_dimensions_pixels": size,
                       "predicted_dimensions_from_tight_bbox_pixels": predicted,
                       "dimensions_agree_within_two_pixels": all(
                           abs(actual - estimated) <= 2 for actual, estimated in zip(size, predicted)),
                       "all_visible_text_inside_export_canvas": all(
                           item["inside_export_canvas"] for item in texts),
                       "visible_text_count": len(texts), "texts": texts})

    previous_savefig = Figure.savefig
    Figure.savefig = inspect_instead_of_saving
    try:
        for record in plot_records:
            selected = record["selected_track"]
            stem = selected["track_id"]
            with display.np.load(profiles / f"{stem}.npz", allow_pickle=False) as saved:
                arrays = {key: saved[key] for key in display.ALLOWED_MEMBERS}
            for kind in ("time", "mean"):
                display.render(presentation / f"{stem}_{kind}.png", arrays, selected, kind)
    finally:
        Figure.savefig = previous_savefig

    source_unchanged = input_hashes == {
        p.name: digest(p) for p in profiles.iterdir() if p.is_file()}
    presentation_unchanged = output_hashes == {
        p.name: digest(p) for p in presentation.iterdir() if p.is_file()}
    passed = (len(bounds) == 36 and source_unchanged and presentation_unchanged
              and all(item["all_visible_text_inside_export_canvas"]
                      and item["dimensions_agree_within_two_pixels"] for item in bounds))
    receipt = {"status": "PASS_ALL_36_PNG_TEXT_BOUNDS" if passed else "FAIL_VISUAL_BOUND_AUDIT",
               "scope": "Visual layout inspection from saved precomputed arrays only; savefig intercepted, no PNG writes and no scientific processing",
               "display_note": "For reliable full-size inspection use view_image detail original and emit image detail original; earlier default-high display showed apparent clipping absent from actualPNGbytes",
               "allowed_npz_members": list(display.ALLOWED_MEMBERS),
               "renderer_sha256": digest(Path(display.__file__)),
               "render_receipt_sha256": digest(render_receipt_path),
               "audit_script_sha256": digest(Path(__file__)),
               "source_files_byte_unchanged": source_unchanged,
               "presentation_files_byte_unchanged": presentation_unchanged,
               "cpu_cap_seconds": 22,
               "audit_method_correction": "The initial audit included unused out-of-view tick artists and measured a100DPI canvas against150DPI export; this corrected audit filters drawn tick locations and measures150DPI. NoPNGchanged",
               "process_cpu_seconds_including_imports": time.process_time() - CPU_START,
               "wall_seconds": time.monotonic() - WALL_START,
               "max_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               "figures": bounds}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "plots": len(bounds),
                      "cpu_seconds": receipt["process_cpu_seconds_including_imports"],
                      "receipt_sha256": digest(args.receipt),
                      "audit_script_sha256": receipt["audit_script_sha256"],
                      "renderer_sha256": receipt["renderer_sha256"],
                      "render_receipt_sha256": receipt["render_receipt_sha256"]}))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
