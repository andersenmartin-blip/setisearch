"""Synthetic format and lifecycle tests for detector-v0.6 disk caches."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from seti_repeater import native_cache_v0p6 as disk_cache
from seti_repeater.search_v0p6 import (
    M37_BANK_SHA256,
    M37_FACTOR_BASIS_SHA256,
    M37_FACTOR_BASIS_LABELS_SHA256,
    M37_FACTOR_SCAN_SELECTION_SHA256S,
    M37_SCAN_INVENTORY_SHA256,
    V0P6CapacityError,
    V0P6ContractError,
    V0P6IncompleteError,
    build_native_filter_cache,
    canonical_json_bytes,
    gather_filtered_native,
    make_proxy_carrier_grid,
    native_filter_cache_plan_from_record,
    plan_native_filter_cache,
    NativeFrequencyGeometry,
)


def _fixture():
    rng = np.random.default_rng(37_060_061)
    frequency_mhz = np.arange(600, dtype=np.float64) / 1e6
    geometry = NativeFrequencyGeometry(
        raw_zero_hz=0.0,
        channel_width_hz=1.0,
        channel_count=600,
    )
    grid = make_proxy_carrier_grid(0.0003, 1.0, 12, 5)
    factor_table = np.array(
        [[1.01, 1.02], [1.04, 1.03]], dtype=np.float64
    )
    plan = plan_native_filter_cache(
        geometry,
        factor_table,
        grid,
        5,
        window_id="synthetic",
        scan_label="epoch1_on",
        scan_kind="on",
        source_sha256="1" * 64,
        factor_basis_sha256_value=M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256_value=M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256_value=M37_SCAN_INVENTORY_SHA256,
        factor_scan_selection_sha256_value=(
            M37_FACTOR_SCAN_SELECTION_SHA256S["epoch1_on"]
        ),
        template_bank_sha256_value=M37_BANK_SHA256,
    )
    normalized = rng.normal(size=(2, 600)).astype(np.float32)
    cache = build_native_filter_cache(normalized, frequency_mhz, plan)
    return plan, cache


def _open(path: Path, plan, receipt, *, arena=None):
    return disk_cache.open_native_filter_cache(
        path,
        expected_plan=plan,
        expected_plan_sha256=receipt.plan_sha256,
        expected_manifest_sha256=receipt.manifest_sha256,
        arena=arena,
    )


def _read_manifest(raw: bytes):
    manifest_length = struct.unpack_from("<I", raw, 20)[0]
    manifest_bytes = raw[64 : 64 + manifest_length]
    return json.loads(manifest_bytes), manifest_bytes


def _rewrite_with_nonfinite_payload(path: Path) -> str:
    raw = bytearray(path.read_bytes())
    manifest, _ = _read_manifest(raw)
    raw[disk_cache.HEADER_SIZE : disk_cache.HEADER_SIZE + 4] = struct.pack(
        "<f", float("nan")
    )
    payload = raw[disk_cache.HEADER_SIZE :]
    manifest["payload"]["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    header = bytearray(disk_cache.HEADER_SIZE)
    header[0:16] = disk_cache.MAGIC
    struct.pack_into("<I", header, 16, disk_cache.SCHEMA_VERSION)
    struct.pack_into("<I", header, 20, len(manifest_bytes))
    header[24:56] = bytes.fromhex(manifest_sha256)
    header[64 : 64 + len(manifest_bytes)] = manifest_bytes
    raw[: disk_cache.HEADER_SIZE] = header
    path.chmod(0o644)
    path.write_bytes(raw)
    path.chmod(0o444)
    return manifest_sha256


class V0P6DiskCacheTests(unittest.TestCase):
    def test_cache_plan_round_trip_from_persisted_manifest_record(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            manifest, _ = _read_manifest(path.read_bytes())
            restored = native_filter_cache_plan_from_record(
                manifest["plan"],
                expected_plan_sha256=receipt.plan_sha256,
            )
            self.assertEqual(restored, plan)
            with _open(path, restored, receipt) as handle:
                np.testing.assert_array_equal(handle._values_for_gather(), cache.values)

    def test_cache_plan_rehydration_requires_independent_identity(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            disk_cache.publish_native_filter_cache(path, cache)
            manifest, _ = _read_manifest(path.read_bytes())
            with self.assertRaisesRegex(V0P6IncompleteError, "independent identity"):
                native_filter_cache_plan_from_record(
                    manifest["plan"],
                    expected_plan_sha256="0" * 64,
                )
            changed = dict(manifest["plan"])
            changed["payload_nbytes"] += 4
            changed_digest = hashlib.sha256(
                canonical_json_bytes(changed)
            ).hexdigest()
            with self.assertRaisesRegex(V0P6ContractError, "byte count"):
                native_filter_cache_plan_from_record(
                    changed,
                    expected_plan_sha256=changed_digest,
                )

    def test_fixed_header_round_trip_and_single_full_validation(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            raw = path.read_bytes()

            self.assertEqual(disk_cache.MAGIC, b"SETI-V06-NFC\0\0\0\0")
            self.assertEqual(len(disk_cache.MAGIC), 16)
            self.assertEqual(raw[:16], disk_cache.MAGIC)
            self.assertEqual(struct.unpack_from("<I", raw, 16)[0], 1)
            self.assertEqual(raw[24:56].hex(), receipt.manifest_sha256)
            self.assertEqual(raw[56:64], b"\0" * 8)
            manifest, manifest_bytes = _read_manifest(raw)
            manifest_stop = 64 + len(manifest_bytes)
            self.assertFalse(any(raw[manifest_stop : disk_cache.HEADER_SIZE]))
            self.assertEqual(manifest["plan_sha256"], plan.plan_sha256)
            self.assertEqual(manifest["payload"]["offset_bytes"], 65_536)
            self.assertEqual(manifest["payload"]["dtype"], "<f4")
            self.assertEqual(manifest["payload"]["order"], "C")
            self.assertEqual(receipt.file_nbytes, len(raw))
            self.assertEqual(receipt.payload_nbytes, plan.payload_nbytes)
            self.assertEqual(
                raw[disk_cache.HEADER_SIZE :],
                np.asarray(cache.values, dtype="<f4", order="C").tobytes(),
            )

            with patch.object(
                disk_cache,
                "_validate_payload_stream",
                wraps=disk_cache._validate_payload_stream,
            ) as validator:
                with _open(path, plan, receipt) as handle:
                    first = handle._values_for_gather()
                    second = handle._values_for_gather()
                    self.assertIs(first, second)
                    self.assertFalse(first.flags.writeable)
                    with self.assertRaises(ValueError):
                        first[0, 0] = 0.0
                    np.testing.assert_array_equal(first, cache.values)
                    grid = make_proxy_carrier_grid(0.0003, 1.0, 12, 5)
                    factors = np.array([1.01, 1.02], dtype=np.float64)
                    for _ in range(3):
                        np.testing.assert_array_equal(
                            gather_filtered_native(handle, factors, grid),
                            gather_filtered_native(cache, factors, grid),
                        )
                    self.assertEqual(validator.call_count, 1)
                    del first, second
            self.assertTrue(handle.closed)
            with self.assertRaisesRegex(V0P6IncompleteError, "closed"):
                handle._values_for_gather()
            handle.close()

    def test_publication_never_overwrites_and_leaves_no_staging_file(self):
        _, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            disk_cache.publish_native_filter_cache(path, cache)
            original = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):
                disk_cache.publish_native_filter_cache(path, cache)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original)
            self.assertEqual(
                [item.name for item in Path(directory).iterdir()], [path.name]
            )

    def test_open_requires_both_independent_identities(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            with self.assertRaisesRegex(V0P6ContractError, "expected plan"):
                disk_cache.open_native_filter_cache(
                    path,
                    expected_plan=plan,
                    expected_plan_sha256="0" * 64,
                    expected_manifest_sha256=receipt.manifest_sha256,
                )
            with self.assertRaisesRegex(V0P6ContractError, "manifest SHA-256"):
                disk_cache.open_native_filter_cache(
                    path,
                    expected_plan=plan,
                    expected_plan_sha256=receipt.plan_sha256,
                    expected_manifest_sha256="0" * 64,
                )
            changed_plan = replace(plan, source_sha256="2" * 64)
            with self.assertRaisesRegex(V0P6ContractError, "plan SHA-256"):
                disk_cache.open_native_filter_cache(
                    path,
                    expected_plan=changed_plan,
                    expected_plan_sha256=receipt.plan_sha256,
                    expected_manifest_sha256=receipt.manifest_sha256,
                )

    def test_sha256_receipts_and_manifest_require_exact_strings(self):
        plan, cache = _fixture()
        numeric_digest = int("1" * 64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            for field, value in (
                ("expected_plan_sha256", numeric_digest),
                ("expected_manifest_sha256", numeric_digest),
            ):
                arguments = {
                    "expected_plan": plan,
                    "expected_plan_sha256": receipt.plan_sha256,
                    "expected_manifest_sha256": receipt.manifest_sha256,
                }
                arguments[field] = value
                with self.subTest(field=field):
                    with self.assertRaisesRegex(
                        V0P6ContractError, "digest string"
                    ):
                        disk_cache.open_native_filter_cache(path, **arguments)

            raw = bytearray(path.read_bytes())
            manifest, _ = _read_manifest(raw)
            manifest["payload"]["sha256"] = numeric_digest
            manifest_bytes = canonical_json_bytes(manifest)
            manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
            header = bytearray(disk_cache.HEADER_SIZE)
            header[0:16] = disk_cache.MAGIC
            struct.pack_into("<I", header, 16, disk_cache.SCHEMA_VERSION)
            struct.pack_into("<I", header, 20, len(manifest_bytes))
            header[24:56] = bytes.fromhex(manifest_sha256)
            header[64 : 64 + len(manifest_bytes)] = manifest_bytes
            raw[: disk_cache.HEADER_SIZE] = header
            path.chmod(0o644)
            path.write_bytes(raw)
            path.chmod(0o444)
            with self.assertRaisesRegex(V0P6ContractError, "digest string"):
                disk_cache.open_native_filter_cache(
                    path,
                    expected_plan=plan,
                    expected_plan_sha256=receipt.plan_sha256,
                    expected_manifest_sha256=manifest_sha256,
                )

    def test_matching_hash_cannot_hide_nonfinite_payload(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            changed_manifest_sha256 = _rewrite_with_nonfinite_payload(path)
            with self.assertRaisesRegex(V0P6IncompleteError, "non-finite"):
                disk_cache.open_native_filter_cache(
                    path,
                    expected_plan=plan,
                    expected_plan_sha256=receipt.plan_sha256,
                    expected_manifest_sha256=changed_manifest_sha256,
                )

    def test_payload_tampering_and_post_open_stat_change_fail_closed(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.cache"
            receipt = disk_cache.publish_native_filter_cache(path, cache)
            path.chmod(0o644)
            with path.open("r+b") as stream:
                stream.seek(disk_cache.HEADER_SIZE)
                first = stream.read(1)
                stream.seek(disk_cache.HEADER_SIZE)
                stream.write(bytes([first[0] ^ 1]))
            path.chmod(0o444)
            with self.assertRaisesRegex(V0P6IncompleteError, "payload SHA-256"):
                _open(path, plan, receipt)

            clean_path = Path(directory) / "clean.cache"
            clean_receipt = disk_cache.publish_native_filter_cache(clean_path, cache)
            handle = _open(clean_path, plan, clean_receipt)
            metadata = clean_path.stat()
            os.utime(
                clean_path,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000),
            )
            with self.assertRaisesRegex(V0P6IncompleteError, "stat identity"):
                handle._values_for_gather()
            handle.close()

    def test_arena_reserves_before_open_releases_and_closes_handles(self):
        plan, cache = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.cache"
            second_path = Path(directory) / "second.cache"
            first_receipt = disk_cache.publish_native_filter_cache(first_path, cache)
            second_receipt = disk_cache.publish_native_filter_cache(second_path, cache)
            too_small = disk_cache.NativeFilterCacheArena(
                plan.payload_nbytes - 1
            )
            with self.assertRaisesRegex(V0P6CapacityError, "cap"):
                _open(
                    Path(directory) / "does-not-exist.cache",
                    plan,
                    first_receipt,
                    arena=too_small,
                )
            self.assertEqual(too_small.mapped_bytes, 0)
            too_small.close()

            arena = disk_cache.NativeFilterCacheArena(plan.payload_nbytes)

            with self.assertRaisesRegex(V0P6ContractError, "manifest SHA-256"):
                disk_cache.open_native_filter_cache(
                    first_path,
                    expected_plan=plan,
                    expected_plan_sha256=first_receipt.plan_sha256,
                    expected_manifest_sha256="0" * 64,
                    arena=arena,
                )
            self.assertEqual(arena.mapped_bytes, 0)
            self.assertEqual(arena.handle_count, 0)

            first = _open(first_path, plan, first_receipt, arena=arena)
            self.assertEqual(arena.mapped_bytes, plan.payload_nbytes)
            self.assertEqual(arena.handle_count, 1)
            with self.assertRaisesRegex(V0P6CapacityError, "cap"):
                _open(second_path, plan, second_receipt, arena=arena)
            first.close()
            self.assertEqual(arena.mapped_bytes, 0)

            second = _open(second_path, plan, second_receipt, arena=arena)
            arena.close()
            self.assertTrue(second.closed)
            self.assertTrue(arena.closed)
            self.assertEqual(arena.mapped_bytes, 0)
            self.assertEqual(arena.handle_count, 0)
            with self.assertRaisesRegex(V0P6IncompleteError, "arena is closed"):
                _open(first_path, plan, first_receipt, arena=arena)


if __name__ == "__main__":
    unittest.main()
