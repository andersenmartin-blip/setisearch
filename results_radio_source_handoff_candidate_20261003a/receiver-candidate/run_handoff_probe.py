"""Fresh receipt-to-receiver handoff probe; never execute NativeRun.

The acquisition index file digest comes from the external caller. The index
binds source.json file bytes, semantic receipt hashes, and all row oracles.
No telescope, holdout, score, control, RNG or network operation is permitted.
"""
import argparse
import ast
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path("/workspace/scratch/fb4056c33767/frozen-project")
RUNTIME = Path("/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a/venv")
BRIDGE_SHA256 = "72a8b4fbfdc3aad809b079523022def77bbfdc44e71408ddfc13ba79e0d7a090"
LIMITS = {"seconds": 60, "peak_rss_bytes": 512 * 1024**2,
          "generated_file_bytes": 16 * 1024**2}
START = time.monotonic()
OUT = None
SOCKET_ATTEMPTS = []
FORBIDDEN_INVOCATIONS = []


def audit(event, args):
    if event.startswith("socket.") and event != "socket.__new__":
        SOCKET_ATTEMPTS.append({"event": event, "argument_types": [type(x).__name__ for x in args]})
        raise RuntimeError("socket operation denied by receiver handoff probe")


sys.addaudithook(audit)
if (not sys.flags.isolated or not sys.dont_write_bytecode
        or Path(sys.prefix).resolve() != RUNTIME.resolve()):
    raise RuntimeError("pinned isolated HDF5 interpreter with -I -B required")
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(Path(__file__).resolve().parent)]
import h5py
import hdf5plugin
import numpy as np
import local_receipt_receiver as bridge
from radio_receiver_adapter_common import context, PINS as CONTEXT_PINS


def canonical(value):
    return bridge.core.canonical_json_bytes(value)


def budget():
    if time.monotonic() - START > LIMITS["seconds"]:
        raise RuntimeError("handoff candidate time ceiling")
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > LIMITS["peak_rss_bytes"]:
        raise RuntimeError("handoff candidate RSS ceiling")
    if OUT is not None and OUT.exists():
        size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
        if size > LIMITS["generated_file_bytes"]:
            raise RuntimeError("handoff candidate output ceiling")


def pin(path, *, maximum=None):
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or (maximum is not None and before.st_size > maximum):
            raise ValueError("only bounded regular input files allowed: " + str(path))
        digest = hashlib.sha256()
        count = 0
        while chunk := handle.read(1024 * 1024):
            count += len(chunk)
            if count > before.st_size or (maximum is not None and count > maximum):
                raise ValueError("input size grew during bounded hash: " + str(path))
            digest.update(chunk)
            budget()
        if count != before.st_size:
            raise ValueError("input size changed during bounded hash: " + str(path))
    return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}


def write(path, value):
    payload = canonical(value)
    budget()
    current = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    if current + len(payload) > LIMITS["generated_file_bytes"]:
        raise RuntimeError("handoff candidate prospective output ceiling")
    with Path(path).open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    budget()


def read_json_once(path, expected_sha256, *, maximum, expected_bytes=None):
    bridge.core._frozen_sha256(expected_sha256, "externally bound file digest")
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum
                or (expected_bytes is not None and before.st_size != expected_bytes)):
            raise ValueError("bound JSON size/type differs: " + str(path))
        payload = handle.read(maximum + 1)
    if len(payload) != before.st_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("bound JSON file bytes differ: " + str(path))
    value = json.loads(payload)
    budget()
    return value, {"path": str(path), "bytes": len(payload), "sha256": expected_sha256}


def runtime_inputs():
    paths = {Path(sys.executable).resolve()}
    modules = {}
    for name, module in tuple(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and Path(file).is_file():
            resolved = Path(file).resolve()
            paths.add(resolved)
            modules[name] = str(resolved)
    mapped = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/"):
            resolved = Path(fields[5]).resolve(strict=True)
            paths.add(resolved)
            mapped.add(str(resolved))
    return paths, modules, sorted(mapped)


def forbid(name):
    def denied(*args, **kwargs):
        FORBIDDEN_INVOCATIONS.append(name)
        raise RuntimeError("forbidden handoff operation: " + name)
    return denied


def main(args):
    global OUT
    OUT = Path(args.output).resolve()
    OUT.mkdir(exist_ok=False)
    write(OUT / "observation-identity.json", {
        "schema": "radio-candidate-procfs-observation-identity-v1",
        "procfs_pid": int(os.readlink("/proc/self")), "namespace_pid": os.getpid(),
        "driver_path": str(Path(__file__).resolve()), "observed_after_module_imports": True,
        "whole_lifetime_certificate": False,
    })
    driver_pin = pin(Path(__file__).resolve(), maximum=64 * 1024)
    bridge_pin = pin(Path(bridge.__file__).resolve(), maximum=64 * 1024)
    if bridge_pin["sha256"] != BRIDGE_SHA256:
        raise ValueError("reviewed receiver bridge source changed")
    acquisition_path = Path(args.acquisition_index).resolve()
    acquisition, acquisition_pin = read_json_once(acquisition_path, args.trusted_acquisition_sha256,
                                                  maximum=8 * 1024**2)
    if (acquisition.get("schema") != "radio-full-source-acquisition-candidate-index-v1"
            or acquisition.get("status") != "PASS"
            or type(acquisition.get("full_scan_window_pairs")) is not int
            or acquisition["full_scan_window_pairs"] != 18
            or type(acquisition.get("row_products")) is not int
            or acquisition["row_products"] != 288
            or acquisition.get("source_or_scientific_admission") is not False
            or acquisition.get("receiver_handoff_qualified") is not False):
        raise ValueError("complete passing local acquisition report required")
    expected_keys = {(role, label) for role in bridge.ROLES for label in bridge.received.LABELS}
    products = acquisition["products"]
    if (len(products) != 18 or {(p["role"], p["label"]) for p in products} != expected_keys):
        raise ValueError("exact eighteen receiver scan/window products required")
    by_key = {(p["role"], p["label"]): p for p in products}
    declared_files = {p["path"]: p for p in acquisition["generated_files"]}
    descriptor_pin = acquisition["fixture_descriptor_pin"]
    descriptor_path = acquisition_path.parent / "fixture-descriptor.json"
    if descriptor_pin["path"] != str(descriptor_path):
        raise ValueError("fixture descriptor path leaves the bound acquisition")
    descriptor, actual_descriptor_pin = read_json_once(descriptor_path, descriptor_pin["sha256"],
        maximum=1024 * 1024, expected_bytes=descriptor_pin["bytes"])
    if (descriptor_pin["sha256"] != acquisition["fixture_source_contract_sha256"]
            or descriptor.get("telescope_provenance") is not False
            or descriptor.get("scientific_allocation") is not False
            or descriptor.get("random_draws") != 0):
        raise ValueError("local fixture descriptor ancestry changed")
    before = {str(acquisition_path): acquisition_pin, str(descriptor_path): actual_descriptor_pin,
              driver_pin["path"]: driver_pin, bridge_pin["path"]: bridge_pin}
    # The complete frozen project and every file actually loaded/mapped by the
    # observed runtime are pinned. This remains an observed file set, not a
    # complete future execution or filesystem lifetime certificate.
    runtime_paths, imported_before, mapped_before = runtime_inputs()
    positive_paths = runtime_paths | {p.resolve() for p in ROOT.rglob("*") if p.is_file()}
    for path in sorted(positive_paths):
        before[str(path)] = pin(path, maximum=256 * 1024**2)
    for name, expected in CONTEXT_PINS.items():
        if before[str(ROOT / name)]["sha256"] != expected:
            raise ValueError("published receiver context input changed: " + name)
    source_receipts = {}
    product_files = []
    for role in bridge.ROLES:
        for label in bridge.received.LABELS:
            product = by_key[role, label]
            directory = acquisition_path.parent / "products" / role / label
            if product["directory"] != str(directory):
                raise ValueError("bound product directory path changed")
            source_path = directory / "source.json"
            source_pin = product["source_file"]
            if source_pin["path"] != str(source_path):
                raise ValueError("bound source receipt path changed")
            receipt, actual_source_pin = read_json_once(source_path, source_pin["sha256"],
                maximum=bridge.MAX_SOURCE_JSON_BYTES, expected_bytes=source_pin["bytes"])
            bridge.rows.verify(receipt)
            if (receipt["receipt_sha256"] != product["receipt_sha256"]
                    or bridge.rows.digest(receipt["scope"]) != product["scope_sha256"]
                    or receipt["scope"]["contract_sha256"] != descriptor_pin["sha256"]
                    or product["fixture_source_contract_sha256"] != descriptor_pin["sha256"]):
                raise ValueError("source semantic receipt differs from externally pinned acquisition report")
            before[str(source_path)] = actual_source_pin
            source_receipts[role, label] = receipt
            if len(product["row_oracles"]) != 16:
                raise ValueError("sixteen externally bound row oracles required")
            for row, oracle in enumerate(product["row_oracles"]):
                if (type(oracle["row"]) is not int or oracle["row"] != row
                        or receipt["rows"][row]["native_sha256"] != oracle["native_sha256"]
                        or receipt["rows"][row]["normalized_sha256"] != oracle["normalized_sha256"]
                        or (row == 0 and oracle["independent_normalized_sha256"] != oracle["normalized_sha256"])):
                    raise ValueError("acquired row receipt differs from bound oracle")
                for suffix, maximum in (("json", bridge.MAX_ROW_JSON_BYTES),
                                        ("native.npy", 65536 * 4 + 4096),
                                        ("normalized.npy", 65536 * 4 + 4096)):
                    path = directory / f"row{row:02d}.{suffix}"
                    actual = pin(path, maximum=maximum)
                    declared = declared_files[str(path)]
                    if actual["bytes"] != declared["bytes"] or actual["sha256"] != declared["sha256"]:
                        raise ValueError("product file differs from trusted acquisition index")
                    before[str(path)] = actual
                    product_files.append(str(path))
    write(OUT / "positive-inputs-before.json", {"schema": "radio-handoff-observed-positive-input-pins-v1",
        "files": [before[p] for p in sorted(before)], "actual_imported_module_paths": imported_before,
        "mapped_paths": mapped_before, "whole_execution_runtime_qualification": False})
    reports = []
    with ExitStack() as stack:
        for name in ("build_store", "cache", "receiver", "calibrate", "execute"):
            stack.enter_context(patch.object(bridge.pipeline.NativeRun, name, side_effect=forbid("NativeRun." + name)))
        for name in ("build_synthetic_cache", "gather_bank_slice"):
            stack.enter_context(patch.object(bridge.native, name, side_effect=forbid("native." + name)))
        for name in ("default_rng", "RandomState", "seed", "random", "normal"):
            stack.enter_context(patch.object(np.random, name, side_effect=forbid("numpy.random." + name)))
        for role in bridge.ROLES:
            c = context(role)
            p = json.loads(c.factor_contract.factors.provenance_json)
            entries = [{"label": label, "scope": source_receipts[role, label]["scope"],
                        "receipt_sha256": by_key[role, label]["receipt_sha256"]}
                       for label in bridge.received.LABELS]
            manifest = {"schema": bridge.SCHEMA, "domain": "local-fixture", **bridge.receiver_window(c),
                "context_sha256": c.identity, "receiver_factor_bank_sha256": c.factor_contract.factors.identity,
                "receiver_source_contract_sha256": p["source_contract_sha256"],
                "fixture_source_contract_sha256": descriptor_pin["sha256"],
                "runtime": acquisition["runtime"], "scans": entries}
            # This derived manifest digest is rooted in the independently given
            # acquisition index SHA, its source file pins/receipt SHA values,
            # and separately pinned published context inputs.
            manifest_digest = bridge.rows.digest(manifest)
            binding = bridge.bind(manifest, manifest_digest, c)
            write(OUT / (role + "-binding.json"), manifest)
            directories = {label: by_key[role, label]["directory"] for label in bridge.received.LABELS}
            run, handoff = bridge.fixture_run(c, binding, directories)
            checked = 0
            for label in bridge.received.LABELS:
                for row, oracle in enumerate(by_key[role, label]["row_oracles"]):
                    if bridge.native.array_hash(run.sources[label].values[row]) != oracle["normalized_sha256"]:
                        raise ValueError("receiver normalized row differs from acquisition oracle")
                    checked += 1
            bridge.rows.verify(handoff)
            write(OUT / (role + "-handoff.json"), handoff)
            reports.append({"role": role, "context_sha256": c.identity, "binding_sha256": binding.identity,
                "handoff_receipt_sha256": handoff["receipt_sha256"], "source_ids": run.source_ids,
                "normalized_rows_compared_to_acquisition_oracles": checked,
                "unique_raw_payloads": handoff["unique_raw_payloads"],
                "unique_normalized_payloads": handoff["unique_normalized_payloads"],
                "modelled_array_bound_bytes": handoff["modelled_array_bound_bytes"]})
            del run, handoff, c
            budget()
    after = {path: pin(path, maximum=256 * 1024**2) for path in sorted(before)}
    if after != before:
        raise ValueError("positive input file payloads changed during handoff probe")
    final_paths, imported_after, mapped_after = runtime_inputs()
    additions = [pin(path, maximum=256 * 1024**2) for path in sorted(final_paths - runtime_paths)]
    write(OUT / "positive-inputs-after.json", {"schema": "radio-handoff-observed-positive-input-pins-v1",
        "files": [after[p] for p in sorted(after)], "actual_imported_module_paths": imported_after,
        "mapped_paths": mapped_after, "additional_observed_runtime_files": additions,
        "whole_execution_runtime_qualification": False})
    metadata_path = ROOT / "src/seti_repeater/prospective_source_metadata_radio.py"
    missing = next(ast.literal_eval(node.value) for node in ast.parse(metadata_path.read_bytes()).body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MISSING_FIELDS"
                                                for target in node.targets))
    if len(missing) != 11 or missing != acquisition["scientific_missing_fields_unchanged"]:
        raise ValueError("eleven scientific missing fields changed")
    if SOCKET_ATTEMPTS or FORBIDDEN_INVOCATIONS:
        raise ValueError("forbidden capability attempted")
    generated = [pin(path, maximum=LIMITS["generated_file_bytes"]) for path in sorted(OUT.rglob("*")) if path.is_file()]
    report = {
        "schema": "radio-local-codec-receiver-handoff-probe-candidate-v1", "status": "PASS",
        "authority": "local synthetic candidate engineering only",
        "acquisition_index_pin": acquisition_pin, "fixture_descriptor_pin": actual_descriptor_pin,
        "driver_pin": driver_pin, "bridge_pin": bridge_pin, "runtime": bridge.codec.runtime(),
        "roles": reports, "receiver_contexts_constructed": 3, "scan_window_products": 18,
        "normalized_rows_compared_to_acquisition_oracles": sum(r["normalized_rows_compared_to_acquisition_oracles"] for r in reports),
        "positive_input_file_count": len(before), "positive_product_row_file_count": len(product_files),
        "positive_input_payloads_unchanged": True,
        "socket_attempts": SOCKET_ATTEMPTS, "forbidden_invocations": FORBIDDEN_INVOCATIONS,
        "network_requests": 0, "telescope_or_holdout_files_opened": 0, "rng_draws": 0,
        "scoring_invoked": False, "reduction_invoked": False, "controls_invoked": False,
        "scientific_missing_fields_unchanged": missing, "resource_limits": LIMITS,
        "observed_seconds": time.monotonic() - START,
        "observed_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "generated_files": generated, "generated_file_bytes_before_report": sum(p["bytes"] for p in generated),
        "complete_execution_runtime_freeze": False, "externally_observed_complete_lifetime": False,
        "whole_execution_runtime_qualification": False, "public_authentication_established": False,
        "source_specific_executable_contract_created": False, "source_or_scientific_admission": False,
        "receiver_scoring_qualified": False, "hosted_transport_qualified": False,
        "telescope_provenance_established": False, "independent_draws_established": False,
        "coverage_limitations": [
            "Synthetic local-fixture receipts and published receiver metadata only; no telescope values or observations.",
            "NativeRun is constructed but scoring, cache, reduction and scientific control stages are not invoked.",
            "Observed file snapshots do not certify complete future execution or filesystem lifetime.",
            "Inherited rehydrate reopens files; hostile concurrent filesystem mutation during that call remains outside qualification.",
        ],
    }
    write(OUT / "index.json", report)
    budget()
    print(json.dumps({"status": "PASS", "contexts": 3, "products": 18, "rows_checked": 288,
                      "seconds": report["observed_seconds"], "report": pin(OUT / "index.json")}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-index", required=True)
    parser.add_argument("--trusted-acquisition-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        main(args)
    except BaseException as error:
        if OUT is not None and OUT.exists() and not (OUT / "failure.json").exists():
            write(OUT / "failure.json", {"schema": "radio-receiver-handoff-candidate-failure-v1",
                "error": repr(error), "traceback": traceback.format_exc(),
                "seconds": time.monotonic() - START, "automatic_retry": False,
                "source_or_scientific_admission": False})
        raise
