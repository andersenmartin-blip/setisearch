"""Tests for the persistent, metadata-only M37 factor bundle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from seti_repeater import factor_bundle_v0p6 as bundle_io
from seti_repeater import search_v0p6 as core


ROOT = Path(__file__).resolve().parents[1]
HAS_ASTROPY = importlib.util.find_spec("astropy") is not None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(HAS_ASTROPY, "pinned Astropy environment is required")
class M37FactorBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.upstream_path = ROOT / "config/hd156668b_m37_preflight.json"
        cls.bank_path = (
            ROOT
            / "results_m37_v0p6_bank_preflight/bank_preflight.json"
        )
        cls.upstream = json.loads(cls.upstream_path.read_text())
        cls.bank_result = json.loads(cls.bank_path.read_text())
        cls.bank = cls.bank_result["template_bank"]["records"]
        cls.basis = core.make_factor_basis_from_metadata(cls.upstream)
        cls.table = core.make_template_factor_table(
            cls.basis,
            cls.bank,
            expected_template_bank_sha256=core.M37_BANK_SHA256,
        )
        cls.environment = {
            "python": "3.12-test",
            "numpy": np.__version__,
            "astropy": "pinned-test-environment",
            "purpose": "metadata-only-factor-bundle-test",
        }
        cls.source_hashes = {
            "continuous_preflight_config": _sha256(cls.upstream_path),
            "bank_preflight_result": _sha256(cls.bank_path),
        }

    def _publish(self, directory: str) -> tuple[Path, bundle_io.FactorBundleReceipt]:
        path = Path(directory) / "m37.factor-bundle"
        receipt = bundle_io.publish_m37_factor_bundle(
            path,
            self.basis,
            self.table,
            self.bank,
            self.upstream["scans"],
            environment=self.environment,
            source_hashes=self.source_hashes,
        )
        return path, receipt

    def test_exact_m37_factor_identities_and_round_trip(self) -> None:
        self.assertEqual(
            self.basis.basis_sha256, core.M37_FACTOR_BASIS_SHA256
        )
        self.assertEqual(
            self.basis.labels_sha256, core.M37_FACTOR_BASIS_LABELS_SHA256
        )
        self.assertEqual(
            self.table.factor_table_sha256,
            "a4d87d8813ec63ff7f3392f5073038f3dc47a9707796a745dd4e752588255fa4",
        )
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._publish(directory)
            restored = bundle_io.open_m37_factor_bundle(
                path,
                expected_manifest_sha256=receipt.manifest_sha256,
                expected_file_sha256=receipt.file_sha256,
                expected_factor_table_sha256=receipt.factor_table_sha256,
            )
            self.assertEqual(restored.receipt, receipt)
            self.assertTrue(
                np.array_equal(restored.basis.times_mjd, self.basis.times_mjd)
            )
            self.assertTrue(
                np.array_equal(restored.basis.baseline, self.basis.baseline)
            )
            self.assertTrue(
                np.array_equal(restored.basis.orbital, self.basis.orbital)
            )
            self.assertTrue(
                np.array_equal(restored.table.factors, self.table.factors)
            )
            self.assertFalse(restored.table.factors.flags.writeable)
            self.assertEqual(restored.environment, self.environment)
            self.assertEqual(restored.source_hashes, self.source_hashes)

    def test_existing_destination_is_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, first = self._publish(directory)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                bundle_io.publish_m37_factor_bundle(
                    path,
                    self.basis,
                    self.table,
                    self.bank,
                    self.upstream["scans"],
                    environment=self.environment,
                    source_hashes=self.source_hashes,
                )
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(_sha256(path), first.file_sha256)

    def test_file_and_manifest_need_independent_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._publish(directory)
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "file identity"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    expected_file_sha256="0" * 64,
                    expected_factor_table_sha256=receipt.factor_table_sha256,
                )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "manifest identity"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256="1" * 64,
                    expected_file_sha256=receipt.file_sha256,
                    expected_factor_table_sha256=receipt.factor_table_sha256,
                )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "factor table"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    expected_file_sha256=receipt.file_sha256,
                    expected_factor_table_sha256="2" * 64,
                )

    def test_payload_mutation_fails_even_when_file_digest_is_updated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._publish(directory)
            changed = bytearray(path.read_bytes())
            changed[-1] ^= 1
            path.chmod(0o644)
            path.write_bytes(changed)
            path.chmod(0o444)
            changed_digest = _sha256(path)
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "payload identity"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    expected_file_sha256=changed_digest,
                    expected_factor_table_sha256=receipt.factor_table_sha256,
                )

    def test_trailing_bytes_and_truncation_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path, receipt = self._publish(directory)
            original = path.read_bytes()
            path.chmod(0o644)
            path.write_bytes(original + b"x")
            path.chmod(0o444)
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "trailing-byte"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    expected_file_sha256=_sha256(path),
                    expected_factor_table_sha256=receipt.factor_table_sha256,
                )
            path.chmod(0o644)
            path.write_bytes(original[:-8])
            path.chmod(0o444)
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "truncated"
            ):
                bundle_io.open_m37_factor_bundle(
                    path,
                    expected_manifest_sha256=receipt.manifest_sha256,
                    expected_file_sha256=_sha256(path),
                    expected_factor_table_sha256=receipt.factor_table_sha256,
                )

    def test_non_digest_source_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.factor-bundle"
            with self.assertRaisesRegex(core.V0P6ContractError, "source hash"):
                bundle_io.publish_m37_factor_bundle(
                    path,
                    self.basis,
                    self.table,
                    self.bank,
                    self.upstream["scans"],
                    environment=self.environment,
                    source_hashes={"config": 123},
                )
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
