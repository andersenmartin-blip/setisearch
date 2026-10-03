"""Candidate certificate metadata tests; no codec packages or payload access.

The fixture consists only of explicitly named, bounded source/JSON/log bytes.
Coherently re-pinned report mutations exercise semantic checks independently of
the outer SHA checks. No receipt path is followed into a native library or HDF5.
"""

import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREFIX = HERE.name + "/"
MODULE_PATH = HERE / "candidate_codec_certificate.py"
VERIFIER_PIN = {"bytes": 1, "sha256": "a" * 64}


def load_standalone_verifier():
    spec = importlib.util.spec_from_file_location("candidate_codec_certificate_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Standalone certificate verifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


certificate = load_standalone_verifier()


def read_metadata(relative):
    path = ROOT / relative
    if (path.suffix not in (".py", ".json", ".log")
            or Path(relative).is_absolute() or ".." in Path(relative).parts):
        raise AssertionError("Nonmetadata test input: " + relative)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1024 * 1024:
            raise AssertionError("Unbounded or aliased test input: " + relative)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(1024 * 1024 + 1)
        after = os.fstat(fd)
        fields = ("st_dev", "st_ino", "st_size", "st_nlink", "st_mtime_ns", "st_ctime_ns")
        if len(raw) > 1024 * 1024 or any(getattr(before, key) != getattr(after, key) for key in fields):
            raise AssertionError("Test input changed during bounded read: " + relative)
        return raw
    finally:
        os.close(fd)


class CandidateCodecCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_raw = {}
        for relative in certificate.INPUT_PATHS:
            # Refuse accidental expansion into a payload/native/runtime fixture.
            cls.original_raw[relative] = read_metadata(relative)
        cls.original_pins = {name: certificate.raw_pin(raw) for name, raw in cls.original_raw.items()}
        cls.verifier_source = read_metadata(PREFIX + MODULE_PATH.name)

    def setUp(self):
        self.raw = dict(self.original_raw)
        self.pins = copy.deepcopy(self.original_pins)

    def build(self, *, raw=None, pins=None, verifier_pin=None):
        return certificate.build_certificate(
            self.raw if raw is None else raw,
            self.pins if pins is None else pins,
            VERIFIER_PIN if verifier_pin is None else verifier_pin,
        )

    def report(self, basename):
        return json.loads(self.raw[PREFIX + basename])

    def mutate(self, basename, edit):
        name = PREFIX + basename
        value = json.loads(self.raw[name])
        edit(value)
        self.replace_raw(name, certificate.canonical(value))

    def replace_raw(self, name, raw):
        self.raw[name] = raw
        self.pins[name] = certificate.raw_pin(raw)
        # Completion logs independently bind the report bytes. Re-pin those
        # bindings as well so negative mutations reach semantic validation.
        for stem in ("candidate-probe", "source-profile-probe"):
            if name == PREFIX + stem + ".json":
                stdout = PREFIX + stem + ".stdout.log"
                wire = json.loads(self.raw[stdout])
                wire["report"].update(self.pins[name])
                self.raw[stdout] = certificate.canonical(wire)
                self.pins[stdout] = certificate.raw_pin(self.raw[stdout])

    def reject_mutation(self, basename, edit):
        self.mutate(basename, edit)
        with self.assertRaises(ValueError):
            self.build()

    def test_published_metadata_builds_and_verifies_deterministically(self):
        self.assertEqual(set(self.raw), set(certificate.INPUT_PATHS))
        self.assertEqual(self.pins, certificate.PUBLISHED_INPUT_PINS)
        result = self.build()
        self.assertEqual(set(result), {
            "schema", "authority", "provenance", "evidence_pins", "verifier_code_pin",
            "source_profile", "runtime", "coverage", "pending_scientific_fields",
            "authority_boundaries",
        })
        self.assertEqual(result["verifier_code_pin"], VERIFIER_PIN)
        self.assertEqual(result["pending_scientific_fields"],
                         self.report("source-profile-probe.json")["scientific_missing_fields_unchanged"])
        self.assertEqual(len(result["pending_scientific_fields"]), 11)
        encoded = certificate.canonical(result)
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(encoded, certificate.canonical(self.build()))
        checked = certificate.verify_certificate(
            encoded, certificate.raw_pin(encoded), self.raw, self.pins, VERIFIER_PIN)
        self.assertEqual(checked, result)

    def test_validation_uses_supplied_bytes_without_payload_or_package_access(self):
        import builtins
        original_import = builtins.__import__

        def metadata_import(name, *args, **kwargs):
            if name.split(".", 1)[0] in {"numpy", "h5py", "hdf5plugin", "seti_repeater"}:
                raise AssertionError("Scientific or codec package import: " + name)
            return original_import(name, *args, **kwargs)

        with (mock.patch("builtins.open", side_effect=AssertionError("Filesystem access")),
              mock.patch("io.open", side_effect=AssertionError("Filesystem access")),
              mock.patch("os.open", side_effect=AssertionError("Filesystem access")),
              mock.patch.object(Path, "open", side_effect=AssertionError("Filesystem access")),
              mock.patch.object(Path, "read_bytes", side_effect=AssertionError("Filesystem access")),
              mock.patch.object(Path, "read_text", side_effect=AssertionError("Filesystem access")),
              mock.patch("builtins.__import__", side_effect=metadata_import)):
            # Include module initialization in the purity check after reading
            # its bounded standalone source, without executing any src module.
            namespace = {"__name__": "candidate_codec_certificate_purity_test", "__file__": str(MODULE_PATH)}
            exec(compile(self.verifier_source, str(MODULE_PATH), "exec"), namespace)
            result = namespace["build_certificate"](self.raw, self.pins, VERIFIER_PIN)
            raw = namespace["canonical"](result)
            self.assertEqual(namespace["verify_certificate"](
                raw, namespace["raw_pin"](raw), self.raw, self.pins, VERIFIER_PIN), result)

    def test_semantically_unchanged_reports_can_be_coherently_repinned(self):
        for basename in ("source-profile-probe.json", "candidate-probe.json"):
            raw = json.dumps(self.report(basename), sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
            self.replace_raw(PREFIX + basename, raw)
            self.assertNotEqual(self.pins[PREFIX + basename], self.original_pins[PREFIX + basename])
        result = self.build()
        raw = certificate.canonical(result)
        self.assertEqual(certificate.verify_certificate(
            raw, certificate.raw_pin(raw), self.raw, self.pins, VERIFIER_PIN), result)
        self.assertEqual(result["pending_scientific_fields"],
                         self.report("source-profile-probe.json")["scientific_missing_fields_unchanged"])

    def test_valid_changed_resource_metrics_are_admitted_without_baseline_provenance(self):
        original = self.report("source-profile-probe.json")
        limits = original["candidate_resource_limits"]
        target_seconds = original["observed_seconds"] + 0.125
        target_rss = original["observed_peak_rss_bytes"] + 4096
        self.assertLess(target_seconds, limits["seconds"])
        self.assertLess(target_rss, limits["peak_rss_bytes"])
        self.mutate("source-profile-probe.json", lambda doc: doc.update(
            observed_seconds=target_seconds, observed_peak_rss_bytes=target_rss))
        changed = self.report("source-profile-probe.json")
        self.assertEqual(changed["observed_seconds"], target_seconds)
        self.assertEqual(changed["observed_peak_rss_bytes"], target_rss)
        self.assertNotEqual(self.pins[PREFIX + "source-profile-probe.json"],
                            self.original_pins[PREFIX + "source-profile-probe.json"])
        self.assertNotEqual(self.pins[PREFIX + "source-profile-probe.stdout.log"],
                            self.original_pins[PREFIX + "source-profile-probe.stdout.log"])
        result = self.build()
        self.assertIs(result["provenance"]["provided_raw_pin_map_matches_published_baseline"], False)
        self.assertIs(result["provenance"]["remote_origin_readback_verified_by_this_pure_verifier"], False)
        self.assertTrue(all(value is False for value in result["authority_boundaries"].values()))
        raw = certificate.canonical(result)
        self.assertEqual(certificate.verify_certificate(
            raw, certificate.raw_pin(raw), self.raw, self.pins, VERIFIER_PIN), result)

    def actual_cli_reader(self):
        """Compile only the held source's exact nested main.read function."""
        tree = ast.parse(self.verifier_source, filename=str(MODULE_PATH))
        mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
        self.assertEqual(len(mains), 1)
        readers = [node for node in mains[0].body if isinstance(node, ast.FunctionDef) and node.name == "read"]
        self.assertEqual(len(readers), 1)
        selected = ast.Module(body=[copy.deepcopy(readers[0])], type_ignores=[])
        self.assertEqual(len(selected.body), 1)
        namespace = {"_need": certificate._need, "MAX_FILE_BYTES": certificate.MAX_FILE_BYTES,
                     "Path": Path, "os": os, "stat": stat}
        exec(compile(ast.fix_missing_locations(selected), str(MODULE_PATH), "exec"), namespace)
        return namespace["read"]

    def test_actual_cli_reader_accepts_bounded_canonical_json_readonly_nofollow(self):
        reader = self.actual_cli_reader()
        with tempfile.TemporaryDirectory(prefix="candidate-certificate-reader-", dir=HERE) as directory:
            path = Path(directory) / "bounded.json"
            raw = b'{"purpose":"metadata-only"}\n'
            path.write_bytes(raw)
            original_open = os.open
            with mock.patch("os.open", wraps=original_open) as opened:
                self.assertEqual(reader(path), raw)
            opened.assert_called_once()
            actual_path, flags = opened.call_args.args
            self.assertEqual(actual_path, path)
            self.assertEqual(flags, os.O_RDONLY | os.O_NOFOLLOW)
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            self.assertEqual(flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND), 0)

    def test_actual_cli_reader_refuses_file_symlink_and_parent_alias_before_open(self):
        reader = self.actual_cli_reader()
        with tempfile.TemporaryDirectory(prefix="candidate-certificate-reader-", dir=HERE) as directory:
            base = Path(directory)
            target = base / "target.json"
            target.write_bytes(b'{"purpose":"metadata-only"}\n')
            link = base / "file-link.json"
            link.symlink_to(target)
            parent_alias = base / "parent-alias"
            parent_alias.symlink_to(base, target_is_directory=True)
            for path in (link, parent_alias / target.name):
                with self.subTest(path=path.name):
                    with mock.patch("os.open", side_effect=AssertionError("Alias must be refused before open")) as opened:
                        with self.assertRaisesRegex(ValueError, "canonical nonsymlink"):
                            reader(path)
                        opened.assert_not_called()

    def test_actual_cli_reader_refuses_nonregular_directory_before_open(self):
        reader = self.actual_cli_reader()
        with tempfile.TemporaryDirectory(prefix="candidate-certificate-reader-", dir=HERE) as directory:
            with mock.patch("os.open", side_effect=AssertionError("Directory must be refused before open")) as opened:
                with self.assertRaisesRegex(ValueError, "canonical nonsymlink"):
                    reader(Path(directory))
                opened.assert_not_called()

    def test_actual_cli_reader_refuses_oversized_json_before_reading_bytes(self):
        reader = self.actual_cli_reader()
        with tempfile.TemporaryDirectory(prefix="candidate-certificate-reader-", dir=HERE) as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b'"' + b'x' * certificate.MAX_FILE_BYTES + b'"\n')
            self.assertGreater(path.stat().st_size, certificate.MAX_FILE_BYTES)
            with mock.patch("os.fdopen", side_effect=AssertionError("Oversized metadata bytes must not be read")) as wrapped:
                with self.assertRaisesRegex(ValueError, "CLI metadata byte limit"):
                    reader(path)
                wrapped.assert_not_called()

    def test_actual_cli_reader_refuses_each_descriptor_identity_change(self):
        reader = self.actual_cli_reader()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        with tempfile.TemporaryDirectory(prefix="candidate-certificate-reader-", dir=HERE) as directory:
            path = Path(directory) / "stable.json"
            path.write_bytes(b'{"purpose":"metadata-only"}\n')
            original_fstat = os.fstat
            original_close = os.close
            for changed_field in fields:
                with self.subTest(changed_field=changed_field):
                    calls = []
                    def changed_after(descriptor, field=changed_field):
                        measured = original_fstat(descriptor)
                        calls.append(descriptor)
                        if len(calls) == 1:
                            return measured
                        values = {key: getattr(measured, key) for key in fields}
                        values[field] += 1
                        return SimpleNamespace(**values)
                    with (mock.patch("os.fstat", side_effect=changed_after),
                          mock.patch("os.close", wraps=original_close) as closed):
                        with self.assertRaisesRegex(ValueError, "descriptor changed during read"):
                            reader(path)
                        self.assertEqual(len(calls), 2)
                        self.assertEqual(calls[0], calls[1])
                        closed.assert_called_once_with(calls[0])

    def test_unpinned_raw_tamper_is_rejected(self):
        name = PREFIX + "source-profile-probe.json"
        self.raw[name] += b" "
        with self.assertRaises(ValueError):
            self.build()

    def test_complete_input_and_external_pin_inventories_are_required(self):
        name = PREFIX + "source-profile-probe.json"
        for subject in ("raw", "pins"):
            with self.subTest(subject=subject):
                raw, pins = dict(self.raw), copy.deepcopy(self.pins)
                (raw if subject == "raw" else pins).pop(name)
                with self.assertRaises(ValueError):
                    self.build(raw=raw, pins=pins)
        for subject in ("raw", "pins"):
            with self.subTest(extra=subject):
                raw, pins = dict(self.raw), copy.deepcopy(self.pins)
                if subject == "raw":
                    raw[PREFIX + "unrequested.json"] = b"{}\n"
                else:
                    pins[PREFIX + "unrequested.json"] = certificate.raw_pin(b"{}\n")
                with self.assertRaises(ValueError):
                    self.build(raw=raw, pins=pins)

    def test_external_pins_require_exact_byte_count_and_sha256(self):
        name = PREFIX + "source-profile-probe.json"
        for field, replacement in (("bytes", True), ("bytes", -1),
                                   ("bytes", self.pins[name]["bytes"] + 1),
                                   ("sha256", "b" * 64), ("sha256", "not-a-pin")):
            with self.subTest(field=field, replacement=replacement):
                pins = copy.deepcopy(self.pins)
                pins[name][field] = replacement
                with self.assertRaises(ValueError):
                    self.build(pins=pins)
        for bad in (None, {"bytes": True, "sha256": "a" * 64},
                    {"bytes": 1, "sha256": "short"},
                    {"bytes": 1, "sha256": "a" * 64, "self_authorized": True}):
            with self.subTest(verifier_pin=bad):
                with self.assertRaises((ValueError, TypeError)):
                    certificate.build_certificate(self.raw, self.pins, bad)

    def test_source_and_producer_code_cannot_be_coherently_repinned(self):
        fixed = [name for name in self.raw if not name.startswith(PREFIX)]
        fixed += [PREFIX + "candidate_probe.py", PREFIX + "source_profile_probe.py"]
        self.assertEqual(len(fixed), 11)
        for name in fixed:
            with self.subTest(name=name):
                raw, pins = dict(self.raw), copy.deepcopy(self.pins)
                raw[name] += b"\n"
                pins[name] = certificate.raw_pin(raw[name])
                with self.assertRaises(ValueError):
                    self.build(raw=raw, pins=pins)

    def test_report_cannot_substitute_or_omit_its_nine_held_source_pins(self):
        source = "src/seti_repeater/hdf5_filter_contract_radio.py"
        edits = (
            lambda doc: doc["held_metadata_and_source_pins"].pop(source),
            lambda doc: doc["held_metadata_and_source_pins"][source].update(sha256="b" * 64),
            lambda doc: doc["held_metadata_and_source_pins"][source].update(bytes=1),
            lambda doc: doc["held_metadata_and_source_pins"].update({"extra.py": {"bytes": 1, "sha256": "b" * 64}}),
        )
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", edit)

    def test_malformed_and_duplicate_key_json_cannot_be_externally_repinned(self):
        name = PREFIX + "source-profile-probe.json"
        for raw in (b"{not-json}\n", b"[]\n", b"null\n",
                    self.raw[name].rstrip()[:-1] + b',"metadata_case_law_count":22}\n'):
            with self.subTest(raw_prefix=raw[:30]):
                self.setUp()
                self.replace_raw(name, raw)
                with self.assertRaises(ValueError):
                    self.build()

    def test_source_profile_identity_and_geometry_drift_are_rejected(self):
        changes = {
            "source_inventory_sha256": "b" * 64,
            "source_shape": [16, 1, 264503295],
            "source_chunks": [1, 1, 524288],
            "source_dtype": "<f8",
            "decoded_chunk_bytes": 4194303,
            "six_scan_metadata_declarations_checked": 5,
            "row_indices_exercised": [0, 14],
        }
        for key, value in changes.items():
            with self.subTest(key=key):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, k=key, v=value: doc.update({k: v}))

    def test_modern_encoder_is_not_the_exact_legacy_source_pipeline(self):
        current = self.report("source-profile-probe.json")["current_encoder_filter_pipeline"]
        self.assertNotEqual(current, [[32008, 1, [0, 3, 4, 0, 2]]])
        self.reject_mutation("source-profile-probe.json", lambda doc: doc.update(exact_source_filter_pipeline=current))

    def test_each_legacy_client_datum_id_and_flags_are_bound(self):
        for index in range(5):
            with self.subTest(index=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, i=index:
                                     doc["exact_source_filter_pipeline"][0][2].__setitem__(i, 99))
        for index, value in ((0, 32004), (1, 0)):
            with self.subTest(field=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, i=index, v=value:
                                     doc["exact_source_filter_pipeline"][0].__setitem__(i, v))

    def test_measured_receipt_order_is_bound_without_claiming_new_source_case_laws(self):
        self.reject_mutation("candidate-probe.json", lambda doc: doc["codec_probes"][1]["filters"].reverse())
        self.setUp()
        self.reject_mutation("source-profile-probe.json", lambda doc:
                             doc["exact_source_filter_pipeline"][0][2].reverse())

    def test_each_runtime_version_is_bound_in_both_reports(self):
        for basename, field in (("source-profile-probe.json", "runtime_version_fields_used_by_source_reader"),
                                ("candidate-probe.json", "runtime")):
            for package in ("numpy", "h5py", "hdf5", "hdf5plugin"):
                with self.subTest(basename=basename, package=package):
                    self.setUp()
                    self.reject_mutation(basename, lambda doc, f=field, p=package:
                                         doc[f].__setitem__(p, "0.0.0"))

    def test_native_binary_sha_missing_duplicate_and_cohort_drift_are_rejected(self):
        edits = (
            lambda doc: doc["candidate_native_binaries"][0].update(sha256="b" * 64),
            lambda doc: doc["candidate_native_binaries"].pop(),
            lambda doc: doc["candidate_native_binaries"].append(copy.deepcopy(doc["candidate_native_binaries"][0])),
            lambda doc: doc["candidate_native_binaries"][0].update(site_relative_path="h5py/forged.so"),
            lambda doc: doc["candidate_native_binaries"][0].update(bytes=1),
        )
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                self.setUp()
                self.reject_mutation("candidate-probe.json", edit)

    def test_official_wheel_provenance_cannot_be_substituted(self):
        changes = {"version": "0.0.0", "sha256": "b" * 64,
                   "url": "https://example.invalid/numpy.whl", "filename": "other.whl",
                   "bytes": 1, "yanked": True, "download_file_readback_sha256_verified": False}
        for field, value in changes.items():
            with self.subTest(field=field):
                self.setUp()
                self.reject_mutation("wheel-provenance.json", lambda doc, f=field, v=value:
                                     doc["official_package_wheels"][0].update({f: v}))

    def test_official_version_metadata_must_match_the_selected_wheel(self):
        for basename in ("numpy-2.3.5-pypi.json", "h5py-3.16.0-pypi.json", "hdf5plugin-7.1.0-pypi.json"):
            with self.subTest(basename=basename):
                self.setUp()
                self.reject_mutation(basename, lambda doc: doc["info"].update(version="0.0.0"))
        filename = self.report("wheel-provenance.json")["official_package_wheels"][0]["filename"]
        for change in ({"yanked": True}, {"digests": {"sha256": "b" * 64}}, {"size": 1}):
            with self.subTest(selected_wheel=change):
                self.setUp()
                def edit(doc, replacement=change):
                    entry = next(item for item in doc["urls"] if item["filename"] == filename)
                    entry.update(replacement)
                self.reject_mutation("numpy-2.3.5-pypi.json", edit)

    def test_exact_six_chunk_and_selection_coverage_is_required(self):
        for field in ("raw_chunk_receipts", "decode_receipts"):
            for operation in ("missing", "duplicate", "replace_last"):
                with self.subTest(field=field, operation=operation):
                    self.setUp()
                    def edit(doc, f=field, op=operation):
                        rows = doc[f]
                        if op == "missing":
                            rows.pop()
                        elif op == "duplicate":
                            rows.append(copy.deepcopy(rows[0]))
                        else:
                            # Counts stay six while one row/role identity disappears.
                            rows[-1] = copy.deepcopy(rows[0])
                    self.reject_mutation("source-profile-probe.json", edit)

    def test_raw_chunk_masks_offsets_sizes_and_hashes_are_bound(self):
        changes = {"row": 14, "role": "pilot", "offset": [0, 0, 0],
                   "filter_mask": 1, "compressed_bytes": 1, "compressed_sha256": "b" * 64}
        for key, value in changes.items():
            with self.subTest(key=key):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, k=key, v=value:
                                     doc["raw_chunk_receipts"][0].update({k: v}))

    def test_decode_selection_mapping_cell_counts_and_bit_exact_receipts_are_bound(self):
        changes = {"row": 14, "role": "pilot", "chunk_index": 158,
                   "archive_interval": [167215105, 167280641], "decoded_cells": 1048575,
                   "selected_cells": 65535, "decoded_sha256": "b" * 64,
                   "selected_sha256": "b" * 64, "bit_exact": False}
        for key, value in changes.items():
            with self.subTest(key=key):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, k=key, v=value:
                                     doc["decode_receipts"][0].update({k: v}))

    def test_rehashed_aggregate_counts_cannot_inflate_actual_coverage(self):
        for key, value in (("complete_chunks_decoded", 7), ("decoded_cells_bit_exact", 6291457),
                           ("selected_cells_bit_exact", 393217), ("metadata_case_law_count", 23)):
            with self.subTest(key=key):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, k=key, v=value: doc.update({k: v}))

    def test_every_metadata_case_requires_its_exact_name_outcome_and_pass(self):
        laws = self.report("source-profile-probe.json")["metadata_case_laws"]
        self.assertEqual(len(laws), 22)
        for index in range(22):
            for field, replacement in (("pass", False), ("name", "unexecuted_law"),
                                       ("expected", "reject" if laws[index]["expected"] == "accept" else "accept")):
                with self.subTest(index=index, field=field):
                    self.setUp()
                    self.reject_mutation("source-profile-probe.json", lambda doc, i=index, f=field, v=replacement:
                                         doc["metadata_case_laws"][i].update({f: v}))
        edits = (
            lambda doc: doc["metadata_case_laws"].pop(),
            lambda doc: doc["metadata_case_laws"].append(copy.deepcopy(doc["metadata_case_laws"][0])),
            lambda doc: doc["metadata_case_laws"].__setitem__(-1, copy.deepcopy(doc["metadata_case_laws"][0])),
            lambda doc: doc["metadata_case_laws"][0].update(name="unexecuted_law"),
            lambda doc: doc["metadata_case_laws"][0].update(expected="reject"),
        )
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", edit)

    def test_synthetic_file_receipt_substitution_is_rejected_without_opening_files(self):
        for key, value in (("sha256", "b" * 64), ("bytes", 1), ("path", "/untrusted/fixture.h5")):
            with self.subTest(key=key):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, k=key, v=value:
                                     doc["fresh_synthetic_files"][0].update({k: v}))

    def test_candidate_receipts_cannot_grant_unexecuted_or_scientific_authority(self):
        false_fields = (
            "rows_1_through_14_exercised", "normalization_or_detector_invoked",
            "acquisition_or_scientific_modules_loaded", "archive_payload_bytes_verified",
            "local_current_encoder_is_original_archive_encoder",
            "hdf5_runtime_field_of_executable_source_contract_filled",
            "authenticated_source_specific_codec_runtime_case_law_certificate",
            "full_source_contract_or_scientific_certificate_ready",
            "primary_runtime_or_frozen_e_material_modified",
        )
        for field in false_fields:
            with self.subTest(field=field):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, f=field: doc.update({f: True}))
        for field in ("network_requests", "rng_draws", "source_analysis_or_reservation_invocations",
                      "telescope_or_holdout_files_opened", "metadata_payload_index_attempts"):
            with self.subTest(counter=field):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, f=field: doc.update({f: 1}))

    def test_report_authority_labels_cannot_claim_source_or_scientific_admission(self):
        for basename, field in (("source-profile-probe.json", "authority"),
                                ("candidate-probe.json", "authority"),
                                ("wheel-provenance.json", "package_authority")):
            with self.subTest(basename=basename):
                self.setUp()
                self.reject_mutation(basename, lambda doc, f=field:
                                     doc.update({f: "scientific-execution-authorized"}))

    def test_candidate_runtime_report_cannot_claim_a_complete_scientific_freeze(self):
        for field in ("complete_execution_runtime_freeze", "source_specific_codec_runtime_certificate",
                      "scientific_trial_admission", "historical_original_runtime_restored"):
            with self.subTest(field=field):
                self.setUp()
                self.reject_mutation("candidate-probe.json", lambda doc, f=field: doc.update({f: True}))

    def test_runtime_report_operation_counters_and_wheel_authority_stay_inactive(self):
        for field in ("project_module_invocations", "rng_invocations", "source_analysis_invocations",
                      "telescope_or_holdout_inputs_opened"):
            with self.subTest(counter=field):
                self.setUp()
                self.reject_mutation("candidate-probe.json", lambda doc, f=field: doc.update({f: 1}))
        for field in ("scientific_execution_authorized", "source_execution_authorized",
                      "primary_runtime_changed", "eleven_source_gates_changed"):
            with self.subTest(wheel_flag=field):
                self.setUp()
                self.reject_mutation("wheel-provenance.json", lambda doc, f=field: doc.update({f: True}))

    def test_loaded_candidate_native_mapping_cannot_contradict_binary_cohort(self):
        native_paths = {row["path"] for row in self.report("candidate-probe.json")["candidate_native_binaries"]}
        mapped = self.report("candidate-probe.json")["loaded_native_mappings"]
        index = next(i for i, row in enumerate(mapped) if row["path"] in native_paths)
        self.reject_mutation("candidate-probe.json", lambda doc:
                             doc["loaded_native_mappings"][index].update(sha256="b" * 64))

    def test_scientific_missing_fields_remain_exactly_eleven(self):
        edits = (
            lambda doc: doc.update(scientific_missing_field_count=10),
            lambda doc: doc["scientific_missing_fields_unchanged"].pop(),
            lambda doc: doc["scientific_missing_fields_unchanged"].__setitem__(1, "hdf5_runtime_admitted"),
        )
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", edit)

    def test_observed_resource_metrics_must_respect_the_bounded_probe(self):
        for field, value in (("observed_peak_rss_bytes", 268435457),
                             ("observed_seconds", 61), ("observed_seconds", -1)):
            with self.subTest(field=field, value=value):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", lambda doc, f=field, v=value: doc.update({f: v}))

    def test_numeric_boolean_and_float_substitutions_are_not_exact_metadata(self):
        edits = (
            lambda doc: doc["source_chunks"].__setitem__(0, True),
            lambda doc: doc["decode_receipts"][0].update(row=False),
            lambda doc: doc["raw_chunk_receipts"][0].update(filter_mask=False),
            lambda doc: doc.update(metadata_case_law_count=22.0),
            lambda doc: doc["metadata_case_laws"][0].update(**{"pass": 1}),
        )
        for index, edit in enumerate(edits):
            with self.subTest(edit=index):
                self.setUp()
                self.reject_mutation("source-profile-probe.json", edit)

    def test_certificate_verification_requires_outer_pin_and_semantic_reconstruction(self):
        result = self.build()
        raw = certificate.canonical(result)
        with self.assertRaises(ValueError):
            certificate.verify_certificate(raw + b" ", certificate.raw_pin(raw),
                                           self.raw, self.pins, VERIFIER_PIN)
        for field in result:
            with self.subTest(field=field):
                changed = copy.deepcopy(result)
                changed[field] = "forged-scientific-admission"
                changed_raw = certificate.canonical(changed)
                with self.assertRaises(ValueError):
                    certificate.verify_certificate(changed_raw, certificate.raw_pin(changed_raw),
                                                   self.raw, self.pins, VERIFIER_PIN)
        changed = copy.deepcopy(result)
        changed["self_authorized"] = True
        changed_raw = certificate.canonical(changed)
        with self.assertRaises(ValueError):
            certificate.verify_certificate(changed_raw, certificate.raw_pin(changed_raw),
                                           self.raw, self.pins, VERIFIER_PIN)
        with self.assertRaises(ValueError):
            certificate.verify_certificate(raw, certificate.raw_pin(raw), self.raw, self.pins,
                                           {"bytes": 2, "sha256": "b" * 64})
        duplicate = raw.rstrip()[:-1] + b',"authority":"forged-scientific-admission"}\n'
        with self.assertRaises(ValueError):
            certificate.verify_certificate(duplicate, certificate.raw_pin(duplicate),
                                           self.raw, self.pins, VERIFIER_PIN)


if __name__ == "__main__":
    unittest.main()
