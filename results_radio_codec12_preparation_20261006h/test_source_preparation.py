"""Source-only regression checks for codec12 H preparation."""
import ast
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from metadata_law_control import observe
from preparation import LABELS, LAW_NAMES, ROLES, build, canonical, parse, read, selected_nodes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


class SourcePreparationTests(unittest.TestCase):
    def test_exact_ordered_handoffs_and_disjoint_indices(self):
        _, _, plan, _ = build(ROOT)
        rows = plan["scope"]["ordered_handoffs"]
        self.assertEqual([(row["role"], row["scan"]) for row in rows],
                         [(role, label) for role in ROLES for label in LABELS])
        self.assertEqual([row["handoff_index"] for row in rows], list(range(12)))
        self.assertEqual([row["chunk_index"] for row in rows], [159] * 6 + [156] * 6)

    def test_exact_laws_and_pure_observation(self):
        _, _, plan, _ = build(ROOT)
        result = observe(ROOT)
        self.assertEqual(tuple(row["name"] for row in result["cases"]), LAW_NAMES)
        self.assertEqual(result["payload_index_attempts"], 0)
        self.assertEqual(result["case_count"], 22)
        self.assertEqual([row["expected"] for row in plan["case_laws"]],
                         [row["observed"] for row in result["cases"]])

    def test_no_native_execution_or_authority_transition(self):
        _, _, plan, review = build(ROOT)
        self.assertEqual(plan["status"], "SOURCE_ONLY_NO_DISPATCH")
        self.assertIs(plan["execution_enabled"], False)
        self.assertTrue(all(value == 0 for value in plan["counters"].values()))
        self.assertEqual(review["status"], "PASS_SOURCE_ONLY")
        self.assertFalse(review["execution_authorized"])
        self.assertTrue(all(name not in sys.modules for name in ("numpy", "h5py", "hdf5plugin")))

    def test_manifest_and_selection_bindings(self):
        manifest, selection, plan, review = build(ROOT)
        self.assertEqual(plan["input_manifest_sha256"], hashlib.sha256(canonical(manifest)).hexdigest())
        self.assertEqual(plan["selection_manifest_sha256"], hashlib.sha256(canonical(selection)).hexdigest())
        self.assertEqual(review["handoff_count"], 12)
        self.assertEqual(review["law_count"], 22)
        self.assertEqual(manifest["files"]["src/seti_repeater/search_v0p6.py"]["sha256"],
                         "6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4")

    def test_resource_caps_are_internally_closed(self):
        _, _, plan, _ = build(ROOT)
        envelope = plan["draft_envelope"]
        self.assertEqual(envelope["hdf5_file_count"] * envelope["each_hdf5_file_cap_bytes"],
                         384 * 1024**2)
        self.assertEqual(envelope["leaf_output_cap_bytes"] + envelope["outer_terminal_reserve_bytes"],
                         envelope["artifact_cap_bytes"])
        self.assertGreaterEqual(envelope["suggested_address_space_bytes"], envelope["suggested_rss_ceiling_bytes"])

    def test_formula_has_explicit_handoff_salt_and_no_prng(self):
        _, _, plan, _ = build(ROOT)
        formula = plan["deterministic_construction"]
        self.assertIn("256*handoff_index", formula["formula"])
        self.assertIs(formula["prng_or_noise_model"], False)
        numerators = {409600 + 256 * handoff for handoff in range(12)}
        self.assertEqual(len(numerators), 12)

    def test_duplicate_json_and_selected_definition_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                parse(raw)
        selection = {"assignments": [], "functions": ["one"], "classes": []}
        with self.assertRaises(ValueError):
            selected_nodes(b"def one(): pass\ndef one(): pass\n", selection)

    def test_bounded_reader_rejects_oversize(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "large"
            path.write_bytes(b"123456789")
            with self.assertRaises(ValueError):
                read(folder, "large", maximum=8)

    def test_metadata_control_imports_stdlib_only(self):
        tree = ast.parse((HERE / "metadata_law_control.py").read_bytes())
        imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertTrue(imports <= {"ast", "copy", "hashlib", "json"})


if __name__ == "__main__":
    unittest.main()
