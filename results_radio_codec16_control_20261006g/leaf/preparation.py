"""Stdlib-only inert planning. Never compiles selected code or imports packages."""
import ast
import hashlib
import json
import os
import stat
from pathlib import Path

COMMIT = "6da771e78667f0746e87d05915c6feb683541a25"
MIB = 1024 ** 2
EXPECTED_METADATA = {
    "config/radio_hd189733_source_preparation_20260927.json": (9707, "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"),
    "results_radio_hd189733_geometry_2026-09-27/window_geometry.json": (35420, "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"),
    "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json": (2453, "0ffbadfacb9de8dd92d3d32b07e97b5c6fb16143483c225cb25bd60439ebe226"),
    "results_radio_hd189733_receiver_2026-09-28/bank_records.json": (7871, "51c1fde64957720e98adc7ecc63209d9b2e406b57dcd790829677a1ceb76b7c8"),
}
SELECTIONS = {
    "src/seti_repeater/source_m43h.py": {
        "assignments": ["BLOCK", "MAX_CHANNELS"],
        "functions": ["normalize_native_row"], "classes": [],
    },
    "src/seti_repeater/source_v0p6.py": {
        "assignments": ["M37_NORMALIZATION_BLOCK_CHANNELS", "M37_NORMALIZATION_MAD_MULTIPLIER", "M37_NORMALIZATION_SCALE_FLOOR", "M37_MAXIMUM_SOURCE_RAW_NBYTES", "_F4"],
        "functions": ["_float32_median_rows", "normalize_float32_blocks_v0p6"], "classes": [],
    },
    "src/seti_repeater/search_v0p6.py": {
        "assignments": [], "functions": [],
        "classes": ["V0P6ContractError", "V0P6CapacityError"],
    },
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read(root, relative, maximum=512 * 1024):
    path = root / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("ordinary pinned input required: " + relative)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        st = os.fstat(handle.fileno())
        if not stat.S_ISREG(st.st_mode) or not 0 < st.st_size <= maximum:
            raise ValueError("input byte bound: " + relative)
        raw = handle.read(maximum + 1)
        if len(raw) != st.st_size:
            raise ValueError("input length changed: " + relative)
    return raw


def node_key(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def selected_nodes(raw, selection):
    """AST inspection only; no selected source is compiled or executed here."""
    text = raw.decode("utf-8")
    wanted = selection["assignments"] + selection["functions"] + selection["classes"]
    found = {}
    for node in ast.parse(text).body:
        key = node_key(node)
        if key in wanted:
            if key in found:
                raise ValueError("duplicate selected source definition")
            wanted_type = ast.Assign if key in selection["assignments"] else ast.FunctionDef if key in selection["functions"] else ast.ClassDef
            if not isinstance(node, wanted_type):
                raise ValueError("selected source kind differs")
            found[key] = node
    if set(found) != set(wanted):
        raise ValueError("selected maintained source incomplete")
    return [(key, found[key]) for key in wanted]


def build(root):
    root = Path(root).resolve()
    retrieval = parse(read(root, "GITHUB_RETRIEVAL.json"))
    if retrieval["commit"] != COMMIT or retrieval["repository"] != "andersenmartin-blip/setisearch":
        raise ValueError("immutable authority differs")
    manifest = {"schema": "codec16-authoritative-input-manifest-v1", "status": "NO_DISPATCHED",
                "commit": COMMIT, "files": {}, "total_raw_bytes": 0}
    contents = {}
    for row in retrieval["files"]:
        path = row["original_path"]
        if path in contents or row["local_path"] != "authoritative/" + path:
            raise ValueError("duplicate or relocated authority input")
        raw = read(root, row["local_path"])
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if git_blob != row["git_blob_sha1"]:
            raise ValueError("retrieved Git blob bytes differ: " + path)
        pin = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob_sha1": git_blob,
               "local_path": row["local_path"]}
        if path in EXPECTED_METADATA and (pin["bytes"], pin["sha256"]) != EXPECTED_METADATA[path]:
            raise ValueError("independent metadata raw pin differs")
        manifest["files"][path] = pin
        manifest["total_raw_bytes"] += len(raw)
        if manifest["total_raw_bytes"] > 2 * MIB:
            raise ValueError("pure input read envelope exceeded")
        contents[path] = raw
    source = parse(contents[next(iter(EXPECTED_METADATA))])
    geometry = parse(contents[list(EXPECTED_METADATA)[1]])
    bound = parse(contents[list(EXPECTED_METADATA)[2]])
    banks = parse(contents[list(EXPECTED_METADATA)[3]])
    basis_raw = contents["results_radio_scientific_execution_prospective_20261003a/preserved-basis.json"]
    basis = parse(basis_raw)["basis"]
    scan = next(row for row in source["scans"] if row["label"] == "epoch1_on")
    window = next(row for row in geometry["windows"] if row["role"] == "calibration")
    if (source["stage"] != "preparation-only-no-spectral-access" or source["hdf5_runtime"] is not None or source["windows"]
            or scan["role"] != "on" or scan["expected_header"]["dataset_shape"] != [16, 1, 264503296]
            or scan["expected_chunks"] != [1, 1, 1048576]
            or window["archive_interval"] != [167215104, 167280640] or window["archive_chunk_index"] != 159
            or window["identity"] != basis["window_identities"]["calibration"]
            or source["source_inventory_sha256"] != basis["source_inventory_sha256"]
            or bound["source_inventory_sha256"] != basis["source_inventory_sha256"]
            or banks[0]["bank_identity"] != basis["receiver_bank_sha256s"]["calibration"]):
        raise ValueError("original calibration source geometry/basis differs")
    selected = {"schema": "codec16-maintained-ast-selection-v1", "status": "INSPECTED_NOT_COMPILED",
                "source_selections": {}, "compiled_or_executed": False}
    for path, selection in SELECTIONS.items():
        raw = contents[path]
        text_lines = raw.decode().splitlines(keepends=True)
        witnesses = []
        for name, node in selected_nodes(raw, selection):
            segment = "".join(text_lines[node.lineno - 1:node.end_lineno]).encode()
            witnesses.append({"name": name, "node_type": type(node).__name__, "first_line": node.lineno,
                              "last_line": node.end_lineno, "bytes": len(segment),
                              "sha256": hashlib.sha256(segment).hexdigest()})
        selected["source_selections"][path] = {**selection, "raw_file_pin": manifest["files"][path], "nodes": witnesses}
    plan = {
        "schema": "codec16-engineering-preparation-plan-v1", "status": "NO_DISPATCHED",
        "execution_enabled": False, "authority_commit": COMMIT,
        "input_manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "selection_manifest_sha256": hashlib.sha256(canonical(selected)).hexdigest(),
        "scope": {"kind": "controlled-source-shaped-codec-normalization", "role": "calibration", "scan": "epoch1_on",
                  "row_indices": list(range(16)), "archive_interval": window["archive_interval"], "chunk_index": 159,
                  "source_shape": [16, 1, 264503296], "source_chunks": [1, 1, 1048576], "source_dtype": "<f4",
                  "legacy_pipeline": [[32008, 1, [0, 3, 4, 0, 2]]], "selected_channels": 65536,
                  "input_orientation": "descending", "normalization_origin": "ascending channel zero of NEW extraction",
                  "normalization_blocks": 16, "normalization_block_channels": 4096,
                  "window_identity": window["identity"], "receiver_context_sha256": basis["receiver_context_sha256s"]["calibration"],
                  "receiver_bank_sha256": basis["receiver_bank_sha256s"]["calibration"],
                  "source_inventory_sha256": basis["source_inventory_sha256"],
                  "geometry": {"raw_zero_hz": window["native_frequency_low_hz"],
                               "raw_bin_width_hz": abs(scan["expected_header"]["foff_mhz"]) * 1e6,
                               "channel_count": 65536}, "telescope_provenance": False},
        "deterministic_construction": {
            "original_algorithm": "source_profile_probe.pattern(chunk,row):69-73",
            "formula": "float32(100)+float32(((i*17+chunk*31+row*13)%4093)/4096)+float32(((i//4096)%17)/32)",
            "independent_integer_numerator": "409600 + ((i*17+chunk*31+row*13)%4093) + 128*((i//4096)%17)",
            "division_denominator": 4096, "chunk_local_indices": [0, 1048576],
            "prng_or_noise_model": False, "expected_control_payloads_generated": False},
        "runtime_basis": {"existing_E_metadata_sha256": "53f52557608cb3014ffe2d025c0f3019d80cf8419af0eefd578513fa7fce09aa",
                          "versions": {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5": "2.0.0", "hdf5plugin": "7.1.0"},
                          "fresh_runtime_inventory_before_after_required_for_future_control": True,
                          "current_E_observation_is_scientific_qualification": False},
        "draft_envelope": {
            "not_reserved_or_measured": True, "one_future_leaf": True,
            "suggested_leaf_wall_seconds": 90, "suggested_leaf_cpu_seconds": 80,
            "suggested_address_space_bytes": 512 * MIB, "suggested_rss_ceiling_bytes": 512 * MIB,
            "projected_incremental_array_codec_cache_memory_bytes": 96 * MIB,
            "compressed_payload_cap_bytes": 5 * MIB, "each_hdf5_file_cap_bytes": 84 * MIB,
            "artifact_cap_bytes": 192 * MIB, "leaf_output_cap_bytes": 184 * MIB,
            "outer_terminal_reserve_bytes": 8 * MIB, "leaf_opaque_read_reservation_bytes": 512 * MIB,
            "parent_read_reservation_must_be_frozen_separately": True,
            "full_dataspace_logical_bytes": 16928210944, "fully_materializing_dataspace_forbidden": True,
            "sequential_rows_and_chunks": True, "row_arrays_retained_as_files": False},
        "future_output": {"engineering_partial_handoff_count": 1, "required_full_codec_handoff_count": 12,
                          "row_receipt_fields": ["row", "compressed_sha256", "compressed_bytes", "full_decoded_sha256",
                                                 "native_descending_sha256", "ascending_raw_sha256", "normalized_sha256"],
                          "complete_codec_certificate_issued": False, "scientific_allocation_charged": False,
                          "scientific_readiness": False},
        "counters": {"scientific_package_native_imports": 0, "hdf5_operations": 0, "control_dispatches": 0, "rng_draws": 0,
                     "archive_spectral_values_read": 0, "scientific_cases_run": 0, "activation_or_freeze_created": 0},
    }
    return manifest, selected, plan


def main():
    root = Path(__file__).resolve().parent
    for name, value in zip(("INPUT_MANIFEST.json", "SELECTED_CODE.json", "PLAN.json"), build(root)):
        path = root / name
        with path.open("xb") as handle:
            handle.write(canonical(value))
    print("NO_DISPATCHED: immutable inputs and AST selections only")


if __name__ == "__main__":
    main()
