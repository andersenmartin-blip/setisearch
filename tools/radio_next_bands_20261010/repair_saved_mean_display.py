#!/usr/bin/env python3
"""One prospective saved-JSON-only repair of the truncated mean-display PNG.

The unchanged f122 renderer is imported for its saved-JSON contract readers and
one plot_means call. Its main and coverage renderer are never called. A temporary
savefig destination adapter preserves the original figure, DPI, labels, metadata
and layout, while collecting a complete PNG in memory. No scientific measurement,
NPZ/HDF5 access, residual calculation, optimization or ranking is performed.

Execution requires a prospectively public plan, preserved opaque corrupt bytes,
and explicit root GO. An exact intended-byte recovery alone may atomically replace
the canonical corrupt image. Any valid different rendering gets a versioned path.
There is one attempt under CPU30s/wall120s/address-space2GiB, with no retry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import resource
import signal
import tempfile
import time

WALL_START = time.monotonic()
CPU_CAP = 30
WALL_CAP = 120
MEMORY_CAP = 2 * 1024**3
PLAN = "tools/radio_next_bands_20261010/DISPLAY_REPAIR_PLAN.json"
FROZEN = "tools/radio_next_bands_20261010/plots_qualified_saved.py"
FROZEN_SHA = "f122449e317d90b8c08f7c259e193c014022b76c44828f470942551b39564f3c"
PUBLISHER = "tools/radio_next_bands_20261010/png_publish.py"
PUBLISHER_SHA = "98330391a76d1fa9b0138f1ecd62be1ef0c5a4c3ac3bdc2a5963538c5aa9434a"
PINS_SHA = "d3b5652b1f101f0abd422f7f84e32ae3c9845be28a11d2865743d9163e1cb08c"
ACCEPTANCE_SHA = "8f744e099b0b31b9c976255c5c321b2ce49243ec56f60460048b966885f2cf37"
ACCEPTANCE_FREEZE = "50c120ba94e0a24c9473afc883ef24f7dd1846f5"
RECEIPT_SHA = "775d8b3f19cc141af5cd22a2ab43b18e64f684cc5a64e61689dad998d4a0950f"
INTENDED_SHA = "df753bf0f3a2733225e394e820bd9e19cb50bddfa627e7d2a05dd335a00d2072"
INTENDED_BYTES = 738873
OBSERVED_SHA = "e1fd8c9cb3aac5cd148216b0c59d8806e34dad5f2d0affe6ea32b2f8ef4eea14"
OBSERVED_BYTES = 393485
AUDIT_SHA = "de5cf2f956c42f6fee82f5372dadc48b82c81a115f0a33a5c6f46a91fe088643"
COVERAGE_SHA = "954c9e19bd351e0d16fe152d7739721fce5e6f42070115fc64f69d1303737cc3"
ATTEMPT_CONTEXT = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_path(root, name):
    if not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Expected a finite root-relative artifact path")
    path = (root / name).resolve()
    path.relative_to(root)
    return path


def check_file(root, item):
    path = root_path(root, item["path"])
    raw = path.read_bytes()
    if (hashlib.sha256(raw).hexdigest() != item["sha256"]
            or len(raw) != item["bytes"]):
        raise ValueError("Prospective repair input bytes changed: " + item["path"])
    return raw


def write_new_atomic(path, raw):
    """Preserve a complete opaque buffer or JSON receipt; never overwrite."""
    if path.exists():
        raise ValueError("Existing repair artifact preserved; no retry")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".display-repair-", suffix=".pending",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(temporary) != hashlib.sha256(raw).hexdigest():
            raise ValueError("Repair artifact temporary bytes changed")
        # Same-filesystem hard-link creation is atomic and fails if the final
        # name exists; another writer cannot be overwritten by this operation.
        os.link(temporary, path)
        temporary.unlink()
        temporary = None
        if digest(path) != hashlib.sha256(raw).hexdigest():
            raise ValueError("Repair artifact publication bytes changed")
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def import_saved_module(path, module_name, clamp_renderer=False):
    """Resource-only adapter prevents the frozen import widening this job's caps."""
    original = resource.setrlimit
    def bounded(which, limits):
        if which == resource.RLIMIT_CPU:
            limits = (CPU_CAP - 1, CPU_CAP)
        elif which == resource.RLIMIT_AS:
            limits = (MEMORY_CAP, MEMORY_CAP)
        return original(which, limits)
    if clamp_renderer:
        resource.setrlimit = bounded
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        resource.setrlimit = original


def main():
    global ATTEMPT_CONTEXT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--repair-freeze-commit", required=True)
    parser.add_argument("--root-authorized-one-display-repair", action="store_true", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.root.is_absolute():
        raise ValueError("An absolute workspace root is required")
    if (len(args.repair_freeze_commit) != 40
            or any(c not in "0123456789abcdef" for c in args.repair_freeze_commit)):
        raise ValueError("Root must provide an exact prospective public repair commit")
    def finite_timeout(signum, frame):
        raise TimeoutError("Finite display-repair resource limit; no retry")
    signal.signal(signal.SIGALRM, finite_timeout)
    signal.signal(signal.SIGXCPU, finite_timeout)
    signal.alarm(WALL_CAP)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP - 1, CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    plan_path = root / PLAN
    if digest(plan_path) != args.expected_plan_sha256:
        raise ValueError("Prospectively public repair plan hash mismatch")
    plan = json.loads(plan_path.read_bytes())
    if (plan["mode"] != "ONE_SAVED_JSON_MEAN_DISPLAY_REPAIR_NO_SCIENTIFIC_PROCESSING"
            or plan["cpu_cap_seconds"] != CPU_CAP or plan["wall_cap_seconds"] != WALL_CAP
            or plan["memory_cap_bytes"] != MEMORY_CAP or plan["maximum_attempts"] != 1
            or plan["acceptance_scope_sha256"] != ACCEPTANCE_SHA
            or plan["acceptance_public_freeze_commit"] != ACCEPTANCE_FREEZE
            or plan["script_sha256"] != digest(Path(__file__))):
        raise ValueError("Finite prospective display-only plan changed")
    frozen_inputs = plan["protected_input_files"]
    protected = {name: check_file(root, item) for name, item in frozen_inputs.items()}
    required = {"frozen_renderer": (FROZEN, FROZEN_SHA),
                "publisher": (PUBLISHER, PUBLISHER_SHA),
                "plot_input_pins": (plan["plot_input_pins_path"], PINS_SHA),
                "original_plotting_receipt": (plan["original_plotting_receipt_path"], RECEIPT_SHA),
                "observed_corrupt_opaque_copy": (plan["observed_corrupt_opaque_copy_path"], OBSERVED_SHA),
                "original_coverage_png": (plan["original_coverage_png_path"], COVERAGE_SHA)}
    for name, (path, sha) in required.items():
        if frozen_inputs[name]["path"] != path or frozen_inputs[name]["sha256"] != sha:
            raise ValueError("An immutable repair dependency was changed")
    if len(protected["observed_corrupt_opaque_copy"]) != OBSERVED_BYTES:
        raise ValueError("The preserved observed corrupt bytes changed")
    original_receipt = json.loads(protected["original_plotting_receipt"])
    corrupt_receipt = json.loads(protected["corruption_receipt"])
    if (corrupt_receipt["observed_corrupt_sha256"] != OBSERVED_SHA
            or corrupt_receipt["observed_corrupt_bytes"] != OBSERVED_BYTES
            or corrupt_receipt["original_plotting_receipt_sha256"] != RECEIPT_SHA
            or corrupt_receipt["cause"] != "UNKNOWN_NOT_ATTRIBUTED_TO_A_TOOL_OR_WRITER"):
        raise ValueError("Public preserved corruption history changed")
    canonical = root_path(root, plan["canonical_mean_png_path"])
    versioned = root_path(root, plan["versioned_mean_png_path"])
    backup = root_path(root, plan["validated_buffer_opaque_copy_path"])
    execution = root_path(root, plan["execution_receipt_path"])
    attempt = root_path(root, plan["attempt_marker_path"])
    for path in (versioned, backup, execution, attempt):
        if path.exists():
            raise ValueError("A prior repair artifact exists; preserve it and do not retry")
    if digest(canonical) != OBSERVED_SHA or canonical.stat().st_size != OBSERVED_BYTES:
        raise ValueError("Canonical corrupt image changed before prospective repair")
    marker = {"schema": "SETI_ONE_DISPLAY_REPAIR_ATTEMPT_V1", "status": "ONE_ATTEMPT_STARTED_NO_RETRY",
              "UTC_started": datetime.now(timezone.utc).isoformat(),
              "script_sha256": digest(Path(__file__)), "plan_sha256": args.expected_plan_sha256,
              "root_confirmed_public_repair_freeze_commit": args.repair_freeze_commit,
              "original_observed_corrupt_sha256": OBSERVED_SHA,
              "cpu_cap_seconds": CPU_CAP, "wall_cap_seconds": WALL_CAP,
              "memory_cap_bytes": MEMORY_CAP}
    write_new_atomic(attempt, (json.dumps(marker, indent=2) + "\n").encode())
    ATTEMPT_CONTEXT = {"execution": execution, "canonical": canonical, "versioned": versioned,
                       "backup": backup, "attempt": attempt, "root": root,
                       "plan_sha256": args.expected_plan_sha256,
                       "public_freeze": args.repair_freeze_commit}
    renderer = import_saved_module(root / FROZEN, "frozen_display_f122", True)
    publisher = import_saved_module(root / PUBLISHER, "display_png_publisher")
    inputs = renderer.PinnedJSON(root, root_path(root, plan["plot_input_pins_path"]))
    if inputs.pins_sha != PINS_SHA or len(inputs.pins) != 37:
        raise ValueError("The exact original37 saved JSON pins are required")
    for name in inputs.pins:
        inputs.pin_only(name)
    if (inputs.pins.get(renderer.SCOPE) != renderer.SCOPE_SHA256
            or inputs.pins.get(renderer.ACCEPTANCE_SCOPE) != ACCEPTANCE_SHA
            or inputs.pins.get(plan["source_audit_receipt_path"]) != AUDIT_SHA):
        raise ValueError("Original scientific/acceptance/source-audit pins changed")
    activation = inputs.load(renderer.ACTIVATION)
    final_scope = inputs.load(renderer.SCOPE)
    if (final_scope["immutable_metadata_selection"] != activation["immutable_metadata_selection"]
            or final_scope["source_chunk_ids"] != [153, 154]
            or final_scope["expected_scan_tiles_per_batch"] != 381
            or final_scope["expected_total_scan_tiles_if_all_four_complete"] != 1524
            or final_scope["expected_total_profiles_if_all_four_complete"] != 36
            or final_scope["OFF_veto"] is not False
            or final_scope["unqualified_exploratory_only"] is not True
            or final_scope["calibrated_SNR_FAP_flux_EIRP_or_sensitivity"] is not False):
        raise ValueError("Original prospective science contract changed")
    acceptance = inputs.load(renderer.ACCEPTANCE_SCOPE)
    if (acceptance["original_scope_sha256"] != renderer.SCOPE_SHA256
            or acceptance["original_wrapper_sha256"] != final_scope["script_sha256"]
            or len(acceptance["job_contracts"]) != 4):
        raise ValueError("Exact public saved-output acceptance contract required")
    geometry = renderer.activation_geometry(activation)
    _, batches, cases, means, labels = renderer.load_batches(inputs, geometry, acceptance, ACCEPTANCE_SHA)
    audit = inputs.load(plan["source_audit_receipt_path"])
    if (audit["status"] != plan["source_audit_required_status"]
            or audit["counts"] != plan["source_audit_required_counts"]
            or audit["counts"]["patches"] != 36
            or audit["counts"]["raw_cells_bitwise_checked"] != 445824
            or audit["acceptance_scope_sha256"] != ACCEPTANCE_SHA
            or audit["freeze_commit"] != ACCEPTANCE_FREEZE
            or audit["original_scientific_freeze_commit"] != renderer.NUMERIC_FREEZE_COMMIT):
        raise ValueError("Exact existing PASS source-cell-audit metadata required")
    if (cases != original_receipt["cases"] or batches != original_receipt["batch_summary"]
            or original_receipt["input_pins_sha256"] != PINS_SHA
            or original_receipt["acceptance_scope_sha256"] != ACCEPTANCE_SHA
            or original_receipt["prospective_acceptance_freeze_commit"] != ACCEPTANCE_FREEZE
            or original_receipt["script_sha256"] != FROZEN_SHA):
        raise ValueError("Original saved display identities/statuses/provenance changed")
    original_plot = next(p for p in original_receipt["plots"]
                         if p["path"] == canonical.name)
    means_sha = hashlib.sha256(means.tobytes()).hexdigest()
    if (means.shape != (36, 6) or means_sha != original_plot["saved_means_float64_sha256"]
            or original_plot["sha256"] != INTENDED_SHA or original_plot["bytes"] != INTENDED_BYTES):
        raise ValueError("All216 original saved means and intended original rendering pin required")
    inputs.verify_unchanged()
    from matplotlib.figure import Figure
    original_savefig = Figure.savefig
    buffer = BytesIO()
    save_calls = []
    def complete_buffer_savefig(figure, destination, *positional, **kwargs):
        if Path(destination) != canonical or positional or "format" in kwargs or save_calls:
            raise ValueError("Only the one original mean-display destination may be adapted")
        save_calls.append(str(destination))
        return original_savefig(figure, buffer, format="png", **kwargs)
    Figure.savefig = complete_buffer_savefig
    try:
        returned_path, details = renderer.plot_means(canonical.parent, means, labels, cases, "ALL_SAVED_VERIFIED")
    finally:
        Figure.savefig = original_savefig
    if returned_path != canonical or len(save_calls) != 1:
        raise ValueError("One frozen mean plotting helper invocation was required")
    for key, value in details.items():
        if original_plot.get(key) != value:
            raise ValueError("Display metadata changed from the original saved rendering: " + key)
    raw = buffer.getvalue()
    validation = publisher.validate_png_bytes(raw, expected_dimensions=(1569, 2932))
    exact = validation["sha256"] == INTENDED_SHA and validation["bytes"] == INTENDED_BYTES
    for item in frozen_inputs.values():
        check_file(root, item)
    inputs.verify_unchanged()
    if digest(plan_path) != args.expected_plan_sha256:
        raise ValueError("Repair plan changed during rendering")
    if digest(canonical) != OBSERVED_SHA or canonical.stat().st_size != OBSERVED_BYTES:
        raise ValueError("Canonical image changed during buffered rendering; no publication")
    if time.process_time() > CPU_CAP or time.monotonic() - WALL_START > WALL_CAP:
        raise TimeoutError("Measured display-repair cap exceeded before publication; no retry")
    write_new_atomic(backup, raw)
    target = canonical if exact else versioned
    if digest(canonical) != OBSERVED_SHA or canonical.stat().st_size != OBSERVED_BYTES:
        raise ValueError("Canonical corrupt bytes changed immediately before publication")
    publication = publisher.publish_png_atomic(target, raw, overwrite=exact, expected_dimensions=(1569, 2932))
    inputs.verify_unchanged()
    for item in frozen_inputs.values():
        check_file(root, item)
    if digest(plan_path) != args.expected_plan_sha256:
        raise ValueError("Repair plan changed at publication")
    if not exact and digest(canonical) != OBSERVED_SHA:
        raise ValueError("A different valid display must preserve the corrupt canonical image")
    cpu = time.process_time()
    wall = time.monotonic() - WALL_START
    receipt = {
        "schema": "SETI_ONE_SAVED_MEAN_DISPLAY_REPAIR_V1",
        "status": "EXACT_ORIGINAL_INTENDED_PNG_BYTES_RECOVERED" if exact else "VALID_VERSIONED_DISPLAY_COPY_ORIGINAL_CORRUPT_IMAGE_PRESERVED",
        "UTC_completed": datetime.now(timezone.utc).isoformat(),
        "script_sha256": digest(Path(__file__)), "plan_sha256": args.expected_plan_sha256,
        "root_confirmed_prospective_public_repair_freeze_commit": args.repair_freeze_commit,
        "acceptance_scope_sha256": ACCEPTANCE_SHA, "acceptance_public_freeze_commit": ACCEPTANCE_FREEZE,
        "original_renderer_sha256": FROZEN_SHA, "original_renderer_main_called": False,
        "one_original_plot_means_helper_call": True, "coverage_plot_rerendered": False,
        "original_plotting_receipt_sha256": RECEIPT_SHA, "original_plotting_receipt_byte_unchanged": True,
        "observed_corrupt_SHA256": OBSERVED_SHA, "observed_corrupt_bytes": OBSERVED_BYTES,
        "public_preserved_opaque_copy_path": plan["observed_corrupt_opaque_copy_path"],
        "public_corruption_receipt": frozen_inputs["corruption_receipt"],
        "corruption_cause": "UNKNOWN_NOT_ATTRIBUTED_TO_A_TOOL_OR_WRITER",
        "intended_original_sha256": INTENDED_SHA, "intended_original_bytes": INTENDED_BYTES,
        "exact_intended_bytes_recovered": exact, "canonical_path_replaced": exact,
        "published_image_path": str(target.relative_to(root)), "published_image_validation": publication,
        "validated_buffer_opaque_backup_path": plan["validated_buffer_opaque_copy_path"],
        "validated_buffer_opaque_backup_sha256": digest(backup),
        "one_attempt_marker_path": plan["attempt_marker_path"],
        "one_attempt_marker_sha256": digest(attempt),
        "input_pins_sha256": PINS_SHA, "input_json": inputs.opened, "input_json_byte_unchanged": True,
        "source_audit_receipt_sha256": AUDIT_SHA, "source_audit_status": audit["status"],
        "source_audit_counts": audit["counts"], "source_audit_reexecuted": False,
        "case_count": 36, "saved_scan_mean_count": 216, "saved_means_float64_sha256": means_sha,
        "original_numeric_statuses_preserved": True,
        "original_resource_failure_count": 3, "original_complete_job_count": 1,
        "scientific_rerun_or_residual_recomputation": False, "source_H5_or_NPZ_access": False,
        "new_optimization_or_classification": False, "cross_batch_reranking": False,
        "process_CPU_seconds_including_imports": cpu, "CPU_cap_seconds": CPU_CAP,
        "wall_seconds": wall, "wall_cap_seconds": WALL_CAP,
        "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "memory_cap_bytes": MEMORY_CAP,
        "OS_RLIMIT_CPU_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
        "OS_RLIMIT_AS_bytes": list(resource.getrlimit(resource.RLIMIT_AS)),
        "all_measured_resource_caps_satisfied": (cpu <= CPU_CAP and wall <= WALL_CAP
                and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= MEMORY_CAP),
        "resource_accounting_end_boundary": "After validated image publication and protected-input verification; before final receipt serialization/hashing/stdout",
        "complete_command_resource_accounting": "Separate outer process resource measurement required by prospective plan",
        "retry_performed": False, "visual_QA": "Pending separate actual-image inspection receipt"
    }
    write_new_atomic(execution, (json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode())
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "published_image_path": receipt["published_image_path"],
                      "sha256": publication["sha256"], "bytes": publication["bytes"],
                      "CPU_seconds": cpu, "wall_seconds": wall, "receipt_sha256": digest(execution)}))


def preserve_failure_receipt(error):
    """Keep the early attempt marker even if no image can be published."""
    if ATTEMPT_CONTEXT is None or ATTEMPT_CONTEXT["execution"].exists():
        return
    context = ATTEMPT_CONTEXT
    state = {}
    for name in ("canonical", "versioned", "backup", "attempt"):
        path = context[name]
        state[name] = {"path": str(path.relative_to(context["root"])), "exists": path.exists()}
        if path.exists():
            state[name].update(sha256=digest(path), bytes=path.stat().st_size)
    receipt = {"schema": "SETI_ONE_SAVED_MEAN_DISPLAY_REPAIR_FAILURE_V1",
               "status": "FAILED_ONE_DISPLAY_REPAIR_ATTEMPT_NO_RETRY",
               "error_type": type(error).__name__, "error_message": str(error),
               "UTC_recorded": datetime.now(timezone.utc).isoformat(),
               "script_sha256": digest(Path(__file__)), "plan_sha256": context["plan_sha256"],
               "root_confirmed_public_repair_freeze_commit": context["public_freeze"],
               "artifact_state": state, "retry_performed": False,
               "process_CPU_seconds_at_failure_receipt_creation": time.process_time(),
               "wall_seconds_at_failure_receipt_creation": time.monotonic() - WALL_START,
               "max_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               "cpu_cap_seconds": CPU_CAP, "wall_cap_seconds": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
               "complete_command_resource_accounting": "Separate outer process resource measurement required by prospective plan"}
    write_new_atomic(context["execution"], (json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        try:
            preserve_failure_receipt(error)
        except Exception as receipt_error:
            print(json.dumps({"failure_receipt_error": type(receipt_error).__name__,
                              "early_attempt_marker_preserved_no_retry": ATTEMPT_CONTEXT is not None}))
        raise
