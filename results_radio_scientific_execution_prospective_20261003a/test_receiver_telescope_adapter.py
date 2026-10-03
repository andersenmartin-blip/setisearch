"""Prospective adapter qualification: retained metadata, tiny injected rows only."""
import builtins
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import receiver_telescope_adapter as adapter

PATHS = {
    "source_metadata": "config/radio_hd189733_source_preparation_20260927.json",
    "window_design": "results_radio_hd189733_geometry_2026-09-27/window_geometry.json",
    "window_contract": "results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json",
    "receiver_bank_records": "results_radio_hd189733_receiver_2026-09-28/bank_records.json",
}
PINS = {
    "source_metadata": {"bytes": 9707, "sha256": "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"},
    "window_design": {"bytes": 35420, "sha256": "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"},
    "window_contract": {"bytes": 2453, "sha256": "0ffbadfacb9de8dd92d3d32b07e97b5c6fb16143483c225cb25bd60439ebe226"},
    "receiver_bank_records": {"bytes": 7871, "sha256": "51c1fde64957720e98adc7ecc63209d9b2e406b57dcd790829677a1ceb76b7c8"},
}
CONTEXTS = {
    "calibration": "8899f84c7e9721e79627a4ec7166b7c941127a50f6ed5cb2d771f2c8518feb13",
    "validation": "304e30cc6eab0f1f88a633021a115e3dd281e223d2549988b64e60918f8b4eb6",
    "pilot": "97e56802242e627696667007c168c476e340d19c7ee0e396ddb64afa07a5a613",
}


def raw_pin(raw):
    return {"bytes": len(raw), "sha256": adapter.sha(raw)}


def metadata_fixture():
    raw = {key: (ROOT / name).read_bytes() for key, name in PATHS.items()}
    for key, value in raw.items():
        if raw_pin(value) != PINS[key]:
            raise AssertionError("retained independently pinned metadata changed: " + key)
    windows = json.loads(raw["window_design"])["windows"]
    banks = json.loads(raw["receiver_bank_records"])
    basis = {field: PINS[name]["sha256"] for field, name in zip(
        ("source_metadata_sha256", "window_design_sha256", "window_contract_sha256", "receiver_bank_records_sha256"), PATHS)}
    basis.update(source_inventory_sha256="3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f",
        window_identities={w["role"]: w["identity"] for w in windows},
        receiver_bank_sha256s={b["provenance"]["role"]: b["bank_identity"] for b in banks},
        receiver_context_sha256s={k: CONTEXTS[k] for k in ("calibration", "validation")})
    return {"raw_metadata": raw, "expected_metadata_pins": copy.deepcopy(PINS), "expected_basis": basis}


def repin_metadata(fixture, name, doc):
    raw = adapter.canonical(doc)
    fixture["raw_metadata"][name] = raw
    fixture["expected_metadata_pins"][name] = raw_pin(raw)
    field = {"source_metadata": "source_metadata_sha256", "window_design": "window_design_sha256",
             "window_contract": "window_contract_sha256", "receiver_bank_records": "receiver_bank_records_sha256"}[name]
    fixture["expected_basis"][field] = adapter.sha(raw)


def seal_receipt(doc):
    return {**doc, "receipt_sha256": adapter.digest(doc)}


def refresh_current_fixture(packet):
    """Update only fictitious test proofs through the real maintained validators."""
    import scientific_admission
    from test_scientific_store import current_admission_fixture
    names = ("raw_documents", "expected_raw_pins", "expected_basis", "expected_publication_chain",
             "expected_execution_inventory", "expected_dependency_edges", "expected_runtime_identity")
    closure = scientific_admission.validate_scientific_closure(**{key: packet[key] for key in names})
    current = current_admission_fixture(closure, packet["expected_basis"], role=packet["role"],
                                       row_receipt_pins=packet["expected_row_receipt_pins"])
    packet.update({key: value for key, value in current.items() if key not in ("verified_closure", "expected_basis", "raw_proof_bytes", "expected_raw_pin")})
    packet["raw_proof"] = current["raw_proof_bytes"]
    packet["expected_proof_pin"] = current["expected_raw_pin"]


class FixtureClock:
    """Explicit simulated clock; never a production time-source qualification."""
    def __init__(self, values=None, *, start=2000):
        self.values = iter(values) if values is not None else None
        self.next_value = start
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.values is not None:
            return next(self.values)
        value = self.next_value
        self.next_value += 1
        return value


def gated_fixture():
    """Entirely fictitious evidence and physical-receipt shapes, in memory only.

    All closure/current proof domains are synthetic-test-fixture; no generated
    outcome, source receipt, ledger or proof is written or published. The short
    callback rows are explicitly disjoint from the physical 65536-channel data.
    """
    from test_scientific_admission import make_fixture
    metadata = metadata_fixture()
    f = make_fixture()
    f.basis.update(metadata["expected_basis"])
    for binding in f.basis["case_bindings"]:
        binding["source_contract_sha256"] = f.basis["source_metadata_sha256"]
        binding["context_sha256"] = f.basis["receiver_context_sha256s"]["calibration" if binding["role"] == "calibration" else "validation"]
    f.docs["basis"]["basis"] = copy.deepcopy(f.basis)
    f.docs["trial_protocol"]["source_inventory_sha256"] = f.basis["source_inventory_sha256"]
    f.docs["executable_freeze"]["source_contract_sha256"] = f.basis["source_metadata_sha256"]
    for handoff in f.docs["codec_certificate"]["normalization_receiver_handoffs"]:
        handoff["receiver_context_sha256"] = f.basis["receiver_context_sha256s"][handoff["role"]]
        handoff["receiver_bank_sha256"] = f.basis["receiver_bank_sha256s"][handoff["role"]]
    for allocated, binding in zip(f.docs["scientific_allocation"]["cases"], f.basis["case_bindings"]):
        allocated["binding"] = copy.deepcopy(binding)
    f.docs["pilot_contract"].update(source_inventory_sha256=f.basis["source_inventory_sha256"],
        window_identity=f.basis["window_identities"]["pilot"], receiver_bank_sha256=f.basis["receiver_bank_sha256s"]["pilot"],
        receiver_context_sha256=CONTEXTS["pilot"])
    f.docs["acquisition_ledger"]["source_inventory_sha256"] = f.basis["source_inventory_sha256"]
    packet = f.seal()
    packet.update(raw_metadata=metadata["raw_metadata"], expected_metadata_pins=metadata["expected_metadata_pins"], role="pilot")
    import scientific_admission
    closure = scientific_admission.validate_scientific_closure(**{key: value for key, value in packet.items()
                                           if key not in ("raw_metadata", "expected_metadata_pins", "role")})
    context = adapter.validate_receiver_metadata(packet["raw_metadata"], packet["expected_metadata_pins"],
                                                expected_basis=packet["expected_basis"], role="pilot")
    raw_receipts, callback_rows = {}, {}
    for ordinal, scan in enumerate(context["context"]["scans"]):
        label = scan["label"]
        rows = tuple(struct.pack("<ffff", float(ordinal), float(j), 1., -1.) for j in range(16))
        callback_rows[label] = rows
        definition = {key: value for key, value in scan.items() if key not in ("epoch", "kind")}
        scope = {"version": "m43h-widened-source-v1", "kind": "telescope-remote",
            "contract_sha256": closure.record()["new_executable_source_contract_sha256"], "definition": definition,
            "window": context["source_window_name"], "archive_interval": context["archive_interval"], "geometry": context["geometry"],
            "normalization": adapter.NORMALIZATION, "modelled_buffer_bound_bytes": 32 * adapter.CHANNELS + 92 * 1024**2}
        row_receipts = [seal_receipt({"scope_sha256": adapter.digest(scope), "row": j,
            "native_sha256": adapter.sha(("MOCK NATIVE " + label + str(j)).encode()),
            "ascending_raw_sha256": adapter.sha(("MOCK ASCENDING " + label + str(j)).encode()),
            "normalized_sha256": adapter.sha(row), "native_file_sha256": adapter.sha(("MOCK NPY NATIVE " + label + str(j)).encode()),
            "normalized_file_sha256": adapter.sha(("MOCK NPY NORMALIZED " + label + str(j)).encode())}) for j, row in enumerate(rows)]
        remote = {"url": scan["url"], "size": scan["expected_remote_size_bytes"], "etag": scan["expected_etag"]}
        checkpoint = {"artifact_type": "seti_repeater.m37_sparse_http_mirror", "schema_version": 1,
            "remote": remote, "segments": [{"start": 0, "stop": 64, "sha256": adapter.sha(b"MOCK RANGE ONLY")}]}
        checkpoint["checkpoint_sha256"] = hashlib.sha256(json.dumps(checkpoint, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        transport = {"kind": "live-identity-bound-http-ranges", "identity": remote,
            "range_plan_file_sha256": adapter.sha(b"MOCK RANGE PLAN ONLY"), "checkpoint": checkpoint,
            "hdf5_runtime": {key: packet["expected_runtime_identity"][key] for key in ("numpy", "h5py", "hdf5", "hdf5plugin")},
            "dataset_filters": [[32008, 1, [0, 3, 4, 0, 2]]]}
        raw_receipts[label] = adapter.canonical(seal_receipt({"scope": scope, "rows": row_receipts, "transport": transport, "complete": True}))
    packet.update(raw_receipts=raw_receipts, expected_row_receipt_pins={key: raw_pin(raw) for key, raw in raw_receipts.items()})
    refresh_current_fixture(packet)
    return packet, callback_rows


class DenyExternalEffects:
    """Read/setup occurs first; the actual metadata API has no filesystem effect."""
    def __enter__(self):
        self.calls = []
        def fail(*args, **kwargs):
            self.calls.append((args, kwargs))
            raise AssertionError("external effect during metadata validation")
        self.patches = [patch.object(target, name, side_effect=fail) for target, name in (
            (builtins, "open"), (io, "open"), (os, "open"), (socket, "socket"),
            (subprocess, "Popen"), (subprocess, "run"), (os, "system"))]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *args):
        for p in reversed(self.patches):
            p.stop()


class ReceiverMetadataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = metadata_fixture()

    def validate(self, role="validation"):
        return adapter.validate_receiver_metadata(**self.fixture, role=role)

    def test_reproduce_all_three_preserved_receiver_contracts_without_source_values(self):
        with DenyExternalEffects() as effects:
            for role in adapter.ROLES:
                context = self.validate(role)
                self.assertEqual(context["context_sha256"], CONTEXTS[role])
                self.assertEqual(context["geometry"]["channel_count"], 65536)
                self.assertEqual(context["source_window_name"], "hd189733_" + role + "_geometry")
                self.assertEqual(context["context"]["window"], "hd189733_" + role + "_receiver_v1")
                self.assertFalse(context["factor_contract"]["orbital_fields_constructed"])
                self.assertFalse(context["factor_contract"]["telescope_access_authorized"])
            self.assertEqual(effects.calls, [])

    def test_exact_metadata_and_independent_pin_domains(self):
        del self.fixture["expected_metadata_pins"]["window_contract"]
        with self.assertRaises(adapter.AdmissionError):
            self.validate()

    def test_changed_raw_metadata_cannot_self_authenticate(self):
        self.fixture["raw_metadata"]["source_metadata"] += b" "
        with self.assertRaisesRegex(adapter.AdmissionError, "independent raw pin"):
            self.validate()

    def test_duplicate_pinned_json_key_refused(self):
        raw = b'{"windows":[],"windows":[]}'
        self.fixture["raw_metadata"]["source_metadata"] = raw
        self.fixture["expected_metadata_pins"]["source_metadata"] = raw_pin(raw)
        with self.assertRaisesRegex(adapter.AdmissionError, "duplicate JSON"):
            self.validate()

    def test_repinning_onoff_role_change_still_refused_semantically(self):
        source = json.loads(self.fixture["raw_metadata"]["source_metadata"])
        source["scans"][1]["role"] = "on"
        source["source_inventory_sha256"] = adapter.digest(source["scans"])
        repin_metadata(self.fixture, "source_metadata", source)
        with self.assertRaisesRegex(adapter.AdmissionError, "paired ON/OFF"):
            self.validate()

    def test_repinning_boolean_chunk_dimension_still_refused(self):
        source = json.loads(self.fixture["raw_metadata"]["source_metadata"])
        source["scans"][0]["expected_chunks"][0] = True
        source["source_inventory_sha256"] = adapter.digest(source["scans"])
        repin_metadata(self.fixture, "source_metadata", source)
        with self.assertRaisesRegex(adapter.AdmissionError, "geometry"):
            self.validate()

    def test_repinning_orbital_bank_cannot_impersonate_receiver_bank(self):
        banks = json.loads(self.fixture["raw_metadata"]["receiver_bank_records"])
        banks[0]["provenance"]["orbital_factor_type"] = True
        repin_metadata(self.fixture, "receiver_bank_records", banks)
        with self.assertRaisesRegex(adapter.AdmissionError, "FactorBasis"):
            self.validate()

    def test_repinning_boolean_width_cannot_pass_numeric_equality(self):
        banks = json.loads(self.fixture["raw_metadata"]["receiver_bank_records"])
        banks[0]["provenance"]["widths"][0] = True
        repin_metadata(self.fixture, "receiver_bank_records", banks)
        with self.assertRaisesRegex(adapter.AdmissionError, "FactorBasis"):
            self.validate()

    def test_basis_bank_pin_is_independent_of_input_self_identity(self):
        self.fixture["expected_basis"]["receiver_bank_sha256s"]["validation"] = "0" * 64
        with self.assertRaisesRegex(adapter.AdmissionError, "basis receiver"):
            self.validate()

    def test_repinned_native_float_factor_hash_refused(self):
        banks = json.loads(self.fixture["raw_metadata"]["receiver_bank_records"])
        banks[0]["factor_sha256"] = "0" * 64
        repin_metadata(self.fixture, "receiver_bank_records", banks)
        with self.assertRaisesRegex(adapter.AdmissionError, "literal factor"):
            self.validate()

    def test_incomplete_scientific_closure_refused_before_loader_or_external_effect(self):
        # Import the maintained pure validators before the effect guard. This
        # test supplies no proof, source receipt, allocation or current session.
        import scientific_admission
        import scientific_store
        calls = []
        def loader(request):
            calls.append(request)
            raise AssertionError("blocked scientific evidence reached row loader")
        metadata = {**self.fixture, "role": "validation", "raw_documents": {}, "expected_raw_pins": {},
                    "expected_publication_chain": {}, "expected_execution_inventory": {}, "expected_dependency_edges": [],
                    "expected_runtime_identity": {}, "raw_proof": b"{}\n", "expected_proof_pin": raw_pin(b"{}\n"),
                    "raw_store_acknowledgement": b"{}\n", "expected_store_acknowledgement_pin": raw_pin(b"{}\n"),
                    "raw_cas_qualification": b"{}\n", "expected_cas_qualification_pin": raw_pin(b"{}\n"),
                    "raw_session_proof": b"{}\n", "expected_session_proof_pin": raw_pin(b"{}\n"),
                    "raw_receipts": {}, "expected_row_receipt_pins": {}, "expected_current_session": {}}
        with DenyExternalEffects() as effects:
            with self.assertRaises(ValueError):
                adapter.from_telescope(row_loader=loader, live_clock=FixtureClock(), **metadata)
            self.assertEqual(calls, [])
            self.assertEqual(effects.calls, [])

    def test_resealed_complete_bound_contract_cannot_change_pending_laws(self):
        bound = json.loads(self.fixture["raw_metadata"]["window_contract"])
        bound["roles_are_independent_observations"] = True
        del bound["contract_sha256"]
        bound["contract_sha256"] = adapter.digest(bound)
        repin_metadata(self.fixture, "window_contract", bound)
        banks = json.loads(self.fixture["raw_metadata"]["receiver_bank_records"])
        for bank in banks:
            bank["provenance"]["window_binding_sha256"] = bound["contract_sha256"]
            del bank["bank_identity"]
            bank["bank_identity"] = hashlib.sha256(json.dumps(bank, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.fixture["expected_basis"]["receiver_bank_sha256s"][bank["provenance"]["role"]] = bank["bank_identity"]
        repin_metadata(self.fixture, "receiver_bank_records", banks)
        with self.assertRaisesRegex(adapter.AdmissionError, "complete 288-chunk"):
            self.validate()


class ReceiverAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.rows = gated_fixture()
        self.pins = {label: [raw_pin(row) for row in rows] for label, rows in self.rows.items()}
        self.calls = []
        self.clock = FixtureClock()

    def loader(self, request):
        self.calls.append(request.label)
        return adapter.LoadedRows(request.receipt_raw, self.rows[request.label])

    def qualify(self, loader=None):
        return adapter.qualify_synthetic_fixture(row_loader=loader or self.loader, fixture_row_pins=self.pins,
                                                 fixture_clock=self.clock, **self.packet)

    def refuse_before_loader(self, pattern=None):
        with self.assertRaisesRegex(ValueError, pattern or ".+"):
            self.qualify()
        self.assertEqual(self.calls, [])

    def change_receipt(self, label, mutate):
        doc = json.loads(self.packet["raw_receipts"][label])
        mutate(doc)
        del doc["receipt_sha256"]
        raw = adapter.canonical(seal_receipt(doc))
        self.packet["raw_receipts"][label] = raw
        self.packet["expected_row_receipt_pins"][label] = raw_pin(raw)
        refresh_current_fixture(self.packet)

    def set_session_window(self, start, deadline, current):
        """Coherent fixture-only pinned session update, preserving allocation IDs."""
        session = json.loads(self.packet["raw_session_proof"])
        session.update(started_epoch_milliseconds=start, deadline_epoch_milliseconds=deadline)
        raw = adapter.canonical(session)
        self.packet["raw_session_proof"] = raw
        self.packet["expected_session_proof_pin"] = raw_pin(raw)
        proof = json.loads(self.packet["raw_proof"])
        proof["session_proof_sha256"] = adapter.sha(raw)
        self.packet["raw_proof"] = adapter.canonical(proof)
        self.packet["expected_proof_pin"] = raw_pin(self.packet["raw_proof"])
        self.packet["expected_current_session"]["now_epoch_milliseconds"] = current

    def test_complete_fixture_qualifies_six_tiny_callbacks_without_actual_authority(self):
        import scientific_admission
        import scientific_store
        with DenyExternalEffects() as effects:
            result = self.qualify()
            record = result.record()
            self.assertEqual(self.calls, list(adapter.LABELS))
            self.assertEqual(record["source_domain"], "synthetic-interface-fixture-only")
            self.assertFalse(record["scientific_execution_authorized"])
            self.assertFalse(record["spectral_access_authorized"])
            self.assertFalse(record["telescope_values_opened"])
            self.assertFalse(record["physical_payload_hashes_qualified"])
            self.assertFalse(record["normalization_performed"])
            self.assertFalse(record["native_execution_performed"])
            self.assertEqual(record["closure_sha256"], json.loads(self.packet["raw_proof"])["closure_sha256"])
            self.assertEqual(record["admission_sha256"], adapter.sha(adapter._gated_metadata(**self.packet)[1].payload))
            self.assertFalse(record["scientific_allocation_charged"])
            self.assertEqual(self.clock.calls, 12)
            observations = record["per_load_live_clock"]["nondecreasing_integer_observations"]
            self.assertEqual([row["epoch_milliseconds"] for row in observations], list(range(2000, 2012)))
            self.assertEqual([row["phase"] for row in observations], [phase for _ in adapter.LABELS for phase in ("before", "after")])
            self.assertFalse(record["per_load_live_clock"]["callback_interruption_guaranteed_here"])
            self.assertEqual(effects.calls, [])
        for request, source in zip(result.requests, result.sources):
            self.assertIs(source.receipt_raw, request.receipt_raw)
            self.assertEqual(source.receipt_raw, self.packet["raw_receipts"][request.label])
            self.assertEqual(sum(len(row) for row in source.rows), 256)
        result.record()["spectral_access_authorized"] = True
        self.assertFalse(result.record()["spectral_access_authorized"])

    def test_valid_pending_fixture_refused_by_production_before_any_row_loader(self):
        with DenyExternalEffects() as effects:
            with self.assertRaisesRegex(adapter.AdmissionError, "remains blocked"):
                adapter.from_telescope(row_loader=self.loader, live_clock=self.clock, **self.packet)
            self.assertEqual(self.calls, [])
            self.assertEqual(self.clock.calls, 0)
            self.assertEqual(effects.calls, [])

    def test_changed_raw_proof_refused_before_loader(self):
        self.packet["raw_proof"] += b" "
        self.refuse_before_loader("independent")

    def test_expired_current_session_refused_before_loader(self):
        self.packet["expected_current_session"]["now_epoch_milliseconds"] = 1201000
        self.refuse_before_loader("Expired")

    def test_unrelated_current_session_refused_before_loader(self):
        self.packet["expected_current_session"]["session_identity"] = "0" * 64
        self.refuse_before_loader()

    def test_missing_151st_outcome_refused_before_any_loader(self):
        from test_scientific_admission import Fixture
        docs = {name: json.loads(raw) for name, raw in self.packet["raw_documents"].items()}
        docs["scientific_result"]["cases"].pop()
        self.packet.update(Fixture(docs, self.packet["expected_basis"]).seal())
        self.refuse_before_loader("151")

    def test_candidate_codec_certificate_refused_before_any_loader(self):
        from test_scientific_admission import Fixture
        docs = {name: json.loads(raw) for name, raw in self.packet["raw_documents"].items()}
        docs["codec_certificate"]["schema"] = "radio-source-profile-candidate-only"
        self.packet.update(Fixture(docs, self.packet["expected_basis"]).seal())
        self.refuse_before_loader("typed evidence")

    def test_unqualified_cas_proof_refused_even_with_coherent_independent_repins(self):
        law = json.loads(self.packet["raw_cas_qualification"])
        law["atomic_expected_revision_cas"] = False
        raw = adapter.canonical(law)
        self.packet["raw_cas_qualification"] = raw
        self.packet["expected_cas_qualification_pin"] = raw_pin(raw)
        ack = json.loads(self.packet["raw_store_acknowledgement"])
        ack["cas_qualification_sha256"] = adapter.sha(raw)
        ack_raw = adapter.canonical(ack)
        self.packet["raw_store_acknowledgement"] = ack_raw
        self.packet["expected_store_acknowledgement_pin"] = raw_pin(ack_raw)
        proof = json.loads(self.packet["raw_proof"])
        proof["store_acknowledgement_sha256"] = adapter.sha(ack_raw)
        self.packet["raw_proof"] = adapter.canonical(proof)
        self.packet["expected_proof_pin"] = raw_pin(self.packet["raw_proof"])
        self.refuse_before_loader("CAS")

    def test_sixth_source_receipt_checked_before_first_loader(self):
        self.change_receipt(adapter.LABELS[-1], lambda doc: doc.update(complete=False))
        self.refuse_before_loader("scope/rows")

    def test_wrong_source_window_name_refused_before_first_loader(self):
        self.change_receipt(adapter.LABELS[-1], lambda doc: doc["scope"].update(window="hd189733_pilot_receiver_v1"))
        self.refuse_before_loader("scope/rows")

    def test_resealed_boolean_filter_pipeline_refused_before_first_loader(self):
        self.change_receipt(adapter.LABELS[-1], lambda doc: doc["transport"]["dataset_filters"][0].__setitem__(1, True))
        self.refuse_before_loader("transport")

    def test_changed_original_receipt_raw_pin_refused_before_first_loader(self):
        self.packet["raw_receipts"][adapter.LABELS[-1]] += b" "
        self.refuse_before_loader("independent raw pin")

    def test_unbounded_fixture_row_pin_refused_before_first_loader(self):
        self.pins[adapter.LABELS[-1]][-1]["bytes"] = 4097
        self.refuse_before_loader("oversized")

    def test_mutable_receipt_cannot_enter_frozen_result_and_no_subsequent_callback(self):
        def loader(request):
            self.calls.append(request.label)
            return adapter.LoadedRows(bytearray(request.receipt_raw), self.rows[request.label])
        with self.assertRaisesRegex(adapter.AdmissionError, "receipt changed"):
            self.qualify(loader)
        self.assertEqual(self.calls, [adapter.LABELS[0]])

    def test_empty_loader_result_is_closed_error_without_fallback_or_later_callback(self):
        def loader(request):
            self.calls.append(request.label)
            return None
        with self.assertRaisesRegex(adapter.AdmissionError, "receipt changed"):
            self.qualify(loader)
        self.assertEqual(self.calls, [adapter.LABELS[0]])

    def test_loader_hash_failure_stops_before_subsequent_source(self):
        def loader(request):
            self.calls.append(request.label)
            rows = self.rows[request.label]
            if request.label == adapter.LABELS[1]:
                rows = (b"\0" * len(rows[0]),) + rows[1:]
            return adapter.LoadedRows(request.receipt_raw, rows)
        with self.assertRaisesRegex(adapter.AdmissionError, "independent pin"):
            self.qualify(loader)
        self.assertEqual(self.calls, list(adapter.LABELS[:2]))

    def test_nonfinite_fixture_is_rejected_even_when_repinned(self):
        label = adapter.LABELS[0]
        bad = struct.pack("<ffff", float("nan"), 1., 2., 3.)
        self.rows[label] = (bad,) + self.rows[label][1:]
        self.pins[label][0] = raw_pin(bad)
        with self.assertRaisesRegex(adapter.AdmissionError, "nonfinite"):
            self.qualify()
        self.assertEqual(self.calls, [label])

    def test_loader_failure_does_not_retry_or_dispatch_later_sources(self):
        def loader(request):
            self.calls.append(request.label)
            raise RuntimeError("synthetic loader failed")
        with self.assertRaisesRegex(RuntimeError, "synthetic loader failed"):
            self.qualify(loader)
        self.assertEqual(self.calls, [adapter.LABELS[0]])
        self.assertEqual(self.clock.calls, 2)

    def test_same_millisecond_observations_are_valid_at_integer_clock_resolution(self):
        self.clock = FixtureClock([2000] * 12)
        record = self.qualify().record()
        self.assertEqual(self.calls, list(adapter.LABELS))
        self.assertEqual([row["epoch_milliseconds"] for row in record["per_load_live_clock"]["nondecreasing_integer_observations"]], [2000] * 12)
        self.assertFalse(record["scientific_execution_authorized"])

    def test_live_session_expired_before_first_loader_has_zero_callback(self):
        self.clock = FixtureClock([1201000])
        self.refuse_before_loader("expired before")
        self.assertEqual(self.clock.calls, 1)

    def test_live_session_expires_during_loader_closes_before_subsequent_source(self):
        self.clock = FixtureClock([1200999, 1201000])
        with self.assertRaisesRegex(adapter.AdmissionError, "expired after"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])
        self.assertEqual(self.clock.calls, 2)

    def test_expired_before_second_loader_does_not_dispatch_second_source(self):
        self.clock = FixtureClock([2000, 2001, 1201000])
        with self.assertRaisesRegex(adapter.AdmissionError, "expired before"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])
        self.assertEqual(self.clock.calls, 3)

    def test_live_clock_cannot_precede_independently_validated_current_time(self):
        self.clock = FixtureClock([1999])
        self.refuse_before_loader("regressed")

    def test_live_clock_regression_after_loader_stops_later_sources(self):
        self.clock = FixtureClock([2001, 2000])
        with self.assertRaisesRegex(adapter.AdmissionError, "regressed"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])

    def test_live_clock_regression_before_second_loader_stops_later_sources(self):
        self.clock = FixtureClock([2000, 2001, 1999])
        with self.assertRaisesRegex(adapter.AdmissionError, "regressed"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])

    def test_boolean_float_nonfinite_or_text_clock_values_fail_before_any_loader(self):
        for value in (True, False, 2000.0, float("nan"), float("inf"), "2000", None):
            with self.subTest(value=value):
                self.clock = FixtureClock([value])
                self.refuse_before_loader("integer epoch")

    def test_missing_independently_supplied_callable_clock_fails_before_any_loader(self):
        self.clock = None
        self.refuse_before_loader("clock required")

    def test_clock_failure_before_first_loader_never_invokes_source_callback(self):
        def fail():
            raise RuntimeError("fixture clock failed")
        self.clock = fail
        with self.assertRaisesRegex(RuntimeError, "fixture clock failed"):
            self.qualify()
        self.assertEqual(self.calls, [])

    def test_clock_failure_after_loader_stops_without_fallback_or_subsequent_source(self):
        values = iter((2000, RuntimeError("fixture clock failed")))
        def clock():
            value = next(values)
            if isinstance(value, Exception):
                raise value
            return value
        self.clock = clock
        with self.assertRaisesRegex(RuntimeError, "fixture clock failed"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])

    def test_fixed_ninth_october_consolidation_boundary_prevents_first_loader(self):
        import scientific_store
        stop = scientific_store.STOP_EPOCH_MILLISECONDS
        self.set_session_window(stop - 100, stop, stop - 5)
        self.clock = FixtureClock([stop])
        self.refuse_before_loader("consolidation deadline expired before")

    def test_fixed_consolidation_boundary_during_loader_stops_later_sources(self):
        import scientific_store
        stop = scientific_store.STOP_EPOCH_MILLISECONDS
        self.set_session_window(stop - 100, stop, stop - 5)
        self.clock = FixtureClock([stop - 1, stop])
        with self.assertRaisesRegex(adapter.AdmissionError, "consolidation deadline expired after"):
            self.qualify()
        self.assertEqual(self.calls, [adapter.LABELS[0]])


if __name__ == "__main__":
    unittest.main()
