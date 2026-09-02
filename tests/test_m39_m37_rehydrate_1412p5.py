"""Contract tests for the restartable M39 source rehydration command."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from seti_repeater import search_v0p6 as core


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m39_m37_rehydrate_1412p5.py"
SPEC = importlib.util.spec_from_file_location("m39_rehydrate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
m39 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m39)


class M39RehydrationTests(unittest.TestCase):
    def test_authorization_gate_precedes_filesystem_or_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "absent"
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                m39.execute(root, authorized=False)
            self.assertFalse(root.exists())

    def test_exact_48_cache_key_inventory(self):
        keys = m39._cache_keys()
        self.assertEqual(len(keys), 48)
        self.assertEqual(
            keys,
            tuple(
                (m39.WINDOW_ID, label, width)
                for _, _, label in core.M37_SCAN_ROLE_ORDER
                for width in core.M37_SPECTRAL_WIDTHS
            ),
        )
        self.assertEqual(len(set(keys)), 48)


if __name__ == "__main__":
    unittest.main()
