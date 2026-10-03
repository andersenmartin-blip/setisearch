"""Fresh candidate codec probe. Uses synthetic bytes and the pure filter guard only."""
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import struct
import sys
import time
import traceback

import h5py
import hdf5plugin
import numpy as np

ROOT = Path("/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive")
CANDIDATE = Path("/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a")
OUT = Path("/workspace/scratch/fa2e54995e11/source-candidate/all-rows-probe-20261003c")
WORK = OUT / "generated"
PINS = {
    "src/seti_repeater/hdf5_filter_contract_radio.py": "65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6",
    "src/seti_repeater/source_radio.py": "d189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f",
    "src/seti_repeater/source_m43h.py": "85ce563e78b2d16f65b6a15313c4ae0c22a58f1455ce8db77acbc9a62d33429d",
    "src/seti_repeater/prospective_source_metadata_radio.py": "2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360",
    "config/radio_hd189733_source_preparation_20260927.json": "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1",
    "results_radio_hd189733_geometry_2026-09-27/window_geometry.json": "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6",
    "results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json": "58b41ebdd2d7e407fc2ae49f594811e38c199f4914d34d0fe8e318bb0936894a",
    "results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json": "2b93524d831627186635963b48ed32ef3c02b6ed7d37d3a0a0ee68e53dfa7ac0",
    "results_radio_hd189733_codec_2026-09-28/postflight.json": "812713dfe264fcd41638b6e6c65f9d9e7595523be8f1e38bf2c59802b81b8874",
}
PROFILE = [[32008, 1, [0, 3, 4, 0, 2]]]
SHAPE = (16, 1, 264503296)
CHUNKS = (1, 1, 1048576)
START = time.monotonic()
LIMITS = {"seconds": 60, "peak_rss_bytes": 256 * 1024**2, "generated_file_bytes": 96 * 1024**2}


def file_pin(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
    st = path.stat()
    return {"path": str(path), "bytes": st.st_size, "sha256": digest.hexdigest(), "allocated_bytes": st.st_blocks * 512}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def write(path, value):
    with path.open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        os.fsync(handle.fileno())


def budget():
    if time.monotonic() - START > LIMITS["seconds"]:
        raise RuntimeError("candidate probe time ceiling")
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > LIMITS["peak_rss_bytes"]:
        raise RuntimeError("candidate probe RSS ceiling")
    if WORK.exists() and sum(p.stat().st_size for p in WORK.iterdir() if p.is_file()) > LIMITS["generated_file_bytes"]:
        raise RuntimeError("candidate generated-file ceiling")


def pattern(chunk, row):
    # Exactly representable binary fractions, no PRNG or source/noise model.
    index = np.arange(CHUNKS[2], dtype="<u4")
    return (np.float32(100) + ((index * 17 + chunk * 31 + row * 13) % 4093).astype("<f4") *
            np.float32(1 / 4096) + ((index // 4096) % 17).astype("<f4") * np.float32(1 / 32)).astype("<f4")


class MetadataDataset:
    def __init__(self, entries):
        self.entries = entries
        self.payload_index_attempts = 0
    def get_create_plist(self):
        return self
    def get_nfilters(self):
        return len(self.entries)
    def get_filter(self, index):
        return self.entries[index]
    @property
    def id(self):
        return self
    def __getitem__(self, key):
        self.payload_index_attempts += 1
        raise RuntimeError("payload indexing is forbidden in metadata case laws")



def closure_snapshot():
    # Candidate package files, shared base stdlib (excluding site-packages),
    # loaded Python sources and all file-backed process mappings. This is a
    # bounded observed closure, not a complete runtime/lifetime certificate.
    paths = set()
    links = []
    candidate_root = CANDIDATE / "venv"
    for path in candidate_root.rglob("*"):
        if path.is_symlink():
            target = path.resolve(strict=True)
            if not target.is_relative_to(candidate_root):
                raise ValueError("candidate runtime link leaves candidate root")
            links.append({"path": str(path), "link_text": os.readlink(path),
                          "resolved_target": str(target), "target_is_directory": target.is_dir()})
            continue
        if path.is_file():
            paths.add(path.resolve())
    stdlib = Path(sys.base_prefix) / "lib/python3.12"
    for directory, subdirs, names in os.walk(stdlib):
        subdirs[:] = [name for name in subdirs if name != "site-packages"]
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                target = path.resolve(strict=True)
                if not target.is_relative_to(stdlib):
                    raise ValueError("base stdlib link leaves stdlib root")
                links.append({"path": str(path), "link_text": os.readlink(path),
                              "resolved_target": str(target), "target_is_directory": target.is_dir()})
                if target.is_file():
                    paths.add(target)
                continue
            if path.is_file():
                paths.add(path.resolve())
    modules = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).is_file():
            path = Path(filename).resolve()
            paths.add(path)
            modules[name] = str(path)
    mapped = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[-1].startswith("/"):
            path = Path(fields[-1])
            if not path.is_file():
                raise ValueError("mapped runtime path unavailable")
            paths.add(path.resolve())
            mapped.add(str(path.resolve()))
    paths.add(Path(sys.executable).resolve())
    records = [file_pin(path) for path in sorted(paths)]
    return {"schema": "radio-candidate-observed-runtime-file-closure-v1",
            "files": records, "file_count": len(records), "links": links,
            "raw_bytes": sum(item["bytes"] for item in records),
            "loaded_module_paths": modules, "mapped_runtime_paths": sorted(mapped),
            "interpreter": str(Path(sys.executable).resolve()),
            "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "sys_path": sys.path, "isolated": bool(sys.flags.isolated),
            "dont_write_bytecode": sys.dont_write_bytecode,
            "complete_execution_runtime_freeze": False,
            "externally_observed_complete_lifetime": False}


def closure_payload(value):
    return {item["path"]: (item["bytes"], item["sha256"], item["allocated_bytes"])
            for item in value["files"]}


def independent_selected_bytes(chunk_index, row, start, stop):
    # Binary-exact integer arithmetic + stdlib IEEE-float packing independently
    # validates every selected synthetic value, without NumPy arithmetic.
    return b"".join(struct.pack("<f", 100 + ((i * 17 + chunk_index * 31 + row * 13) % 4093) / 4096
                               + ((i // 4096) % 17) / 32) for i in range(start, stop))

def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix).resolve() != (CANDIDATE / "venv").resolve():
        raise RuntimeError("candidate probe requires its isolated interpreter with -I -B")
    frozen_runtime = closure_snapshot()
    write(OUT / "runtime-closure-before.json", frozen_runtime)
    WORK.mkdir(exist_ok=False)
    material = {}
    for relative, expected in PINS.items():
        path = ROOT / relative
        pin = file_pin(path)
        if pin["sha256"] != expected:
            raise ValueError("source or metadata pin differs: " + relative)
        material[relative] = pin
    # The exact 1,651-byte pure guard has no imports and only functions.
    # No acquisition, normalization, detector or scientific module is loaded.
    guard_path = ROOT / "src/seti_repeater/hdf5_filter_contract_radio.py"
    guard_tree = ast.parse(guard_path.read_bytes())
    if any(not isinstance(node, (ast.Expr, ast.FunctionDef)) for node in guard_tree.body):
        raise ValueError("pure filter guard top-level capability changed")
    guard = {"__builtins__": __builtins__}
    exec(compile(guard_tree, str(guard_path), "exec"), guard)
    source = json.loads((ROOT / "config/radio_hd189733_source_preparation_20260927.json").read_bytes())
    retained = json.loads((ROOT / "results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json").read_bytes())
    geometry = json.loads((ROOT / "results_radio_hd189733_geometry_2026-09-27/window_geometry.json").read_bytes())
    if source["hdf5_runtime"] is not None or source["windows"] or source["stage"] != "preparation-only-no-spectral-access":
        raise ValueError("original inactive source boundary changed")
    if len(source["scans"]) != 6 or [scan["role"] for scan in source["scans"]] != ["on", "off"] * 3:
        raise ValueError("six-scan order differs")
    for scan in source["scans"]:
        header = scan["expected_header"]
        if tuple(header["dataset_shape"]) != SHAPE or tuple(scan["expected_chunks"]) != CHUNKS or header["dataset_dtype"] != "float32":
            raise ValueError("six-scan geometry differs")
        if guard["declared"](scan, required=True) != PROFILE:
            raise ValueError("six-scan exact source profile differs")
    if retained["filter_pipeline"] != PROFILE or tuple(retained["dataset_shape"]) != SHAPE or tuple(retained["chunks"]) != CHUNKS:
        raise ValueError("retained fixture profile differs")
    windows = geometry["windows"]
    if [w["role"] for w in windows] != ["calibration", "validation", "pilot"]:
        raise ValueError("three-window order differs")
    for window in windows:
        lo, hi = window["archive_interval"]
        ci = window["archive_chunk_index"]
        if hi - lo != 65536 or not ci * CHUNKS[2] <= lo < hi <= (ci + 1) * CHUNKS[2]:
            raise ValueError("declared extraction window differs")
    cases = []
    def expect(name, operation, rejects=False):
        try:
            operation()
        except ValueError:
            if not rejects:
                raise
        else:
            if rejects:
                raise AssertionError("metadata case unexpectedly accepted: " + name)
        cases.append({"name": name, "expected": "reject" if rejects else "accept", "pass": True})
    positive = MetadataDataset(copy.deepcopy(PROFILE))
    expect("exact_pipeline", lambda: guard["check_dataset"](positive, PROFILE))
    named = [[32008, 1, [0, 3, 4, 0, 2], "display label is not codec authority"]]
    expect("display_name_ignored", lambda: guard["check_dataset"](MetadataDataset(named), PROFILE))
    expect("explicit_unfiltered", lambda: guard["declared"]({"observed_hdf5_filters": []}, required=True))
    expect("missing_optional_local_declaration", lambda: guard["declared"]({}, required=False))
    expect("missing_required_declaration", lambda: guard["declared"]({}, required=True), True)
    mutated = []
    for position in (0, 1):
        value = copy.deepcopy(PROFILE); value[0][position] += 1
        mutated.append(("pipeline_" + ("id" if position == 0 else "flags") + "_mutation", value))
    for index in range(5):
        value = copy.deepcopy(PROFILE); value[0][2][index] += 1
        mutated.append(("client_datum_" + str(index) + "_mutation", value))
    mutated.extend([("removed_filter", []), ("extra_filter", PROFILE + [[1, 1, [4]]])])
    datasets = []
    for name, entries in mutated:
        dataset = MetadataDataset(entries); datasets.append(dataset)
        expect(name, lambda dataset=dataset: guard["check_dataset"](dataset, PROFILE), True)
    for index, invalid in enumerate((True, -1, 2.0, "2")):
        value = copy.deepcopy(PROFILE); value[0][2][4] = invalid
        expect("invalid_client_datum_type_" + str(index), lambda value=value: guard["signature"](value), True)
    for name, entries in (("boolean_filter_id", [[True, 1, []]]), ("boolean_filter_flags", [[32008, True, []]]),
                          ("nonexplicit_pipeline", {}), ("malformed_filter_entry", [[32008, 1]])):
        expect(name, lambda entries=entries: guard["signature"](entries), True)
    if positive.payload_index_attempts or any(ds.payload_index_attempts for ds in datasets):
        raise AssertionError("metadata guard attempted a payload read")
    runtime = {"numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
               "hdf5plugin": importlib.metadata.version("hdf5plugin")}
    old_runtime = json.loads((ROOT / "results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json").read_bytes())
    if runtime != {key: old_runtime[key] for key in runtime}:
        raise ValueError("candidate runtime version tuple differs from archived local baseline")
    encoder = WORK / "candidate-current-encoder.h5"
    legacy = WORK / "candidate-legacy-declaration.h5"
    raw_receipts = []
    offsets = [(row, window) for row in range(16) for window in windows]
    with h5py.File(encoder, "x", rdcc_nbytes=8 * 1024**2) as handle:
        dataset = handle.create_dataset("data", shape=SHAPE, chunks=CHUNKS, dtype="<f4",
                                       **hdf5plugin.Bitshuffle(nelems=0, cname="lz4"))
        encoder_profile = guard["signature"]([dataset.id.get_create_plist().get_filter(0)])
        for row, window in offsets:
            ci = window["archive_chunk_index"]
            dataset[row, 0, ci * CHUNKS[2]:(ci + 1) * CHUNKS[2]] = pattern(ci, row)
            budget()
        handle.flush()
        if dataset.id.get_num_chunks() != 48:
            raise AssertionError("encoder populated chunk count differs")
    plugin_paths = [h5py.h5pl.get(index) for index in range(h5py.h5pl.size())]
    try:
        for index in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(index)
        if not h5py.h5z.unregister_filter(32008) or h5py.h5z.filter_avail(32008):
            raise RuntimeError("optional codec declaration isolation failed")
        with h5py.File(legacy, "x", rdcc_nbytes=8 * 1024**2) as handle:
            creation = h5py.h5p.create(h5py.h5p.DATASET_CREATE)
            creation.set_chunk(CHUNKS)
            creation.set_filter(32008, h5py.h5z.FLAG_OPTIONAL, (0, 3, 4, 0, 2))
            creation.set_fill_time(h5py.h5d.FILL_TIME_NEVER)
            identifier = h5py.h5d.create(handle.id, b"data", h5py.h5t.IEEE_F32LE,
                                         h5py.h5s.create_simple(SHAPE), dcpl=creation)
            dataset = h5py.Dataset(identifier)
            guard["check_dataset"](dataset, PROFILE)
            with h5py.File(encoder, "r", rdcc_nbytes=8 * 1024**2) as encoded:
                for row, window in offsets:
                    offset = (row, 0, window["archive_chunk_index"] * CHUNKS[2])
                    mask, payload = encoded["data"].id.read_direct_chunk(offset)
                    if mask != 0:
                        raise ValueError("encoder skipped the requested filter")
                    dataset.id.write_direct_chunk(offset, payload, filter_mask=0)
                    raw_receipts.append({"row": row, "role": window["role"], "offset": list(offset),
                                         "filter_mask": int(mask), "compressed_bytes": len(payload),
                                         "compressed_sha256": hashlib.sha256(payload).hexdigest()})
                    budget()
            handle.flush()
    finally:
        for index in range(h5py.h5pl.size() - 1, -1, -1):
            h5py.h5pl.remove(index)
        for path in plugin_paths:
            h5py.h5pl.append(path)
        if not hdf5plugin.register(filters=32008, force=True):
            raise RuntimeError("candidate process filter restoration failed")
    decoded = []
    independent_cells = 0
    with h5py.File(legacy, "r", rdcc_nbytes=8 * 1024**2) as handle:
        dataset = handle["data"]
        guard["check_dataset"](dataset, PROFILE)
        if dataset.shape != SHAPE or dataset.chunks != CHUNKS or dataset.dtype.str != "<f4" or dataset.id.get_num_chunks() != 48:
            raise ValueError("exact source-shaped legacy metadata differs")
        for row, window in offsets:
            lo, hi = window["archive_interval"]
            ci = window["archive_chunk_index"]
            expected = pattern(ci, row)
            full = dataset[row, 0, ci * CHUNKS[2]:(ci + 1) * CHUNKS[2]]
            selected = dataset[row, 0, lo:hi]
            wanted = expected[lo - ci * CHUNKS[2]:hi - ci * CHUNKS[2]]
            independent = independent_selected_bytes(ci, row, lo - ci * CHUNKS[2], hi - ci * CHUNKS[2])
            if wanted.tobytes() != independent:
                raise ValueError("independent stdlib construction disagrees with NumPy")
            independent_cells += len(independent) // 4
            if full.tobytes() != expected.tobytes() or selected.tobytes() != wanted.tobytes():
                raise ValueError("exact legacy declaration full chunk or window selection differs")
            decoded.append({"row": row, "role": window["role"], "chunk_index": ci,
                            "decoded_cells": full.size, "decoded_sha256": hashlib.sha256(full.tobytes()).hexdigest(),
                            "archive_interval": [lo, hi], "selected_cells": selected.size,
                            "selected_sha256": hashlib.sha256(selected.tobytes()).hexdigest(), "bit_exact": True})
            budget()
    for path in (encoder, legacy):
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
    for relative, expected in PINS.items():
        if file_pin(ROOT / relative)["sha256"] != expected:
            raise ValueError("held source/metadata changed during candidate qualification")
    prospective = ast.parse((ROOT / "src/seti_repeater/prospective_source_metadata_radio.py").read_bytes())
    missing = [ast.literal_eval(node.value) for node in prospective.body if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id == "MISSING_FIELDS" for target in node.targets)]
    if len(missing) != 1 or len(missing[0]) != 11:
        raise ValueError("permanently blocked scientific constructor differs")
    budget()
    final_runtime = closure_snapshot()
    write(OUT / "runtime-closure-after.json", final_runtime)
    if closure_payload(frozen_runtime) != closure_payload(final_runtime):
        raise ValueError("runtime file bytes or complete candidate inventory changed during probe")
    if frozen_runtime["links"] != final_runtime["links"]:
        raise ValueError("observed runtime symlink topology changed during probe")
    if frozen_runtime["mapped_runtime_paths"] != final_runtime["mapped_runtime_paths"]:
        raise ValueError("runtime mapped-file closure changed during probe")
    if any(name == "seti_repeater" or name.startswith("seti_repeater.") for name in sys.modules):
        raise ValueError("source/scientific module unexpectedly loaded")
    budget()
    result = {"schema": "radio-native-v3-candidate-all-rows-source-profile-v2", "authority": "candidate-only synthetic preparation",
              "status": "EXACT_LEGACY_DECLARATION_SYNTHETIC_DECODE_AND_METADATA_CASE_LAWS_PASS",
              "script_pin": file_pin(Path(__file__)),
              "derived_from_retained_probe": file_pin(ROOT / "results_radio_native_v3_hdf5_runtime_candidate_20261003a/source_profile_probe.py"),
              "runtime_closure_before": file_pin(OUT / "runtime-closure-before.json"),
              "runtime_closure_after": file_pin(OUT / "runtime-closure-after.json"),
              "runtime_file_payloads_unchanged": True,
              "runtime_mapping_paths_unchanged": True,
              "runtime_closure_file_count": frozen_runtime["file_count"],
              "runtime_closure_raw_bytes": frozen_runtime["raw_bytes"],
              "complete_execution_runtime_freeze": False,
              "externally_observed_complete_lifetime": False,
              "independent_struct_verified_selected_cells": independent_cells,
              "maximum_sparse_chunk_population": 48, "held_metadata_and_source_pins": material,
              "runtime_version_fields_used_by_source_reader": runtime, "all_four_match_archived_local_baseline": True,
              "source_inventory_sha256": source["source_inventory_sha256"],
              "six_scan_metadata_declarations_checked": 6, "source_shape": list(SHAPE), "source_chunks": list(CHUNKS),
              "source_dtype": "<f4", "decoded_chunk_bytes": CHUNKS[2] * 4,
              "exact_source_filter_pipeline": PROFILE, "current_encoder_filter_pipeline": encoder_profile,
              "local_current_encoder_is_original_archive_encoder": False, "archive_payload_bytes_verified": False,
              "legacy_declaration_preserved_by_raw_local_chunk_transfer": True,
              "fresh_synthetic_files": [file_pin(encoder), file_pin(legacy)], "raw_chunk_receipts": raw_receipts,
              "complete_chunks_decoded": len(decoded), "decoded_cells_bit_exact": sum(row["decoded_cells"] for row in decoded),
              "selected_cells_bit_exact": sum(row["selected_cells"] for row in decoded), "decode_receipts": decoded,
              "row_indices_exercised": list(range(16)), "rows_1_through_14_exercised": True,
              "three_declared_window_positions_exercised": True, "normalization_or_detector_invoked": False,
              "metadata_case_laws": cases, "metadata_case_law_count": len(cases), "metadata_payload_index_attempts": 0,
              "pure_filter_guard_directly_executed": True, "acquisition_or_scientific_modules_loaded": False,
              "telescope_or_holdout_files_opened": 0, "network_requests": 0, "rng_draws": 0,
              "source_analysis_or_reservation_invocations": 0, "primary_runtime_or_frozen_e_material_modified": False,
              "candidate_resource_limits": LIMITS, "observed_seconds": time.monotonic() - START,
              "observed_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
              "scientific_missing_fields_unchanged": list(missing[0]), "scientific_missing_field_count": 11,
              "hdf5_runtime_field_of_executable_source_contract_filled": False,
              "authenticated_source_specific_codec_runtime_case_law_certificate": False,
              "full_source_contract_or_scientific_certificate_ready": False,
              "coverage": {"source_exact_metadata_profile": "measured and source-pinned",
                           "four_version_runtime_equality": "measured; no executable source contract created",
                           "legacy_codec_compatibility_at_declared_positions": "48 full chunks, all 16 rows and three declared windows; synthetic only",
                           "metadata_fail_closed_case_laws": "exact pure source guard executed; 22 acceptance/rejection cases",
                           "normalization_receiver_handoff": "not exercised",
                           "288 role_scan_row_source_payload_identities": "metadata definition only; no source payload acquisition",
                           "public_certificate_authentication_and_full_runtime_lifetime_closure": "pending",
                           "complete_127_24_scientific_certificate": "pending"}}
    write(OUT / "all-rows-probe.json", result)
    print(json.dumps({"status": result["status"], "report": file_pin(OUT / "all-rows-probe.json"),
                      "metadata_case_laws": len(cases), "decoded_cells": result["decoded_cells_bit_exact"],
                      "selected_cells": result["selected_cells_bit_exact"], "scientific_missing_fields": 11}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        path = OUT / "all-rows-probe-error.json"
        if not path.exists():
            write(path, {"schema": "radio-native-v3-candidate-all-rows-profile-failure-v2", "error": repr(error),
                         "traceback": traceback.format_exc(), "seconds": time.monotonic() - START,
                         "authority": "candidate-only", "automatic_retry": False, "scientific_gates_changed": False})
        raise
