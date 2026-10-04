"""Prospective receiver-coordinate source admission, without acquisition or scoring.

All arguments are already retained raw bytes and independent publication pins.
The production entry point verifies the complete detached scientific closure and
the current irrevocable store/session proof before invoking any row loader.  It
does not import the legacy FactorBasis constructor, read files, normalize rows,
open HDF5, contact a host, allocate a trial or execute a native detector.

``qualify_synthetic_fixture`` is a separate interface qualification. Its short
in-memory rows have their own independent pins, cannot impersonate the physical
receipt's native geometry, and confer no telescope/scientific authority.
"""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import re
import struct
from urllib.parse import urlparse

SCHEMA = "radio-receiver-telescope-adapter-prospective-v1"
LABELS = tuple(f"epoch{e}_{kind}" for e in (1, 2, 3) for kind in ("on", "off"))
ROLES = ("calibration", "validation", "pilot")
METADATA_KEYS = ("source_metadata", "window_design", "window_contract", "receiver_bank_records")
CHANNELS = 65536
ROWS = 16
NORMALIZATION = "ascending new-extraction origin; float32 median/MAD; blocks 4096"
MAX_METADATA_BYTES = 2 * 1024**2
MAX_RECEIPT_BYTES = 128 * 1024
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class AdmissionError(ValueError):
    """Closed admission failure; no callback is attempted before all gates pass."""


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def _same(left, right):
    """JSON type equality also distinguishes boolean and numeric impostors."""
    return canonical(left) == canonical(right)


def _need(condition, reason):
    if not condition:
        raise AdmissionError(reason)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _pin(raw, expected, name, cap=MAX_METADATA_BYTES):
    _need(type(raw) is bytes and 0 < len(raw) <= cap, name + " raw metadata bound")
    _need(type(expected) is dict and set(expected) == {"bytes", "sha256"}, name + " independent pin missing")
    _need(type(expected["bytes"]) is int and expected["bytes"] == len(raw)
          and type(expected["sha256"]) is str and _HEX.fullmatch(expected["sha256"])
          and sha(raw) == expected["sha256"], name + " differs from independent raw pin")
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(AdmissionError("nonfinite JSON number")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AdmissionError(name + " is not UTF-8 JSON") from exc


def _sealed(record, key, reason):
    _need(type(record) is dict and record.get(key) == digest({k: v for k, v in record.items() if k != key}), reason)


def _float_bytes(values):
    return b"".join(struct.pack("<d", v) for v in values)


def _clock(scans):
    first = scans[0]["expected_header"]
    origin = Fraction(first["tstart_mjd"])
    anchor = Fraction(first["tsamp_s"]) / 2
    result = []
    for scan in scans:
        h = scan["expected_header"]
        dt = Fraction(h["tsamp_s"])
        start = (Fraction(h["tstart_mjd"]) - origin) * 86400 - anchor
        result.extend(tuple(start + (Fraction(i) + offset) * dt
                            for offset in (Fraction(0), Fraction(1, 2), Fraction(1)))
                      for i in range(ROWS))
    _need(result[0][1] == 0 and all(a[2] <= b[0] for a, b in zip(result, result[1:])), "source clocks overlap")
    return result


def _source(scans, source):
    _need(type(scans) is list and len(scans) == 6 and tuple(s.get("label") for s in scans) == LABELS,
          "exact alternating six-source inventory required")
    _need(source.get("artifact_type") == "radio-source-contract-v1"
          and source.get("cadence_id") == 85030 and type(source["cadence_id"]) is int
          and source.get("archive_target") == "HIP98505"
          and source.get("stage") == "preparation-only-no-spectral-access"
          and source.get("windows") == [] and source.get("hdf5_runtime") is None,
          "preserved source preparation was rewritten")
    _need(source.get("source_inventory_sha256") == digest(scans), "source inventory identity differs")
    geometries = []
    for i, scan in enumerate(scans):
        h = scan["expected_header"]
        parsed = urlparse(scan["url"])
        _need(scan.get("role") == ("on" if i % 2 == 0 else "off")
              and h.get("source_name") == ("HIP98505" if i % 2 == 0 else "HIP98505_OFF"),
              "paired ON/OFF roles differ")
        _need(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
              and not parsed.fragment and not parsed.query
              and type(scan["expected_remote_size_bytes"]) is int and scan["expected_remote_size_bytes"] > 0
              and type(scan["expected_etag"]) is str and scan["expected_etag"].startswith('"')
              and scan["expected_etag"].endswith('"'), "invalid remote identity metadata")
        _need(h["dataset_shape"] == [16, 1, 264503296] and all(type(n) is int for n in h["dataset_shape"])
              and h["dataset_dtype"] == "float32" and _same(scan["expected_chunks"], [1, 1, 1048576]),
              "receiver source geometry changed")
        filters = scan.get("observed_hdf5_filters")
        _need(type(filters) is list and len(filters) == 1 and type(filters[0]) is list and len(filters[0]) == 4
              and _same(filters[0][:3], [32008, 1, [0, 3, 4, 0, 2]]) and type(filters[0][3]) is str,
              "preserved source codec declaration differs")
        numbers = [h[k] for k in ("tstart_mjd", "tsamp_s", "fch1_mhz", "foff_mhz", "src_raj_hours", "src_dej_deg")]
        _need(all(type(n) in (int, float) and math.isfinite(n) for n in numbers)
              and h["tsamp_s"] > 0 and h["foff_mhz"] < 0, "invalid finite source clock/frequency")
        geometries.append((h["dataset_shape"], h["dataset_dtype"], h["tsamp_s"], h["fch1_mhz"], h["foff_mhz"]))
    _need(len({s["url"] for s in scans}) == 6 and all(g == geometries[0] for g in geometries),
          "cadence remote identities or geometry differ")


def validate_receiver_metadata(raw_metadata, expected_metadata_pins, *, expected_basis, role):
    """Reproduce literal receiver metadata identities; no source values are used."""
    _need(role in ROLES and set(raw_metadata) == set(METADATA_KEYS)
          and set(expected_metadata_pins) == set(METADATA_KEYS), "exact receiver metadata domain required")
    docs = {name: _pin(raw_metadata[name], expected_metadata_pins[name], name) for name in METADATA_KEYS}
    source, design, bound, banks = (docs[name] for name in METADATA_KEYS)
    pin_fields = ("source_metadata_sha256", "window_design_sha256", "window_contract_sha256", "receiver_bank_records_sha256")
    _need(all(expected_basis.get(field) == expected_metadata_pins[name]["sha256"]
              for field, name in zip(pin_fields, METADATA_KEYS)), "receiver metadata differs from independently frozen basis")
    scans = source["scans"]
    _source(scans, source)
    _need(expected_basis.get("source_inventory_sha256") == source["source_inventory_sha256"], "basis source inventory differs")
    _need(design.get("schema") == "radio-hd189733-window-geometry-study-v1"
          and design.get("status") == "PROSPECTIVE_IDENTITIES_ONLY_NOT_AN_EXECUTABLE_PROTOCOL"
          and design.get("primary") == "neighbor9"
          and all(design.get(k) is False for k in ("spectral_access_authorized", "physical_bank_qualified", "new_control_panel_executed",
              "calibration_numeric_transfer_qualified", "development_identity_allocated", "new_control_panel_identities_frozen", "legacy_v1_modified"))
          and type(design.get("normalization_block_count")) is int and design["normalization_block_count"] == 48
          and type(design.get("payload_identity_count")) is int and design["payload_identity_count"] == 18,
          "retained window metadata asserts unauthorized science")
    _need(type(design.get("windows")) is list and tuple(w["role"] for w in design["windows"]) == ROLES,
          "role windows reordered")
    _sealed(bound, "contract_sha256", "window contract identity differs")
    _need(bound.get("schema") == "radio-hd189733-window-identities-v2"
          and bound.get("source_contract_sha256") == expected_metadata_pins["source_metadata"]["sha256"]
          and bound.get("window_design_sha256") == expected_metadata_pins["window_design"]["sha256"]
          and bound.get("source_inventory_sha256") == source["source_inventory_sha256"]
          and bound.get("spectral_access_authorized") is False and bound.get("threshold_transfer_authorized") is False,
          "window contract ancestry or authority differs")
    _need(type(banks) is list and len(banks) == 3, "exact three receiver bank records required")
    rows = _clock(scans)
    clock_hash = sha(json.dumps([[[q.numerator, q.denominator] for q in row] for row in rows],
                               sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    records = []
    flat = set()
    selected = None
    for window, bank in zip(design["windows"], banks):
        _sealed(window, "identity", "window identity differs")
        current_role = window["role"]
        _need(window.get("name") == "hd189733_" + current_role + "_geometry", "source window name differs from receiver role")
        a, z = window["archive_interval"]
        k = window["archive_chunk_index"]
        _need(all(type(n) is int for n in (a, z, k)) and a >= 0 and z - a == CHANNELS
              and window["native_channel_count"] == CHANNELS
              and window["source_contract_sha256"] == expected_metadata_pins["source_metadata"]["sha256"]
              and _same(window["normalization_blocks_native_channels"], [[j, j + 4096] for j in range(0, CHANNELS, 4096)])
              and window.get("spectral_values_included") is False and window.get("spectral_access_authorized") is False,
              "receiver extraction/normalization boundary differs")
        _need(len(window["payload_keys"]) == 6 and window["payload_keys_sha256"] == digest(window["payload_keys"]),
              "receiver payload identity inventory differs")
        for scan, payload in zip(scans, window["payload_keys"]):
            h = scan["expected_header"]
            chunk = scan["expected_chunks"][2]
            _need(a // chunk == k == (z - 1) // chunk and z <= h["dataset_shape"][2], "window crosses source chunk")
            _need(_same(payload, {"source_url": scan["url"], "source_size_bytes": scan["expected_remote_size_bytes"],
                                 "etag": scan["expected_etag"], "chunk_coordinates_time_feed_frequency": [[j, 0, k] for j in range(16)]}),
                  "physical payload source identity differs")
            low = (h["fch1_mhz"] + (z - 1) * h["foff_mhz"]) * 1e6
            high = (h["fch1_mhz"] + a * h["foff_mhz"]) * 1e6
            center = (h["fch1_mhz"] + ((a + z) // 2) * h["foff_mhz"]) * 1e6
            _need((low, high, center) == (window["native_frequency_low_hz"], window["native_frequency_high_hz"],
                                         window["proposed_first_on_midpoint_carrier_center_hz"]), "native frequency affine geometry differs")
            for j in range(ROWS):
                identity = (scan["url"], scan["expected_etag"], j, 0, k)
                _need(identity not in flat, "role windows share native chunk identity")
                flat.add(identity)
        records.append({"role": current_role, "window_identity": window["identity"],
                        "payload_keys_sha256": window["payload_keys_sha256"], "archive_interval": [a, z],
                        "archive_chunk_index": k, "native_channel_count": CHANNELS, "normalization_block_count": 16})
        p = bank["provenance"]
        center = window["proposed_first_on_midpoint_carrier_center_hz"]
        expected_provenance = {"source_contract_sha256": expected_metadata_pins["source_metadata"]["sha256"],
            "window_design_sha256": expected_metadata_pins["window_design"]["sha256"], "window_binding_sha256": bound["contract_sha256"],
            "window_identity": window["identity"], "role": current_role, "center_hz": center, "clock_rationals_sha256": clock_hash,
            "rate_tenths": list(range(-40, 41)), "widths": [1, 3, 5, 9, 17, 33, 65, 129], "primary": "neighbor9",
            "frame": "recorded-topocentric", "formula": "F=1+(rate_tenths/10)*t/center; f=q*F; actual slope=q*(rate_tenths/10)/center",
            "observer_ephemeris_used": False, "orbital_factor_type": False, "score_half_bins": 40, "support_guard_bins": 9}
        _need(_same(p, expected_provenance), "receiver bank provenance differs; FactorBasis is not accepted")
        values = [1 + (rate / 10) * float(t) / center for rate in range(-40, 41) for row in rows for t in row]
        _need(all(math.isfinite(v) and 0 < v < 2 for v in values)
              and all(values[rate_index * 96 * 3 + 1] == 1 for rate_index in range(81)),
              "receiver factor finite/range/midpoint law differs")
        _need(bank.get("schema") == "radio-hd189733-received-linear-bank-v1" and _same(bank.get("shape"), [81, 96, 3])
              and bank.get("factor_sha256") == sha(_float_bytes(values))
              and bank.get("encoding") == "C-order little-endian float64"
              and bank.get("axes") == ["rate-tenths-index", "scan-major integration", "start-midpoint-end"]
              and all(bank.get(flag) is False for flag in ("spectral_access_authorized", "scientific_recovery_qualified", "planetary_or_observer_ephemeris_coverage_claimed")),
              "receiver literal factor record differs")
        # ReceiverBank uses compact JSON without LF; downstream contracts use LF.
        expected_bank_identity = sha(json.dumps({key: value for key, value in bank.items() if key != "bank_identity"},
                                                sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        _need(bank["bank_identity"] == expected_bank_identity
              and expected_basis["window_identities"][current_role] == window["identity"]
              and expected_basis["receiver_bank_sha256s"][current_role] == bank["bank_identity"], "basis receiver bank/window identity differs")
        if current_role == role:
            selected = (window, bank, values)
    expected_bound = {"schema": "radio-hd189733-window-identities-v2",
        "source_contract_sha256": expected_metadata_pins["source_metadata"]["sha256"],
        "window_design_sha256": expected_metadata_pins["window_design"]["sha256"],
        "source_inventory_sha256": source["source_inventory_sha256"], "primary": "neighbor9", "windows": records,
        "roles": list(ROLES), "decoded_payload_groups": 18, "distinct_native_chunk_identities": 288,
        "normalization_blocks": 48, "roles_are_independent_observations": False,
        "spectral_access_authorized": False, "threshold_transfer_authorized": False,
        "status": "IDENTITIES_BOUND_SCIENTIFIC_AND_EXECUTION_GATES_PENDING",
        "remaining_requirements": ["qualified source-specific motion/width bank",
            "source codec/runtime evidence and live receipt handoff",
            "fresh disjoint development/calibration/evaluation identity freeze",
            "numeric cross-window transfer and recovery/RFI/null evaluation",
            "integrated prospective protocol and cumulative acquisition/trial ledger"]}
    _need(len(flat) == 288 and _same(bound, {**expected_bound, "contract_sha256": digest(expected_bound)}),
          "complete 288-chunk identity contract differs")
    window, bank, values = selected
    return _context(source, window, bank, values)


def _context(source, window, bank, values):
    scans = [{**s, "kind": s["role"], "epoch": i // 2 + 1} for i, s in enumerate(source["scans"])]
    scan_inventory = digest([{"scan_index": i, "epoch": i // 2 + 1, "scan_kind": s["role"], "scan_label": s["label"],
                              "integration_count": ROWS, "factor_row_start": i * ROWS, "factor_row_stop": (i + 1) * ROWS}
                             for i, s in enumerate(scans)])
    catalogue = [{"schema": "radio-received-linear-template-v1", "template_index": i, "line_index": i,
                  "line_coefficient": rate / 10, "rate_label_hz_s": rate / 10,
                  "rate_reference_hz": bank["provenance"]["center_hz"],
                  "actual_slope_formula": "q*rate_label_hz_s/rate_reference_hz", "receiver_bank_sha256": bank["bank_identity"],
                  "line_fields_are_retention_compatibility_metadata": True} for i, rate in enumerate(range(-40, 41))]
    labels = digest({"schema": "radio-receiver-midpoint-labels-v1", "receiver_bank_sha256": bank["bank_identity"],
                     "scan_labels": list(LABELS), "integrations_per_scan": ROWS, "sample": "midpoint"})
    factor_record = {"schema": "radio-receiver-downstream-factor-contract-v1", "receiver_bank_sha256": bank["bank_identity"],
        "labels_sha256": labels, "factor_table_sha256": sha(_float_bytes(values[1::3])),
        "template_bank_sha256": digest(catalogue), "scan_inventory_sha256": scan_inventory,
        "legacy_certificate_slot_mapping": {"factor_basis_sha256": "receiver_bank_sha256 (literal factors; no FactorBasis)",
                                             "factor_basis_labels_sha256": "receiver midpoint labels_sha256"},
        "orbital_fields_constructed": False, "telescope_access_authorized": False}
    center_mhz = window["proposed_first_on_midpoint_carrier_center_hz"] / 1e6
    df = abs(scans[0]["expected_header"]["foff_mhz"]) * 1e6
    support_hz = [center_mhz * 1e6 + j * df for j in range(-49, 50)]
    score_hz = support_hz[9:-9]
    grid_record = {"center_mhz": center_mhz, "channel_width_hz": df, "score_half_bins": 40, "support_guard_bins": 9,
        "support_hz_sha256": sha(_float_bytes(support_hz)), "score_hz_sha256": sha(_float_bytes(score_hz)),
        "support_mhz_sha256": sha(_float_bytes([v / 1e6 for v in support_hz])),
        "score_mhz_sha256": sha(_float_bytes([v / 1e6 for v in score_hz]))}
    context = {"schema": "radio-receiver-downstream-context-v1", "window": "hd189733_" + window["role"] + "_receiver_v1",
        "scans": scans, "receiver_factor_contract_sha256": digest(factor_record), "template_bank_sha256": digest(catalogue),
        "grid_sha256": digest(grid_record), "primary": "neighbor9", "maximum_records": 10000,
        "memory_limit_bytes": 256 * 1024**2, "telescope_constructor_available": False,
        "scientific_candidate_selection_authorized": False}
    return {"role": window["role"], "context_sha256": digest(context), "context": context,
            "factor_contract": factor_record, "receiver_bank_sha256": bank["bank_identity"],
            "window_identity": window["identity"], "source_window_name": window["name"], "archive_interval": window["archive_interval"],
            "source_inventory_sha256": source["source_inventory_sha256"],
            "geometry": {"raw_zero_hz": window["native_frequency_low_hz"], "channel_width_hz": df, "channel_count": CHANNELS}}


@dataclass(frozen=True)
class LoadRequest:
    label: str
    receipt_raw: bytes
    receipt_raw_sha256: str
    receipt_identity: str
    integration_count: int
    channel_count: int
    source_contract_sha256: str
    context_sha256: str
    receiver_bank_sha256: str


@dataclass(frozen=True)
class LoadedRows:
    """Loader result: unchanged physical receipt and immutable normalized bytes."""
    receipt_raw: bytes
    rows: tuple


@dataclass(frozen=True)
class ReceiverCadence:
    record_raw: bytes
    requests: tuple
    sources: tuple

    def record(self):
        return json.loads(self.record_raw)


def _receipts(raw_receipts, expected_receipt_pins, context, source_contract_sha256, runtime_identity):
    _need(set(raw_receipts) == set(LABELS) and set(expected_receipt_pins) == set(LABELS), "exact independently pinned six-receipt inventory required")
    requests = []
    decoded = []
    for scan in context["context"]["scans"]:
        label = scan["label"]
        raw = raw_receipts[label]
        receipt = _pin(raw, expected_receipt_pins[label], label + " source receipt", MAX_RECEIPT_BYTES)
        _sealed(receipt, "receipt_sha256", "source receipt identity differs")
        _need(set(receipt) == {"scope", "rows", "transport", "complete", "receipt_sha256"}, "physical source receipt schema differs")
        definition = {k: v for k, v in scan.items() if k not in ("kind", "epoch")}
        scope = {"version": "m43h-widened-source-v1", "kind": "telescope-remote", "contract_sha256": source_contract_sha256,
                 "definition": definition, "window": context["source_window_name"], "archive_interval": context["archive_interval"],
                 "geometry": context["geometry"], "normalization": NORMALIZATION,
                 "modelled_buffer_bound_bytes": 32 * CHANNELS + 92 * 1024**2}
        _need(_same(receipt.get("scope"), scope) and receipt.get("complete") is True
              and type(receipt.get("rows")) is list and len(receipt["rows"]) == ROWS, "physical source receipt scope/rows differ")
        for j, row in enumerate(receipt["rows"]):
            _sealed(row, "receipt_sha256", "physical row receipt identity differs")
            _need(set(row) == {"scope_sha256", "row", "native_sha256", "ascending_raw_sha256", "normalized_sha256",
                               "native_file_sha256", "normalized_file_sha256", "receipt_sha256"}
                  and type(row.get("row")) is int and row["row"] == j and row.get("scope_sha256") == digest(scope)
                  and all(type(row.get(k)) is str and _HEX.fullmatch(row[k]) for k in
                          ("native_sha256", "ascending_raw_sha256", "normalized_sha256", "native_file_sha256", "normalized_file_sha256")),
                  "physical row hashes/order differ")
        transport = receipt.get("transport")
        remote = {"url": scan["url"], "size": scan["expected_remote_size_bytes"], "etag": scan["expected_etag"]}
        _need(type(transport) is dict
              and set(transport) == {"kind", "identity", "range_plan_file_sha256", "checkpoint", "hdf5_runtime", "dataset_filters"}
              and transport.get("kind") == "live-identity-bound-http-ranges"
              and _same(transport.get("identity"), remote)
              and type(transport.get("range_plan_file_sha256")) is str and _HEX.fullmatch(transport["range_plan_file_sha256"])
              and _same(transport.get("hdf5_runtime"), {key: runtime_identity[key] for key in ("numpy", "h5py", "hdf5", "hdf5plugin")})
              and _same(transport.get("dataset_filters"), [[32008, 1, [0, 3, 4, 0, 2]]]),
              "source receipt lacks identity-bound physical transport")
        checkpoint = transport.get("checkpoint")
        _need(type(checkpoint) is dict
              and set(checkpoint) == {"artifact_type", "schema_version", "remote", "segments", "checkpoint_sha256"}
              and checkpoint.get("artifact_type") == "seti_repeater.m37_sparse_http_mirror"
              and type(checkpoint.get("schema_version")) is int and checkpoint["schema_version"] == 1
              and checkpoint.get("remote") == remote
              and checkpoint.get("checkpoint_sha256") == sha(json.dumps({k: v for k, v in checkpoint.items() if k != "checkpoint_sha256"},
                                                                         sort_keys=True, separators=(",", ":"), allow_nan=False).encode()),
              "physical transport checkpoint identity differs")
        segments = checkpoint["segments"]
        _need(type(segments) is list and 0 < len(segments) <= 500, "physical transport segment inventory incomplete")
        end = 0
        for segment in segments:
            _need(type(segment) is dict and set(segment) == {"start", "stop", "sha256"}
                  and type(segment["start"]) is int and type(segment["stop"]) is int
                  and end <= segment["start"] < segment["stop"] <= remote["size"]
                  and type(segment["sha256"]) is str and _HEX.fullmatch(segment["sha256"]),
                  "physical transport range identity/order differs")
            end = segment["stop"]
        requests.append(LoadRequest(label, raw, sha(raw), receipt["receipt_sha256"], ROWS, CHANNELS,
                                    source_contract_sha256, context["context_sha256"], context["receiver_bank_sha256"]))
        decoded.append(receipt)
    return tuple(requests), tuple(decoded)


def _gated_metadata(*, raw_documents, expected_raw_pins, expected_basis, expected_publication_chain,
                    expected_execution_inventory, expected_dependency_edges, expected_runtime_identity,
                    raw_metadata, expected_metadata_pins, role, raw_proof, expected_proof_pin,
                    raw_store_acknowledgement, expected_store_acknowledgement_pin,
                    raw_cas_qualification, expected_cas_qualification_pin,
                    raw_session_proof, expected_session_proof_pin, raw_receipts, expected_row_receipt_pins,
                    expected_current_session):
    # Fixed maintained validators, never an injected trust/authority callback.
    from scientific_admission import validate_scientific_closure
    from scientific_store import validate_current_admission
    closure = validate_scientific_closure(raw_documents, expected_raw_pins,
        expected_basis=expected_basis, expected_publication_chain=expected_publication_chain,
        expected_execution_inventory=expected_execution_inventory, expected_dependency_edges=expected_dependency_edges,
        expected_runtime_identity=expected_runtime_identity)
    context = validate_receiver_metadata(raw_metadata, expected_metadata_pins, expected_basis=expected_basis, role=role)
    basis_contexts = expected_basis.get("receiver_context_sha256s", {})
    closure_record = closure.record()
    _need(context["context_sha256"] == basis_contexts.get(role, closure_record.get("pilot_receiver_context_sha256")),
          "receiver context differs from complete scientific basis")
    admission = validate_current_admission(raw_proof, expected_proof_pin, verified_closure=closure,
        expected_basis=expected_basis, raw_store_acknowledgement=raw_store_acknowledgement,
        expected_store_acknowledgement_pin=expected_store_acknowledgement_pin,
        raw_cas_qualification=raw_cas_qualification, expected_cas_qualification_pin=expected_cas_qualification_pin,
        raw_session_proof=raw_session_proof, expected_session_proof_pin=expected_session_proof_pin,
        expected_row_receipt_pins=expected_row_receipt_pins, expected_current_session=expected_current_session)
    record = admission.record()
    _need(record.get("context_sha256") == context["context_sha256"]
          and record.get("receiver_bank_sha256") == context["receiver_bank_sha256"]
          and record.get("window_identity") == context["window_identity"]
          and record.get("role") == role, "current admitted receiver binding differs")
    requests, receipts = _receipts(raw_receipts, expected_row_receipt_pins, context,
                                  closure_record["new_executable_source_contract_sha256"], closure_record["runtime_identity"])
    return closure, admission, context, requests, receipts


class _LoadClock:
    """Per-attempt freshness checks against authenticated fixed time bounds.

    The independently supplied clock and loader require bounded outer runtime
    supervision. A synchronous Python callback cannot be interrupted here.
    """
    def __init__(self, clock, admission, raw_session, session_pin):
        _need(callable(clock), "independently supplied live clock required")
        authority = admission.record()
        session = _pin(raw_session, session_pin, "current source session")
        self.start = session["started_epoch_milliseconds"]
        self.anchor = authority["validated_current_epoch_milliseconds"]
        self.deadline = authority["session_deadline_epoch_milliseconds"]
        self.stop = authority["stop_epoch_milliseconds"]
        _need(all(type(value) is int for value in (self.start, self.anchor, self.deadline, self.stop))
              and self.start <= self.anchor < self.deadline <= self.stop
              and session["deadline_epoch_milliseconds"] == self.deadline,
              "authenticated current source clock bounds differ")
        self.clock = clock
        self.previous = None
        self.observations = []

    def observe(self, label, phase):
        now = self.clock()
        _need(type(now) is int, "live clock must return integer epoch milliseconds")
        _need(now >= self.anchor and (self.previous is None or now >= self.previous),
              "live clock regressed")
        _need(self.start <= now < self.deadline and now < self.stop,
              "source session or fixed consolidation deadline expired " + phase + " loader")
        self.previous = now
        self.observations.append({"scan": label, "phase": phase, "epoch_milliseconds": now})

    def load(self, row_loader, request):
        self.observe(request.label, "before")
        try:
            return row_loader(request)
        finally:
            # Runs on normal return and callback failure. A hung callback still
            # requires the outer qualified supervisor; no interruption is claimed.
            self.observe(request.label, "after")

    def record(self):
        return {"session_started_epoch_milliseconds": self.start,
                "validated_current_epoch_milliseconds": self.anchor,
                "session_deadline_epoch_milliseconds": self.deadline,
                "stop_epoch_milliseconds": self.stop,
                "nondecreasing_integer_observations": list(self.observations),
                "checked_before_and_after_every_loader_attempt": True,
                "time_source_assumption": "independently trusted current epoch-millisecond clock",
                "callback_interruption_guaranteed_here": False}


def from_telescope(*, row_loader, live_clock, **metadata):
    """Return receiver rows only after independently authenticated ACTIVE admission.

    This invokes no normalizer. The bounded loader must return already normalized
    row bytes that match the separately authenticated physical receipt. An empty,
    changed, wrong-kind, failed or expired loader is a closed error; no fallback
    occurs. The independently supplied live clock must return integer epoch
    milliseconds and never regress between successive observations. Equal
    millisecond values are permitted at this clock resolution. Freshness
    is checked before and after each attempt; callback interruption and resource
    limits require an independently qualified bounded outer supervisor.
    """
    closure, admission, context, requests, receipts = _gated_metadata(**metadata)
    authority = admission.record()
    _need(authority.get("status") == "ACTIVE" and authority.get("scientific_execution_authorized") is True
          and authority.get("domain") == "public-scientific-evidence",
          "current acquisition/trial/session admission remains blocked")
    _need(callable(row_loader), "bounded row loader required")
    clock = _LoadClock(live_clock, admission, metadata["raw_session_proof"], metadata["expected_session_proof_pin"])
    loaded = []
    for request, receipt in zip(requests, receipts):
        source = clock.load(row_loader, request)
        _need(type(source) is LoadedRows and type(source.receipt_raw) is bytes and source.receipt_raw == request.receipt_raw
              and type(source.rows) is tuple and len(source.rows) == ROWS, "loader source receipt/row inventory differs")
        for row, evidence in zip(source.rows, receipt["rows"]):
            _need(type(row) is bytes and len(row) == CHANNELS * 4 and sha(row) == evidence["normalized_sha256"],
                  "loader normalized row bytes differ from physical receipt")
            _need(all(math.isfinite(value[0]) for value in struct.iter_unpack("<f", row)), "loader normalized row is nonfinite")
        loaded.append(source)
    record = {"schema": SCHEMA, "source_domain": "telescope-remote", "status": "ADMITTED_ROWS_VERIFIED",
              "context_sha256": context["context_sha256"], "receiver_bank_sha256": context["receiver_bank_sha256"],
              "window_identity": context["window_identity"], "source_inventory_sha256": context["source_inventory_sha256"],
              "closure_sha256": sha(closure.payload), "admission_sha256": sha(admission.payload),
              "physical_receipt_raw_sha256s": {request.label: request.receipt_raw_sha256 for request in requests},
              "normalization_performed": False, "native_execution_performed": False,
              "scientific_candidate_selection_performed": False, "acquisition_performed": False,
              "fresh_dispatch_claimed_here": False, "host_runtime_observed_here": False,
              "row_loader_runtime_supervision_required": True, "current_admission_checked_before_loader": True,
              "per_load_live_clock": clock.record(),
              "telescope_values_opened": True}
    return ReceiverCadence(canonical(record), requests, tuple(loaded))


def qualify_synthetic_fixture(*, row_loader, fixture_row_pins, fixture_clock, **metadata):
    """Qualify the gated loader interface with independently pinned tiny rows.

    Physical receipt metadata remains byte-identical. Fixture rows have a
    disjoint domain/geometry and are not compared with physical payload hashes.
    This method cannot return an admitted telescope cadence.
    """
    closure, admission, context, requests, _ = _gated_metadata(**metadata)
    authority = admission.record()
    _need(authority.get("domain") == "synthetic-test-fixture" and authority.get("status") == "PENDING"
          and authority.get("scientific_execution_authorized") is False,
          "synthetic qualification requires explicitly simulated blocked authority")
    _need(callable(row_loader) and set(fixture_row_pins) == set(LABELS), "exact synthetic callback/pin inventory required")
    clock = _LoadClock(fixture_clock, admission, metadata["raw_session_proof"], metadata["expected_session_proof_pin"])
    for label in LABELS:
        pins = fixture_row_pins[label]
        _need(type(pins) is list and len(pins) == ROWS
              and all(type(p) is dict and set(p) == {"bytes", "sha256"}
                      and type(p["bytes"]) is int and 0 < p["bytes"] <= 4096 and p["bytes"] % 4 == 0
                      and type(p["sha256"]) is str and _HEX.fullmatch(p["sha256"]) for p in pins),
              "synthetic row pins invalid or oversized")
    loaded = []
    for request in requests:
        source = clock.load(row_loader, request)
        _need(type(source) is LoadedRows and type(source.receipt_raw) is bytes and source.receipt_raw == request.receipt_raw
              and type(source.rows) is tuple and len(source.rows) == ROWS, "synthetic loader physical receipt changed")
        for row, pin in zip(source.rows, fixture_row_pins[request.label]):
            _need(type(row) is bytes and len(row) == pin["bytes"] and sha(row) == pin["sha256"], "synthetic fixture row differs from independent pin")
            _need(all(math.isfinite(value[0]) for value in struct.iter_unpack("<f", row)), "synthetic fixture row is nonfinite")
        loaded.append(source)
    record = {"schema": SCHEMA, "source_domain": "synthetic-interface-fixture-only", "status": "SYNTHETIC_INTERFACE_QUALIFIED",
        "context_sha256": context["context_sha256"], "receiver_bank_sha256": context["receiver_bank_sha256"],
        "window_identity": context["window_identity"], "closure_sha256": sha(closure.payload),
        "admission_sha256": sha(admission.payload),
        "physical_receipt_metadata_raw_sha256s": {request.label: request.receipt_raw_sha256 for request in requests},
        "fixture_row_pins": fixture_row_pins, "physical_payload_hashes_qualified": False,
        "normalization_performed": False, "native_execution_performed": False,
        "scientific_execution_authorized": False, "spectral_access_authorized": False,
        "scientific_allocation_charged": False, "fresh_dispatch_claimed_here": False, "host_runtime_observed_here": False,
        "current_admission_checked_before_loader": True,
        "per_load_live_clock": clock.record(),
        "telescope_values_opened": False, "acquisition_performed": False}
    return ReceiverCadence(canonical(record), requests, tuple(loaded))
