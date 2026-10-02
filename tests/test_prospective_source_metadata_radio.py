"""Retained metadata and in-memory negatives; no source runtime or workload."""
import ast
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from seti_repeater import prospective_source_metadata_radio as metadata

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results_radio_hd189733_metadata_preparation_20261002a"


def pins_for(values):
    return {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in values.items()}


class ProspectiveMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_pins = json.loads((BASE / "evidence_pins.json").read_text())
        cls.original_raw = {path: (ROOT / path).read_bytes() for path in cls.original_pins}
        cls.original_outputs = metadata.build_prospective_source_contract(
            cls.original_raw, cls.original_pins, expected_source_inventory_sha256=metadata.SOURCE_INVENTORY)

    def setUp(self):
        self.raw = dict(self.original_raw)
        self.pins = copy.deepcopy(self.original_pins)

    def build(self, **kwargs):
        return metadata.build_prospective_source_contract(self.raw, self.pins,
            expected_source_inventory_sha256=metadata.SOURCE_INVENTORY, **kwargs)

    def validate(self, outputs=None, output_pins=None):
        values = self.original_outputs if outputs is None else outputs
        return metadata.validate_prospective_source_metadata(values, pins_for(values) if output_pins is None else output_pins,
            self.raw, self.pins, expected_source_inventory_sha256=metadata.SOURCE_INVENTORY)

    def edit_input(self, path, edit):
        value = json.loads(self.raw[path])
        edit(value)
        self.raw[path] = metadata.canonical(value)
        self.pins[path] = pins_for({path: self.raw[path]})[path]

    def resigned_outputs(self, edit):
        """Coherently rehash tampering so negatives exercise semantic validation."""
        values = {name: json.loads(raw) for name, raw in self.original_outputs.items()}
        edit(values)
        wrapper, matrix, rebinding = (values[name] for name in metadata.OUTPUT_KEYS)
        if "prospective_source_fields" in wrapper:
            wrapper["prospective_source_fields_sha256"] = metadata.digest(wrapper["prospective_source_fields"])
            rebinding["prospective_source_fields_sha256"] = wrapper["prospective_source_fields_sha256"]
        matrix["prospective_wrapper_sha256"] = metadata.digest(wrapper)
        matrix["provenance_rebinding_sha256"] = metadata.digest(rebinding)
        return {name: metadata.canonical(value) for name, value in values.items()}

    def test_retained_metadata_outputs_are_permanently_blocked(self):
        result = self.validate()
        self.assertEqual(result["status"], "VERIFIED_BLOCKED_METADATA_ONLY")
        self.assertEqual(result["authenticated_input_count"], 25)
        self.assertFalse(result["executable_contract_or_certificate_issued"])
        for raw in self.original_outputs.values():
            value = json.loads(raw)
            self.assertEqual(value["status"], metadata.STATUS)
            self.assertTrue(all(flag is False for flag in value["authority"].values()))
            self.assertTrue(all(counter == 0 for counter in value["workload_counters"].values()))
            self.assertEqual(value["stop_date"], "2026-10-09")

    def test_wrapper_is_not_the_live_source_contract_artifact(self):
        wrapper = json.loads(self.original_outputs["prospective_wrapper"])
        self.assertNotEqual(wrapper["artifact_type"], "radio-source-contract-v1")
        self.assertFalse(wrapper["loadable_source_contract_issued"])
        fields = wrapper["prospective_source_fields"]
        self.assertEqual(fields["artifact_type"], "radio-source-contract-v1")
        self.assertIsNone(fields["hdf5_runtime"])
        self.assertIsNone(fields["reservation_store"])
        self.assertIsNone(fields["cumulative_limits"])
        self.assertTrue(all(gate["status"] != "passed" for gate in fields["gates"].values()))

    def test_exact_clock_matches_independent_retained_bank_pin(self):
        observation = json.loads(self.original_outputs["admission_matrix"])["observed_semantics"]
        self.assertEqual(observation["header_clock_rationals_sha256"],
                         "807e59e40311d623231a13f05bd3bdf4801e83bacd90aae5f9f3b28380f02c48")
        rows = observation["header_clock_rationals"]
        self.assertEqual(len(rows), 96)
        self.assertEqual(Fraction(*rows[0][1]), 0)
        source = json.loads(self.raw[metadata.SOURCE])
        duration = Fraction(source["scans"][0]["expected_header"]["tsamp_s"])
        self.assertEqual(Fraction(*rows[0][0]), -duration / 2)
        self.assertEqual(Fraction(*rows[0][2]), duration / 2)
        for row in rows:
            self.assertEqual(2 * Fraction(*row[1]), Fraction(*row[0]) + Fraction(*row[2]))

    def test_source_and_windows_preserve_288_scan_row_chunk_identities(self):
        observation = json.loads(self.original_outputs["admission_matrix"])["observed_semantics"]
        self.assertEqual(observation["scan_count"], 6)
        self.assertEqual(observation["distinct_native_chunk_identities"], 288)
        self.assertEqual([w["role"] for w in observation["role_windows"]], list(metadata.ROLES))
        self.assertEqual([w["archive_chunk_index"] for w in observation["role_windows"]], [159, 156, 152])
        self.assertFalse(observation["roles_are_independent_observations"])

    def test_scored_span_and_rate_width_scope_are_not_extraction_width(self):
        observation = json.loads(self.original_outputs["admission_matrix"])["observed_semantics"]
        self.assertAlmostEqual(observation["score_span_hz"], 226.84027347621408)
        self.assertEqual(observation["rate_tenths"], list(range(-40, 41)))
        self.assertEqual(observation["widths_channels"], [1, 3, 5, 9, 17, 33, 65, 129])
        self.assertEqual(observation["recorded_frame"], "recorded-topocentric")

    def test_current_nine_implementation_pins_include_reader_search_filter_acquisition_drift(self):
        wrapper = json.loads(self.original_outputs["prospective_wrapper"])
        fields = wrapper["prospective_source_fields"]
        self.assertEqual(fields["implementation_paths"], list(metadata.IMPLEMENTATION_PATHS))
        self.assertEqual(fields["pinned_files"]["src/seti_repeater/search_v0p6.py"],
                         "6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4")
        drift = json.loads(self.original_outputs["admission_matrix"])["old_implementation_pin_drift"]
        self.assertEqual(set(drift), {metadata.IMPLEMENTATION_PATHS[i] for i in (0, 6, 7, 8)})

    def test_historical_factor_records_stay_ancestry_without_numeric_reconstruction(self):
        rebinding = json.loads(self.original_outputs["provenance_rebinding"])
        self.assertIsNone(rebinding["new_executable_source_contract_sha256"])
        self.assertFalse(rebinding["executable_provenance_rebinding_admitted"])
        self.assertTrue(all(bank["factor_bytes_recomputed"] is False for bank in rebinding["observed_semantics"]["historical_banks"]))

    def test_raw_pin_mismatch_refused_by_builder_and_validator(self):
        self.raw[metadata.HEADERS] += b" "
        for call in (self.build, self.validate):
            with self.assertRaisesRegex(ValueError, "byte count|external pin"):
                call()

    def test_every_implementation_file_is_required(self):
        for path in metadata.IMPLEMENTATION_PATHS:
            with self.subTest(path=path):
                raw, pin = self.raw.pop(path), self.pins.pop(path)
                with self.assertRaisesRegex(ValueError, "closure required"):
                    self.build()
                self.raw[path], self.pins[path] = raw, pin

    def test_extra_input_and_local_path_substitution_are_refused(self):
        self.raw["local-fixture/ledger.json"] = b"{}"
        self.pins["local-fixture/ledger.json"] = pins_for({"x": b"{}"})["x"]
        with self.assertRaisesRegex(ValueError, "closure required"):
            self.build()

    def test_mutable_input_bytes_refused(self):
        self.raw[metadata.HEADERS] = bytearray(self.raw[metadata.HEADERS])
        with self.assertRaisesRegex(ValueError, "raw bytes"):
            self.build()

    def test_per_file_input_bound_refused_without_large_file(self):
        path = metadata.IMPLEMENTATION_PATHS[0]
        self.raw[path] = b"x" * (metadata.MAX_FILE_BYTES + 1)
        self.pins[path] = pins_for({path: self.raw[path]})[path]
        with self.assertRaisesRegex(ValueError, "raw bytes"):
            self.build()

    def test_total_metadata_bound_refused_without_large_file(self):
        for path in metadata.IMPLEMENTATION_PATHS:
            self.raw[path] = b"x" * 300000
            self.pins[path] = pins_for({path: self.raw[path]})[path]
        with self.assertRaisesRegex(ValueError, "input budget"):
            self.build()

    def test_duplicate_json_even_with_matching_pin_is_refused(self):
        raw = self.raw[metadata.QUALIFICATION]
        self.raw[metadata.QUALIFICATION] = b'{"network_requests":0,' + raw[raw.index(b"{") + 1:]
        self.pins[metadata.QUALIFICATION] = pins_for({"x": self.raw[metadata.QUALIFICATION]})["x"]
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            self.build()

    def test_nonfinite_json_is_refused(self):
        for raw in (b'{"bad":NaN}', b'{"bad":1e9999}'):
            with self.subTest(raw=raw):
                self.raw[metadata.QUALIFICATION] = raw
                self.pins[metadata.QUALIFICATION] = pins_for({"x": raw})["x"]
                with self.assertRaisesRegex(ValueError, "Nonfinite JSON"):
                    self.build()

    def test_wrong_source_inventory_and_checkpoint_are_refused(self):
        with self.assertRaisesRegex(ValueError, "reviewed source"):
            metadata.build_prospective_source_contract(self.raw, self.pins, expected_source_inventory_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            self.build(evidence_checkpoint="1" * 40)

    def test_last_off_scan_change_refused_after_attacker_repins_input(self):
        self.edit_input(metadata.SOURCE, lambda source: source["scans"][-1].update(url=source["scans"][-2]["url"]))
        with self.assertRaisesRegex(ValueError, "order or identity|inventory"):
            self.build()

    def test_retained_header_etag_change_refused_after_repin(self):
        self.edit_input(metadata.HEADERS, lambda headers: headers[-1].update(etag='"substituted"'))
        with self.assertRaisesRegex(ValueError, "header source binding"):
            self.build()

    def test_retained_header_integer_float_boolean_aliases_refused(self):
        for field, index, replacement in (("dataset_shape", 1, True), ("dataset_chunks", 0, 1.0)):
            with self.subTest(field=field):
                self.setUp()
                self.edit_input(metadata.HEADERS, lambda headers: headers[0][field].__setitem__(index, replacement))
                with self.assertRaisesRegex(ValueError, "header source binding|Retained header"):
                    self.build()

    def test_bank_shape_numeric_alias_refused_even_with_coherent_bank_hash(self):
        def change(banks):
            banks[0]["shape"][0] = 81.0
            banks[0]["bank_identity"] = metadata.digest({k: v for k, v in banks[0].items() if k != "bank_identity"})
        self.edit_input(metadata.BANKS, change)
        with self.assertRaisesRegex(ValueError, "Bank schema"):
            self.build()

    def test_historical_session_limit_change_refused(self):
        self.edit_input(metadata.SOURCE, lambda source: source["session_limits"].update(max_bytes=1073741824))
        with self.assertRaisesRegex(ValueError, "session declaration"):
            self.build()

    def test_overlapping_roles_refused_even_with_rehashed_window_identity(self):
        def overlap(design):
            first, second = design["windows"][:2]
            for key in ("archive_interval", "archive_chunk_index", "payload_keys", "payload_keys_sha256", "native_frequency_low_hz",
                        "native_frequency_high_hz", "proposed_first_on_midpoint_carrier_center_hz"):
                second[key] = copy.deepcopy(first[key])
            second["identity"] = metadata.legacy_digest({k: v for k, v in second.items() if k != "identity"})
        self.edit_input(metadata.GEOMETRY, overlap)
        with self.assertRaisesRegex(ValueError, "share native chunk"):
            self.build()

    def test_rounding_clock_receipt_cannot_replace_exact_rational_clock(self):
        def change(banks):
            banks[0]["provenance"]["clock_rationals_sha256"] = "0" * 64
            banks[0]["bank_identity"] = metadata.digest({k: v for k, v in banks[0].items() if k != "bank_identity"})
        self.edit_input(metadata.BANKS, change)
        with self.assertRaisesRegex(ValueError, "clock/rate/width"):
            self.build()

    def test_expanded_rate_width_frame_and_fake_bank_identity_refused(self):
        for field, replacement in (("rate_tenths", list(range(-41, 41))), ("widths", [1, 3, 5, 257]), ("frame", "barycentric")):
            with self.subTest(field=field):
                self.setUp()
                def change(banks):
                    banks[0]["provenance"][field] = replacement
                    banks[0]["bank_identity"] = metadata.digest({k: v for k, v in banks[0].items() if k != "bank_identity"})
                self.edit_input(metadata.BANKS, change)
                with self.assertRaisesRegex(ValueError, "clock/rate/width"):
                    self.build()
        self.setUp()
        self.edit_input(metadata.BANKS, lambda banks: banks[0].update(bank_identity="0" * 64))
        with self.assertRaisesRegex(ValueError, "bank identity"):
            self.build()

    def test_scientific_rank_tie_empty_gate_changes_refused(self):
        for field, value in (("reference_count", 4), ("denominator", 5), ("keep_every_empty", False), ("ties_randomized", True), ("ceiling_numerator", True)):
            with self.subTest(field=field):
                self.setUp()
                self.edit_input(metadata.PROPOSAL, lambda proposal: proposal["rank_rule"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "rank/EMPTY"):
                    self.build()

    def test_incomplete_or_executed_proposal_is_not_empty_success(self):
        self.edit_input(metadata.PROPOSAL, lambda proposal: proposal["cases"].pop())
        with self.assertRaisesRegex(ValueError, "127/24"):
            self.build()
        self.setUp()
        self.edit_input(metadata.PROPOSAL, lambda proposal: proposal["cases"][0].update(executed=True))
        with self.assertRaisesRegex(ValueError, "spent, executed"):
            self.build()

    def test_metadata_proximity_does_not_upgrade_physical_science(self):
        self.edit_input(metadata.QUALIFICATION, lambda qualification: qualification.update(physical_motion_bank_qualified=True))
        with self.assertRaisesRegex(ValueError, "upgrade scientific"):
            self.build()

    def test_all_future_authority_parameters_are_refused_not_trusted(self):
        for field in ("intended_code_runtime_binding", "scientific_certificate_pin", "joined_transport_certificate_pin",
                      "reservation_store", "cumulative_limits", "trial_protocol_pin"):
            for value in (True, {"status": "passed"}, {"kind": "local-fixture"}, {"kind": "github"}):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, "cannot be supplied"):
                        self.build(**{field: value})

    def test_coherently_rehashed_wrapper_passed_gate_is_rejected(self):
        outputs = self.resigned_outputs(lambda docs: docs["prospective_wrapper"]["prospective_source_fields"]["gates"]["prospective_protocol"].update(status="passed"))
        with self.assertRaisesRegex(ValueError, "source fields"):
            self.validate(outputs)

    def test_rehashed_fake_runtime_allocation_and_certificate_are_rejected(self):
        for field, value in (("hdf5_runtime", {"numpy": "2.3.5"}), ("reservation_store", {"kind": "github"}),
                             ("scientific_certificate", {"passed": True}), ("cumulative_limits", {"max_requests": 500})):
            with self.subTest(field=field):
                outputs = self.resigned_outputs(lambda docs: docs["prospective_wrapper"]["prospective_source_fields"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "source fields"):
                    self.validate(outputs)

    def test_rehashed_shared_observation_forgery_is_recomputed(self):
        def change(docs):
            for name in ("admission_matrix", "provenance_rebinding"):
                docs[name]["observed_semantics"]["distinct_native_chunk_identities"] = 96
        with self.assertRaisesRegex(ValueError, "matrix closure"):
            self.validate(self.resigned_outputs(change))

    def test_json_numeric_equality_cannot_substitute_float_clock_rationals(self):
        for replacement in (0.0, False):
            with self.subTest(replacement=replacement):
                def change(docs):
                    for name in ("admission_matrix", "provenance_rebinding"):
                        docs[name]["observed_semantics"]["header_clock_rationals"][0][1][0] = replacement
                with self.assertRaisesRegex(ValueError, "matrix closure"):
                    self.validate(self.resigned_outputs(change))

    def test_numeric_boolean_equivalence_cannot_rewrite_prospective_pin_bytes(self):
        def change(docs):
            pins = docs["admission_matrix"]["externally_supplied_raw_file_pins"]
            pins[metadata.HEADERS]["bytes"] = float(pins[metadata.HEADERS]["bytes"])
        with self.assertRaisesRegex(ValueError, "matrix closure"):
            self.validate(self.resigned_outputs(change))

    def test_rehashed_requirement_deletion_or_executable_rebinding_refused(self):
        with self.assertRaisesRegex(ValueError, "matrix closure"):
            self.validate(self.resigned_outputs(lambda docs: docs["admission_matrix"]["requirements"].pop()))
        with self.assertRaisesRegex(ValueError, "rebinding boundary"):
            self.validate(self.resigned_outputs(lambda docs: docs["provenance_rebinding"].update(new_executable_source_contract_sha256="0" * 64)))

    def test_output_authority_status_counters_and_extension_refused(self):
        for field, value in (("status", "READY"), ("stop_date", "2026-10-16"),
                             ("authority", {**metadata._authority(), "spectral_access_authorized": True}),
                             ("authority", {**metadata._authority(), "spectral_access_authorized": 0}),
                             ("workload_counters", {**metadata._counters(), "rng_draws": 1})):
            with self.subTest(field=field, value=value):
                outputs = self.resigned_outputs(lambda docs: docs["prospective_wrapper"].update({field: value}))
                with self.assertRaisesRegex(ValueError, "promote authority"):
                    self.validate(outputs)

    def test_unknown_output_authority_fields_refused_after_rehash(self):
        outputs = self.resigned_outputs(lambda docs: docs["admission_matrix"].update(spectral_access_authorized=True))
        with self.assertRaisesRegex(ValueError, "Unknown output"):
            self.validate(outputs)

    def test_missing_wrong_or_unbounded_output_pin_refused(self):
        pins = pins_for(self.original_outputs)
        pins["prospective_wrapper"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "retained pin"):
            self.validate(output_pins=pins)
        outputs = dict(self.original_outputs)
        outputs["prospective_wrapper"] = b"x" * (metadata.MAX_OUTPUT_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "retained pin"):
            self.validate(outputs)
        del outputs["admission_matrix"]
        with self.assertRaisesRegex(ValueError, "output inventory"):
            self.validate(outputs)

    def test_noncanonical_output_refused_even_with_matching_pin(self):
        outputs = dict(self.original_outputs)
        outputs["prospective_wrapper"] = json.dumps(json.loads(outputs["prospective_wrapper"]), indent=2).encode()
        with self.assertRaisesRegex(ValueError, "canonical"):
            self.validate(outputs)

    def test_duplicate_output_members_refused_even_with_matching_pin(self):
        outputs = dict(self.original_outputs)
        outputs["prospective_wrapper"] = b'{"status":"PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED",' + outputs["prospective_wrapper"][1:]
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            self.validate(outputs)

    def test_validator_does_not_call_builder(self):
        with mock.patch.object(metadata, "build_prospective_source_contract", side_effect=AssertionError("builder called")):
            self.assertEqual(self.validate()["status"], "VERIFIED_BLOCKED_METADATA_ONLY")

    def test_pure_operations_do_not_open_files_launch_children_network_or_import_runtime(self):
        with mock.patch("builtins.open", side_effect=AssertionError("file I/O")), \
             mock.patch("socket.socket", side_effect=AssertionError("network")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("child")), \
             mock.patch("importlib.import_module", side_effect=AssertionError("runtime import")):
            outputs = self.build()
            self.assertEqual(self.validate(outputs)["status"], "VERIFIED_BLOCKED_METADATA_ONLY")

    def test_import_closure_contains_only_approved_standard_library(self):
        tree = ast.parse(Path(metadata.__file__).read_text())
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        modules.update(name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names)
        self.assertEqual(modules, {"fractions", "hashlib", "json", "math", "re"})


if __name__ == "__main__":
    unittest.main()
