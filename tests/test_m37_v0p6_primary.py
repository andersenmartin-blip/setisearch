"""Metadata-boundary tests for the restartable M37 primary controller."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from seti_repeater import run_state_v0p6 as state
from seti_repeater import source_v0p6 as source


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts" / "m37_v0p6_primary.py"
    spec = importlib.util.spec_from_file_location("m37_v0p6_primary_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class M37PrimaryControllerTests(unittest.TestCase):
    def test_prepare_authorize_and_restart_are_metadata_only(self):
        primary = _module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            record = primary.prepare(root, "synthetic-primary")
            self.assertEqual(record["stage"], "factor_bundle_ready")
            self.assertFalse((root / primary.AUTHORIZATION_PATH).exists())

            authorized = primary.authorize(root, record)
            self.assertEqual(authorized["stage"], "spectral_access_authorized")
            artifact = primary._read_canonical(root / primary.AUTHORIZATION_PATH)
            self.assertTrue(artifact["spectral_access_authorized"])
            self.assertFalse(artifact["spectral_dataset_values_read"])
            self.assertEqual(
                artifact["authorization_scope"],
                state.M37_SPECTRAL_AUTHORIZATION_SCOPE,
            )
            self.assertEqual(primary._status(root), authorized)
            self.assertEqual(primary.authorize(root, authorized), authorized)

    def test_source_hash_inventory_binds_the_frozen_extractor(self):
        primary = _module()
        hashes = primary._source_hashes()
        self.assertEqual(
            hashes["hdf5_extractor"],
            source.M37_HDF5_EXTRACTOR_SOURCE_SHA256,
        )
        self.assertIn("http_range_transport", hashes)
        self.assertIn("primary_controller", hashes)


if __name__ == "__main__":
    unittest.main()
