"""Adversarial tests for width-at-a-time native-cache streaming."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from seti_repeater import cache_manifest_v0p6 as run_cache
from seti_repeater import native_cache_v0p6 as disk_cache
from seti_repeater import search_v0p6 as core
from seti_repeater.cache_stream_v0p6 import (
    CacheWidthStream,
    validate_stream_resource_certificate,
)


def _fixture(root: Path):
    geometry = core.NativeFrequencyGeometry(0.0, 1.0, 600)
    grid = core.make_proxy_carrier_grid(0.0003, 1.0, 12, 5)
    factor_rows = np.array([[1.01, 1.02], [1.04, 1.03]], dtype=np.float64)
    widths = (1, 3)
    labels = ("epoch1_on", "epoch2_on", "epoch3_on")
    cache_root = root / "caches"
    cache_root.mkdir()
    entries = []
    expected_keys = []
    for width in widths:
        for label_ordinal, label in enumerate(labels):
            plan = core.plan_native_filter_cache(
                geometry,
                factor_rows,
                grid,
                width,
                window_id="synthetic",
                scan_label=label,
                scan_kind="on",
                source_sha256=f"{label_ordinal + 1:064x}",
                factor_basis_sha256_value="a" * 64,
                factor_basis_labels_sha256_value="b" * 64,
                scan_inventory_sha256_value="c" * 64,
                factor_scan_selection_sha256_value=f"{label_ordinal + 4:064x}",
                template_bank_sha256_value="d" * 64,
            )
            values = np.full(
                plan.payload_shape,
                np.float32(width + label_ordinal),
                dtype=np.dtype("<f4"),
            )
            values.setflags(write=False)
            cache = core.NativeFilterCache(
                plan=plan,
                values=values,
                payload_sha256=core.float32_array_sha256(values),
            )
            relative = f"caches/{width}-{label}.cache"
            receipt = disk_cache.publish_native_filter_cache(
                root / relative, cache
            )
            entries.append(
                run_cache.make_cache_manifest_entry(relative, plan, receipt)
            )
            expected_keys.append(("synthetic", label, width))
    manifest_path = root / "cache-run.json"
    receipt = run_cache.publish_cache_run_manifest(
        manifest_path,
        entries,
        run_id="stream-test",
        factor_bundle_manifest_sha256="e" * 64,
        expected_keys=expected_keys,
    )
    manifest = run_cache.open_cache_run_manifest(
        manifest_path,
        expected_file_sha256=receipt.file_sha256,
        expected_factor_bundle_manifest_sha256="e" * 64,
        expected_keys=expected_keys,
    )
    return widths, labels, tuple(expected_keys), receipt, manifest


def _stream(root, fixture, *, maximum_mapped_bytes):
    widths, labels, keys, receipt, manifest = fixture
    return CacheWidthStream(
        root,
        manifest,
        expected_manifest_file_sha256=receipt.file_sha256,
        expected_inventory_sha256=receipt.inventory_sha256,
        expected_factor_bundle_manifest_sha256="e" * 64,
        expected_keys=keys,
        window_id="synthetic",
        scan_kind="on",
        scan_labels=labels,
        spectral_widths=widths,
        maximum_mapped_bytes=maximum_mapped_bytes,
    )


class CacheWidthStreamTests(unittest.TestCase):
    def test_width_batches_close_and_resource_receipt_binds_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _fixture(root)
            payload = fixture[-1].entries[0].payload_nbytes
            stream = _stream(
                root, fixture, maximum_mapped_bytes=3 * payload
            )
            retained = []
            for width in fixture[0]:
                with stream.open_width(width) as caches:
                    self.assertEqual(tuple(caches), fixture[1])
                    self.assertTrue(all(not cache.closed for cache in caches.values()))
                    retained.extend(caches.values())
                self.assertTrue(all(cache.closed for cache in retained))
            receipt = stream.seal(
                evidence_artifact_type="synthetic-evidence",
                evidence_sha256="f" * 64,
            )
            self.assertEqual(receipt["batch_count"], 2)
            self.assertEqual(receipt["opened_cache_count"], 6)
            self.assertEqual(receipt["peak_handle_count"], 3)
            self.assertEqual(receipt["peak_mapped_bytes"], 3 * payload)
            self.assertTrue(receipt["all_handles_closed_before_seal"])
            self.assertEqual(receipt["evidence_sha256"], "f" * 64)
            self.assertEqual(
                len(receipt["stream_resource_certificate_sha256"]), 64
            )
            validated = validate_stream_resource_certificate(
                receipt,
                expected_certificate_sha256=receipt[
                    "stream_resource_certificate_sha256"
                ],
                expected_evidence_sha256="f" * 64,
            )
            self.assertEqual(validated, receipt)

            forged = json.loads(core.canonical_json_bytes(receipt))
            forged["peak_handle_count"] = 2
            forged.pop("stream_resource_certificate_sha256")
            forged["stream_resource_certificate_sha256"] = hashlib.sha256(
                core.canonical_json_bytes(forged)
            ).hexdigest()
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "aggregate accounting"
            ):
                validate_stream_resource_certificate(forged)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "sealed"):
                stream.open_width(fixture[0][0]).__enter__()

    def test_order_skip_and_capacity_fail_permanently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _fixture(root)
            payload = fixture[-1].entries[0].payload_nbytes
            out_of_order = _stream(
                root, fixture, maximum_mapped_bytes=3 * payload
            )
            with self.assertRaisesRegex(core.V0P6IncompleteError, "order"):
                with out_of_order.open_width(fixture[0][1]):
                    pass
            with self.assertRaisesRegex(core.V0P6IncompleteError, "invalid"):
                with out_of_order.open_width(fixture[0][0]):
                    pass

            too_small = _stream(
                root, fixture, maximum_mapped_bytes=3 * payload - 1
            )
            with self.assertRaisesRegex(core.V0P6CapacityError, "cap"):
                with too_small.open_width(fixture[0][0]):
                    pass
            with self.assertRaisesRegex(core.V0P6IncompleteError, "invalid"):
                too_small.seal(
                    evidence_artifact_type="synthetic",
                    evidence_sha256="f" * 64,
                )

    def test_manifest_object_needs_independent_unchanged_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _fixture(root)
            widths, labels, keys, receipt, manifest = fixture
            forged = replace(
                manifest,
                receipt=replace(
                    manifest.receipt,
                    inventory_sha256="0" * 64,
                ),
            )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "trusted inventory"
            ):
                CacheWidthStream(
                    root,
                    forged,
                    expected_manifest_file_sha256=receipt.file_sha256,
                    expected_inventory_sha256=receipt.inventory_sha256,
                    expected_factor_bundle_manifest_sha256="e" * 64,
                    expected_keys=keys,
                    window_id="synthetic",
                    scan_kind="on",
                    scan_labels=labels,
                    spectral_widths=widths,
                    maximum_mapped_bytes=core.M37_LIVE_NDARRAY_CAP_BYTES,
                )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "trusted inventory"
            ):
                CacheWidthStream(
                    root,
                    replace(manifest, run_id="forged-run-id"),
                    expected_manifest_file_sha256=receipt.file_sha256,
                    expected_inventory_sha256=receipt.inventory_sha256,
                    expected_factor_bundle_manifest_sha256="e" * 64,
                    expected_keys=keys,
                    window_id="synthetic",
                    scan_kind="on",
                    scan_labels=labels,
                    spectral_widths=widths,
                    maximum_mapped_bytes=core.M37_LIVE_NDARRAY_CAP_BYTES,
                )


if __name__ == "__main__":
    unittest.main()
