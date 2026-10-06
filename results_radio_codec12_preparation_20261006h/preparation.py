"""Stdlib-only source preparation for the complete 12-handoff codec control.

This module inspects and hashes source/metadata only.  It never imports native
packages, opens HDF5, creates a dispatch, or reads telescope spectra.
"""
import ast
import hashlib
import json
import os
import re
import stat
from pathlib import Path

AUTHORITY_COMMIT = "505b2adc210c11701a3762383d2bfb8eb8986ec1"
MIB = 1024 ** 2
LABELS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ROLES = ("calibration", "validation")
LAW_NAMES = (
    "exact_pipeline", "display_name_ignored", "explicit_unfiltered",
    "missing_optional_local_declaration", "missing_required_declaration",
    "pipeline_id_mutation", "pipeline_flags_mutation", "client_datum_0_mutation",
    "client_datum_1_mutation", "client_datum_2_mutation", "client_datum_3_mutation",
    "client_datum_4_mutation", "removed_filter", "extra_filter",
    "invalid_client_datum_type_0", "invalid_client_datum_type_1",
    "invalid_client_datum_type_2", "invalid_client_datum_type_3",
    "boolean_filter_id", "boolean_filter_flags", "nonexplicit_pipeline",
    "malformed_filter_entry",
)
PIPELINE = [[32008, 1, [0, 3, 4, 0, 2]]]

INPUTS = (
    "config/radio_hd189733_source_preparation_20260927.json",
    "results_radio_hd189733_geometry_2026-09-27/window_geometry.json",
    "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json",
    "results_radio_hd189733_receiver_2026-09-28/bank_records.json",
    "results_radio_scientific_execution_prospective_20261003a/preserved-basis.json",
    "results_radio_scientific_execution_prospective_20261003a/receiver_telescope_adapter.py",
    "results_radio_scientific_execution_prospective_20261003a/scientific_admission.py",
    "src/seti_repeater/hdf5_filter_contract_radio.py",
    "src/seti_repeater/source_m43h.py",
    "src/seti_repeater/source_v0p6.py",
    "src/seti_repeater/search_v0p6.py",
    "results_radio_codec16_control_20261006g/leaf/codec16_control.py",
    "results_radio_codec16_control_20261006g/actual/controlled/codec16-receipt.json",
    "results_radio_codec16_control_20261006g/closed/actual-review.json",
)

EXPECTED_RAW = {
    "config/radio_hd189733_source_preparation_20260927.json": (9707, "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"),
    "results_radio_hd189733_geometry_2026-09-27/window_geometry.json": (35420, "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"),
    "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json": (2453, "0ffbadfacb9de8dd92d3d32b07e97b5c6fb16143483c225cb25bd60439ebe226"),
    "results_radio_hd189733_receiver_2026-09-28/bank_records.json": (7871, "51c1fde64957720e98adc7ecc63209d9b2e406b57dcd790829677a1ceb76b7c8"),
    "src/seti_repeater/hdf5_filter_contract_radio.py": (1651, "65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6"),
    "results_radio_codec16_control_20261006g/leaf/codec16_control.py": (19302, "7962ef03add6ca0ec97812a9c713256afe7b82a22fec55addb6485b2c36a8d8a"),
    "results_radio_codec16_control_20261006g/actual/controlled/codec16-receipt.json": (15859, "7cb7a13a469f5c542e0c5ff8a4a99b508549a136c3170f9208b3c61b7b9645c9"),
    "results_radio_codec16_control_20261006g/closed/actual-review.json": (6471, "545c612b7979b8608c2dc7e98822e368075e78468749b39965ee7e7f72f5ee71"),
}

SELECTIONS = {
    "src/seti_repeater/source_m43h.py": {
        "assignments": ["BLOCK", "MAX_CHANNELS"], "functions": ["normalize_native_row"], "classes": [],
    },
    "src/seti_repeater/source_v0p6.py": {
        "assignments": ["M37_NORMALIZATION_BLOCK_CHANNELS", "M37_NORMALIZATION_MAD_MULTIPLIER",
                        "M37_NORMALIZATION_SCALE_FLOOR", "M37_MAXIMUM_SOURCE_RAW_NBYTES", "_F4"],
        "functions": ["_float32_median_rows", "normalize_float32_blocks_v0p6"], "classes": [],
    },
    "src/seti_repeater/search_v0p6.py": {
        "assignments": [], "functions": [], "classes": ["V0P6ContractError", "V0P6CapacityError"],
    },
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: " + key)
        out[key] = value
    return out


def parse(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read(root, relative, maximum=2 * MIB):
    root = Path(root).resolve()
    path = root / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError("ordinary contained input required: " + relative)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError("input byte bound: " + relative)
        raw = handle.read(maximum + 1)
        after = os.fstat(handle.fileno())
        if len(raw) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                                          before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                                                 after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("input changed while reading: " + relative)
    return raw


def _node_key(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def selected_nodes(raw, selection):
    wanted = selection["assignments"] + selection["functions"] + selection["classes"]
    found = {}
    for node in ast.parse(raw.decode()).body:
        key = _node_key(node)
        if key in wanted:
            if key in found:
                raise ValueError("duplicate selected definition: " + key)
            expected = ast.Assign if key in selection["assignments"] else ast.FunctionDef if key in selection["functions"] else ast.ClassDef
            if not isinstance(node, expected):
                raise ValueError("selected source kind differs: " + key)
            found[key] = node
    if set(found) != set(wanted):
        raise ValueError("selected maintained source incomplete")
    return [(name, found[name]) for name in wanted]


def _assignment(raw, name):
    hits = [node for node in ast.parse(raw.decode()).body
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    if len(hits) != 1:
        raise ValueError("unique admission assignment required: " + name)
    return ast.literal_eval(hits[0].value)


def _admission_labels(raw):
    """Inspect the one comprehension without compiling the admission module."""
    hits = [node for node in ast.parse(raw.decode()).body
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LABELS" for t in node.targets)]
    if len(hits) != 1:
        raise ValueError("unique LABELS assignment required")
    expected = ast.parse('LABELS = tuple(f"epoch{i}_{r}" for i in (1, 2, 3) for r in ("on", "off"))').body[0].value
    if ast.dump(hits[0].value, include_attributes=False) != ast.dump(expected, include_attributes=False):
        raise ValueError("admission LABELS construction differs")
    return LABELS


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def build(repo_root):
    root = Path(repo_root).resolve()
    contents, pins, total = {}, {}, 0
    for path in INPUTS:
        raw = read(root, path)
        pin = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob_sha1": _git_blob(raw)}
        if path in EXPECTED_RAW and (pin["bytes"], pin["sha256"]) != EXPECTED_RAW[path]:
            raise ValueError("independent raw pin differs: " + path)
        contents[path], pins[path] = raw, pin
        total += len(raw)
    if total > 4 * MIB:
        raise ValueError("source-only input envelope exceeded")

    source = parse(contents[INPUTS[0]])
    geometry = parse(contents[INPUTS[1]])
    contract = parse(contents[INPUTS[2]])
    banks = parse(contents[INPUTS[3]])
    basis = parse(contents[INPUTS[4]])["basis"]
    admission = contents[INPUTS[6]]
    observed_labels = tuple(_admission_labels(admission))
    observed_laws = tuple(_assignment(admission, "LAW_NAMES"))
    if observed_labels != LABELS or observed_laws != LAW_NAMES:
        raise ValueError("scientific admission order differs")
    if source["stage"] != "preparation-only-no-spectral-access" or source["hdf5_runtime"] is not None or source["windows"]:
        raise ValueError("original source preparation state differs")
    scan_map = {row["label"]: row for row in source["scans"]}
    if tuple(scan_map) != LABELS or len(scan_map) != 6:
        raise ValueError("six ordered source scans required")
    if any(row["expected_header"]["dataset_shape"] != [16, 1, 264503296]
           or row["expected_chunks"] != [1, 1, 1048576]
           or [entry[:3] for entry in row["observed_hdf5_filters"]] != PIPELINE for row in scan_map.values()):
        raise ValueError("source profile differs")
    windows = {row["role"]: row for row in geometry["windows"] if row["role"] in ROLES}
    if set(windows) != set(ROLES):
        raise ValueError("calibration/validation windows required")
    bank_map = {role: next((row for row in banks if row["bank_identity"] == basis["receiver_bank_sha256s"][role]), None)
                for role in ROLES}
    if set(bank_map) != set(ROLES):
        raise ValueError("calibration/validation banks required")
    expected_intervals = {"calibration": ([167215104, 167280640], 159),
                          "validation": ([164069376, 164134912], 156)}
    handoffs = []
    for role in ROLES:
        window = windows[role]
        interval, chunk = expected_intervals[role]
        if (window["archive_interval"], window["archive_chunk_index"]) != (interval, chunk):
            raise ValueError("fixed role window differs")
        if window["identity"] != basis["window_identities"][role] or bank_map[role]["bank_identity"] != basis["receiver_bank_sha256s"][role]:
            raise ValueError("role basis identity differs")
        for label in LABELS:
            handoffs.append({"role": role, "scan": label, "handoff_index": len(handoffs),
                             "archive_interval": interval, "chunk_index": chunk,
                             "window_identity": window["identity"],
                             "receiver_context_sha256": basis["receiver_context_sha256s"][role],
                             "receiver_bank_sha256": basis["receiver_bank_sha256s"][role]})
    if len(handoffs) != 12:
        raise AssertionError

    g_receipt = parse(contents[INPUTS[-2]])
    g_review = parse(contents[INPUTS[-1]])
    if (g_receipt["status"] != "OBSERVED_ENGINEERING_ONLY" or g_receipt["handoffs_observed"] != 1
            or g_receipt["complete_codec_handoffs_required"] != 12
            or g_receipt["complete_codec_certificate_issued"] is not False
            or g_review["status"] != "VERIFIED_CONTROLLED_PARTIAL_HANDOFF"
            or g_review["scientific_certificate_issued"] is not False):
        raise ValueError("closed G basis differs")

    manifest = {"schema": "codec12-source-input-manifest-v1", "status": "SOURCE_ONLY_NO_DISPATCH",
                "authority_commit": AUTHORITY_COMMIT, "files": pins, "total_raw_bytes": total}
    selection = {"schema": "codec12-maintained-ast-selection-v1", "status": "INSPECTED_NOT_COMPILED",
                 "compiled_or_executed": False, "source_selections": {}}
    for path, specification in SELECTIONS.items():
        lines = contents[path].decode().splitlines(keepends=True)
        witnesses = []
        for name, node in selected_nodes(contents[path], specification):
            segment = "".join(lines[node.lineno - 1:node.end_lineno]).encode()
            witnesses.append({"name": name, "node_type": type(node).__name__, "first_line": node.lineno,
                              "last_line": node.end_lineno, "bytes": len(segment),
                              "sha256": hashlib.sha256(segment).hexdigest()})
        selection["source_selections"][path] = {**specification, "raw_file_pin": pins[path], "nodes": witnesses}

    law_rows = [{"index": i, "name": name, "expected": "accept" if i < 4 else "reject"}
                for i, name in enumerate(LAW_NAMES)]
    plan = {
        "schema": "codec12-complete-handoff-source-preparation-v1", "status": "SOURCE_ONLY_NO_DISPATCH",
        "execution_enabled": False, "authority_commit": AUTHORITY_COMMIT,
        "input_manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "selection_manifest_sha256": hashlib.sha256(canonical(selection)).hexdigest(),
        "scope": {"target": "HD189733/HIP98505", "cadence_id": "85030", "primary": "neighbor9",
                  "kind": "controlled-source-shaped-complete-codec-handoffs", "ordered_handoffs": handoffs,
                  "source_shape": [16, 1, 264503296], "source_chunks": [1, 1, 1048576],
                  "source_dtype": "<f4", "legacy_pipeline": PIPELINE, "row_indices": list(range(16)),
                  "selected_channels": 65536, "normalization_blocks": 16,
                  "normalization_block_channels": 4096, "input_orientation": "descending",
                  "telescope_provenance": False},
        "case_laws": law_rows,
        "deterministic_construction": {
            "formula": "float32((409600 + 256*handoff_index + ((i*17+chunk*31+row*13)%4093) + 128*((i//4096)%17))/4096)",
            "handoff_salt_is_exact_binary": True, "prng_or_noise_model": False,
            "payloads_generated_during_preparation": False,
            "purpose": "disjoint deterministic controlled rows; no telescope interpretation"},
        "runtime_basis": {"versions_observed_in_closed_G": g_receipt["runtime"],
                          "fresh_runtime_inventory_before_after_required": True,
                          "closed_G_is_design_evidence_not_reused_output": True},
        "draft_envelope": {"not_reserved_or_measured": True, "one_future_leaf": True,
                           "suggested_leaf_wall_seconds": 600, "suggested_leaf_cpu_seconds": 540,
                           "suggested_address_space_bytes": 1024 * MIB, "suggested_rss_ceiling_bytes": 768 * MIB,
                           "compressed_payload_cap_bytes": 5 * MIB, "each_hdf5_file_cap_bytes": 16 * MIB,
                           "hdf5_file_count": 24, "leaf_output_cap_bytes": 400 * MIB,
                           "outer_terminal_reserve_bytes": 48 * MIB, "artifact_cap_bytes": 448 * MIB,
                           "parent_explicit_read_reservation_bytes": 4 * 1024 * MIB,
                           "leaf_opaque_read_reservation_bytes": 1024 * MIB,
                           "full_dataspace_logical_bytes_each": 16928210944,
                           "fully_materializing_any_dataspace_forbidden": True,
                           "sequential_handoffs_rows_and_chunks": True},
        "future_output": {"required_handoff_count": 12, "required_row_hashes_per_handoff": 16,
                          "required_case_law_count": 22, "raw_row_convention": "native archive-descending selected float32 rows",
                          "complete_codec_certificate_issued_by_this_stage": False,
                          "scientific_allocation_charged": False, "scientific_readiness": False},
        "gates": {"future_outer_freeze_required": True, "future_native_runtime_attestation_required": True,
                  "future_independent_result_review_required": True, "future_certificate_publication_required": True,
                  "archive_spectra_permitted": False, "holdouts_permitted": False},
        "counters": {"native_imports": 0, "hdf5_operations": 0, "control_dispatches": 0,
                     "rng_draws": 0, "archive_spectral_values_read": 0, "scientific_cases_run": 0,
                     "activation_or_allocation_created": 0},
    }
    review = {"schema": "codec12-source-only-review-v1", "status": "PASS_SOURCE_ONLY",
              "authority_commit": AUTHORITY_COMMIT, "handoff_count": len(handoffs),
              "handoff_order_sha256": hashlib.sha256(canonical(handoffs)).hexdigest(),
              "law_count": len(law_rows), "law_order_sha256": hashlib.sha256(canonical(law_rows)).hexdigest(),
              "all_native_counters_zero": True, "spectra_opened": False, "holdouts_opened": False,
              "execution_authorized": False, "next": "freeze and independently review a distinct future control; do not dispatch from this preparation"}
    return manifest, selection, plan, review


def main():
    here = Path(__file__).resolve().parent
    values = build(here.parent)
    for name, value in zip(("INPUT_MANIFEST.json", "SELECTED_CODE.json", "PLAN.json", "SOURCE_ONLY_REVIEW.json"), values):
        with (here / name).open("xb") as handle:
            handle.write(canonical(value))
    print("SOURCE_ONLY_NO_DISPATCH: 12 handoffs and 22 laws frozen; zero native actions")


if __name__ == "__main__":
    main()
