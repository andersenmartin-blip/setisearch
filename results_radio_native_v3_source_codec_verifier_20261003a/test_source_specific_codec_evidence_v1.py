"""Adversarial laws for exact, source-specific engineering evidence."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import qualify_candidate as driver
import source_specific_codec_evidence_v1 as verifier


class CandidateEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence, cls.raw, cls.trusted = driver.prepare()
        cls.probe = verifier.strict_json((driver.PROBE / "all-rows-probe.json").read_bytes())
        cls.before = verifier.strict_json((driver.PROBE / "runtime-closure-before.json").read_bytes())
        cls.source = verifier.strict_json((driver.SOURCE / "config/radio_hd189733_source_preparation_20260927.json").read_bytes())
        cls.geometry = verifier.strict_json((driver.SOURCE / "results_radio_hd189733_geometry_2026-09-27/window_geometry.json").read_bytes())

    def reject_envelope(self, mutation):
        evidence = copy.deepcopy(self.evidence)
        mutation(evidence)
        raw = verifier.canonical(evidence)
        trusted = replace(self.trusted, evidence_sha256=verifier.sha256(raw))
        with self.assertRaises(verifier.EvidenceError):
            verifier.verify_candidate_evidence(raw, trusted)

    def reject_probe(self, mutation):
        probe = copy.deepcopy(self.probe)
        mutation(probe)
        # Semantic laws remain authoritative even if a caller separately
        # reviews/repins an altered report. This does not rewrite frozen c.
        with self.assertRaises(verifier.EvidenceError):
            verifier._probe(probe, self.source, self.geometry, self.trusted)

    def test_real_candidate_evidence_live_bytes_and_all_selected_hashes(self):
        result = verifier.verify_candidate_evidence(self.raw, self.trusted)
        self.assertEqual(result["status"], "QUALIFIED_CANDIDATE_ENGINEERING_EVIDENCE")
        self.assertEqual(result["live_runtime_file_pins_verified"], 2517)
        self.assertEqual(result["live_runtime_logical_bytes_verified"], 406038889)
        self.assertEqual(result["independently_regenerated_selected_cells"], 3145728)
        for key in ("complete_execution_runtime_freeze", "externally_observed_complete_lifetime", "public_authentication_established", "telescope_admission_authorized", "scientific_admission_authorized", "executable_source_contract_created"):
            self.assertIs(result[key], False)

    def test_wrong_case_law_version(self):
        self.reject_envelope(lambda e: e.update(case_law_version="unrelated-law"))

    def test_wrong_source_inventory(self):
        self.reject_envelope(lambda e: e.update(source_inventory_sha256="0" * 64))

    def test_other_source_filter_signature(self):
        self.reject_envelope(lambda e: e.update(exact_source_filter_pipeline=verifier.ENCODER_FILTER))

    def test_encoder_cannot_be_relabelled_as_original_source_encoder(self):
        self.reject_envelope(lambda e: e.update(current_encoder_filter_pipeline=verifier.SOURCE_FILTER))
        self.reject_probe(lambda p: p.update(local_current_encoder_is_original_archive_encoder=True))

    def test_filter_boolean_alias_rejected(self):
        self.reject_envelope(lambda e: e["exact_source_filter_pipeline"][0].__setitem__(1, True))

    def test_runtime_requires_exact_four_versions(self):
        self.reject_envelope(lambda e: e["runtime"].update(hdf5="2.0.1"))
        self.reject_envelope(lambda e: e["runtime"].update(python="3.12.14"))
        self.reject_envelope(lambda e: e["runtime"].__setitem__("numpy", 2.3))

    def test_ordered_scan_metadata_cannot_reorder(self):
        self.reject_envelope(lambda e: e["ordered_source_scans"].reverse())

    def test_exact_scan_header_cannot_mutate(self):
        self.reject_envelope(lambda e: e["ordered_source_scans"][0]["expected_header"].update(tstart_mjd=1.0))

    def test_unknown_scan_field_rejected(self):
        self.reject_envelope(lambda e: e["ordered_source_scans"][0].update(admission=True))

    def test_ordered_window_metadata_cannot_reorder(self):
        self.reject_envelope(lambda e: e["ordered_window_metadata"].reverse())

    def test_window_payload_identity_cannot_mutate(self):
        self.reject_envelope(lambda e: e["ordered_window_metadata"][0]["payload_keys"][0].update(etag='"changed"'))

    def test_unknown_envelope_field(self):
        self.reject_envelope(lambda e: e.update(certificate=True))

    def test_false_scientific_or_public_authority(self):
        for key in ("telescope_admission_authorized", "scientific_admission_authorized", "public_authentication_established", "complete_runtime_lifetime_established"):
            self.reject_envelope(lambda e, key=key: e.__setitem__(key, True))
        self.reject_envelope(lambda e: e.update(authority="scientific certificate"))

    def test_evidence_byte_tamper_not_self_authenticating(self):
        with self.assertRaises(verifier.EvidenceError):
            verifier.verify_candidate_evidence(self.raw + b" ", self.trusted)

    def test_reference_sha_tampering(self):
        for key in ("probe", "runtime_closure_before", "runtime_closure_after", "verifier_code_pin"):
            self.reject_envelope(lambda e, key=key: e[key].update(sha256="0" * 64))

    def test_source_input_pin_sha_tampering(self):
        self.reject_envelope(lambda e: e["code_input_pins"][next(iter(e["code_input_pins"]))].update(sha256="0" * 64))

    def test_missing_or_false_negative_guard(self):
        self.reject_probe(lambda p: p["metadata_case_laws"].pop())
        self.reject_probe(lambda p: p["metadata_case_laws"][4].update(expected="accept"))
        self.reject_probe(lambda p: p["metadata_case_laws"][4].update({"pass": False}))

    def test_guard_boolean_success_cannot_be_integer(self):
        self.reject_probe(lambda p: p["metadata_case_laws"][0].update({"pass": 1}))

    def test_probe_unknown_and_hidden_scientific_authority(self):
        self.reject_probe(lambda p: p.update(source_authorized=True))
        self.reject_probe(lambda p: p.update(authenticated_source_specific_codec_runtime_case_law_certificate=True))
        self.reject_probe(lambda p: p["coverage"].update(normalization_receiver_handoff="scientific certificate complete"))

    def test_probe_wrong_runtime_or_pipeline(self):
        self.reject_probe(lambda p: p["runtime_version_fields_used_by_source_reader"].update(numpy="3.0.0"))
        self.reject_probe(lambda p: p.update(exact_source_filter_pipeline=[]))

    def test_partial_row_coverage(self):
        self.reject_probe(lambda p: p.update(row_indices_exercised=[0, 15]))
        self.reject_probe(lambda p: p["decode_receipts"].pop())

    def test_wrong_decode_mapping(self):
        self.reject_probe(lambda p: p["decode_receipts"][0].update(row=1))
        self.reject_probe(lambda p: p["decode_receipts"][0].update(chunk_index=156))

    def test_independently_derived_selected_hash_rejects_forgery(self):
        self.reject_probe(lambda p: p["decode_receipts"][0].update(selected_sha256="0" * 64))

    def test_raw_filter_mask_and_offset(self):
        # Independent byte oracle is exercised above; isolate raw mapping laws.
        def valid_hash(row, chunk_index, interval):
            return next(r["selected_sha256"] for r in self.probe["decode_receipts"] if r["row"] == row and r["chunk_index"] == chunk_index)
        with patch.object(verifier, "_selected_pattern_hash", side_effect=valid_hash):
            self.reject_probe(lambda p: p["raw_chunk_receipts"][0].update(filter_mask=1))
            self.reject_probe(lambda p: p["raw_chunk_receipts"][0].update(offset=[0, 0, 1]))

    def test_probe_count_boolean_rejected(self):
        self.reject_probe(lambda p: p.update(network_requests=False))

    def test_closure_missing_mapped_binary_or_unknown_field(self):
        for mutation in (lambda c: c.update(extra=True), lambda c: c["mapped_runtime_paths"].append("/missing.so"), lambda c: c.update(file_count=True)):
            closure = copy.deepcopy(self.before)
            mutation(closure)
            with self.assertRaises(verifier.EvidenceError):
                verifier._closure(closure, self.trusted, self.probe["script_pin"]["path"])

    def test_duplicate_json_fields(self):
        with self.assertRaises(verifier.EvidenceError):
            verifier.strict_json(b'{"x":1,"x":2}')

    def test_nonfinite_json_numbers(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
            with self.assertRaises(verifier.EvidenceError):
                verifier.strict_json(raw)

    def test_live_byte_hash_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            path.write_bytes(b"abc")
            pin = driver.pin(path)
            path.write_bytes(b"xyz")
            with self.assertRaises(verifier.EvidenceError):
                verifier._read_pin(pin, [temp])

    def test_telescope_payload_path_is_not_a_candidate_reader(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "telescope.h5"
            path.write_bytes(b"opaque")
            with self.assertRaises(verifier.EvidenceError):
                verifier._read_pin(driver.pin(path), [temp])


if __name__ == "__main__":
    unittest.main(verbosity=2)
