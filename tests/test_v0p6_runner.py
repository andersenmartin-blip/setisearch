"""Tests for the restartable non-spectral M37 runner bootstrap."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from seti_repeater import runner_v0p6 as runner
from seti_repeater.search_v0p6 import V0P6IncompleteError


ROOT = Path(__file__).resolve().parents[1]
HAS_ASTROPY = importlib.util.find_spec("astropy") is not None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(HAS_ASTROPY, "pinned Astropy environment is required")
class M37BootstrapRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.upstream_path = ROOT / "config/hd156668b_m37_preflight.json"
        cls.bank_path = (
            ROOT / "results_m37_v0p6_bank_preflight/bank_preflight.json"
        )
        cls.upstream = json.loads(cls.upstream_path.read_text())
        cls.bank = json.loads(cls.bank_path.read_text())
        cls.environment = {
            "python": "3.12-test",
            "astropy": "pinned-test-environment",
            "purpose": "non-spectral-runner-bootstrap-test",
        }
        cls.source_hashes = {
            "continuous_preflight_config": _sha256(cls.upstream_path),
            "bank_preflight_result": _sha256(cls.bank_path),
        }

    def _bootstrap(self, directory: str):
        root = Path(directory) / "m37-run"
        receipt = runner.bootstrap_m37_run(
            root,
            run_id="m37-bootstrap-test-001",
            upstream_metadata=self.upstream,
            bank_preflight_result=self.bank,
            environment=self.environment,
            source_hashes=self.source_hashes,
        )
        return root, receipt

    def test_atomic_bootstrap_round_trip_and_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = self._bootstrap(directory)
            self.assertEqual(
                sorted(item.name for item in root.iterdir()),
                ["bootstrap.json", "factor_bundle.v0p6", "run.journal.jsonl"],
            )
            self.assertFalse(receipt.spectral_access_authorized)
            self.assertFalse(receipt.spectral_dataset_values_read)
            self.assertEqual(receipt.journal_head_sha256, runner.open_m37_bootstrap(
                root,
                expected_bootstrap_sha256=receipt.bootstrap_sha256,
            ).journal.head_sha256)
            opened = runner.open_m37_bootstrap(
                root,
                expected_bootstrap_sha256=receipt.bootstrap_sha256,
            )
            self.assertEqual(opened.receipt, receipt)
            self.assertEqual(opened.journal.stage, "factor_bundle_ready")
            self.assertEqual(opened.journal.event_count, 2)
            self.assertFalse(opened.journal.complete)
            self.assertEqual(
                opened.factor_bundle.table.factor_table_sha256,
                receipt.factor_table_sha256,
            )

    def test_existing_run_directory_is_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = self._bootstrap(directory)
            bootstrap_bytes = (root / "bootstrap.json").read_bytes()
            with self.assertRaises(FileExistsError):
                runner.bootstrap_m37_run(
                    root,
                    run_id="replacement-attempt",
                    upstream_metadata=self.upstream,
                    bank_preflight_result=self.bank,
                    environment=self.environment,
                    source_hashes=self.source_hashes,
                )
            self.assertEqual((root / "bootstrap.json").read_bytes(), bootstrap_bytes)
            self.assertEqual(
                runner.open_m37_bootstrap(
                    root,
                    expected_bootstrap_sha256=receipt.bootstrap_sha256,
                ).receipt,
                receipt,
            )

    def test_bootstrap_requires_independent_root_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _ = self._bootstrap(directory)
            with self.assertRaisesRegex(V0P6IncompleteError, "independent identity"):
                runner.open_m37_bootstrap(
                    root,
                    expected_bootstrap_sha256="0" * 64,
                )

    def test_factor_payload_and_journal_tampering_break_the_join(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, receipt = self._bootstrap(directory)
            factor_path = root / "factor_bundle.v0p6"
            factor = bytearray(factor_path.read_bytes())
            factor[-1] ^= 1
            factor_path.chmod(0o644)
            factor_path.write_bytes(factor)
            factor_path.chmod(0o444)
            with self.assertRaisesRegex(V0P6IncompleteError, "file identity"):
                runner.open_m37_bootstrap(
                    root,
                    expected_bootstrap_sha256=receipt.bootstrap_sha256,
                )

        with tempfile.TemporaryDirectory() as directory:
            root, receipt = self._bootstrap(directory)
            journal = root / "run.journal.jsonl"
            journal.write_bytes(journal.read_bytes()[:-1])
            with self.assertRaisesRegex(V0P6IncompleteError, "final newline"):
                runner.open_m37_bootstrap(
                    root,
                    expected_bootstrap_sha256=receipt.bootstrap_sha256,
                )


if __name__ == "__main__":
    unittest.main()
