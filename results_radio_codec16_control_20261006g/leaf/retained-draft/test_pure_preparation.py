"""Source/metadata-only checks; drafted control imported only for closed rejection."""
import ast
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from preparation import build, canonical, parse, read, selected_nodes

ROOT = Path(__file__).resolve().parent


class PurePreparationTests(unittest.TestCase):
    def test_fresh_draft_has_no_execution_or_value_generation(self):
        _, _, plan = build(ROOT)
        self.assertEqual(plan["status"], "NO_DISPATCHED")
        self.assertIs(plan["execution_enabled"], False)
        self.assertTrue(all(value == 0 for value in plan["counters"].values()))
        self.assertIs(plan["deterministic_construction"]["expected_control_payloads_generated"], False)
        self.assertNotIn("numpy", sys.modules)
        self.assertNotIn("h5py", sys.modules)
        self.assertNotIn("hdf5plugin", sys.modules)

    def test_exact_calibration_partial_coverage_and_profile(self):
        _, _, plan = build(ROOT)
        scope = plan["scope"]
        self.assertEqual((scope["role"], scope["scan"]), ("calibration", "epoch1_on"))
        self.assertEqual(scope["row_indices"], list(range(16)))
        self.assertEqual(scope["archive_interval"], [167215104, 167280640])
        self.assertEqual(scope["legacy_pipeline"], [[32008, 1, [0, 3, 4, 0, 2]]])
        self.assertEqual(plan["future_output"]["engineering_partial_handoff_count"], 1)
        self.assertIs(plan["future_output"]["scientific_readiness"], False)

    def test_exact_authority_pins_and_noncyclic_plan_bindings(self):
        manifest, selection, plan = build(ROOT)
        self.assertEqual(plan["input_manifest_sha256"], hashlib.sha256(canonical(manifest)).hexdigest())
        self.assertEqual(plan["selection_manifest_sha256"], hashlib.sha256(canonical(selection)).hexdigest())
        self.assertNotIn("plan_sha256", manifest)
        self.assertEqual(manifest["files"]["src/seti_repeater/search_v0p6.py"]["sha256"],
                         "6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4")

    def test_duplicate_and_missing_selected_definitions_refused(self):
        want = {"assignments": [], "functions": ["one"], "classes": []}
        with self.assertRaises(ValueError):
            selected_nodes(b"def one(): pass\ndef one(): pass\n", want)
        with self.assertRaises(ValueError):
            selected_nodes(b"def other(): pass\n", want)

    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                parse(raw)

    def test_selected_normalizer_segments_preserve_original_bytes(self):
        _, selections, _ = build(ROOT)
        nodes = {row["name"]: row for group in selections["source_selections"].values() for row in group["nodes"]}
        self.assertEqual(nodes["normalize_native_row"]["sha256"], "8478ff02561308c6919db86c47857e022341108eda97f604184e38c555f2c65d")
        self.assertEqual(nodes["_float32_median_rows"]["sha256"], "2ccb25d5ea6507c37ad447ef2a39a9845a8ef67a129932ff741577ee316765b2")
        self.assertEqual(nodes["normalize_float32_blocks_v0p6"]["sha256"], "16b67e64c6fcb80268fd395326868e98d1a18169a8f29a5513e9bc50925628eb")

    def test_future_control_native_imports_are_deferred_and_cli_refuses(self):
        tree = ast.parse((ROOT / "codec16_control.py").read_bytes())
        for node in tree.body:
            if isinstance(node, ast.Import):
                self.assertFalse(any(alias.name.split(".")[0] in ("numpy", "h5py", "hdf5plugin") for alias in node.names))
        future = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "produce")
        native = {alias.name for node in ast.walk(future) if isinstance(node, ast.Import) for alias in node.names}
        self.assertTrue({"numpy", "h5py", "hdf5plugin"} <= native)
        cli = tree.body[-1]
        self.assertIsInstance(cli, ast.If)
        self.assertIsInstance(cli.body[0], ast.Raise)

    def test_missing_future_dispatch_stops_before_native_import_or_output(self):
        import codec16_control
        manifest, selection, plan = build(ROOT)
        blobs = [canonical(value) for value in (plan, manifest, selection, {"schema": "inert"})]
        pins = [{"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} for raw in blobs]
        nonexistent = ROOT / "NO_TEST_CONTROL_OUTPUT"
        self.assertFalse(nonexistent.exists())
        with self.assertRaises(ValueError):
            codec16_control.produce(ROOT, nonexistent, plan_raw=blobs[0], expected_plan_pin=pins[0],
                                    manifest_raw=blobs[1], expected_manifest_pin=pins[1],
                                    selection_raw=blobs[2], expected_selection_pin=pins[2],
                                    dispatch_raw=blobs[3], expected_dispatch_pin=pins[3])
        self.assertFalse(nonexistent.exists())
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin")))

    def test_wrong_external_dispatch_pin_is_closed_before_inspection(self):
        import codec16_control
        with self.assertRaises(ValueError):
            codec16_control._authenticate(b"{}", {"bytes": 2, "sha256": "0" * 64})

    def test_bounded_read_refuses_oversized_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "oversized.json").write_bytes(b"123456789")
            with self.assertRaises(ValueError):
                read(root, "oversized.json", maximum=8)


if __name__ == "__main__":
    unittest.main()
