"""Fail-closed, source-specific *candidate engineering* evidence verifier.

No network client, telescope reader, executable source contract, reservation,
or scientific admission API exists in this module. JSON hashes authenticate
bytes only relative to the independent pins supplied in TrustedPins. They are
not public authentication, and observed snapshots are not lifetime closure.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct

SCHEMA = "radio-source-specific-candidate-codec-evidence-v1"
LAW = "hd189733-legacy32008-metadata-laws-and-all16-fixed3-v1"
INVENTORY = "3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f"
RUNTIME = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5": "2.0.0", "hdf5plugin": "7.1.0"}
SOURCE_FILTER = [[32008, 1, [0, 3, 4, 0, 2]]]
ENCODER_FILTER = [[32008, 1, [0, 4, 4, 0, 2]]]
BUNDLED_OPAQUE_DATA = {
    "lib/python3.12/site-packages/h5py/tests/data_files/compound-dtype-complex.h5",
    "lib/python3.12/site-packages/h5py/tests/data_files/vlen_string_dset.h5",
    "lib/python3.12/site-packages/h5py/tests/data_files/vlen_string_dset_utc.h5",
    "lib/python3.12/site-packages/h5py/tests/data_files/vlen_string_s390x.h5",
    "lib/python3.12/site-packages/numpy/_core/tests/data/recarray_from_file.fits",
}
SOURCE_PINS = {
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
MISSING = ["complete_execution_code_input_runtime_freeze", "hdf5_runtime",
           "source_specific_codec_runtime_case_law_certificate", "complete_127_24_scientific_certificate",
           "joined_hosted_transport_certificate", "source_specific_executable_trial_protocol",
           "cumulative_limits", "reservation_store", "public_acquisition_ledger_revision_and_sha256",
           "fresh_irrevocable_acquisition_and_trial_allocation", "new_executable_source_contract_sha256"]
POSITIVE = ["exact_pipeline", "display_name_ignored", "explicit_unfiltered", "missing_optional_local_declaration"]
NEGATIVE = ["missing_required_declaration", "pipeline_id_mutation", "pipeline_flags_mutation"] + [
    "client_datum_%d_mutation" % i for i in range(5)] + ["removed_filter", "extra_filter"] + [
    "invalid_client_datum_type_%d" % i for i in range(4)] + [
    "boolean_filter_id", "boolean_filter_flags", "nonexplicit_pipeline", "malformed_filter_entry"]
CASES = [{"name": name, "expected": "accept" if name in POSITIVE else "reject", "pass": True}
         for name in POSITIVE + NEGATIVE]
COVERAGE = {
    "288 role_scan_row_source_payload_identities": "metadata definition only; no source payload acquisition",
    "complete_127_24_scientific_certificate": "pending",
    "four_version_runtime_equality": "measured; no executable source contract created",
    "legacy_codec_compatibility_at_declared_positions": "48 full chunks, all 16 rows and three declared windows; synthetic only",
    "metadata_fail_closed_case_laws": "exact pure source guard executed; 22 acceptance/rejection cases",
    "normalization_receiver_handoff": "not exercised",
    "public_certificate_authentication_and_full_runtime_lifetime_closure": "pending",
    "source_exact_metadata_profile": "measured and source-pinned",
}
PROBE_KEYS = set("acquisition_or_scientific_modules_loaded all_four_match_archived_local_baseline archive_payload_bytes_verified authenticated_source_specific_codec_runtime_case_law_certificate authority candidate_resource_limits complete_chunks_decoded complete_execution_runtime_freeze coverage current_encoder_filter_pipeline decode_receipts decoded_cells_bit_exact decoded_chunk_bytes derived_from_retained_probe exact_source_filter_pipeline externally_observed_complete_lifetime fresh_synthetic_files full_source_contract_or_scientific_certificate_ready hdf5_runtime_field_of_executable_source_contract_filled held_metadata_and_source_pins independent_struct_verified_selected_cells legacy_declaration_preserved_by_raw_local_chunk_transfer local_current_encoder_is_original_archive_encoder maximum_sparse_chunk_population metadata_case_law_count metadata_case_laws metadata_payload_index_attempts network_requests normalization_or_detector_invoked observed_peak_rss_bytes observed_seconds primary_runtime_or_frozen_e_material_modified pure_filter_guard_directly_executed raw_chunk_receipts rng_draws row_indices_exercised rows_1_through_14_exercised runtime_closure_after runtime_closure_before runtime_closure_file_count runtime_closure_raw_bytes runtime_file_payloads_unchanged runtime_mapping_paths_unchanged runtime_version_fields_used_by_source_reader schema scientific_missing_field_count scientific_missing_fields_unchanged script_pin selected_cells_bit_exact six_scan_metadata_declarations_checked source_analysis_or_reservation_invocations source_chunks source_dtype source_inventory_sha256 source_shape status telescope_or_holdout_files_opened three_declared_window_positions_exercised".split())
CLOSURE_KEYS = set("base_prefix complete_execution_runtime_freeze dont_write_bytecode externally_observed_complete_lifetime file_count files interpreter isolated links loaded_module_paths mapped_runtime_paths prefix raw_bytes schema sys_path".split())
ENVELOPE_KEYS = set("schema case_law_version authority source_inventory_sha256 ordered_source_scans ordered_window_metadata runtime exact_source_filter_pipeline current_encoder_filter_pipeline probe runtime_closure_before runtime_closure_after code_input_pins verifier_code_pin runtime_closure_payload_sha256 telescope_admission_authorized scientific_admission_authorized public_authentication_established complete_runtime_lifetime_established".split())


class EvidenceError(ValueError):
    """An evidence field, external pin, or observed byte inventory is invalid."""


@dataclass(frozen=True)
class TrustedPins:
    """Must be supplied independently of the untrusted evidence document.

    Paths designate local retained metadata, a candidate probe directory and
    its isolated runtime. A repinned document is a new review, not continuity.
    """
    evidence_sha256: str
    probe_sha256: str
    closure_before_sha256: str
    closure_after_sha256: str
    verifier_sha256: str
    source_root: str
    probe_root: str
    candidate_runtime_root: str
    base_runtime_root: str


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _fail(message):
    raise EvidenceError(message)


def _exact(actual, expected, label):
    """Recursive type-sensitive equality; bool never stands in for int."""
    if type(actual) is not type(expected):
        _fail(label + ": exact type differs")
    if isinstance(expected, dict):
        _keys(actual, set(expected), label)
        for key in expected:
            _exact(actual[key], expected[key], label + "." + key)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            _fail(label + ": ordered length differs")
        for index, value in enumerate(expected):
            _exact(actual[index], value, "%s[%d]" % (label, index))
    elif actual != expected:
        _fail(label + ": value differs")


def _keys(value, expected, label):
    if type(value) is not dict or set(value) != expected:
        _fail(label + ": missing or unknown fields")


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        _fail(label + ": exact integer required")
    return value


def _hash(value, label):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail(label + ": lowercase SHA256 required")


def _string(value, label):
    if type(value) is not str or not value or "\x00" in value:
        _fail(label + ": nonempty string required")


def _finite_tree(value):
    if type(value) is float and not math.isfinite(value):
        _fail("nonfinite JSON number")
    if isinstance(value, dict):
        for item in value.values():
            _finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            _finite_tree(item)


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("duplicate JSON field: " + key)
            result[key] = value
        return result
    def invalid(value):
        _fail("nonfinite JSON token: " + value)
    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError("invalid JSON encoding") from error
    _finite_tree(result)
    return result


def _pin(pin, label):
    _keys(pin, {"path", "bytes", "sha256", "allocated_bytes"}, label)
    _string(pin["path"], label + ".path")
    if not Path(pin["path"]).is_absolute() or ".." in Path(pin["path"]).parts:
        _fail(label + ": absolute normalized local path required")
    _hash(pin["sha256"], label)
    _integer(pin["bytes"], label)
    _integer(pin["allocated_bytes"], label)


def _under(path, roots):
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(root).resolve()) for root in roots)


def _read_pin(pin, roots, *, allow_opaque_payload=False):
    _pin(pin, "file pin")
    if not _under(pin["path"], roots):
        _fail("file outside independently trusted local roots")
    if Path(pin["path"]).suffix.lower() in {".h5", ".hdf5", ".fil", ".fits"} and not allow_opaque_payload:
        _fail("telescope-shaped payload is not readable by this evidence API")
    digest = hashlib.sha256()
    data = bytearray()
    with open(pin["path"], "rb") as handle:
        before = os.fstat(handle.fileno())
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
            data.extend(part)
        after = os.fstat(handle.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        _fail("file changed while hashing")
    if len(data) != pin["bytes"] or digest.hexdigest() != pin["sha256"]:
        _fail("live file byte hash or size differs")
    return bytes(data)


def _closure(value, trusted, script_path):
    _keys(value, CLOSURE_KEYS, "runtime closure")
    _exact(value["schema"], "radio-candidate-observed-runtime-file-closure-v1", "closure schema")
    for key in ("complete_execution_runtime_freeze", "externally_observed_complete_lifetime"):
        _exact(value[key], False, key)
    for key in ("dont_write_bytecode", "isolated"):
        _exact(value[key], True, key)
    _exact(value["prefix"], str(Path(trusted.candidate_runtime_root)), "runtime prefix")
    _exact(value["base_prefix"], str(Path(trusted.base_runtime_root)), "runtime base prefix")
    _exact(value["interpreter"], str(Path(trusted.candidate_runtime_root) / "bin/python"), "interpreter")
    for key in ("files", "links", "mapped_runtime_paths", "sys_path"):
        if type(value[key]) is not list:
            _fail(key + ": explicit list required")
    paths = []
    for pin in value["files"]:
        _pin(pin, "closure file")
        paths.append(pin["path"])
    if len(paths) != len(set(paths)):
        _fail("runtime file inventory must be unique; order is externally hash-pinned")
    _exact(value["file_count"], len(paths), "runtime file count")
    _exact(value["raw_bytes"], sum(pin["bytes"] for pin in value["files"]), "runtime raw bytes")
    if len(paths) < 100 or value["interpreter"] not in paths or script_path not in paths:
        _fail("candidate runtime closure is incomplete")
    if not any("hdf5plugin/plugins/libh5bshuf.so" in path for path in paths):
        _fail("actual bitshuffle decoder binary is absent")
    if not any("h5py.libs/libhdf5-" in path for path in paths):
        _fail("actual HDF5 binary is absent")
    for key in ("mapped_runtime_paths", "sys_path"):
        for path in value[key]:
            _string(path, key)
    if value["mapped_runtime_paths"] != sorted(set(value["mapped_runtime_paths"])):
        _fail("mapped runtime inventory must be unique and ordered")
    if not set(value["mapped_runtime_paths"]).issubset(paths):
        _fail("mapped binary lacks a pinned file payload")
    if type(value["loaded_module_paths"]) is not dict:
        _fail("loaded modules must be an explicit map")
    for name, path in value["loaded_module_paths"].items():
        _string(name, "module name")
        _string(path, "module path")
        if path not in paths:
            _fail("loaded module lacks a pinned file payload")
    link_paths = []
    for link in value["links"]:
        _keys(link, {"path", "link_text", "resolved_target", "target_is_directory"}, "runtime link")
        for key in ("path", "link_text", "resolved_target"):
            _string(link[key], "runtime link " + key)
        _exact(link["target_is_directory"], True, "link directory")
        if not _under(link["path"], [trusted.candidate_runtime_root]) or not _under(link["resolved_target"], [trusted.candidate_runtime_root]):
            _fail("runtime alias escapes isolated candidate")
        link_paths.append(link["path"])
    if link_paths != sorted(set(link_paths)):
        _fail("runtime links must be unique and ordered")


def _selected_pattern_hash(row, chunk_index, interval):
    start = interval[0] - chunk_index * 1048576
    end = interval[1] - chunk_index * 1048576
    # All terms are exact binary fractions. Python and float32 represent this
    # range exactly, providing an independent oracle without loading NumPy.
    raw = bytearray((end - start) * 4)
    for offset, index in enumerate(range(start, end)):
        numerator = 409600 + (index * 17 + chunk_index * 31 + row * 13) % 4093 + 128 * ((index // 4096) % 17)
        struct.pack_into("<f", raw, offset * 4, numerator / 4096)
    return sha256(raw)


def _probe(probe, source, geometry, trusted):
    _keys(probe, PROBE_KEYS, "probe report")
    _exact(probe["schema"], "radio-native-v3-candidate-all-rows-source-profile-v2", "probe schema")
    _exact(probe["authority"], "candidate-only synthetic preparation", "probe authority")
    _exact(probe["status"], "EXACT_LEGACY_DECLARATION_SYNTHETIC_DECODE_AND_METADATA_CASE_LAWS_PASS", "probe status")
    for key in ("acquisition_or_scientific_modules_loaded", "archive_payload_bytes_verified", "authenticated_source_specific_codec_runtime_case_law_certificate", "complete_execution_runtime_freeze", "externally_observed_complete_lifetime", "full_source_contract_or_scientific_certificate_ready", "hdf5_runtime_field_of_executable_source_contract_filled", "local_current_encoder_is_original_archive_encoder", "normalization_or_detector_invoked", "primary_runtime_or_frozen_e_material_modified"):
        _exact(probe[key], False, key)
    for key in ("all_four_match_archived_local_baseline", "legacy_declaration_preserved_by_raw_local_chunk_transfer", "pure_filter_guard_directly_executed", "rows_1_through_14_exercised", "runtime_file_payloads_unchanged", "runtime_mapping_paths_unchanged", "three_declared_window_positions_exercised"):
        _exact(probe[key], True, key)
    for key in ("metadata_payload_index_attempts", "network_requests", "rng_draws", "source_analysis_or_reservation_invocations", "telescope_or_holdout_files_opened"):
        _exact(probe[key], 0, key)
    counts = {"complete_chunks_decoded": 48, "maximum_sparse_chunk_population": 48, "decoded_cells_bit_exact": 48 * 1048576, "selected_cells_bit_exact": 48 * 65536, "independent_struct_verified_selected_cells": 48 * 65536, "decoded_chunk_bytes": 4194304, "metadata_case_law_count": 22, "scientific_missing_field_count": 11, "six_scan_metadata_declarations_checked": 6}
    for key, expected in counts.items():
        _exact(probe[key], expected, key)
    for key, expected in {"runtime_version_fields_used_by_source_reader": RUNTIME, "exact_source_filter_pipeline": SOURCE_FILTER, "current_encoder_filter_pipeline": ENCODER_FILTER, "source_inventory_sha256": INVENTORY, "source_shape": [16, 1, 264503296], "source_chunks": [1, 1, 1048576], "source_dtype": "<f4", "row_indices_exercised": list(range(16)), "scientific_missing_fields_unchanged": MISSING, "metadata_case_laws": CASES}.items():
        _exact(probe[key], expected, key)
    _exact(probe["candidate_resource_limits"], {"generated_file_bytes": 100663296, "peak_rss_bytes": 268435456, "seconds": 60}, "candidate ceilings")
    _integer(probe["observed_peak_rss_bytes"], "observed RSS", 1)
    seconds = probe["observed_seconds"]
    if type(seconds) is not float or not 0 < seconds <= 60 or probe["observed_peak_rss_bytes"] > 268435456:
        _fail("observed internal candidate budget exceeded or wrong type")
    _exact(probe["coverage"], COVERAGE, "bounded candidate coverage statements")
    for kind, keys in (("decode_receipts", {"archive_interval", "bit_exact", "chunk_index", "decoded_cells", "decoded_sha256", "role", "row", "selected_cells", "selected_sha256"}), ("raw_chunk_receipts", {"compressed_bytes", "compressed_sha256", "filter_mask", "offset", "role", "row"})):
        receipts = probe[kind]
        if type(receipts) is not list or len(receipts) != 48:
            _fail("all sixteen rows by three windows required")
        for index, receipt in enumerate(receipts):
            _keys(receipt, keys, kind)
            row = index // 3
            window = geometry["windows"][index % 3]
            _exact(receipt["row"], row, "receipt row")
            _exact(receipt["role"], window["role"], "receipt role")
            if kind == "decode_receipts":
                _exact(receipt["archive_interval"], window["archive_interval"], "window mapping")
                _exact(receipt["chunk_index"], window["archive_chunk_index"], "chunk mapping")
                _exact(receipt["bit_exact"], True, "decoded byte equality")
                _exact(receipt["decoded_cells"], 1048576, "full chunk coverage")
                _exact(receipt["selected_cells"], 65536, "selected window coverage")
                _hash(receipt["decoded_sha256"], "decoded hash")
                _hash(receipt["selected_sha256"], "selected hash")
                _exact(receipt["selected_sha256"], _selected_pattern_hash(row, receipt["chunk_index"], receipt["archive_interval"]), "independent selected byte oracle")
            else:
                _exact(receipt["offset"], [row, 0, window["archive_chunk_index"] * 1048576], "raw chunk offset")
                _exact(receipt["filter_mask"], 0, "raw chunk codec enabled")
                _integer(receipt["compressed_bytes"], "compressed bytes", 1)
                _hash(receipt["compressed_sha256"], "compressed hash")
    for key in ("script_pin", "derived_from_retained_probe", "runtime_closure_before", "runtime_closure_after"):
        _pin(probe[key], key)
    _keys(probe["held_metadata_and_source_pins"], set(SOURCE_PINS), "held source pins")
    for relative, digest in SOURCE_PINS.items():
        pin = probe["held_metadata_and_source_pins"][relative]
        _pin(pin, relative)
        _exact(pin["path"], str(Path(trusted.source_root) / relative), "held source path")
        _exact(pin["sha256"], digest, "held source digest")
    files = probe["fresh_synthetic_files"]
    if type(files) is not list or len(files) != 2:
        _fail("two fresh synthetic codec files required")
    expected_names = ["candidate-current-encoder.h5", "candidate-legacy-declaration.h5"]
    for pin, name in zip(files, expected_names):
        _pin(pin, "synthetic file")
        _exact(pin["path"], str(Path(trusted.probe_root) / "generated" / name), "synthetic file scope")
    if sum(pin["bytes"] for pin in files) > 100663296:
        _fail("synthetic file budget exceeded")


def verify_candidate_evidence(evidence_bytes, trusted):
    """Return candidate codec evidence only after semantics and live byte pins.

    Caller must obtain TrustedPins outside the submitted evidence. A successful
    result is deliberately incapable of filling any scientific admission field.
    All HDF5 products remain opaque byte files; no dataset or archive is opened.
    """
    if type(trusted) is not TrustedPins or type(evidence_bytes) is not bytes:
        _fail("independent TrustedPins and exact bytes required")
    for digest in (trusted.evidence_sha256, trusted.probe_sha256, trusted.closure_before_sha256, trusted.closure_after_sha256, trusted.verifier_sha256):
        _hash(digest, "trusted digest")
    _exact(sha256(evidence_bytes), trusted.evidence_sha256, "independent evidence pin")
    evidence = strict_json(evidence_bytes)
    _keys(evidence, ENVELOPE_KEYS, "candidate evidence")
    _pin(evidence["verifier_code_pin"], "verifier code pin")
    _exact(evidence["verifier_code_pin"]["sha256"], trusted.verifier_sha256, "independent verifier code pin")
    _exact(Path(evidence["verifier_code_pin"]["path"]).resolve(), Path(__file__).resolve(), "executed verifier module path")
    _read_pin(evidence["verifier_code_pin"], [str(Path(__file__).resolve().parent)])
    for key, expected in {"schema": SCHEMA, "case_law_version": LAW, "authority": "candidate-engineering-only", "source_inventory_sha256": INVENTORY, "runtime": RUNTIME, "exact_source_filter_pipeline": SOURCE_FILTER, "current_encoder_filter_pipeline": ENCODER_FILTER}.items():
        _exact(evidence[key], expected, key)
    for key in ("telescope_admission_authorized", "scientific_admission_authorized", "public_authentication_established", "complete_runtime_lifetime_established"):
        _exact(evidence[key], False, key)
    _keys(evidence["code_input_pins"], set(SOURCE_PINS), "code/input closure")
    source_data = {}
    for relative, digest in SOURCE_PINS.items():
        pin = evidence["code_input_pins"][relative]
        _pin(pin, relative)
        _exact(pin["path"], str(Path(trusted.source_root) / relative), "source metadata path")
        _exact(pin["sha256"], digest, "independent source byte pin")
        source_data[relative] = _read_pin(pin, [trusted.source_root])
    source = strict_json(source_data["config/radio_hd189733_source_preparation_20260927.json"])
    geometry = strict_json(source_data["results_radio_hd189733_geometry_2026-09-27/window_geometry.json"])
    retained = strict_json(source_data["results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json"])
    _exact(source["stage"], "preparation-only-no-spectral-access", "inactive source stage")
    _exact(source["hdf5_runtime"], None, "inactive source runtime")
    _exact(source["windows"], [], "inactive executable source windows")
    _exact(evidence["ordered_source_scans"], source["scans"], "ordered exact six source scans")
    _exact(evidence["ordered_window_metadata"], geometry["windows"], "ordered exact source/window metadata")
    _exact(source["source_inventory_sha256"], INVENTORY, "source inventory")
    _exact(sha256(canonical(source["scans"])), INVENTORY, "inventory digest algorithm")
    _exact(retained["filter_pipeline"], SOURCE_FILTER, "source filter declaration")
    _exact([scan["role"] for scan in source["scans"]], ["on", "off"] * 3, "scan order")
    _exact([window["role"] for window in geometry["windows"]], ["calibration", "validation", "pilot"], "window order")
    for key, digest in (("probe", trusted.probe_sha256), ("runtime_closure_before", trusted.closure_before_sha256), ("runtime_closure_after", trusted.closure_after_sha256)):
        _pin(evidence[key], key)
        _exact(evidence[key]["sha256"], digest, "independent " + key + " digest")
    probe = strict_json(_read_pin(evidence["probe"], [trusted.probe_root]))
    _probe(probe, source, geometry, trusted)
    _exact(probe["held_metadata_and_source_pins"], evidence["code_input_pins"], "probe code/input binding")
    _exact(probe["runtime_closure_before"], evidence["runtime_closure_before"], "before snapshot binding")
    _exact(probe["runtime_closure_after"], evidence["runtime_closure_after"], "after snapshot binding")
    _read_pin(probe["script_pin"], [trusted.probe_root])
    _read_pin(probe["derived_from_retained_probe"], [trusted.source_root])
    closures = [strict_json(_read_pin(evidence[key], [trusted.probe_root])) for key in ("runtime_closure_before", "runtime_closure_after")]
    for closure in closures:
        _closure(closure, trusted, probe["script_pin"]["path"])
    before, after = closures
    for key in CLOSURE_KEYS - {"loaded_module_paths"}:
        _exact(after[key], before[key], "unchanged snapshot " + key)
    _exact(probe["runtime_closure_file_count"], before["file_count"], "probe closure count")
    _exact(probe["runtime_closure_raw_bytes"], before["raw_bytes"], "probe closure bytes")
    _exact(evidence["runtime_closure_payload_sha256"], sha256(canonical(before["files"])), "binary/code/runtime closure payload digest")
    allowed_runtime_roots = [trusted.candidate_runtime_root, trusted.base_runtime_root, "/usr/lib", trusted.probe_root]
    bundled_paths = {str(Path(trusted.candidate_runtime_root) / relative) for relative in BUNDLED_OPAQUE_DATA}
    for pin in before["files"]:
        # Package test data are included in the byte inventory, never decoded
        # or used as a scientific control. Only these five exact paths qualify.
        _read_pin(pin, allowed_runtime_roots, allow_opaque_payload=pin["path"] in bundled_paths)
    for link in before["links"]:
        if not Path(link["path"]).is_symlink() or os.readlink(link["path"]) != link["link_text"] or str(Path(link["path"]).resolve()) != link["resolved_target"]:
            _fail("live runtime symlink topology differs")
    for pin in probe["fresh_synthetic_files"]:
        _read_pin(pin, [str(Path(trusted.probe_root) / "generated")], allow_opaque_payload=True)
    return {
        "schema": SCHEMA + "-verification-result",
        "status": "QUALIFIED_CANDIDATE_ENGINEERING_EVIDENCE",
        "authority": "candidate-engineering-only",
        "evidence_sha256": trusted.evidence_sha256,
        "source_inventory_sha256": INVENTORY,
        "case_law_version": LAW,
        "runtime": dict(RUNTIME),
        "ordered_scan_count": 6,
        "ordered_window_count": 3,
        "synthetic_row_window_decode_receipts": 48,
        "independently_regenerated_selected_cells": 3145728,
        "positive_metadata_laws": 4,
        "negative_metadata_laws": 18,
        "live_runtime_file_pins_verified": before["file_count"],
        "live_runtime_logical_bytes_verified": before["raw_bytes"],
        "runtime_closure_payload_sha256": evidence["runtime_closure_payload_sha256"],
        "observed_snapshot_byte_closure_verified": True,
        "complete_execution_runtime_freeze": False,
        "externally_observed_complete_lifetime": False,
        "public_authentication_established": False,
        "telescope_admission_authorized": False,
        "scientific_admission_authorized": False,
        "executable_source_contract_created": False,
        "scientific_missing_fields_unchanged": list(MISSING),
    }
