"""Inert codec16 implementation draft; direct invocation never dispatches.

The effectful function requires separately frozen raw dispatch evidence and an
outer supervisor. That integration is not supplied by this preparation.
All native imports and selected-code compilation are deferred to that function.
"""
import ast
import hashlib
import json
import re
import stat
import struct
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

from preparation import MIB, canonical, parse, read, selected_nodes


def _authenticate(raw, expected):
    if (not isinstance(raw, bytes) or not isinstance(expected, dict)
            or set(expected) != {"bytes", "sha256"} or type(expected["bytes"]) is not int
            or not 0 < expected["bytes"] <= 2 * MIB or not isinstance(expected["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]) or len(raw) != expected["bytes"]
            or hashlib.sha256(raw).hexdigest() != expected["sha256"]):
        raise ValueError("external raw pin differs")
    return parse(raw)


def _verify_authority(root, manifest):
    contents = {}
    for original, pin in manifest["files"].items():
        raw = read(root, pin["local_path"])
        if len(raw) != pin["bytes"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise ValueError("maintained source/input bytes changed: " + original)
        contents[original] = raw
    return contents


def _compile_nodes(raw, selected, environment):
    """Only a future admitted control may call this maintained-node compiler."""
    nodes = [node for _, node in selected_nodes(raw, selected)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<pinned-maintained-selection>", "exec"), environment)
    return environment


def _normalizer(np, contents, selection):
    """Bind exact maintained arithmetic, without importing detector/HTTP modules."""
    selections = selection["source_selections"]
    errors = _compile_nodes(contents["src/seti_repeater/search_v0p6.py"], selections["src/seti_repeater/search_v0p6.py"], {"__name__": "_codec16_maintained_errors"})
    core = SimpleNamespace(V0P6ContractError=errors["V0P6ContractError"], V0P6CapacityError=errors["V0P6CapacityError"])
    legacy = _compile_nodes(contents["src/seti_repeater/source_v0p6.py"], selections["src/seti_repeater/source_v0p6.py"], {"np": np, "core": core})
    row = _compile_nodes(contents["src/seti_repeater/source_m43h.py"], selections["src/seti_repeater/source_m43h.py"],
                         {"np": np, "legacy": SimpleNamespace(normalize_float32_blocks_v0p6=legacy["normalize_float32_blocks_v0p6"])})
    return row["normalize_native_row"]


def _guard(contents):
    path = "src/seti_repeater/hdf5_filter_contract_radio.py"
    tree = ast.parse(contents[path])
    if any(not isinstance(node, (ast.Expr, ast.FunctionDef)) for node in tree.body):
        raise ValueError("pure filter guard source capability differs")
    namespace = {}
    exec(compile(tree, "<pinned-filter-guard>", "exec"), namespace)
    return namespace


def _pattern(np, contents):
    path = "results_radio_native_v3_hdf5_runtime_candidate_20261003a/source_profile_probe.py"
    selection = {"assignments": [], "functions": ["pattern"], "classes": []}
    return _compile_nodes(contents[path], selection, {"np": np, "CHUNKS": (1, 1, 1048576)})["pattern"]


def _receiver_metadata(root, manifest, contents, plan):
    """Pure original metadata validator; never call its closure/loader APIs."""
    path = "results_radio_scientific_execution_prospective_20261003a/receiver_telescope_adapter.py"
    module_name = "_codec16_pinned_receiver_metadata"
    if module_name in sys.modules:
        raise ValueError("fresh receiver metadata module required")
    module = ModuleType(module_name)
    module.__file__ = str(root / manifest["files"][path]["local_path"])
    sys.modules[module_name] = module
    exec(compile(contents[path], module.__file__, "exec"), module.__dict__)
    paths = {
        "source_metadata": "config/radio_hd189733_source_preparation_20260927.json",
        "window_design": "results_radio_hd189733_geometry_2026-09-27/window_geometry.json",
        "window_contract": "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json",
        "receiver_bank_records": "results_radio_hd189733_receiver_2026-09-28/bank_records.json",
    }
    raw = {key: contents[path] for key, path in paths.items()}
    pins = {key: {field: manifest["files"][path][field] for field in ("bytes", "sha256")} for key, path in paths.items()}
    basis = parse(contents["results_radio_scientific_execution_prospective_20261003a/preserved-basis.json"])["basis"]
    context = module.validate_receiver_metadata(raw, pins, expected_basis=basis, role="calibration")
    if context["context_sha256"] != plan["scope"]["receiver_context_sha256"] or context["receiver_bank_sha256"] != plan["scope"]["receiver_bank_sha256"]:
        raise ValueError("receiver context/bank differs from external plan")
    return context


def _array_hash(array):
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def _independent_selected_hash(row, chunk, start, stop):
    """Future scalar witness: exact binary rational construction, no NumPy/PRNG."""
    digest = hashlib.sha256()
    for index in range(start, stop):
        numerator = 409600 + ((index * 17 + chunk * 31 + row * 13) % 4093) + 128 * ((index // 4096) % 17)
        digest.update(struct.pack("<f", numerator / 4096))
    return digest.hexdigest()


def _file_pin(path, cap):
    st = path.stat()
    if st.st_size > cap or st.st_blocks * 512 > cap:
        raise ValueError("logical or allocated output ceiling")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(MIB), b""):
            digest.update(block)
    return {"name": path.name, "bytes": st.st_size, "allocated_bytes_snapshot": st.st_blocks * 512,
            "sha256": digest.hexdigest()}


def produce(root, output, *, plan_raw, expected_plan_pin, manifest_raw, expected_manifest_pin,
            selection_raw, expected_selection_pin, dispatch_raw, expected_dispatch_pin):
    """Future single engineering leaf; no in-process spawning, RNG or acquisition.

    The caller must freeze/qualify the outer supervisor and runtime-byte checks.
    Dispatch evidence is an external engineering input, not a science certificate.
    The draft does not create this evidence and cannot invoke this function.
    """
    plan = _authenticate(plan_raw, expected_plan_pin)
    manifest = _authenticate(manifest_raw, expected_manifest_pin)
    selection = _authenticate(selection_raw, expected_selection_pin)
    dispatch = _authenticate(dispatch_raw, expected_dispatch_pin)
    required = {"schema", "scope_id", "plan_sha256", "input_manifest_sha256", "selection_sha256",
                "runtime_prefix", "outer_supervisor_scope_sha256", "engineering_execution_authorized"}
    if (set(dispatch) != required or dispatch["schema"] != "codec16-fresh-engineering-dispatch-v1"
            or dispatch["engineering_execution_authorized"] is not True
            or not re.fullmatch(r"codec16-[a-z0-9-]{1,80}", dispatch["scope_id"])
            or dispatch["plan_sha256"] != expected_plan_pin["sha256"]
            or dispatch["input_manifest_sha256"] != expected_manifest_pin["sha256"]
            or dispatch["selection_sha256"] != expected_selection_pin["sha256"]
            or not re.fullmatch(r"[0-9a-f]{64}", dispatch["outer_supervisor_scope_sha256"])
            or plan["input_manifest_sha256"] != expected_manifest_pin["sha256"]
            or plan["selection_manifest_sha256"] != expected_selection_pin["sha256"]
            or not sys.flags.isolated or not sys.dont_write_bytecode
            or Path(sys.prefix).resolve() != Path(dispatch["runtime_prefix"]).resolve()):
        raise ValueError("separate fresh engineering dispatch/runtime input required")
    scope = plan["scope"]
    if (scope["role"] != "calibration" or scope["scan"] != "epoch1_on" or scope["row_indices"] != list(range(16))
            or scope["source_shape"] != [16, 1, 264503296] or scope["source_chunks"] != [1, 1, 1048576]
            or scope["source_dtype"] != "<f4" or scope["legacy_pipeline"] != [[32008, 1, [0, 3, 4, 0, 2]]]
            or scope["archive_interval"] != [167215104, 167280640] or scope["chunk_index"] != 159
            or scope["input_orientation"] != "descending" or scope["selected_channels"] != 65536):
        raise ValueError("fixed partial codec16 scope differs")
    root = Path(root).resolve()
    contents = _verify_authority(root, manifest)
    context = _receiver_metadata(root, manifest, contents, plan)
    output = Path(output)
    output.mkdir(mode=0o700, exist_ok=False)
    start = time.monotonic()
    # Deferred: never performed by preparation, inspection or direct CLI entry.
    import numpy as np
    import h5py
    import hdf5plugin
    import importlib.metadata
    runtime = {"numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
               "hdf5plugin": importlib.metadata.version("hdf5plugin")}
    if runtime != plan["runtime_basis"]["versions"]:
        raise ValueError("current E version identity differs")
    normalize = _normalizer(np, contents, selection)
    pattern = _pattern(np, contents)
    guard = _guard(contents)
    envelope = plan["draft_envelope"]
    scope = plan["scope"]
    shape, chunks = tuple(scope["source_shape"]), tuple(scope["source_chunks"])
    pipeline = scope["legacy_pipeline"]
    source_definition = parse(contents["config/radio_hd189733_source_preparation_20260927.json"])
    scan_definition = next(row for row in source_definition["scans"] if row["label"] == "epoch1_on")
    if guard["declared"](scan_definition, required=True) != pipeline:
        raise ValueError("exact original scan declaration differs")
    chunk = scope["chunk_index"]
    lo, hi = scope["archive_interval"]
    origin = chunk * chunks[2]
    cache = 8 * MIB
    encoder, legacy = output / "controlled-encoder.h5", output / "controlled-legacy.h5"
    encoder_pipeline = None
    with h5py.File(encoder, "x", rdcc_nbytes=cache) as handle:
        dataset = handle.create_dataset("data", shape=shape, chunks=chunks, dtype="<f4",
                                        **hdf5plugin.Bitshuffle(nelems=0, cname="lz4"))
        encoder_pipeline = guard["signature"]([dataset.id.get_create_plist().get_filter(0)])
        for row in range(16):
            values = pattern(chunk, row)
            dataset[row, 0, origin:origin + chunks[2]] = values
            del values
            handle.flush()
            _bounded_stat(encoder, envelope["each_hdf5_file_cap_bytes"])
            _bounded_output(output, envelope["leaf_output_cap_bytes"])
        if dataset.id.get_num_chunks() != 16:
            raise ValueError("exact sixteen encoder chunks required")
    paths = [h5py.h5pl.get(i) for i in range(h5py.h5pl.size())]
    compressed = []
    try:
        for i in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(i)
        if not h5py.h5z.unregister_filter(32008) or h5py.h5z.filter_avail(32008):
            raise ValueError("optional legacy declaration isolation failed")
        with h5py.File(legacy, "x", rdcc_nbytes=cache) as handle:
            creation = h5py.h5p.create(h5py.h5p.DATASET_CREATE)
            creation.set_chunk(chunks)
            creation.set_filter(32008, h5py.h5z.FLAG_OPTIONAL, tuple(pipeline[0][2]))
            creation.set_fill_time(h5py.h5d.FILL_TIME_NEVER)
            dataset = h5py.Dataset(h5py.h5d.create(handle.id, b"data", h5py.h5t.IEEE_F32LE,
                                                  h5py.h5s.create_simple(shape), dcpl=creation))
            guard["check_dataset"](dataset, pipeline)
            with h5py.File(encoder, "r", rdcc_nbytes=cache) as encoded:
                for row in range(16):
                    offset = (row, 0, origin)
                    info = encoded["data"].id.get_chunk_info_by_coord(offset)
                    if info.filter_mask != 0 or not 0 < info.size <= envelope["compressed_payload_cap_bytes"]:
                        raise ValueError("compressed chunk metadata exceeds bound before allocation")
                    mask, payload = encoded["data"].id.read_direct_chunk(offset)
                    if mask != 0 or len(payload) != info.size or not 0 < len(payload) <= envelope["compressed_payload_cap_bytes"]:
                        raise ValueError("filtered compressed payload bound/mask differs")
                    dataset.id.write_direct_chunk(offset, payload, filter_mask=0)
                    compressed.append({"row": row, "compressed_bytes": len(payload), "compressed_sha256": hashlib.sha256(payload).hexdigest()})
                    del payload
                    handle.flush()
                    _bounded_stat(legacy, envelope["each_hdf5_file_cap_bytes"])
                    _bounded_output(output, envelope["leaf_output_cap_bytes"])
    finally:
        for i in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(i)
        for path in paths:
            h5py.h5pl.append(path)
        if not hdf5plugin.register(filters=32008, force=True):
            raise ValueError("controlled process filter restoration failed")
    rows = []
    with h5py.File(legacy, "r", rdcc_nbytes=cache) as handle:
        dataset = handle["data"]
        guard["check_dataset"](dataset, pipeline)
        if dataset.shape != shape or dataset.chunks != chunks or dataset.dtype.str != "<f4" or dataset.id.get_num_chunks() != 16:
            raise ValueError("exact legacy geometry/chunk count differs")
        for row in range(16):
            expected = pattern(chunk, row)
            full = dataset[row, 0, origin:origin + chunks[2]]
            native = dataset[row, 0, lo:hi]
            expected_full_hash = _array_hash(expected)
            expected_selected_hash = _independent_selected_hash(row, chunk, lo - origin, hi - origin)
            if _array_hash(full) != expected_full_hash or _array_hash(native) != expected_selected_hash:
                raise ValueError("controlled full chunk/selected row is not bit exact")
            ascending, normalized = normalize(native)
            rows.append({**compressed[row], "full_decoded_sha256": _array_hash(full),
                         "independent_selected_construction_sha256": expected_selected_hash,
                         "native_descending_sha256": _array_hash(native), "ascending_raw_sha256": _array_hash(ascending),
                         "normalized_sha256": _array_hash(normalized), "selected_cells": 65536})
            del expected, full, native, ascending, normalized
    _verify_authority(root, manifest)
    files = [_file_pin(path, envelope["each_hdf5_file_cap_bytes"]) for path in (encoder, legacy)]
    result = {"schema": "codec16-controlled-partial-handoff-v1", "status": "OBSERVED_ENGINEERING_ONLY",
              "scope_id": dispatch["scope_id"], "plan_sha256": expected_plan_pin["sha256"], "runtime": runtime,
              "scope": scope, "receiver_context_sha256": context["context_sha256"],
              "receiver_bank_sha256": context["receiver_bank_sha256"], "encoder_pipeline": encoder_pipeline,
              "legacy_pipeline": pipeline, "rows": rows, "hdf5_files": files,
              "elapsed_seconds_from_output_creation_before_receipt": time.monotonic() - start,
              "handoff": {"role": "calibration", "scan": "epoch1_on", "receiver_context_sha256": scope["receiver_context_sha256"],
                          "receiver_bank_sha256": scope["receiver_bank_sha256"],
                          "raw_row_sha256s": [row["native_descending_sha256"] for row in rows],
                          "normalized_row_sha256s": [row["normalized_sha256"] for row in rows]},
              "raw_row_convention": "native archive-descending selected float32 rows",
              "metadata_case_laws_executed_here": False, "handoffs_observed": 1, "complete_codec_handoffs_required": 12,
              "telescope_provenance": False, "archive_payload_verified": False,
              "complete_codec_certificate_issued": False, "scientific_readiness": False,
              "scientific_allocation_charged": False, "rng_draws": 0, "network_requests": 0,
              "inner_process_rss_or_complete_native_io_claimed": False,
              "outer_lifetime_runtime_integrity_read_accounting_required": True}
    receipt = output / "codec16-receipt.json"
    with receipt.open("xb") as handle:
        handle.write(canonical(result))
    _bounded_output(output, envelope["leaf_output_cap_bytes"])
    return result


def _bounded_stat(path, cap):
    st = path.stat()
    if st.st_size > cap or st.st_blocks * 512 > cap:
        raise ValueError("controlled HDF5 file exceeds frozen byte ceiling")


def _bounded_output(root, cap):
    logical, allocated = 0, 0
    for path in (root, *root.rglob("*")):
        st = path.lstat()
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            raise ValueError("ordinary output files/directories required")
        logical += st.st_size
        allocated += st.st_blocks * 512
    if max(logical, allocated) > cap:
        raise ValueError("aggregate leaf output snapshot exceeds ceiling")


if __name__ == "__main__":
    raise SystemExit("NO_DISPATCHED: this inert draft has no executable dispatcher")
