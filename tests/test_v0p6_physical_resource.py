"""End-to-end synthetic tests for the physical resource envelope."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from seti_repeater import cache_manifest_v0p6 as run_cache
from seti_repeater import native_cache_v0p6 as disk_cache
from seti_repeater import physical_resource_manifest_v0p6 as run_resource
from seti_repeater import physical_resource_v0p6 as physical
from seti_repeater import search_v0p6 as core
from seti_repeater.cache_stream_v0p6 import CacheWidthStream


ROOT = Path(__file__).resolve().parents[1]


def _rehash(record, digest_field):
    detached = json.loads(core.canonical_json_bytes(record))
    detached.pop(digest_field, None)
    detached[digest_field] = hashlib.sha256(
        core.canonical_json_bytes(detached)
    ).hexdigest()
    return detached


class PhysicalResourceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        config = json.loads(
            (ROOT / "config/hd156668b_m37_preflight.json").read_text()
        )
        self.scan_definitions = config["scans"]
        labels = [
            {
                "scan_index": scan_index,
                "scan_label": scan["label"],
                "integration_index": integration_index,
            }
            for scan_index, scan in enumerate(self.scan_definitions)
            for integration_index in range(16)
        ]
        self.factor_basis = core.make_factor_basis_from_arrays(
            np.arange(96, dtype=np.float64) + 57_470.0,
            labels,
            np.full(96, 1.01, dtype=np.float64),
            np.zeros((96, 2), dtype=np.float64),
            expected_sha256=None,
        )
        self.template_bank = [core.make_line_template_bank()[0]]
        self.factor_table = core.make_template_factor_table(
            self.factor_basis,
            self.template_bank,
            expected_template_bank_sha256=core.template_bank_sha256(
                self.template_bank
            ),
        )
        self.grid = core.make_proxy_carrier_grid(0.0005, 1.0, 10, 200)
        self.geometry = core.NativeFrequencyGeometry(0.0, 1.0, 1000)
        self.widths = (1,)
        self.caches = self._make_caches()
        self.records, self.retention_certificate = self._retention_product()

    def _make_caches(self):
        caches = {"on": {1: {}}, "off": {1: {}}}
        for scan_index, definition in enumerate(self.scan_definitions):
            label = str(definition["label"])
            kind = str(definition["kind"])
            scan_table = core.factor_table_for_scan(
                self.factor_table, self.factor_basis, label
            )
            plan = core.plan_native_filter_cache(
                self.geometry,
                scan_table,
                self.grid,
                1,
                window_id="synthetic",
                scan_label=label,
                scan_kind=kind,
                source_sha256=f"{scan_index + 1:064x}",
                factor_basis_sha256_value=self.factor_basis.basis_sha256,
                factor_basis_labels_sha256_value=(
                    self.factor_basis.labels_sha256
                ),
                scan_inventory_sha256_value=core.scan_inventory_sha256(
                    self.scan_definitions
                ),
                factor_scan_selection_sha256_value=(
                    core.factor_scan_selection_sha256(
                        self.factor_basis, self.scan_definitions, label
                    )
                ),
                template_bank_sha256_value=(
                    self.factor_table.template_bank_sha256
                ),
            )
            values = np.zeros(plan.payload_shape, dtype=np.dtype("<f4"))
            values.setflags(write=False)
            caches[kind][1][label] = core.NativeFilterCache(
                plan=plan,
                values=values,
                payload_sha256=core.float32_array_sha256(values),
            )
        return caches

    def _retention_product(self):
        bank_sha256 = core.template_bank_sha256(self.template_bank)
        scan_sha256 = core.scan_inventory_sha256(self.scan_definitions)
        on_rows_sha256 = core.factor_row_selection_sha256(
            self.factor_basis, self.scan_definitions, "on"
        )
        shifts = core.make_scramble_shift_table(
            1,
            3,
            self.grid.score_bin_count,
            seed=37_060_828,
            minimum_shift_bins=1,
        )
        calibration = core.CalibrationAccumulator.create(
            window_id="synthetic",
            score_bin_count=self.grid.score_bin_count,
            template_count=1,
            template_bank_sha256_value=bank_sha256,
            factor_basis_sha256_value=self.factor_basis.basis_sha256,
            factor_basis_labels_sha256_value=self.factor_basis.labels_sha256,
            scan_inventory_sha256_value=scan_sha256,
            factor_row_selection_sha256_value=on_rows_sha256,
            factor_table_sha256_value=self.factor_table.factor_table_sha256,
            spectral_widths=self.widths,
            activity_subsets=((0, 2),),
            minimum_active_epoch_snr=3.0,
            stack_statistic="sum",
            scramble_shifts=shifts,
            minimum_shift_bins=1,
            expected_scramble_sha256=core.scramble_table_sha256(shifts),
        )
        calibration_vectors = np.full(
            (3, self.grid.score_bin_count), 3.0, dtype=np.float32
        )
        core.update_calibration(
            calibration,
            calibration_vectors,
            template_index=0,
            width_index=0,
            exclusion_mask=None,
        )
        calibration.finalize()
        threshold = core.calibrated_threshold(
            (calibration,),
            expected_window_ids=("synthetic",),
            reference_floor=7.0,
        )
        ledger = core.ExhaustiveRetentionLedger(
            window_id="synthetic",
            scan_kind="on",
            grid=self.grid,
            threshold_certificate=threshold,
            maximum_records=10,
            template_bank=self.template_bank,
            spectral_widths=self.widths,
            activity_subsets=((0, 2),),
            expected_template_bank_sha256=bank_sha256,
            factor_basis_sha256=self.factor_basis.basis_sha256,
            factor_basis_labels_sha256=self.factor_basis.labels_sha256,
            scan_inventory_sha256=scan_sha256,
            factor_row_selection_sha256=on_rows_sha256,
            factor_table_sha256=self.factor_table.factor_table_sha256,
            epoch_count=3,
            minimum_active_epoch_snr=3.0,
            stack_statistic="sum",
        )
        vectors = np.zeros(
            (3, self.grid.score_bin_count), dtype=np.float32
        )
        vectors[0, 10] = 6.0
        vectors[2, 10] = 6.0
        ledger.add_hypothesis(
            vectors,
            (0, 2),
            template=self.template_bank[0],
            width_index=0,
            width_channels=1,
            exclusion_mask=None,
        )
        records = ledger.finalize()
        certificate = ledger.certificate()
        for record in records:
            record["epoch_vector_product_sha256"] = hashlib.sha256(
                core.canonical_json_bytes(record["record_key"])
                + b"physical resource synthetic epoch product"
            ).hexdigest()
        on_labels = [
            str(item["label"])
            for item in self.scan_definitions
            if item["kind"] == "on"
        ]
        selected = [self.caches["on"][1][label] for label in on_labels]
        provenance = {
            0: (
                tuple(item.plan.plan_sha256 for item in selected),
                tuple(item.payload_sha256 for item in selected),
            )
        }
        certificate["require_epoch_vector_product"] = True
        certificate["epoch_product_inventory_sha256"] = (
            core._epoch_product_inventory_sha256(
                {(0, 0): hashlib.sha256(b"0:0").hexdigest()}
            )
        )
        certificate["cache_provenance_inventory_sha256"] = (
            core._cache_provenance_inventory_sha256(provenance)
        )
        records.sort(key=core._retention_record_sort_key)
        certificate["canonical_record_bytes"] = sum(
            len(core.canonical_json_bytes(item)) for item in records
        )
        certificate["records_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(records)
        ).hexdigest()
        certificate.pop("retention_certificate_sha256")
        certificate["retention_certificate_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(certificate)
        ).hexdigest()
        return records, certificate

    def _streams(self, root):
        cache_root = root / "caches"
        cache_root.mkdir()
        entries = []
        keys = []
        for definition in self.scan_definitions:
            label = str(definition["label"])
            kind = str(definition["kind"])
            cache = self.caches[kind][1][label]
            relative = f"caches/1-{label}.cache"
            receipt = disk_cache.publish_native_filter_cache(
                root / relative, cache
            )
            entries.append(
                run_cache.make_cache_manifest_entry(
                    relative, cache.plan, receipt
                )
            )
            keys.append(("synthetic", label, 1))
        manifest_receipt = run_cache.publish_cache_run_manifest(
            root / "cache-run.json",
            entries,
            run_id="physical-resource-test",
            factor_bundle_manifest_sha256="e" * 64,
            expected_keys=keys,
        )
        manifest = run_cache.open_cache_run_manifest(
            root / "cache-run.json",
            expected_file_sha256=manifest_receipt.file_sha256,
            expected_factor_bundle_manifest_sha256="e" * 64,
            expected_keys=keys,
        )
        payload_nbytes = entries[0].payload_nbytes

        def make(kind):
            labels = tuple(
                str(item["label"])
                for item in self.scan_definitions
                if item["kind"] == kind
            )
            return CacheWidthStream(
                root,
                manifest,
                expected_manifest_file_sha256=manifest_receipt.file_sha256,
                expected_inventory_sha256=manifest_receipt.inventory_sha256,
                expected_factor_bundle_manifest_sha256="e" * 64,
                expected_keys=keys,
                window_id="synthetic",
                scan_kind=kind,
                scan_labels=labels,
                spectral_widths=self.widths,
                maximum_mapped_bytes=3 * payload_nbytes,
            )

        return make("on"), make("off")

    def _execute(self, root):
        on_stream, off_stream = self._streams(root)
        result = physical.execute_physical_evidence_streams(
            self.records,
            self.retention_certificate,
            on_stream,
            off_stream,
            self.scan_definitions,
            self.factor_basis,
            self.factor_table,
            self.template_bank,
            self.grid,
            local_receiver_half_width_hz=100.0,
            local_receiver_peak_snr_floor=5.5,
            single_adjacent_off_snr_floor=5.5,
            maximum_records=10,
            maximum_receiver_queries=3,
            maximum_receiver_local_channel_visits=1_000,
            maximum_signature_record_canonical_bytes=6_144,
            maximum_adjacent_queries=2,
            maximum_evidence_canonical_bytes=100_000,
            expected_on_retention_certificate_sha256=(
                self.retention_certificate["retention_certificate_sha256"]
            ),
            adjacent_chunk_bins=1,
        )
        return result, on_stream, off_stream

    def _published_run_child(self, root):
        result, _, _ = self._execute(root)
        envelope = result["resource_envelope"]
        physical_root = root / "physical"
        physical_root.mkdir()
        relative_path = "physical/synthetic-resource.json"
        artifact_path = root / relative_path
        receipt = physical.publish_physical_resource_artifact(
            artifact_path,
            envelope,
            expected_envelope_sha256=envelope[
                "resource_envelope_sha256"
            ],
        )
        artifact = physical.open_physical_resource_artifact(
            artifact_path,
            expected_file_sha256=receipt.file_sha256,
            expected_envelope_sha256=receipt.resource_envelope_sha256,
            expected_run_id=receipt.run_id,
            expected_cache_run_manifest_file_sha256=(
                receipt.cache_run_manifest_file_sha256
            ),
            expected_factor_bundle_manifest_sha256=(
                receipt.factor_bundle_manifest_sha256
            ),
            expected_on_retention_certificate_sha256=(
                receipt.on_retention_certificate_sha256
            ),
        )
        entry = run_resource.make_physical_resource_run_entry(
            relative_path, artifact
        )
        retention_inventory_sha256 = (
            run_resource.on_retention_inventory_sha256((entry,))
        )
        arguments = {
            "expected_window_ids": ("synthetic",),
            "expected_run_id": receipt.run_id,
            "expected_cache_run_manifest_file_sha256": (
                receipt.cache_run_manifest_file_sha256
            ),
            "expected_factor_bundle_manifest_sha256": (
                receipt.factor_bundle_manifest_sha256
            ),
            "expected_on_retention_inventory_sha256": (
                retention_inventory_sha256
            ),
        }
        return artifact_path, entry, arguments

    def test_sequential_execution_closes_and_binds_both_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            result, on_stream, off_stream = self._execute(Path(directory))
        envelope = result["resource_envelope"]
        validated = physical.validate_physical_resource_envelope(
            envelope,
            expected_envelope_sha256=envelope[
                "resource_envelope_sha256"
            ],
        )
        self.assertEqual(validated, envelope)
        self.assertEqual(
            envelope["resource_envelope_sha256"],
            "f64d93cdb027d09ca6486bd533b48990b11c16451fc5c8b2b57c89bd4e898191",
        )
        self.assertEqual(
            result["execution_result_sha256"],
            "6d323d2142bfc195514ccd8955331d8e30f2175f37fa8b26324baf89b9e919e7",
        )
        self.assertEqual(envelope["aggregate_batch_count"], 2)
        self.assertEqual(envelope["aggregate_opened_cache_count"], 6)
        self.assertEqual(envelope["aggregate_peak_handle_count"], 3)
        self.assertEqual(
            envelope["receiver_result_sha256"],
            result["receiver_result"]["result_sha256"],
        )
        self.assertEqual(
            envelope["adjacent_evidence_sha256"],
            result["adjacent_result"]["certificate"]["evidence_sha256"],
        )
        self.assertEqual(
            result["execution_result_sha256"],
            hashlib.sha256(
                core.canonical_json_bytes(
                    {
                        "receiver_result": result["receiver_result"],
                        "adjacent_result": result["adjacent_result"],
                        "resource_envelope": envelope,
                    }
                )
            ).hexdigest(),
        )
        for stream in (on_stream, off_stream):
            with self.assertRaisesRegex(core.V0P6IncompleteError, "sealed"):
                with stream.open_width(1):
                    pass

    def test_independent_root_and_rehashed_cross_ancestry_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _, _ = self._execute(Path(directory))
        envelope = result["resource_envelope"]
        with self.assertRaisesRegex(core.V0P6ContractError, "trusted receipt"):
            physical.validate_physical_resource_envelope(
                envelope, expected_envelope_sha256="0" * 64
            )

        forged = json.loads(core.canonical_json_bytes(envelope))
        adjacent_stream = forged[
            "adjacent_stream_resource_certificate"
        ]
        adjacent_stream["run_id"] = "different-run"
        forged["adjacent_stream_resource_certificate"] = _rehash(
            adjacent_stream, "stream_resource_certificate_sha256"
        )
        forged = _rehash(forged, "resource_envelope_sha256")
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "one ancestry"
        ):
            physical.validate_physical_resource_envelope(
                forged,
                expected_envelope_sha256=forged[
                    "resource_envelope_sha256"
                ],
            )

    def test_rehashed_stream_cache_mutation_breaks_aggregate_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _, _ = self._execute(Path(directory))
        forged = json.loads(
            core.canonical_json_bytes(result["resource_envelope"])
        )
        receiver_stream = forged[
            "receiver_stream_resource_certificate"
        ]
        receiver_stream["batch_inventory"][0]["cache_receipts"][0][
            "cache_payload_sha256"
        ] = "0" * 64
        receiver_stream["batch_inventory_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(receiver_stream["batch_inventory"])
        ).hexdigest()
        forged["receiver_stream_resource_certificate"] = _rehash(
            receiver_stream, "stream_resource_certificate_sha256"
        )
        forged = _rehash(forged, "resource_envelope_sha256")
        with self.assertRaisesRegex(
            core.V0P6IncompleteError, "accounting changed"
        ):
            physical.validate_physical_resource_envelope(
                forged,
                expected_envelope_sha256=forged[
                    "resource_envelope_sha256"
                ],
            )

    def test_synthetic_envelope_cannot_expand_into_m37_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _, _ = self._execute(Path(directory))
        envelope = result["resource_envelope"]
        with self.assertRaisesRegex(core.V0P6ContractError, "M37 contract"):
            physical.validate_m37_physical_resource_envelope(
                envelope,
                expected_envelope_sha256=envelope[
                    "resource_envelope_sha256"
                ],
            )

    def test_atomic_read_only_artifact_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result, _, _ = self._execute(root)
            envelope = result["resource_envelope"]
            path = root / "physical-resource.json"
            receipt = physical.publish_physical_resource_artifact(
                path,
                envelope,
                expected_envelope_sha256=envelope[
                    "resource_envelope_sha256"
                ],
            )
            self.assertEqual(path.stat().st_mode & 0o222, 0)
            self.assertEqual(
                receipt.file_sha256,
                "7a4c5e36042f687265a0ac3844ae29c6cd7803742e5d61f1512d340e5f178e48",
            )
            self.assertEqual(receipt.file_nbytes, 8_474)
            self.assertEqual(
                receipt.file_sha256,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            opened = physical.open_physical_resource_artifact(
                path,
                expected_file_sha256=receipt.file_sha256,
                expected_envelope_sha256=receipt.resource_envelope_sha256,
                expected_run_id=receipt.run_id,
                expected_cache_run_manifest_file_sha256=(
                    receipt.cache_run_manifest_file_sha256
                ),
                expected_factor_bundle_manifest_sha256=(
                    receipt.factor_bundle_manifest_sha256
                ),
                expected_on_retention_certificate_sha256=(
                    receipt.on_retention_certificate_sha256
                ),
            )
            self.assertEqual(opened.envelope, envelope)
            self.assertEqual(opened.receipt, receipt)
            with self.assertRaises(FileExistsError):
                physical.publish_physical_resource_artifact(
                    path,
                    envelope,
                    expected_envelope_sha256=(
                        envelope["resource_envelope_sha256"]
                    ),
                )

    def test_artifact_requires_independent_file_and_ancestry_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result, _, _ = self._execute(root)
            envelope = result["resource_envelope"]
            path = root / "physical-resource.json"
            receipt = physical.publish_physical_resource_artifact(
                path,
                envelope,
                expected_envelope_sha256=envelope[
                    "resource_envelope_sha256"
                ],
            )
            arguments = {
                "expected_file_sha256": receipt.file_sha256,
                "expected_envelope_sha256": (
                    receipt.resource_envelope_sha256
                ),
                "expected_run_id": receipt.run_id,
                "expected_cache_run_manifest_file_sha256": (
                    receipt.cache_run_manifest_file_sha256
                ),
                "expected_factor_bundle_manifest_sha256": (
                    receipt.factor_bundle_manifest_sha256
                ),
                "expected_on_retention_certificate_sha256": (
                    receipt.on_retention_certificate_sha256
                ),
            }
            wrong_file = dict(arguments)
            wrong_file["expected_file_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "file identity"
            ):
                physical.open_physical_resource_artifact(path, **wrong_file)
            wrong_ancestry = dict(arguments)
            wrong_ancestry["expected_factor_bundle_manifest_sha256"] = (
                "0" * 64
            )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "ancestry"
            ):
                physical.open_physical_resource_artifact(
                    path, **wrong_ancestry
                )
            oversized = root / "oversized-resource.json"
            with oversized.open("wb") as stream:
                stream.seek(
                    physical.PHYSICAL_RESOURCE_ARTIFACT_MAXIMUM_BYTES
                )
                stream.write(b"x")
            with self.assertRaisesRegex(
                core.V0P6CapacityError, "byte cap"
            ):
                physical.open_physical_resource_artifact(
                    oversized, **arguments
                )

    def test_m37_artifact_gate_rejects_synthetic_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result, _, _ = self._execute(root)
            envelope = result["resource_envelope"]
            path = root / "forbidden-m37-resource.json"
            with self.assertRaisesRegex(core.V0P6ContractError, "M37 contract"):
                physical.publish_m37_physical_resource_artifact(
                    path,
                    envelope,
                    expected_envelope_sha256=(
                        envelope["resource_envelope_sha256"]
                    ),
                )
            self.assertFalse(path.exists())

    def test_run_manifest_round_trip_reopens_every_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, entry, arguments = self._published_run_child(root)
            path = root / "physical-resource-run.json"
            receipt = run_resource.publish_physical_resource_run_manifest(
                path, (entry,), **arguments
            )
            self.assertEqual(path.stat().st_mode & 0o222, 0)
            self.assertEqual(
                receipt.file_sha256,
                "4f9f8fad548afb51aabede5703b3a77ee99f48a89e2b1ea4b8d83add3e29fa11",
            )
            self.assertEqual(
                receipt.manifest_sha256,
                "76e751f689c74e17f6abac2be3e855a32387bd0d07000664b199abe220d9e6ea",
            )
            self.assertEqual(
                receipt.resource_artifact_inventory_sha256,
                "266932487d92bb814740b9ff89254f758e652b5912f25c1518ff4a14caf599e7",
            )
            self.assertEqual(
                receipt.on_retention_inventory_sha256,
                "9d1a971a13fab595ba60caa46ca072dca348db2d24aa514a2d1db23ef88f665a",
            )
            self.assertEqual(receipt.file_nbytes, 1_468)
            opened = run_resource.open_physical_resource_run_manifest(
                path,
                expected_file_sha256=receipt.file_sha256,
                expected_manifest_sha256=receipt.manifest_sha256,
                **arguments,
            )
            self.assertEqual(opened.entries, (entry,))
            self.assertEqual(opened.receipt, receipt)
            self.assertEqual(len(opened.artifacts), 1)
            self.assertEqual(
                opened.artifacts[0].receipt.file_sha256,
                entry.artifact_file_sha256,
            )
            self.assertEqual(receipt.window_count, 1)
            self.assertEqual(
                receipt.maximum_process_mapped_bytes,
                entry.maximum_process_mapped_bytes,
            )
            self.assertEqual(
                receipt.maximum_window_peak_mapped_bytes,
                entry.aggregate_peak_mapped_bytes,
            )
            self.assertEqual(
                receipt.maximum_window_peak_handle_count,
                entry.aggregate_peak_handle_count,
            )
            self.assertEqual(
                receipt.total_batch_count, entry.aggregate_batch_count
            )
            self.assertEqual(
                receipt.total_opened_cache_count,
                entry.aggregate_opened_cache_count,
            )
            self.assertEqual(
                receipt.total_artifact_file_nbytes,
                entry.artifact_file_nbytes,
            )
            with self.assertRaises(FileExistsError):
                run_resource.publish_physical_resource_run_manifest(
                    path, (entry,), **arguments
                )

    def test_run_manifest_requires_complete_inventory_and_external_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, entry, arguments = self._published_run_child(root)
            missing_path = root / "missing-window-run.json"
            missing = dict(arguments)
            missing["expected_window_ids"] = ("synthetic", "missing")
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "missing"
            ):
                run_resource.publish_physical_resource_run_manifest(
                    missing_path, (entry,), **missing
                )
            self.assertFalse(missing_path.exists())
            wrong_root_path = root / "wrong-root-run.json"
            wrong_root = dict(arguments)
            wrong_root["expected_on_retention_inventory_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "retention inventory"
            ):
                run_resource.publish_physical_resource_run_manifest(
                    wrong_root_path, (entry,), **wrong_root
                )
            self.assertFalse(wrong_root_path.exists())
            with self.assertRaisesRegex(
                core.V0P6ContractError, "escapes"
            ):
                run_resource.make_physical_resource_run_entry(
                    "../outside.json",
                    physical.open_physical_resource_artifact(
                        root / entry.relative_path,
                        expected_file_sha256=entry.artifact_file_sha256,
                        expected_envelope_sha256=(
                            entry.resource_envelope_sha256
                        ),
                        expected_run_id=arguments["expected_run_id"],
                        expected_cache_run_manifest_file_sha256=arguments[
                            "expected_cache_run_manifest_file_sha256"
                        ],
                        expected_factor_bundle_manifest_sha256=arguments[
                            "expected_factor_bundle_manifest_sha256"
                        ],
                        expected_on_retention_certificate_sha256=(
                            entry.on_retention_certificate_sha256
                        ),
                    ),
                )

    def test_run_manifest_child_mutation_and_m37_expansion_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_path, entry, arguments = self._published_run_child(root)
            path = root / "physical-resource-run.json"
            receipt = run_resource.publish_physical_resource_run_manifest(
                path, (entry,), **arguments
            )
            artifact_path.chmod(0o644)
            with artifact_path.open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "file identity"
            ):
                run_resource.open_physical_resource_run_manifest(
                    path,
                    expected_file_sha256=receipt.file_sha256,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    **arguments,
                )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, entry, arguments = self._published_run_child(root)
            path = root / "forbidden-m37-resource-run.json"
            m37_arguments = dict(arguments)
            m37_arguments.pop("expected_window_ids")
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "missing"
            ):
                run_resource.publish_m37_physical_resource_run_manifest(
                    path, (entry,), **m37_arguments
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
