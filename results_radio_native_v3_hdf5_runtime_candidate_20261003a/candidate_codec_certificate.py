"""Pure metadata verifier for ONE prospective candidate codec proof.

This schema grants no source-contract, acquisition, runtime-lifetime or science
authority. Callers must authenticate this verifier and every outer pin before
calling it. No scientific modules, package binaries, HDF5 files or network APIs
are used by build_certificate/verify_certificate.
"""
import hashlib
import json
import math
import re

SCHEMA = "radio-native-v3-prospective-candidate-codec-certificate-v1"
AUTHORITY = "prospective-candidate-codec-proof-only"
PUBLIC_CHECKPOINT = "39b3d09d7f4986dd7fb0f1e8d631c9bb0e023cc3"
REPOSITORY_ROOT = "/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive"
CANDIDATE_ROOT = "/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a"
RESULT = "results_radio_native_v3_hdf5_runtime_candidate_20261003a/"
SITE_ROOT = CANDIDATE_ROOT + "/venv/lib/python3.12/site-packages/"
VERIFIER_PATH = RESULT + "candidate_codec_certificate.py"
SOURCE_INVENTORY = "3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f"
RUNTIME = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5": "2.0.0", "hdf5plugin": "7.1.0"}
LEGACY_PROFILE = [[32008, 1, [0, 3, 4, 0, 2]]]
ENCODER_PROFILE = [[32008, 1, [0, 4, 4, 0, 2]]]
SHAPE = [16, 1, 264503296]
CHUNKS = [1, 1, 1048576]
LABELS = ["epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off"]
WINDOWS = [("calibration", 159, [167215104, 167280640]),
           ("validation", 156, [164069376, 164134912]),
           ("pilot", 152, [159875072, 159940608])]
PENDING = ["complete_execution_code_input_runtime_freeze", "hdf5_runtime",
           "source_specific_codec_runtime_case_law_certificate", "complete_127_24_scientific_certificate",
           "joined_hosted_transport_certificate", "source_specific_executable_trial_protocol",
           "cumulative_limits", "reservation_store", "public_acquisition_ledger_revision_and_sha256",
           "fresh_irrevocable_acquisition_and_trial_allocation", "new_executable_source_contract_sha256"]
SOURCE_PINS = {
    "src/seti_repeater/hdf5_filter_contract_radio.py": {"bytes": 1651, "sha256": "65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6"},
    "src/seti_repeater/source_radio.py": {"bytes": 10344, "sha256": "d189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f"},
    "src/seti_repeater/source_m43h.py": {"bytes": 15415, "sha256": "85ce563e78b2d16f65b6a15313c4ae0c22a58f1455ce8db77acbc9a62d33429d"},
    "src/seti_repeater/prospective_source_metadata_radio.py": {"bytes": 31819, "sha256": "2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360"},
    "config/radio_hd189733_source_preparation_20260927.json": {"bytes": 9707, "sha256": "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"},
    "results_radio_hd189733_geometry_2026-09-27/window_geometry.json": {"bytes": 35420, "sha256": "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"},
    "results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json": {"bytes": 1477, "sha256": "58b41ebdd2d7e407fc2ae49f594811e38c199f4914d34d0fe8e318bb0936894a"},
    "results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json": {"bytes": 3768, "sha256": "2b93524d831627186635963b48ed32ef3c02b6ed7d37d3a0a0ee68e53dfa7ac0"},
    "results_radio_hd189733_codec_2026-09-28/postflight.json": {"bytes": 3711, "sha256": "812713dfe264fcd41638b6e6c65f9d9e7595523be8f1e38bf2c59802b81b8874"},
}
PRODUCER_CODE_PINS = {
    RESULT + "candidate_probe.py": {"bytes": 6621, "sha256": "4d91be02b37c2c0678383073c6389d02842e3141c0ba890b1c2640b3ebf3328f"},
    RESULT + "source_profile_probe.py": {"bytes": 18960, "sha256": "ca339a21fc2c2e3e318d4ef97b2e63a98fb97877dcd4d3d63e55eb1c6733c8f9"},
}
PUBLISHED_INPUT_PINS = {**SOURCE_PINS, **PRODUCER_CODE_PINS,
    RESULT + "wheel-provenance.json": {"bytes": 4999, "sha256": "5ebdc675b1b2fda827312179ff7e494a18148893b49bbf85c9012e7467694da6"},
    RESULT + "candidate-probe.json": {"bytes": 41342, "sha256": "1c3e0d7b43e5d4a7b62c55a6347a3857717fb3e1aef416170231d4e0c37deeb6"},
    RESULT + "source-profile-probe.json": {"bytes": 11026, "sha256": "f8de675f6066badee6abe9645b925ac05d3373d657b92dfa6d3e0b83bdc8e32b"},
    RESULT + "numpy-2.3.5-pypi.json": {"bytes": 126913, "sha256": "26add04c77407fa4570d2cd4fe6dc966826b630f26822b9299957ae5fb816667"},
    RESULT + "h5py-3.16.0-pypi.json": {"bytes": 43906, "sha256": "acf09e71f9b25db02081a260399e4e9020da7bec56d291d1f597d01b52f4b760"},
    RESULT + "hdf5plugin-7.1.0-pypi.json": {"bytes": 9569, "sha256": "e435f8222a011e22c59788eba70d2150fdd28131910fa8fd518c5702725f4ba0"},
    RESULT + "candidate-probe.stdout.log": {"bytes": 521, "sha256": "9e007dafa1895b2a8f21316212b8bab969a766163707371644ac040dd33d18af"},
    RESULT + "candidate-probe.stderr.log": {"bytes": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    RESULT + "source-profile-probe.stdout.log": {"bytes": 481, "sha256": "0d0014f9c307ee5fb44677b8720887cb67c8f91433ac0f56cce232553b84b73b"},
    RESULT + "source-profile-probe.stderr.log": {"bytes": 0, "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
}
INPUT_PATHS = tuple(sorted(PUBLISHED_INPUT_PINS))
MAX_FILE_BYTES = 524288
MAX_INPUT_BYTES = 2097152
NATIVE_COHORT_SHA256 = "23429d09226bf4811daa430f0f86d80fe16bf9f78958bb4a8c068816fa72c359"
RAW_CHUNK_COHORT_SHA256 = "430cb3986dbe3777cc43b6c521a0d22b5411a92faf775bd56335027b14105532"
DECODE_COHORT_SHA256 = "367e46b1c8de87b61eb704dba51fa9d63b59fe5b48bc54ac9b1ce339525637f4"
SYNTHETIC_FILE_COHORT_SHA256 = "bfc547e0295db107937fec14f707c501d12e89c81cef628a4ca31778f87f397c"
GENERIC_PROBE_COHORT_SHA256 = "996de2f25e08cc66d2434cdb6a87122eabedac66e6732dc0b511ea3ab01e3d81"
LOADED_MAPPING_COHORT_SHA256 = "0dbf7d4bd31d4032c91b8ad1d266ab44f075a162bf7704f9de5e28d2203fbfcd"
LAW_EXPECTATIONS = [("exact_pipeline", "accept"), ("display_name_ignored", "accept"),
    ("explicit_unfiltered", "accept"), ("missing_optional_local_declaration", "accept"),
    ("missing_required_declaration", "reject"), ("pipeline_id_mutation", "reject"),
    ("pipeline_flags_mutation", "reject")] + [("client_datum_" + str(i) + "_mutation", "reject") for i in range(5)] + [
    ("removed_filter", "reject"), ("extra_filter", "reject")] + [("invalid_client_datum_type_" + str(i), "reject") for i in range(4)] + [
    ("boolean_filter_id", "reject"), ("boolean_filter_flags", "reject"),
    ("nonexplicit_pipeline", "reject"), ("malformed_filter_entry", "reject")]
PROFILE_REPORT_KEYS = set("acquisition_or_scientific_modules_loaded all_four_match_archived_local_baseline archive_payload_bytes_verified authenticated_source_specific_codec_runtime_case_law_certificate authority candidate_resource_limits complete_chunks_decoded coverage current_encoder_filter_pipeline decode_receipts decoded_cells_bit_exact decoded_chunk_bytes exact_source_filter_pipeline fresh_synthetic_files full_source_contract_or_scientific_certificate_ready hdf5_runtime_field_of_executable_source_contract_filled held_metadata_and_source_pins legacy_declaration_preserved_by_raw_local_chunk_transfer local_current_encoder_is_original_archive_encoder metadata_case_law_count metadata_case_laws metadata_payload_index_attempts network_requests normalization_or_detector_invoked observed_peak_rss_bytes observed_seconds primary_runtime_or_frozen_e_material_modified pure_filter_guard_directly_executed raw_chunk_receipts rng_draws row_indices_exercised rows_1_through_14_exercised runtime_version_fields_used_by_source_reader schema scientific_missing_field_count scientific_missing_fields_unchanged script_pin selected_cells_bit_exact six_scan_metadata_declarations_checked source_analysis_or_reservation_invocations source_chunks source_dtype source_inventory_sha256 source_shape status telescope_or_holdout_files_opened three_declared_window_positions_exercised".split())
BASE_REPORT_KEYS = set("authority candidate_native_binaries codec_probes complete_execution_runtime_freeze historical_binary_comparison historical_original_runtime_restored loaded_native_mappings project_module_invocations rng_invocations runtime schema scientific_trial_admission source_analysis_invocations source_specific_codec_runtime_certificate synthetic_source telescope_or_holdout_inputs_opened".split())
PROVENANCE_KEYS = set("candidate_root compatibility_tag_count eleven_source_gates_changed official_package_wheels package_authority primary_python primary_python_sha256 primary_runtime_changed protected_control_invocations python_version remote_repository_readback_or_historical_identity_claim rng_draws schema scientific_cases_run scientific_execution_authorized source_execution_authorized telescope_reads wheel_bytes".split())
COVERAGE = {
    "source_exact_metadata_profile": "measured and source-pinned",
    "four_version_runtime_equality": "measured; no executable source contract created",
    "legacy_codec_compatibility_at_declared_positions": "six full chunks, rows 0 and 15; synthetic only",
    "metadata_fail_closed_case_laws": "exact pure source guard executed; 22 acceptance/rejection cases",
    "normalization_receiver_handoff": "not exercised",
    "288 role_scan_row_source_payload_identities": "metadata definition only; no source payload acquisition",
    "public_certificate_authentication_and_full_runtime_lifetime_closure": "pending",
    "complete_127_24_scientific_certificate": "pending",
}
AUTHORITY_BOUNDARIES = {"executable_source_contract_admitted": False, "hdf5_runtime_field_filled": False,
    "authenticated_source_specific_scientific_codec_certificate": False, "complete_runtime_lifetime": False,
    "complete_127_24_scientific_certificate": False, "acquisition_authorized": False,
    "reservation_authorized": False, "native_trial_authorized": False, "rng_authorized": False,
    "scientific_execution_authorized": False, "threshold_transfer_authorized": False,
    "old_runtime_identity_restored": False, "fresh_runtime_available_now_verified": False}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def raw_pin(raw):
    _need(type(raw) is bytes, "raw bytes required")
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _pin(value):
    _need(type(value) is dict and set(value) == {"bytes", "sha256"}, "exact outer raw pin required")
    _integer(value["bytes"])
    _sha(value["sha256"])
    return value


def _integer(value, minimum=0):
    _need(type(value) is int and value >= minimum, "nonnegative exact integer required")
    return value


def _sha(value):
    _need(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "SHA256 required")
    return value


def _same(left, right):
    return canonical(left) == canonical(right)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "duplicate JSON member")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite JSON number: " + value)
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is float:
                _need(math.isfinite(item), "nonfinite numeric value")
            elif type(item) is dict:
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
        return value
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise ValueError("malformed bounded JSON") from error


def _cohort(value, expected, message):
    _need(hashlib.sha256(canonical(value)).hexdigest() == expected, message)


def _file_record(record, path, expected=None):
    _need(type(record) is dict and set(record) == {"path", "bytes", "sha256", "allocated_bytes"}, "exact measured file pin required")
    _need(record["path"] == path, "noncanonical measured file path")
    _integer(record["bytes"], 1); _integer(record["allocated_bytes"]); _sha(record["sha256"])
    if expected is not None:
        _need(_same({key: record[key] for key in ("bytes", "sha256")}, expected), "measured pin differs from outer raw source pin")


def _authenticate(raw_inputs, expected_raw_pins):
    _need(type(raw_inputs) is dict and type(expected_raw_pins) is dict and
          set(raw_inputs) == set(expected_raw_pins) == set(INPUT_PATHS), "exact complete evidence and external pin map required")
    docs = {}
    total = 0
    for path in INPUT_PATHS:
        raw = raw_inputs[path]
        _need(type(raw) is bytes and len(raw) <= MAX_FILE_BYTES, "bounded raw evidence required")
        total += len(raw)
        _need(total <= MAX_INPUT_BYTES, "aggregate metadata byte bound")
        _need(_same(raw_pin(raw), _pin(expected_raw_pins[path])), "raw evidence differs from independently supplied pin: " + path)
        if path in SOURCE_PINS or path in PRODUCER_CODE_PINS:
            fixed = SOURCE_PINS.get(path, PRODUCER_CODE_PINS.get(path))
            _need(_same(expected_raw_pins[path], fixed), "immutable source or producer code pin differs")
        if path.endswith(".json"):
            docs[path] = _json(raw)
    for stem in ("candidate-probe", "source-profile-probe"):
        _need(raw_inputs[RESULT + stem + ".stderr.log"] == b"", "probe stderr is not empty")
        wire = _json(raw_inputs[RESULT + stem + ".stdout.log"])
        _file_record(wire["report"], REPOSITORY_ROOT + "/" + RESULT + stem + ".json", expected_raw_pins[RESULT + stem + ".json"])
        if stem == "candidate-probe":
            _need(set(wire) == {"status", "report", "runtime_versions", "probes", "historical_binary_byte_matches", "historical_expected", "candidate_only"}, "ambiguous base probe completion")
            _need(wire["status"] == "pass" and wire["candidate_only"] is True and _same(wire["runtime_versions"], {"python": "3.12.14", **RUNTIME}), "base probe completion mismatch")
            _need(_same([wire["probes"], wire["historical_binary_byte_matches"], wire["historical_expected"]], [3, 30, 30]), "base probe completion counts differ")
        else:
            _need(set(wire) == {"status", "report", "metadata_case_laws", "decoded_cells", "selected_cells", "scientific_missing_fields"}, "ambiguous profile completion")
            _need(wire["status"] == "EXACT_LEGACY_DECLARATION_SYNTHETIC_DECODE_AND_METADATA_CASE_LAWS_PASS" and
                  _same([wire["metadata_case_laws"], wire["decoded_cells"], wire["selected_cells"], wire["scientific_missing_fields"]], [22, 6291456, 393216, 11]), "profile completion counts differ")
    return docs


def _official_packages(docs, expected_raw_pins):
    provenance = docs[RESULT + "wheel-provenance.json"]
    _need(type(provenance) is dict and set(provenance) == PROVENANCE_KEYS, "ambiguous official wheel provenance")
    _need(provenance["schema"] == "radio-native-v3-isolated-hdf5-wheel-provenance-v1" and
          provenance["package_authority"] == "official PyPI version JSON and files.pythonhosted.org wheel URLs, HTTPS with redirects refused" and
          provenance["primary_python"] == "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12" and
          provenance["primary_python_sha256"] == "fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7" and
          _same(provenance["compatibility_tag_count"], 1068), "official wheel authority/bootstrap scope differs")
    _need(provenance["candidate_root"] == CANDIDATE_ROOT and provenance["python_version"] == "3.12.14", "candidate provenance identity differs")
    for flag in ("eleven_source_gates_changed", "primary_runtime_changed", "remote_repository_readback_or_historical_identity_claim", "scientific_execution_authorized", "source_execution_authorized"):
        _need(provenance[flag] is False, "wheel provenance cannot grant authority")
    for counter in ("protected_control_invocations", "rng_draws", "scientific_cases_run", "telescope_reads"):
        _need(type(provenance[counter]) is int and provenance[counter] == 0, "wheel provenance operation counter differs")
    _need(provenance["wheel_bytes"] == 68409067 and type(provenance["wheel_bytes"]) is int, "wheel byte total differs")
    wheels = provenance["official_package_wheels"]
    _need(type(wheels) is list and [w["name"] for w in wheels] == ["numpy", "h5py", "hdf5plugin"], "exact ordered three wheels required")
    result = []
    expected_wheels = {
        "numpy": ("2.3.5", "numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl", 16606086, "0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28"),
        "h5py": ("3.16.0", "h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl", 5405250, "dfc21898ff025f1e8e67e194965a95a8d4754f452f83454538f98f8a3fcb207e"),
        "hdf5plugin": ("7.1.0", "hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl", 46397731, "9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247"),
    }
    wheel_keys = set("bytes download_file_readback_sha256_verified download_path filename matching_tags metadata_pin metadata_readback_matches_initial_pin metadata_url name requires_dist requires_python retained_metadata_pin sha256 tag_matches_primary url version yanked".split())
    for wheel in wheels:
        _need(set(wheel) == wheel_keys, "ambiguous wheel fields")
        name = wheel["name"]; version, filename, size, digest = expected_wheels[name]
        _need(_same([wheel["version"], wheel["filename"], wheel["bytes"], wheel["sha256"]], [version, filename, size, digest]), "official wheel selection differs")
        metadata_path = RESULT + name + "-" + version + "-pypi.json"
        metadata = docs[metadata_path]
        _need(metadata["info"]["name"].lower() == name and metadata["info"]["version"] == version, "official package identity differs")
        selected = [entry for entry in metadata["urls"] if entry["filename"] == filename]
        _need(len(selected) == 1, "ambiguous exact official wheel URL selection")
        entry = selected[0]
        _need(entry["packagetype"] == "bdist_wheel" and entry["yanked"] is False and wheel["yanked"] is False,
              "official selected wheel must be nonyanked binary distribution")
        _need(_same([entry["size"], entry["digests"]["sha256"], entry["url"]], [size, digest, wheel["url"]]), "official wheel URL/hash/size differs")
        _need(type(wheel["url"]) is str and wheel["url"].startswith("https://files.pythonhosted.org/packages/") and
              wheel["url"].endswith("/" + filename) and "?" not in wheel["url"] and "#" not in wheel["url"], "official package URL required")
        _need(wheel["metadata_url"] == "https://pypi.org/pypi/" + name + "/" + version + "/json" and
              wheel["download_path"] == CANDIDATE_ROOT + "/wheelhouse/" + filename, "official metadata/download identity differs")
        _need(wheel["tag_matches_primary"] is True and wheel["download_file_readback_sha256_verified"] is True and
              wheel["metadata_readback_matches_initial_pin"] is True, "wheel preparation qualification incomplete")
        expected_tags = {"numpy": ["cp312-cp312-manylinux_2_27_x86_64", "cp312-cp312-manylinux_2_28_x86_64"],
                         "h5py": ["cp312-cp312-manylinux_2_28_x86_64"],
                         "hdf5plugin": ["py3-none-manylinux_2_27_x86_64", "py3-none-manylinux_2_28_x86_64"]}
        _need(_same(wheel["matching_tags"], expected_tags[name]), "invalid wheel compatibility receipt")
        _need(_same(wheel["requires_python"], metadata["info"]["requires_python"]) and _same(wheel["requires_dist"], metadata["info"]["requires_dist"]), "package dependency metadata differs")
        _need(_same(_pin(wheel["metadata_pin"]), expected_raw_pins[metadata_path]), "initial official metadata raw pin differs")
        retained_pin = wheel["retained_metadata_pin"]
        _need(set(retained_pin) == {"path", "bytes", "sha256"} and retained_pin["path"] == REPOSITORY_ROOT + "/" + metadata_path and
              _same({key: retained_pin[key] for key in ("bytes", "sha256")}, expected_raw_pins[metadata_path]), "retained official metadata outer pin differs")
        result.append({"name": name, "version": version, "filename": filename, "bytes": size, "sha256": digest,
                       "url": wheel["url"], "metadata_raw_pin": expected_raw_pins[metadata_path]})
    return result


def _base_runtime(docs):
    base = docs[RESULT + "candidate-probe.json"]
    _need(type(base) is dict and set(base) == BASE_REPORT_KEYS, "ambiguous candidate runtime report")
    _need(base["schema"] == "radio-native-v3-hdf5-runtime-candidate-probe-v1" and base["authority"] == "candidate-only", "candidate report scope differs")
    for key in ("complete_execution_runtime_freeze", "historical_original_runtime_restored", "scientific_trial_admission", "source_specific_codec_runtime_certificate"):
        _need(base[key] is False, "runtime report cannot grant scientific authority")
    for key in ("project_module_invocations", "rng_invocations", "source_analysis_invocations", "telescope_or_holdout_inputs_opened"):
        _need(type(base[key]) is int and base[key] == 0, "candidate report operation count differs")
    runtime = base["runtime"]
    expected_keys = set("base_prefix byteorder dont_write_bytecode h5py hdf5 hdf5plugin isolated libc machine numpy prefix python python_binary pyvenv_configuration sys_path".split())
    _need(set(runtime) == expected_keys and _same({key: runtime[key] for key in RUNTIME}, RUNTIME), "runtime version fields differ")
    _need(runtime["python"] == "3.12.14" and runtime["machine"] == "x86_64" and runtime["byteorder"] == "little" and
          runtime["isolated"] is True and runtime["dont_write_bytecode"] is True and runtime["prefix"] == CANDIDATE_ROOT + "/venv" and
          runtime["base_prefix"] == "/opt/codex/runtimes/codex-primary-runtime/dependencies/python", "candidate runtime identity differs")
    _file_record(runtime["python_binary"], CANDIDATE_ROOT + "/venv/bin/python", {"bytes": 30894944, "sha256": "fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7"})
    python_base = "/opt/codex/runtimes/codex-primary-runtime/dependencies/python"
    configuration = ("home = " + python_base + "/bin\ninclude-system-site-packages = false\nversion = 3.12.14\n"
        "executable = " + python_base + "/bin/python3.12\ncommand = " + python_base +
        "/bin/python3.12 -m venv --copies --without-pip " + CANDIDATE_ROOT + "/venv\n")
    _need(runtime["pyvenv_configuration"] == configuration and _same(runtime["libc"], ["glibc", "2.39"]) and
          runtime["sys_path"] == [runtime["base_prefix"] + "/lib/python312.zip", runtime["base_prefix"] + "/lib/python3.12",
             runtime["base_prefix"] + "/lib/python3.12/lib-dynload", SITE_ROOT[:-1]], "isolated candidate path closure differs")
    native = base["candidate_native_binaries"]
    _need(type(native) is list and len(native) == 63, "exact 63-native byte cohort required")
    normalized = []; seen = set()
    for row in native:
        _need(set(row) == {"path", "bytes", "sha256", "allocated_bytes", "site_relative_path"}, "ambiguous native row")
        relative = row["site_relative_path"]
        _need(type(relative) is str and relative not in seen and not relative.startswith("/") and
              all(part not in ("", ".", "..") for part in relative.split("/")) and ".so" in relative, "duplicate or noncanonical native path")
        seen.add(relative)
        _file_record({key: row[key] for key in ("path", "bytes", "sha256", "allocated_bytes")}, SITE_ROOT + relative)
        normalized.append({key: row[key] for key in ("site_relative_path", "bytes", "sha256")})
    normalized.sort(key=lambda row: row["site_relative_path"])
    _cohort(normalized, NATIVE_COHORT_SHA256, "native byte/hash cohort differs")
    historical = docs["results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json"]
    _need(_same({key: historical[key] for key in RUNTIME}, RUNTIME) and len(historical["binary_sha256s"]) == 30, "historical local baseline differs")
    observed = {row["site_relative_path"]: row["sha256"] for row in normalized}
    _need(all(observed.get(path) == digest for path, digest in historical["binary_sha256s"].items()), "historical 30-native bytes differ")
    compare = base["historical_binary_comparison"]
    _need(set(compare) == set("expected_count historical_metadata historical_storage_or_inode_recovery_established identity_continuity_established matching_count matching_paths mismatches missing_paths".split()), "ambiguous historical comparison")
    _need(_same([compare["expected_count"], compare["matching_count"]], [30, 30]) and compare["matching_paths"] == sorted(historical["binary_sha256s"]) and
          compare["missing_paths"] == [] and compare["mismatches"] == [] and compare["identity_continuity_established"] is False and
          compare["historical_storage_or_inode_recovery_established"] is False, "historical comparison cannot establish continuity")
    _file_record(compare["historical_metadata"], REPOSITORY_ROOT + "/results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json", SOURCE_PINS["results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json"])
    _cohort(base["codec_probes"], GENERIC_PROBE_COHORT_SHA256, "generic codec probe evidence differs")
    _cohort(base["loaded_native_mappings"], LOADED_MAPPING_COHORT_SHA256, "loaded native mapping byte cohort differs")
    _need(set(base["synthetic_source"]) == {"bytes", "construction", "independent_struct_agreement", "sha256"} and
          base["synthetic_source"]["construction"] == "float32((i % 257) * 0.125), i=0..2047" and
          base["synthetic_source"]["independent_struct_agreement"] is True and base["synthetic_source"]["bytes"] == 8192 and
          base["synthetic_source"]["sha256"] == "587a7e1bfc3ec86b28e16d67bb8efdfb652789e7004d98c6e3f39ae0de7e24bd", "generic synthetic construction differs")
    return normalized


def _profile(docs, expected_raw_pins):
    report = docs[RESULT + "source-profile-probe.json"]
    _need(type(report) is dict and set(report) == PROFILE_REPORT_KEYS, "ambiguous candidate source-profile report")
    _need(report["schema"] == "radio-native-v3-candidate-exact-source-profile-v1" and report["authority"] == "candidate-only synthetic preparation" and
          report["status"] == "EXACT_LEGACY_DECLARATION_SYNTHETIC_DECODE_AND_METADATA_CASE_LAWS_PASS", "profile proof status/scope differs")
    for key in ("acquisition_or_scientific_modules_loaded", "archive_payload_bytes_verified", "authenticated_source_specific_codec_runtime_case_law_certificate",
                "full_source_contract_or_scientific_certificate_ready", "hdf5_runtime_field_of_executable_source_contract_filled", "local_current_encoder_is_original_archive_encoder",
                "normalization_or_detector_invoked", "primary_runtime_or_frozen_e_material_modified", "rows_1_through_14_exercised"):
        _need(report[key] is False, "candidate profile cannot grant future/full authority")
    for key in ("all_four_match_archived_local_baseline", "legacy_declaration_preserved_by_raw_local_chunk_transfer", "pure_filter_guard_directly_executed", "three_declared_window_positions_exercised"):
        _need(report[key] is True, "candidate exact-profile qualification missing")
    for key in ("metadata_payload_index_attempts", "network_requests", "rng_draws", "source_analysis_or_reservation_invocations", "telescope_or_holdout_files_opened"):
        _need(type(report[key]) is int and report[key] == 0, "profile operation counter differs")
    _need(_same(report["source_shape"], SHAPE) and _same(report["source_chunks"], CHUNKS) and report["source_dtype"] == "<f4" and
          _same(report["exact_source_filter_pipeline"], LEGACY_PROFILE) and _same(report["current_encoder_filter_pipeline"], ENCODER_PROFILE), "legacy/source profile confused with encoder")
    _need(_same(report["runtime_version_fields_used_by_source_reader"], RUNTIME) and report["source_inventory_sha256"] == SOURCE_INVENTORY, "source runtime/inventory binding differs")
    _need(_same([report["scientific_missing_field_count"], report["decoded_chunk_bytes"], report["complete_chunks_decoded"], report["decoded_cells_bit_exact"],
                 report["selected_cells_bit_exact"], report["six_scan_metadata_declarations_checked"], report["metadata_case_law_count"]],
                [11, 4194304, 6, 6291456, 393216, 6, 22]), "candidate profile aggregate counts differ")
    _need(_same(report["row_indices_exercised"], [0, 15]) and _same(report["scientific_missing_fields_unchanged"], PENDING) and
          _same(report["coverage"], COVERAGE), "scope/coverage cannot silently upgrade")
    held = report["held_metadata_and_source_pins"]
    _need(type(held) is dict and set(held) == set(SOURCE_PINS), "exact nine held source/metadata pins required")
    for path in SOURCE_PINS:
        _file_record(held[path], REPOSITORY_ROOT + "/" + path, expected_raw_pins[path])
    _file_record(report["script_pin"], REPOSITORY_ROOT + "/" + RESULT + "source_profile_probe.py", expected_raw_pins[RESULT + "source_profile_probe.py"])
    source = docs["config/radio_hd189733_source_preparation_20260927.json"]
    _need(source["source_inventory_sha256"] == SOURCE_INVENTORY and source["hdf5_runtime"] is None and source["windows"] == [] and
          source["stage"] == "preparation-only-no-spectral-access" and [s["label"] for s in source["scans"]] == LABELS and
          [s["role"] for s in source["scans"]] == ["on", "off"] * 3, "immutable source preparation boundary differs")
    for scan in source["scans"]:
        _need(_same(scan["expected_chunks"], CHUNKS) and _same(scan["expected_header"]["dataset_shape"], SHAPE) and
              scan["expected_header"]["dataset_dtype"] == "float32" and _same([entry[:3] for entry in scan["observed_hdf5_filters"]], LEGACY_PROFILE), "six-scan source profile differs")
    geometry = docs["results_radio_hd189733_geometry_2026-09-27/window_geometry.json"]
    actual_windows = [(window["role"], window["archive_chunk_index"], window["archive_interval"]) for window in geometry["windows"]]
    _need(_same(actual_windows, WINDOWS), "window profile ancestry differs")
    expected_keys = [(row, role) for row in (0, 15) for role, _, _ in WINDOWS]
    raw_rows = report["raw_chunk_receipts"]; decoded = report["decode_receipts"]
    _need(type(raw_rows) is list and type(decoded) is list and len(raw_rows) == len(decoded) == 6, "exact six raw and decoded receipts required")
    _need([(row["row"], row["role"]) for row in raw_rows] == expected_keys and [(row["row"], row["role"]) for row in decoded] == expected_keys,
          "one-to-one ordered row/role coverage missing or duplicated")
    for index, (row_number, role) in enumerate(expected_keys):
        _, chunk, interval = next(window for window in WINDOWS if window[0] == role)
        raw = raw_rows[index]; decode = decoded[index]
        _need(set(raw) == {"row", "role", "offset", "filter_mask", "compressed_bytes", "compressed_sha256"} and
              set(decode) == {"row", "role", "chunk_index", "archive_interval", "decoded_cells", "decoded_sha256", "selected_cells", "selected_sha256", "bit_exact"}, "ambiguous raw/decode receipt")
        _need(type(raw["row"]) is int and type(decode["row"]) is int and _same(raw["offset"], [row_number, 0, chunk * 1048576]) and
              type(raw["filter_mask"]) is int and raw["filter_mask"] == 0, "raw chunk mapping/filter-mask differs")
        _integer(raw["compressed_bytes"], 1); _sha(raw["compressed_sha256"])
        _need(type(decode["chunk_index"]) is int and decode["chunk_index"] == chunk and _same(decode["archive_interval"], interval) and
              _same([decode["decoded_cells"], decode["selected_cells"]], [1048576, 65536]) and decode["bit_exact"] is True, "decoded chunk/window proof differs")
        _sha(decode["decoded_sha256"]); _sha(decode["selected_sha256"])
    _cohort(raw_rows, RAW_CHUNK_COHORT_SHA256, "fixed raw compressed byte receipts differ")
    _cohort(decoded, DECODE_COHORT_SHA256, "fixed full/selected decoded byte receipts differ")
    _cohort(report["fresh_synthetic_files"], SYNTHETIC_FILE_COHORT_SHA256, "two retained synthetic file pins differ")
    laws = report["metadata_case_laws"]
    _need(type(laws) is list and len(laws) == 22, "exact 22 metadata laws required")
    for row, (name, expected) in zip(laws, LAW_EXPECTATIONS):
        _need(set(row) == {"name", "expected", "pass"} and row["name"] == name and row["expected"] == expected and row["pass"] is True,
              "one-to-one metadata case-law coverage differs")
    limits = {"seconds": 60, "peak_rss_bytes": 268435456, "generated_file_bytes": 33554432}
    _need(_same(report["candidate_resource_limits"], limits), "candidate bounded scope differs")
    seconds = report["observed_seconds"]
    _need(type(seconds) in (float, int) and math.isfinite(seconds) and 0 <= seconds <= limits["seconds"] and
          type(report["observed_peak_rss_bytes"]) is int and 0 < report["observed_peak_rss_bytes"] <= limits["peak_rss_bytes"] and
          sum(row["bytes"] for row in report["fresh_synthetic_files"]) <= limits["generated_file_bytes"], "candidate resource observation exceeds scope")
    return report


def _build_certificate(raw_inputs, expected_raw_pins, verifier_code_pin):
    """Build narrow prospective evidence. Every pin is a caller trust input."""
    _pin(verifier_code_pin)
    _need(verifier_code_pin["bytes"] > 0, "independently authenticated verifier code pin required")
    docs = _authenticate(raw_inputs, expected_raw_pins)
    wheels = _official_packages(docs, expected_raw_pins)
    native = _base_runtime(docs)
    profile = _profile(docs, expected_raw_pins)
    certificate = {"schema": SCHEMA, "authority": AUTHORITY,
        "provenance": {"published_baseline_checkpoint": PUBLIC_CHECKPOINT,
                       "provided_raw_pin_map_matches_published_baseline": _same(expected_raw_pins, PUBLISHED_INPUT_PINS),
                       "external_raw_pins_required": True,
                       "remote_origin_readback_verified_by_this_pure_verifier": False},
        "evidence_pins": expected_raw_pins, "verifier_code_pin": verifier_code_pin,
        "source_profile": {"source_inventory_sha256": SOURCE_INVENTORY, "source_raw_pins": SOURCE_PINS,
                           "shape": SHAPE, "chunks": CHUNKS, "dtype": "<f4", "legacy_filter_pipeline": LEGACY_PROFILE,
                           "current_encoder_filter_pipeline": ENCODER_PROFILE, "six_scan_metadata_definitions": LABELS},
        "runtime": {"versions": RUNTIME, "python": "3.12.14", "native_byte_cohort_count": len(native),
                    "native_byte_cohort_sha256": NATIVE_COHORT_SHA256, "native_byte_cohort": native,
                    "official_wheels": wheels, "historical_hdf5_byte_matches": 30, "primary_stdlib_shared": True,
                    "fresh_live_runtime_reobservation_performed": False},
        "coverage": {"raw_chunk_receipt_sha256": RAW_CHUNK_COHORT_SHA256, "decode_receipt_sha256": DECODE_COHORT_SHA256,
                     "complete_chunks": 6, "decoded_cells": 6291456, "selected_cells": 393216,
                     "row_role_pairs": [[row, role] for row in (0, 15) for role, _, _ in WINDOWS],
                     "windows": [{"role": role, "chunk_index": chunk, "archive_interval": interval} for role, chunk, interval in WINDOWS],
                     "metadata_case_laws": profile["metadata_case_laws"], "metadata_case_law_count": 22,
                     "scope": COVERAGE, "rows_1_through_14_exercised": False, "original_archive_payload_verified": False},
        "pending_scientific_fields": PENDING, "authority_boundaries": AUTHORITY_BOUNDARIES}
    # Detach all caller-owned structures; no post-verification mutation alias.
    return _json(canonical(certificate))


def build_certificate(raw_inputs, expected_raw_pins, verifier_code_pin):
    """Reject malformed nested schemas with one fail-closed exception type."""
    try:
        return _build_certificate(raw_inputs, expected_raw_pins, verifier_code_pin)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError("malformed candidate evidence schema") from error


def verify_certificate(certificate_raw, expected_certificate_pin, raw_inputs, expected_raw_pins, verifier_code_pin):
    """Require outer certificate authentication and exact deterministic semantics."""
    _need(type(certificate_raw) is bytes and len(certificate_raw) <= MAX_FILE_BYTES, "bounded raw certificate required")
    _need(_same(raw_pin(certificate_raw), _pin(expected_certificate_pin)), "certificate differs from independent outer pin")
    parsed = _json(certificate_raw)
    _need(certificate_raw == canonical(parsed), "canonical certificate bytes required")
    expected = build_certificate(raw_inputs, expected_raw_pins, verifier_code_pin)
    _need(_same(parsed, expected), "certificate semantics, scope, coverage or authority differs")
    return _json(canonical(expected))


def main():
    """Fixed-path metadata-only CLI; bootstrap hashes are explicit outer inputs."""
    import argparse
    import os
    from pathlib import Path
    import stat
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--verifier-sha256", required=True)
    parser.add_argument("--pins", required=True, help="independently authenticated complete evidence pin-map JSON")
    parser.add_argument("--pins-sha256", required=True)
    parser.add_argument("--certificate", required=True, help="fixed candidate result filename for exclusive build or readonly verify")
    parser.add_argument("--certificate-sha256", help="independently authenticated outer certificate SHA for verify")
    args = parser.parse_args()
    _need(sys.dont_write_bytecode and bool(sys.flags.isolated), "CLI requires -I -B")
    _need(Path(__file__).resolve() == Path(REPOSITORY_ROOT + "/" + VERIFIER_PATH), "fixed independently pinned verifier entrypoint required")
    _need(Path(args.pins) == Path(REPOSITORY_ROOT + "/" + RESULT + "candidate-codec-external-pins.json"), "fixed candidate external pin-map path required")
    def read(path):
        _need(str(path) == str(path.resolve()) and stat.S_ISREG(path.lstat().st_mode), "canonical nonsymlink metadata descriptor required")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            _need(before.st_size <= MAX_FILE_BYTES, "CLI metadata byte limit")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            after = os.fstat(descriptor)
            _need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                  (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) and len(raw) == before.st_size,
                  "metadata descriptor changed during read")
            return raw
        finally:
            os.close(descriptor)
    own = read(Path(REPOSITORY_ROOT + "/" + VERIFIER_PATH))
    _need(raw_pin(own)["sha256"] == _sha(args.verifier_sha256), "verifier code differs from independent bootstrap pin")
    pins_raw = read(Path(args.pins))
    _need(raw_pin(pins_raw)["sha256"] == _sha(args.pins_sha256), "external pin-map bootstrap hash differs")
    pins = _json(pins_raw)
    raw_inputs = {path: read(Path(REPOSITORY_ROOT + "/" + path)) for path in INPUT_PATHS}
    target = Path(args.certificate)
    _need(target.parent == Path(REPOSITORY_ROOT + "/" + RESULT) and target.name in
          ("prospective-codec-certificate.json", "prospective-codec-certificate-review.json"), "fixed candidate certificate output required")
    if args.action == "build":
        _need(args.certificate_sha256 is None, "build cannot self-supply a certificate grant")
        raw = canonical(build_certificate(raw_inputs, pins, raw_pin(own)))
        with target.open("xb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        parent_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    else:
        _need(args.certificate_sha256 is not None, "verify requires independent certificate outer hash")
        raw = read(target)
        verify_certificate(raw, {"bytes": len(raw), "sha256": _sha(args.certificate_sha256)}, raw_inputs, pins, raw_pin(own))
    print(json.dumps({"schema": SCHEMA + "-cli", "status": "verified-candidate-only", "action": args.action,
                      "certificate": {"path": str(target), **raw_pin(raw)}, "scientific_execution_authorized": False,
                      "pending_scientific_field_count": 11}, sort_keys=True))


if __name__ == "__main__":
    main()
