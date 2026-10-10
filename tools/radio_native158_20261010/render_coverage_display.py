#!/usr/bin/env python3
"""One versioned native158 coverage layout copy from the unchanged saved JSON.

Import the pinned COMPLETE-only renderer and its readers. Call plot_coverage
once, never its main or plot_means. Adapt only the figure height/legend anchor
before the pinned complete-buffer atomic publisher. Original images, numerical
outputs, plotting receipt and failed visual-QA receipt remain byte-unchanged.
Requires prospective public plan/readback and root GO; CPU30/wall120/AS2GiB.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time

CPU_CAP, WALL_CAP, MEMORY_CAP = 30, 120, 2 * 1024**3
START = time.monotonic()
PLAN = "tools/radio_native158_20261010/COVERAGE_DISPLAY_PLAN.json"
RENDERER = "tools/radio_saved_stages_20261010/plots_saved_stages.py"
RENDERER_SHA = "dcda1f4a238c11b67692111b01adcac43e9f2c7c602e601235e0cf0a4d393fba"
PUBLISHER_SHA = "98330391a76d1fa9b0138f1ecd62be1ef0c5a4c3ac3bdc2a5963538c5aa9434a"
POST_SHA = "f065a101fd3ea59f041e5f9c923b8a28b0c1c9638d68c80d3a37dcb4ad242d69"
POST_FREEZE = "c8f222e3da85cfdc3519e67cf1b64d65775ab54f"
PINS_SHA = "d9d56580c2a0905734c4029614ebb211b31f1532c24f17f401c41c7211aca93c"
ORIGINAL_COVERAGE_SHA = "3bb01c64fb6bc0595a9cd85da2438149f24168608ba78ee0011859569c3c26df"
ORIGINAL_MEANS_SHA = "14030ef66f00e340ba665c51a71b86824fbcef2a8bfbcf93b0bd3638a989659e"
ORIGINAL_RECEIPT_SHA = "fb3ee8272beb4aeeec623e0f35149a91d02599d03de5d891a8d8a552cd1e181a"
ORIGINAL_QA_SHA = "2416e7f5fc1ed1cde019495b00d1204d13fbc40b25ce71f5d57e185b153d69d3"
ATTEMPT = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, name):
    if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Finite root-relative path required")
    path = (root / name).resolve()
    path.relative_to(root)
    return path


def new_file(path, data):
    """Exclusive atomic metadata publication from a complete fsynced buffer."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".coverage-display-",
                                         suffix=".pending", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary.read_bytes() != data:
            raise ValueError("Complete metadata buffer changed")
        os.link(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def protect(root, inventory):
    for name, item in inventory.items():
        path = inside(root, name)
        if digest(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Protected original display/provenance changed: " + name)


def main():
    global ATTEMPT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--display-freeze-commit", required=True)
    parser.add_argument("--root-authorized-one-display-copy", action="store_true", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.root.is_absolute() or (len(args.display_freeze_commit) != 40
            or any(c not in "0123456789abcdef" for c in args.display_freeze_commit)):
        raise ValueError("Absolute root and exact prospective public display commit required")
    def timeout(signum, frame):
        raise TimeoutError("Finite one-shot coverage display cap; no retry")
    signal.signal(signal.SIGALRM, timeout)
    signal.signal(signal.SIGXCPU, timeout)
    signal.alarm(WALL_CAP)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP - 1, CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    plan_path = root / PLAN
    if digest(plan_path) != args.expected_plan_sha256:
        raise ValueError("Prospective display-plan hash mismatch")
    plan = json.loads(plan_path.read_bytes())
    if (plan["mode"] != "ONE_NATIVE158_SAVED_COVERAGE_LAYOUT_COPY"
            or plan["CPU_cap_seconds"] != CPU_CAP or plan["wall_cap_seconds"] != WALL_CAP
            or plan["memory_cap_bytes"] != MEMORY_CAP or plan["maximum_attempts"] != 1
            or plan["script_sha256"] != digest(Path(__file__))
            or plan["postprocessing_scope_sha256"] != POST_SHA
            or plan["public_postprocessing_freeze_commit"] != POST_FREEZE
            or plan["input_pins_sha256"] != PINS_SHA):
        raise ValueError("Fixed finite saved-only display plan changed")
    protected = plan["protected_original_files"]
    protect(root, protected)
    known = {RENDERER: RENDERER_SHA, plan["original_coverage_path"]: ORIGINAL_COVERAGE_SHA,
             plan["original_means_path"]: ORIGINAL_MEANS_SHA,
             plan["original_plotting_receipt_path"]: ORIGINAL_RECEIPT_SHA,
             plan["original_visual_QA_path"]: ORIGINAL_QA_SHA}
    for name, sha in known.items():
        if protected.get(name, {}).get("sha256") != sha:
            raise ValueError("Exact original display/code/receipt pins required")
    destination = inside(root, plan["output_display_path"])
    marker = inside(root, plan["attempt_marker_path"])
    receipt_path = inside(root, plan["execution_receipt_path"])
    if destination.name != "STAGE_COVERAGE_DISPLAY_01.png":
        raise ValueError("A separate versioned display path is required")
    for path in (destination, marker, receipt_path):
        if path.exists():
            raise ValueError("Existing display attempt/output preserved; no retry")
    attempt = {"status": "ONE_NATIVE158_COVERAGE_DISPLAY_ATTEMPT_STARTED_NO_RETRY",
               "UTC_started": datetime.now(timezone.utc).isoformat(),
               "script_sha256": digest(Path(__file__)), "plan_sha256": args.expected_plan_sha256,
               "root_confirmed_public_display_freeze_commit": args.display_freeze_commit}
    new_file(marker, (json.dumps(attempt, indent=2) + "\n").encode())
    ATTEMPT = {"root": root, "marker": marker, "receipt": receipt_path,
               "destination": destination, "plan_sha256": args.expected_plan_sha256,
               "freeze": args.display_freeze_commit}
    # The frozen import requests its historical60s/4GiB limits. Clamp only those
    # resource requests to this prospectively authorized30s/2GiB job.
    original_setrlimit = resource.setrlimit
    def clamped(which, limits):
        if which == resource.RLIMIT_CPU:
            limits = (CPU_CAP - 1, CPU_CAP)
        elif which == resource.RLIMIT_AS:
            limits = (MEMORY_CAP, MEMORY_CAP)
        return original_setrlimit(which, limits)
    sys.path.insert(0, str((root / RENDERER).parent))
    resource.setrlimit = clamped
    try:
        spec = importlib.util.spec_from_file_location("pinned_stage_renderer", root / RENDERER)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
    finally:
        resource.setrlimit = original_setrlimit
    if digest(Path(renderer.png_publish.__file__)) != PUBLISHER_SHA:
        raise ValueError("Exact complete-buffer atomic PNG publisher required")
    reader = renderer.saved.PinnedJSON(root, inside(root, plan["input_pins_path"]))
    if reader.pins_sha != PINS_SHA or len(reader.pins) != 20:
        raise ValueError("Exact20 original saved-JSON inputs required")
    post, _, chunks, batches, _, audit = renderer.read_complete_stage(reader, "native158", POST_SHA)
    dependencies = post["pinned_dependency_files"]
    if len(dependencies) != 47:
        raise ValueError("Exact47 prospectively frozen dependencies required")
    def unchanged_dependencies():
        for name, sha in dependencies.items():
            if digest(inside(root, name)) != sha:
                raise ValueError("Prospectively frozen dependency changed: " + name)
    unchanged_dependencies()
    if chunks != [158] and chunks != (158,):
        raise ValueError("Only the original native158 stage may be displayed")
    if audit["receipt_sha256"] != plan["source_audit_receipt_sha256"]:
        raise ValueError("Exact already-passed native158 source-cell audit required")
    original_receipt = json.loads(inside(root, plan["original_plotting_receipt_path"]).read_bytes())
    original_plot = next(p for p in original_receipt["plots"]
                         if p["path"] == plan["original_coverage_path"])
    if original_receipt["input_pins_sha256"] != PINS_SHA:
        raise ValueError("Original plotting inputs changed")
    old_publish = renderer.png_publish.save_figure_atomic
    calls, layout = [], {}
    def display_publish(figure, path, **kwargs):
        if Path(path) != destination or calls:
            raise ValueError("Only one versioned coverage publication is authorized")
        if tuple(figure.get_size_inches()) != (14.8, 6.8) or len(figure.legends) != 1:
            raise ValueError("Original single-chunk figure geometry changed")
        calls.append(str(path))
        figure.set_size_inches(14.8, 8.5, forward=False)
        figure.legends[0].set_bbox_to_anchor((.55, .92))
        figure.canvas.draw()
        drawing = figure.canvas.get_renderer()
        title = figure.axes[0].title.get_window_extent(drawing)
        legend = figure.legends[0].get_window_extent(drawing)
        if title.overlaps(legend) or legend.y0 - title.y1 < 8:
            raise ValueError("Display title and legend still overlap or lack margin")
        layout.update(original_size_inches=[14.8, 6.8], display_size_inches=[14.8, 8.5],
                      original_legend_anchor=[.55, .855], display_legend_anchor=[.55, .92],
                      title_legend_vertical_gap_pixels=float(legend.y0 - title.y1),
                      title_and_legend_bboxes_disjoint=True)
        return old_publish(figure, path, **kwargs)
    renderer.png_publish.save_figure_atomic = display_publish
    try:
        details = renderer.plot_coverage(destination, chunks, batches, "native158")
    finally:
        renderer.png_publish.save_figure_atomic = old_publish
    if len(calls) != 1:
        raise ValueError("One frozen coverage helper call required")
    for key, value in details.items():
        if key != "PNG_atomic_publication" and original_plot.get(key) != value:
            raise ValueError("Saved coverage content changed: " + key)
    reader.unchanged()
    unchanged_dependencies()
    protect(root, protected)
    if digest(plan_path) != args.expected_plan_sha256:
        raise ValueError("Prospective display plan changed")
    cpu, wall = time.process_time(), time.monotonic() - START
    receipt = {"schema": "SETI_NATIVE158_ONE_VERSIONED_COVERAGE_DISPLAY_V1",
               "status": "COMPLETE_ONE_VERSIONED_COVERAGE_DISPLAY_COPY" if cpu <= CPU_CAP and wall <= WALL_CAP else "COMPLETE_DISPLAY_RESOURCE_CAP_EXCEEDED_NO_RETRY",
               "UTC_completed": datetime.now(timezone.utc).isoformat(),
               "script_sha256": digest(Path(__file__)), "plan_sha256": args.expected_plan_sha256,
               "root_confirmed_prospective_display_freeze_commit": args.display_freeze_commit,
               "original_renderer_sha256": RENDERER_SHA, "publisher_sha256": PUBLISHER_SHA,
               "postprocessing_scope_sha256": POST_SHA, "public_postprocessing_freeze_commit": POST_FREEZE,
               "input_pins_sha256": PINS_SHA, "opened_input_JSON": reader.opened,
               "all20_saved_input_JSON_and47dependency_hashes_unchanged": True,
               "original_coverage_mean_plotting_and_failed_visualQA_byte_unchanged": True,
               "protected_original_files": protected, "layout_only_changes": layout,
               "unchanged_coverage_content": {k: v for k, v in details.items() if k != "PNG_atomic_publication"},
               "output_display_path": plan["output_display_path"],
               "PNG_atomic_publication": details["PNG_atomic_publication"],
               "attempt_marker_path": plan["attempt_marker_path"], "attempt_marker_sha256": digest(marker),
               "original_renderer_main_called": False, "original_means_rerendered": False,
               "one_frozen_plot_coverage_helper_call": True, "retry_performed": False,
               "HDF5_NPZ_or_source_HTTP_access": False, "rescore_profile_or_normalization_remeasurement": False,
               "source_audit_receipt_metadata": audit, "source_audit_reexecuted": False,
               "CPU_seconds_at_receipt_creation_including_imports": cpu,
               "wall_seconds_at_receipt_creation": wall, "CPU_cap_seconds": CPU_CAP,
               "wall_cap_seconds": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
               "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               "OS_RLIMIT_CPU_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
               "OS_RLIMIT_AS_bytes": list(resource.getrlimit(resource.RLIMIT_AS)),
               "complete_command_resource_measurement": "Separate outer child CPU/RSS/wall measurement including final receipt/stdout required",
               "visual_QA": "Pending separate original-detail inspection of private byte-exact copy"}
    new_file(receipt_path, (json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode())
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "output": plan["output_display_path"],
                      "sha256": digest(destination), "bytes": destination.stat().st_size,
                      "CPU_seconds": cpu, "receipt_sha256": digest(receipt_path)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if ATTEMPT is not None and not ATTEMPT["receipt"].exists():
            try:
                failed = {"status": "FAILED_ONE_VERSIONED_COVERAGE_DISPLAY_ATTEMPT_NO_RETRY",
                          "error_type": type(error).__name__, "error_message": str(error),
                          "plan_sha256": ATTEMPT["plan_sha256"], "freeze_commit": ATTEMPT["freeze"],
                          "attempt_marker_sha256": digest(ATTEMPT["marker"]),
                          "output_exists": ATTEMPT["destination"].exists(),
                          "CPU_seconds_at_failure_receipt_creation": time.process_time(),
                          "wall_seconds_at_failure_receipt_creation": time.monotonic() - START,
                          "retry_performed": False}
                new_file(ATTEMPT["receipt"], (json.dumps(failed, indent=2) + "\n").encode())
            except Exception:
                pass  # The exclusive attempt marker still blocks any retry.
        raise
