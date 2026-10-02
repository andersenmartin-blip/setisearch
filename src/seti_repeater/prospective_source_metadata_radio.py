"""Pure, permanently blocked HD189733 metadata construction and validation.

Callers supply raw bytes plus independently retained raw-file pins. No project
module is imported; no file, network, runtime, reservation or worker API is used.
This module cannot produce an executable source contract or scientific gate.
"""
from fractions import Fraction
import hashlib
import json
import math
import re

CHECKPOINT = "58e7a883bf8ccf7951e8365f658d7b6645f161e4"
SOURCE_INVENTORY = "3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f"
SOURCE = "config/radio_hd189733_source_preparation_20260927.json"
HEADERS = "results_radio_alternate_2026-09-27/attempt01/85030/headers.json"
QUALIFICATION = "results_radio_alternate_2026-09-27/source_qualification.json"
GEOMETRY = "results_radio_hd189733_geometry_2026-09-27/window_geometry.json"
WINDOWS = "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json"
BANKS = "results_radio_hd189733_receiver_2026-09-28/bank_records.json"
PROPOSAL = "config/radio_whole_cadence_null_proposal_20260928.json"
IMPLEMENTATION_PATHS = (
    "src/seti_repeater/source_radio.py", "src/seti_repeater/transport_radio.py",
    "src/seti_repeater/source_m43h.py", "src/seti_repeater/transport_m43h.py",
    "src/seti_repeater/http_range_v0p6.py", "src/seti_repeater/source_v0p6.py",
    "src/seti_repeater/search_v0p6.py", "src/seti_repeater/hdf5_filter_contract_radio.py",
    "src/seti_repeater/acquisition_radio.py",
)
MATRIX_PATHS = (
    SOURCE, HEADERS, QUALIFICATION, GEOMETRY, WINDOWS, BANKS,
    "results_radio_hd189733_receiver_2026-09-28/arithmetic_and_containment.json",
    "results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json",
    "results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json",
    "results_radio_hd189733_codec_2026-09-28/postflight.json",
    "results_radio_whole_cadence_handoff_2026-09-28/postflight.json", PROPOSAL,
    IMPLEMENTATION_PATHS[0], IMPLEMENTATION_PATHS[7],
    "src/seti_repeater/window_identity_radio_v2.py",
    "src/seti_repeater/receiver_bank_radio.py", IMPLEMENTATION_PATHS[8],
    "src/seti_repeater/native_v2_runner_radio.py",
    "src/seti_repeater/whole_cadence_downstream_radio.py",
)
REQUIRED_PATHS = frozenset(MATRIX_PATHS + IMPLEMENTATION_PATHS)
ROLES = ("calibration", "validation", "pilot")
LABELS = tuple(f"epoch{epoch}_{role}" for epoch in (1, 2, 3) for role in ("on", "off"))
RATES = tuple(range(-40, 41))
WIDTHS = (1, 3, 5, 9, 17, 33, 65, 129)
STATUS = "PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED"
OUTPUT_KEYS = ("prospective_wrapper", "admission_matrix", "provenance_rebinding")
MAX_FILE_BYTES = 524288
MAX_INPUT_BYTES = 2097152
MAX_OUTPUT_BYTES = 262144
AUTHORITY_FIELDS = (
    "spectral_access_authorized", "execution_authorized", "reservation_authorized",
    "rng_authorized", "scientific_execution_authorized", "threshold_transfer_authorized",
)
COUNTER_FIELDS = (
    "network_requests", "spectral_dataset_values_read", "scientific_cases_run",
    "native_case_executions", "native_case_reservations", "rng_draws", "telescope_reads",
    "new_control_invocations", "source_generation", "reservation_mutations",
)
MISSING_FIELDS = (
    "complete_execution_code_input_runtime_freeze", "hdf5_runtime",
    "source_specific_codec_runtime_case_law_certificate", "complete_127_24_scientific_certificate",
    "joined_hosted_transport_certificate", "source_specific_executable_trial_protocol",
    "cumulative_limits", "reservation_store", "public_acquisition_ledger_revision_and_sha256",
    "fresh_irrevocable_acquisition_and_trial_allocation", "new_executable_source_contract_sha256",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def legacy_digest(value):
    """The pinned source/window APIs hash compact JSON including one newline."""
    return hashlib.sha256(canonical(value) + b"\n").hexdigest()


def _same(left, right):
    """Canonical comparison preserves JSON integer/float/Boolean distinctions."""
    return canonical(left) == canonical(right)


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "Invalid SHA256 pin")
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "Duplicate JSON member")
        result[key] = value
    return result


def _json(raw):
    def invalid(value):
        raise ValueError("Nonfinite JSON value: " + value)
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)
        pending = [value]
        while pending:
            item = pending.pop()
            if type(item) is float:
                _need(math.isfinite(item), "Nonfinite JSON numeric value")
            elif type(item) is dict:
                pending.extend(item.values())
            elif type(item) is list:
                pending.extend(item)
        return value
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed bounded JSON") from error


def _authenticate(raw_files, expected_file_pins):
    _need(type(raw_files) is dict and type(expected_file_pins) is dict,
          "Raw evidence and external pins must be dictionaries")
    _need(set(raw_files) == REQUIRED_PATHS == set(expected_file_pins),
          "Exact 19 matrix plus nine implementation closure required")
    total = 0
    docs = {}
    for path in sorted(REQUIRED_PATHS):
        raw = raw_files[path]
        pin = expected_file_pins[path]
        _need(type(raw) is bytes and 0 < len(raw) <= MAX_FILE_BYTES, "Bounded raw bytes required")
        _need(type(pin) is dict and set(pin) == {"bytes", "sha256"}, "Exact raw pin envelope required")
        _need(type(pin["bytes"]) is int and pin["bytes"] == len(raw), "Raw byte count mismatch")
        _need(hashlib.sha256(raw).hexdigest() == _sha(pin["sha256"]), "Raw evidence differs from external pin")
        total += len(raw)
        _need(total <= MAX_INPUT_BYTES, "Metadata input budget exceeded")
        if path.endswith(".json"):
            docs[path] = _json(raw)
    return docs


def _rational(value):
    _need(type(value) in (int, float) and math.isfinite(value), "Finite exact header number required")
    return Fraction(value)


def _authority():
    return {name: False for name in AUTHORITY_FIELDS}


def _counters():
    return {name: False if name in ("spectral_dataset_values_read", "source_generation") else 0
            for name in COUNTER_FIELDS}


def _scan_semantics(source, headers, qualification, expected_inventory):
    _need(expected_inventory == SOURCE_INVENTORY, "This candidate is restricted to the reviewed source inventory")
    _need(source.get("artifact_type") == "radio-source-contract-v1"
          and source.get("stage") == "preparation-only-no-spectral-access"
          and _same(source.get("windows"), []) and source.get("hdf5_runtime") is None
          and _same(source.get("cadence_id"), 85030) and source.get("archive_target") == "HIP98505",
          "Original immutable preparation boundary changed")
    _need(canonical(source.get("session_limits")) == canonical({"max_requests": 500, "max_bytes": 536870912, "max_seconds": 1200}),
          "Historical inactive session declaration changed")
    scans = source["scans"]
    _need(type(scans) is list and len(scans) == 6 and type(headers) is list and len(headers) == 6,
          "Six retained scans and headers required")
    _need(tuple(s["label"] for s in scans) == LABELS and tuple(s["role"] for s in scans) == ("on", "off") * 3
          and len({s["url"] for s in scans}) == 6, "Alternating six-scan order or identity changed")
    _need(legacy_digest(scans) == expected_inventory == source.get("source_inventory_sha256"), "Source inventory mismatch")
    header_names = {"dataset_shape": "dataset_shape", "dataset_dtype": "dataset_dtype"}
    attr_names = {"fch1_mhz": "fch1", "foff_mhz": "foff", "source_name": "source_name",
                  "src_dej_deg": "src_dej", "src_raj_hours": "src_raj", "tsamp_s": "tsamp", "tstart_mjd": "tstart"}
    clock = []
    origin = _rational(scans[0]["expected_header"]["tstart_mjd"])
    anchor = _rational(scans[0]["expected_header"]["tsamp_s"]) / 2
    for scan, retained in zip(scans, headers):
        h = scan["expected_header"]
        _need(retained.get("spectral_dataset_values_read") is False, "Retained headers must contain no spectra")
        _need(scan["url"] == retained["url"] and scan["expected_etag"] == retained["etag"]
              and _same(scan["expected_remote_size_bytes"], retained["remote_size_bytes"])
              and _same(scan["expected_chunks"], retained["dataset_chunks"])
              and _same(scan["observed_hdf5_filters"], retained["hdf5_filters"]), "Scan/header source binding differs")
        _need(all(_same(h[k], retained[v]) for k, v in header_names.items())
              and all(_same(h[k], retained["data_attributes"][v]) for k, v in attr_names.items()), "Retained header differs")
        _need(_same(h["dataset_shape"], [16, 1, 264503296]) and h["dataset_dtype"] == "float32"
              and _same(scan["expected_chunks"], [1, 1, 1048576]) and h["foff_mhz"] < 0
              and (h["source_name"] == "HIP98505") == (scan["role"] == "on"), "Frozen source geometry changed")
        dt = _rational(h["tsamp_s"])
        _need(dt > 0, "Positive source integration required")
        start = (_rational(h["tstart_mjd"]) - origin) * 86400 - anchor
        clock.extend(tuple(start + (Fraction(i) + part) * dt for part in (Fraction(0), Fraction(1, 2), Fraction(1)))
                     for i in range(16))
    _need(clock[0][1] == 0 and all(a[2] <= b[0] for a, b in zip(clock, clock[1:]))
          and all(row[1] * 2 == row[0] + row[2] for row in clock), "Exact six-scan header clock changed")
    _need(qualification.get("source_inventory_sha256") == expected_inventory
          and qualification.get("source_metadata_proximity_gate_passed") is True
          and qualification.get("spectral_dataset_values_read") is False, "Metadata qualification belongs to another source")
    for flag in ("physical_motion_bank_qualified", "cross_window_numeric_transfer_qualified",
                 "recovery_rfi_null_evaluation_qualified", "telescope_codec_handoff_qualified"):
        _need(qualification.get(flag) is False, "Historical metadata cannot upgrade scientific qualification")
    return [[[q.numerator, q.denominator] for q in row] for row in clock]


def _window_semantics(source, design, bound, source_sha, design_sha):
    _need(design.get("schema") == "radio-hd189733-window-geometry-study-v1"
          and design.get("status") == "PROSPECTIVE_IDENTITIES_ONLY_NOT_AN_EXECUTABLE_PROTOCOL"
          and design.get("primary") == "neighbor9", "Wrong prospective window study")
    for flag in ("spectral_access_authorized", "physical_bank_qualified", "new_control_panel_executed"):
        _need(design.get(flag) is False, "Window study cannot authorize work")
    windows = design["windows"]
    _need(type(windows) is list and len(windows) == 3 and tuple(w["role"] for w in windows) == ROLES,
          "Exactly three ordered roles required")
    flat, records = set(), []
    blocks = [[i, i + 4096] for i in range(0, 65536, 4096)]
    for window in windows:
        _need(window.get("identity") == legacy_digest({k: v for k, v in window.items() if k != "identity"}), "Window identity mismatch")
        _need(window["source_contract_sha256"] == source_sha and _same(window["native_channel_count"], 65536)
              and _same(window["normalization_blocks_native_channels"], blocks)
              and window.get("spectral_values_included") is False and window.get("spectral_access_authorized") is False,
              "Window provenance or normalization changed")
        a, z = window["archive_interval"]
        k = window["archive_chunk_index"]
        _need(all(type(v) is int for v in (a, z, k)) and 0 <= a < z and z - a == 65536,
              "Invalid fixed window interval")
        payloads = window["payload_keys"]
        _need(len(payloads) == 6 and window["payload_keys_sha256"] == legacy_digest(payloads), "Incomplete or changed payload identities")
        for scan, payload in zip(source["scans"], payloads):
            h = scan["expected_header"]
            chunk = scan["expected_chunks"][2]
            expected = {"source_url": scan["url"], "source_size_bytes": scan["expected_remote_size_bytes"],
                        "etag": scan["expected_etag"], "chunk_coordinates_time_feed_frequency": [[i, 0, k] for i in range(16)]}
            _need(z <= h["dataset_shape"][2] and a // chunk == k == (z - 1) // chunk and _same(payload, expected),
                  "Window native chunk/header identity changed")
            low = (h["fch1_mhz"] + (z - 1) * h["foff_mhz"]) * 1e6
            high = (h["fch1_mhz"] + a * h["foff_mhz"]) * 1e6
            center = (h["fch1_mhz"] + ((a + z) // 2) * h["foff_mhz"]) * 1e6
            _need(_same((window["native_frequency_low_hz"], window["native_frequency_high_hz"],
                        window["proposed_first_on_midpoint_carrier_center_hz"]), (low, high, center)), "Frequency convention changed")
            for row in range(16):
                key = (scan["url"], scan["expected_etag"], row, 0, k)
                _need(key not in flat, "Role windows share native chunk identity")
                flat.add(key)
        records.append({"role": window["role"], "window_identity": window["identity"],
                        "payload_keys_sha256": window["payload_keys_sha256"], "archive_interval": [a, z],
                        "archive_chunk_index": k, "native_channel_count": 65536, "normalization_block_count": 16})
    _need(len(flat) == 288, "Exact 288 distinct role/scan/row identities required")
    _need(bound.get("schema") == "radio-hd189733-window-identities-v2"
          and bound.get("source_contract_sha256") == source_sha and bound.get("window_design_sha256") == design_sha
          and bound.get("source_inventory_sha256") == SOURCE_INVENTORY and _same(bound.get("windows"), records)
          and _same(bound.get("roles"), list(ROLES)) and _same(bound.get("distinct_native_chunk_identities"), 288)
          and _same(bound.get("normalization_blocks"), 48) and _same(bound.get("decoded_payload_groups"), 18)
          and bound.get("roles_are_independent_observations") is False
          and bound.get("spectral_access_authorized") is False and bound.get("threshold_transfer_authorized") is False
          and bound.get("contract_sha256") == legacy_digest({k: v for k, v in bound.items() if k != "contract_sha256"}),
          "Original window contract ancestry differs")
    return records


def _bank_semantics(banks, design, bound, source_sha, design_sha, clock_pairs):
    _need(type(banks) is list and len(banks) == 3, "Three historical bank records required")
    result = []
    formula = "F=1+(rate_tenths/10)*t/center; f=q*F; actual slope=q*(rate_tenths/10)/center"
    for bank, window in zip(banks, design["windows"]):
        p = bank["provenance"]
        _need(bank.get("schema") == "radio-hd189733-received-linear-bank-v1"
              and _same(bank.get("shape"), [81, 96, 3]) and bank.get("encoding") == "C-order little-endian float64"
              and _same(bank.get("axes"), ["rate-tenths-index", "scan-major integration", "start-midpoint-end"])
              and bank.get("spectral_access_authorized") is False and bank.get("scientific_recovery_qualified") is False
              and bank.get("planetary_or_observer_ephemeris_coverage_claimed") is False, "Bank schema or qualification changed")
        expected = {"source_contract_sha256": source_sha, "window_design_sha256": design_sha,
                    "window_binding_sha256": bound["contract_sha256"], "window_identity": window["identity"],
                    "role": window["role"], "center_hz": window["proposed_first_on_midpoint_carrier_center_hz"],
                    "clock_rationals_sha256": digest(clock_pairs), "rate_tenths": list(RATES), "widths": list(WIDTHS),
                    "primary": "neighbor9", "frame": "recorded-topocentric", "formula": formula,
                    "observer_ephemeris_used": False, "orbital_factor_type": False, "score_half_bins": 40, "support_guard_bins": 9}
        _need(_same(p, expected), "Bank source/clock/rate/width semantics changed")
        _sha(bank["factor_sha256"])
        _need(bank["bank_identity"] == digest({k: v for k, v in bank.items() if k != "bank_identity"}), "Historical bank identity mismatch")
        result.append({"role": window["role"], "historical_bank_identity": bank["bank_identity"],
                       "historical_factor_sha256": bank["factor_sha256"], "factor_bytes_recomputed": False})
    return result


def _proposal_semantics(proposal, source_sha):
    _need(proposal.get("schema") == "radio-whole-cadence-null-proposal-config-v1"
          and proposal.get("status") == "PROPOSED_NOT_ACTIVATED" and proposal.get("primary") == "neighbor9",
          "Wrong inactive scientific proposal")
    for flag in ("detector_certificate_issued", "new_values_generated", "new_budget_charged", "telescope_access_authorized",
                 "old_attempt_or_identity_reuse_authorized", "score_shift_resampling"):
        _need(proposal.get(flag) is False, "Proposal cannot activate or claim executed science")
    rank = {"ceiling_denominator": 100, "ceiling_numerator": 1, "denominator": 128, "floor_snr": 10,
            "higher_quantile_denominator": 1, "higher_quantile_numerator": 1,
            "inclusive_numerator": "1 + count(reference >= observed member)", "keep_every_empty": True,
            "reference_count": 127, "ties_randomized": False}
    _need(canonical(proposal["rank_rule"]) == canonical(rank), "127-reference inclusive rank/EMPTY semantics changed")
    score = proposal["score_bank"]
    _need(_same(score["rate_labels_hz_s"], [x / 10 for x in RATES]) and _same(score["widths_channels"], list(WIDTHS))
          and _same(score["activity_subsets"], [[0, 1], [0, 2], [1, 2], [0, 1, 2]])
          and _same(score["minimum_active_epoch_snr"], 3) and score["stack_statistic"] == "sum", "Scientific searched scope expanded")
    cases = proposal["cases"]
    _need(len(cases) == 151 and len({case["identity"] for case in cases}) == 151,
          "Complete retained 127/24 proposal identity inventory required")
    _need(_same([case["role"] for case in cases], ["calibration"] * 127 + ["evaluation"] * 24),
          "Reference/evaluation ordering changed")
    for case in cases:
        _need(case["source_contract_sha256"] == source_sha and case.get("executed") is False
              and case.get("budget_charged") is False and case.get("proposed_only") is True
              and case.get("outcomes_may_select_settings") is False, "Proposal identity is spent, executed or substituted")
    evaluation = [case["recipe"]["kind"] for case in cases[127:]]
    _need({kind: evaluation.count(kind) for kind in set(evaluation)} ==
          {"on_signal": 10, "matched_on_off": 10, "single_adjacent_off": 2, "noise_null": 2}, "Fixed 24 evaluation recipes changed")
    return {"reference_count": 127, "evaluation_count": 24, "rank_rule": rank,
            "ordered_reference_identities_sha256": digest([c["identity"] for c in cases[:127]]),
            "ordered_evaluation_identities_sha256": digest([c["identity"] for c in cases[127:]]),
            "historical_proposal_only": True, "scientific_certificate_issued": False}


def _observe(raw_files, pins, expected_inventory, checkpoint):
    _need(checkpoint == CHECKPOINT, "Unreviewed evidence checkpoint")
    docs = _authenticate(raw_files, pins)
    source, design, bound = docs[SOURCE], docs[GEOMETRY], docs[WINDOWS]
    source_sha, design_sha = pins[SOURCE]["sha256"], pins[GEOMETRY]["sha256"]
    clock_pairs = _scan_semantics(source, docs[HEADERS], docs[QUALIFICATION], expected_inventory)
    windows = _window_semantics(source, design, bound, source_sha, design_sha)
    banks = _bank_semantics(docs[BANKS], design, bound, source_sha, design_sha, clock_pairs)
    scientific = _proposal_semantics(docs[PROPOSAL], source_sha)
    return docs, {"source_inventory_sha256": expected_inventory, "scan_count": 6, "role_windows": windows,
                  "distinct_native_chunk_identities": 288, "header_clock_rationals": clock_pairs,
                  "header_clock_rationals_sha256": digest(clock_pairs), "historical_banks": banks,
                  "scientific_proposal": scientific, "score_span_hz": 80 * abs(source["scans"][0]["expected_header"]["foff_mhz"]) * 1e6,
                  "rate_tenths": list(RATES), "widths_channels": list(WIDTHS), "primary": "neighbor9",
                  "recorded_frame": "recorded-topocentric", "roles_are_independent_observations": False}


def _prospective_fields(docs, pins, observed):
    source = docs[SOURCE]
    return {"artifact_type": "radio-source-contract-v1", "stage": "prospective-not-executable-no-spectral-access",
            "archive_target": source["archive_target"], "cadence_id": source["cadence_id"],
            "source_inventory_sha256": observed["source_inventory_sha256"], "scans": source["scans"],
            "windows": [{"name": w["name"], "archive_interval": w["archive_interval"], "role": w["role"]}
                        for w in docs[GEOMETRY]["windows"]],
            "pinned_files": {path: pins[path]["sha256"] for path in sorted(REQUIRED_PATHS)},
            "implementation_paths": list(IMPLEMENTATION_PATHS), "hdf5_runtime": None,
            "acquisition_policy": "radio-irrevocable-session-reservations-v1",
            "session_limits": source["session_limits"], "session_limits_are_inactive_historical_declaration": True,
            "cumulative_limits": None, "reservation_store": None,
            "scientific_certificate": None, "joined_transport_certificate": None, "trial_protocol": None,
            "gates": {name: {"status": "pending-new-source-admission", "source_inventory_sha256": SOURCE_INVENTORY}
                      for name in ("pointing", "prospective_protocol", "codec_integration")}}


def build_prospective_source_contract(raw_files, expected_file_pins, *, expected_source_inventory_sha256,
                                    evidence_checkpoint=CHECKPOINT, intended_code_runtime_binding=None,
                                    scientific_certificate_pin=None, joined_transport_certificate_pin=None,
                                    reservation_store=None, cumulative_limits=None, trial_protocol_pin=None):
    """Return three canonical byte documents; every output is permanently blocked.

    Future authority inputs are deliberately rejected, rather than copied into a
    supposed certificate. Runtime/certificate/allocation admission is a later API.
    """
    _need(all(value is None for value in (intended_code_runtime_binding, scientific_certificate_pin,
          joined_transport_certificate_pin, reservation_store, cumulative_limits, trial_protocol_pin)),
          "Future runtime/certificate/allocation authority cannot be supplied to this candidate")
    docs, observed = _observe(raw_files, expected_file_pins, expected_source_inventory_sha256, evidence_checkpoint)
    fields = _prospective_fields(docs, expected_file_pins, observed)
    common = {"status": STATUS, "authority": _authority(), "workload_counters": _counters(), "stop_date": "2026-10-09"}
    wrapper = {**common, "schema": "radio-prospective-source-metadata-wrapper-v1",
               "artifact_type": "radio-prospective-source-metadata-wrapper-v1", "evidence_checkpoint": evidence_checkpoint,
               "prospective_source_fields": fields, "prospective_source_fields_sha256": digest(fields),
               "missing_required_fields": list(MISSING_FIELDS), "loadable_source_contract_issued": False}
    rebinding = {**common, "schema": "radio-prospective-source-provenance-rebinding-v1",
                 "old_source_contract_file_pin": expected_file_pins[SOURCE],
                 "old_window_design_file_pin": expected_file_pins[GEOMETRY],
                 "old_window_contract_file_pin": expected_file_pins[WINDOWS],
                 "old_bank_records_file_pin": expected_file_pins[BANKS],
                 "new_executable_source_contract_sha256": None,
                 "prospective_source_fields_sha256": digest(fields), "observed_semantics": observed,
                 "binding_target": "prospective-fields-only-not-executable-contract",
                 "executable_provenance_rebinding_admitted": False}
    matrix = {**common, "schema": "radio-new-source-admission-matrix-v1", "evidence_checkpoint": evidence_checkpoint,
              "externally_supplied_raw_file_pins": expected_file_pins, "observed_semantics": observed,
              "prospective_wrapper_sha256": digest(wrapper), "provenance_rebinding_sha256": digest(rebinding),
              "requirements": [{"field": field, "status": "missing-not-admitted"} for field in MISSING_FIELDS],
              "old_implementation_pin_drift": [path for path in IMPLEMENTATION_PATHS
                  if docs[SOURCE]["pinned_files"].get(path) != expected_file_pins[path]["sha256"]],
              "certificate_or_transport_join_performed": False}
    outputs = {name: canonical(value) for name, value in zip(OUTPUT_KEYS, (wrapper, matrix, rebinding))}
    _need(all(len(raw) <= MAX_OUTPUT_BYTES for raw in outputs.values()), "Prospective metadata output budget exceeded")
    return outputs


def validate_prospective_source_metadata(outputs, expected_output_pins, raw_files, expected_file_pins, *,
                                         expected_source_inventory_sha256, evidence_checkpoint=CHECKPOINT):
    """Independently authenticate and check output semantics without the builder.

    A valid result means bounded blocked metadata agrees with supplied evidence;
    it grants no extraction, certificate, runtime, allocation or execution gate.
    """
    _need(type(outputs) is dict and type(expected_output_pins) is dict
          and set(outputs) == set(expected_output_pins) == set(OUTPUT_KEYS), "Exact separate output inventory required")
    docs, observed = _observe(raw_files, expected_file_pins, expected_source_inventory_sha256, evidence_checkpoint)
    parsed = {}
    for name in OUTPUT_KEYS:
        raw, pin = outputs[name], expected_output_pins[name]
        _need(type(raw) is bytes and 0 < len(raw) <= MAX_OUTPUT_BYTES and type(pin) is dict
              and set(pin) == {"bytes", "sha256"} and type(pin["bytes"]) is int and pin["bytes"] == len(raw)
              and hashlib.sha256(raw).hexdigest() == _sha(pin["sha256"]), "Output differs from independent retained pin")
        value = _json(raw)
        _need(type(value) is dict, "Separate output JSON object required")
        _need(canonical(value) == raw, "Output must be canonical, duplicate-free JSON")
        _need(value.get("status") == STATUS and canonical(value.get("authority")) == canonical(_authority())
              and canonical(value.get("workload_counters")) == canonical(_counters()) and value.get("stop_date") == "2026-10-09",
              "Output cannot promote authority, workloads or deadline")
        parsed[name] = value
    wrapper, matrix, rebinding = (parsed[name] for name in OUTPUT_KEYS)
    _need(wrapper.get("schema") == "radio-prospective-source-metadata-wrapper-v1"
          and wrapper.get("artifact_type") == "radio-prospective-source-metadata-wrapper-v1"
          and wrapper.get("evidence_checkpoint") == evidence_checkpoint
          and wrapper.get("loadable_source_contract_issued") is False
          and _same(wrapper.get("missing_required_fields"), list(MISSING_FIELDS)), "Wrapper is not permanently blocked")
    fields = wrapper["prospective_source_fields"]
    # This reconstruction reads authenticated inputs; it never calls the builder.
    _need(_same(fields, _prospective_fields(docs, expected_file_pins, observed))
          and wrapper["prospective_source_fields_sha256"] == digest(fields), "Prospective source fields differ from retained source")
    _need(matrix.get("schema") == "radio-new-source-admission-matrix-v1"
          and matrix.get("evidence_checkpoint") == evidence_checkpoint
          and _same(matrix.get("externally_supplied_raw_file_pins"), expected_file_pins)
          and _same(matrix.get("observed_semantics"), observed)
          and matrix.get("prospective_wrapper_sha256") == digest(wrapper)
          and matrix.get("provenance_rebinding_sha256") == digest(rebinding)
          and _same(matrix.get("requirements"), [{"field": field, "status": "missing-not-admitted"} for field in MISSING_FIELDS])
          and _same(matrix.get("old_implementation_pin_drift"), [path for path in IMPLEMENTATION_PATHS
              if docs[SOURCE]["pinned_files"].get(path) != expected_file_pins[path]["sha256"]])
          and matrix.get("certificate_or_transport_join_performed") is False, "Admission matrix closure or blocked requirements differ")
    _need(rebinding.get("schema") == "radio-prospective-source-provenance-rebinding-v1"
          and all(_same(rebinding.get(field), expected_file_pins[path]) for field, path in
                  (("old_source_contract_file_pin", SOURCE), ("old_window_design_file_pin", GEOMETRY),
                   ("old_window_contract_file_pin", WINDOWS), ("old_bank_records_file_pin", BANKS)))
          and _same(rebinding.get("observed_semantics"), observed)
          and rebinding.get("new_executable_source_contract_sha256") is None
          and rebinding.get("prospective_source_fields_sha256") == digest(fields)
          and rebinding.get("binding_target") == "prospective-fields-only-not-executable-contract"
          and rebinding.get("executable_provenance_rebinding_admitted") is False, "Provenance ancestry/rebinding boundary differs")
    expected_keys = {
        "prospective_wrapper": {"status", "authority", "workload_counters", "stop_date", "schema", "artifact_type",
            "evidence_checkpoint", "prospective_source_fields", "prospective_source_fields_sha256", "missing_required_fields", "loadable_source_contract_issued"},
        "admission_matrix": {"status", "authority", "workload_counters", "stop_date", "schema", "evidence_checkpoint",
            "externally_supplied_raw_file_pins", "observed_semantics", "prospective_wrapper_sha256", "provenance_rebinding_sha256",
            "requirements", "old_implementation_pin_drift", "certificate_or_transport_join_performed"},
        "provenance_rebinding": {"status", "authority", "workload_counters", "stop_date", "schema", "old_source_contract_file_pin",
            "old_window_design_file_pin", "old_window_contract_file_pin", "old_bank_records_file_pin", "new_executable_source_contract_sha256",
            "prospective_source_fields_sha256", "observed_semantics", "binding_target", "executable_provenance_rebinding_admitted"},
    }
    _need(all(set(parsed[name]) == expected_keys[name] for name in OUTPUT_KEYS), "Unknown output fields cannot carry authority")
    return {"schema": "radio-prospective-source-metadata-validation-v1", "status": "VERIFIED_BLOCKED_METADATA_ONLY",
            "source_inventory_sha256": expected_source_inventory_sha256, "authenticated_input_count": len(REQUIRED_PATHS),
            "distinct_native_chunk_identities": 288, "header_clock_rationals_sha256": observed["header_clock_rationals_sha256"],
            "authority": _authority(), "workload_counters": _counters(), "stop_date": "2026-10-09",
            "independent_of_builder_invocation": True, "executable_contract_or_certificate_issued": False}
