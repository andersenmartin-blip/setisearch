"""Tests for aggregate detector-v0.6 cache-run manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from seti_repeater import cache_manifest_v0p6 as run_cache
from seti_repeater import native_cache_v0p6 as disk_cache
from seti_repeater import search_v0p6 as core


def _fixture(directory: Path):
    rng = np.random.default_rng(37_060_062)
    frequency_mhz = np.arange(600, dtype=np.float64) / 1e6
    geometry = core.NativeFrequencyGeometry(0.0, 1.0, 600)
    grid = core.make_proxy_carrier_grid(0.0003, 1.0, 12, 5)
    factors = np.array([[1.01, 1.02], [1.04, 1.03]], dtype=np.float64)
    plan = core.plan_native_filter_cache(
        geometry,
        factors,
        grid,
        5,
        window_id="synthetic",
        scan_label="epoch1_on",
        scan_kind="on",
        source_sha256="1" * 64,
        factor_basis_sha256_value=core.M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256_value=core.M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256_value=core.M37_SCAN_INVENTORY_SHA256,
        factor_scan_selection_sha256_value=(
            core.M37_FACTOR_SCAN_SELECTION_SHA256S["epoch1_on"]
        ),
        template_bank_sha256_value=core.M37_BANK_SHA256,
    )
    normalized = rng.normal(size=(2, 600)).astype(np.float32)
    cache = core.build_native_filter_cache(normalized, frequency_mhz, plan)
    cache_dir = directory / "caches"
    cache_dir.mkdir()
    cache_path = cache_dir / "synthetic.cache"
    receipt = disk_cache.publish_native_filter_cache(cache_path, cache)
    entry = run_cache.make_cache_manifest_entry(
        "caches/synthetic.cache", plan, receipt
    )
    return plan, cache, entry


class CacheRunManifestTests(unittest.TestCase):
    def test_round_trip_and_full_file_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, entry = _fixture(root)
            path = root / "cache-manifest.json"
            keys = (("synthetic", "epoch1_on", 5),)
            receipt = run_cache.publish_cache_run_manifest(
                path,
                (entry,),
                run_id="synthetic-run",
                factor_bundle_manifest_sha256="a" * 64,
                expected_keys=keys,
            )
            opened = run_cache.open_cache_run_manifest(
                path,
                expected_file_sha256=receipt.file_sha256,
                expected_factor_bundle_manifest_sha256="a" * 64,
                expected_keys=keys,
            )
            self.assertEqual(opened.receipt, receipt)
            self.assertEqual(opened.entries, (entry,))
            verified = run_cache.verify_cache_run_files(root, opened)
            self.assertEqual(len(verified), 64)

    def test_missing_reordered_and_m37_incomplete_inventories_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, entry = _fixture(root)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "inventory"):
                run_cache.publish_cache_run_manifest(
                    root / "missing.json",
                    (),
                    run_id="synthetic-run",
                    factor_bundle_manifest_sha256="a" * 64,
                    expected_keys=(("synthetic", "epoch1_on", 5),),
                )
            with self.assertRaisesRegex(core.V0P6IncompleteError, "inventory"):
                run_cache.publish_m37_cache_run_manifest(
                    root / "m37.json",
                    (entry,),
                    run_id="m37-run",
                    factor_bundle_manifest_sha256="a" * 64,
                )

    def test_existing_manifest_and_ancestry_are_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, entry = _fixture(root)
            path = root / "cache-manifest.json"
            keys = (("synthetic", "epoch1_on", 5),)
            receipt = run_cache.publish_cache_run_manifest(
                path,
                (entry,),
                run_id="synthetic-run",
                factor_bundle_manifest_sha256="a" * 64,
                expected_keys=keys,
            )
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                run_cache.publish_cache_run_manifest(
                    path,
                    (entry,),
                    run_id="replacement",
                    factor_bundle_manifest_sha256="a" * 64,
                    expected_keys=keys,
                )
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "file identity"):
                run_cache.open_cache_run_manifest(
                    path,
                    expected_file_sha256="0" * 64,
                    expected_factor_bundle_manifest_sha256="a" * 64,
                    expected_keys=keys,
                )
            with self.assertRaisesRegex(core.V0P6IncompleteError, "ancestry"):
                run_cache.open_cache_run_manifest(
                    path,
                    expected_file_sha256=receipt.file_sha256,
                    expected_factor_bundle_manifest_sha256="b" * 64,
                    expected_keys=keys,
                )

    def test_path_traversal_and_resealed_entry_mutation_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, _, entry = _fixture(root)
            fake_receipt = disk_cache.NativeFilterCacheReceipt(
                path="ignored",
                manifest_sha256=entry.cache_manifest_sha256,
                plan_sha256=entry.plan_sha256,
                payload_sha256=entry.payload_sha256,
                payload_nbytes=entry.payload_nbytes,
                file_nbytes=entry.file_nbytes,
            )
            with self.assertRaisesRegex(core.V0P6ContractError, "escapes"):
                run_cache.make_cache_manifest_entry("../escape.cache", plan, fake_receipt)

            path = root / "cache-manifest.json"
            keys = (("synthetic", "epoch1_on", 5),)
            run_cache.publish_cache_run_manifest(
                path,
                (entry,),
                run_id="synthetic-run",
                factor_bundle_manifest_sha256="a" * 64,
                expected_keys=keys,
            )
            record = json.loads(path.read_text())
            record["entries"][0]["payload_nbytes"] += 4
            changed = core.canonical_json_bytes(record)
            path.chmod(0o644)
            path.write_bytes(changed)
            path.chmod(0o444)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "entry and plan"):
                run_cache.open_cache_run_manifest(
                    path,
                    expected_file_sha256=hashlib.sha256(changed).hexdigest(),
                    expected_factor_bundle_manifest_sha256="a" * 64,
                    expected_keys=keys,
                )


if __name__ == "__main__":
    unittest.main()
