"""Offline gate admission/custody tests using synthetic receipts and temp files.

No activation, installation, guard invocation, native package import or scientific
data operation occurs. Only pure admission/parsing and stdlib held-file reads run.
"""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).with_name("runtime_gate.py")
spec = importlib.util.spec_from_file_location("offline_runtime_gate_under_test", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def inputs():
    # These intentionally synthetic publication identities refer to no repository
    # object, file receipt, activation or real prospective scope mutation.
    prepared = "1" * 40
    tree = "2" * 40
    marker_path = "config/SYNTHETIC_OFFLINE_TEST_ONLY.activate.json"
    sources = [{"path": "SYNTHETIC_SOURCE_ONLY.py", "bytes": 7, "sha256": "3" * 64}]
    freeze_hash, marker_hash = "4" * 64, "5" * 64
    freeze = dict(schema=gate.SCHEMA, identity=gate.IDENTITY, single_use=True,
                  automatic_successor=False, engineering_only=True, network=False,
                  hdf5_dataset_access=False, scientific_authority=False,
                  marker_repository_path=marker_path, published_sources=sources,
                  limits=dict(wall_seconds=300, operation_seconds=270,
                    child_wall_seconds=120, child_cpu_seconds=100,
                    parent_address_space_bytes=512*1024**2,
                    child_address_space_bytes=512*1024**2, artifact_bytes=1536*1024**2,
                    parent_read_bytes=3*1024**3, child_read_reserve_bytes=1024**3,
                    joined_read_bytes=4*1024**3, stream_bytes=4*1024**2,
                    root_explicit_read_bytes=624*1024**2,
                    installer_explicit_read_bytes=2304*1024**2,
                    supervisor_explicit_pin_read_bytes=64*1024**2,
                    supervisor_explicit_proc_read_bytes=64*1024**2,
                    misc_stream_read_bytes=16*1024**2,
                    child_sample_interval_seconds=0.02, child_cleanup_seconds=10,
                    file_bytes=128*1024**2, file_count=20000, directory_count=4096,
                    child_dispatches=2, terminal_reserve_bytes=8*1024**2))
    marker = dict(schema="radio-offline-runtime-materialization-activation-v1",
                  identity=gate.IDENTITY, freeze_sha256=freeze_hash,
                  prepared_commit=prepared, prepared_tree=tree,
                  single_use=True, automatic_successor=False)
    proof = dict(schema="radio-offline-runtime-materialization-publication-proof-v1",
                 repository="andersenmartin-blip/setisearch", branch="m43-support-qualification",
                 preparation_commit=prepared, preparation_tree=tree,
                 activation_commit="6"*40, marker_sha256=marker_hash,
                 sole_parent=prepared, changed_paths=[marker_path],
                 full_preparation_readback_exact=True, marker_readback_exact=True,
                 source_readbacks=copy.deepcopy(sources))
    return freeze, proof, marker, freeze_hash, marker_hash


class AdmissionTests(unittest.TestCase):
    def test_synthetic_binding_admitted_without_side_effects(self):
        args = inputs()
        before = copy.deepcopy(args)
        self.assertIsNone(gate.admit(*args))
        self.assertEqual(args, before)

    def test_wrong_diff_extra_or_reordered_paths_refused(self):
        for changed in ([], ["wrong"], [inputs()[0]["marker_repository_path"], "extra"]):
            with self.subTest(changed=changed):
                args = inputs(); args[1]["changed_paths"] = changed
                with self.assertRaises(gate.Refusal): gate.admit(*args)

    def test_wrong_parent_preparation_tree_and_raw_bindings_refused(self):
        for item, key, value in ((1,"sole_parent","0"*40),
                                 (1,"preparation_commit","0"*40),
                                 (1,"preparation_tree","0"*40),
                                 (1,"marker_sha256","0"*64),
                                 (2,"freeze_sha256","0"*64)):
            with self.subTest(key=key):
                args = inputs(); args[item][key] = value
                with self.assertRaises(gate.Refusal): gate.admit(*args)

    def test_every_scope_flag_and_readback_flag_must_be_exact_boolean(self):
        cases = [(0,k) for k in ("single_use","automatic_successor","engineering_only",
                 "network","hdf5_dataset_access","scientific_authority")]
        cases += [(2,k) for k in ("single_use","automatic_successor")]
        cases += [(1,k) for k in ("full_preparation_readback_exact","marker_readback_exact")]
        for item,key in cases:
            for value in (not inputs()[item][key], int(inputs()[item][key]), None):
                with self.subTest(item=item,key=key,value=value):
                    args = inputs(); args[item][key] = value
                    with self.assertRaises(gate.Refusal): gate.admit(*args)

    def test_each_limit_cannot_expand_or_shrink(self):
        for key in inputs()[0]["limits"]:
            for delta in (-1,1):
                with self.subTest(limit=key,delta=delta):
                    args = inputs(); args[0]["limits"][key] += delta
                    with self.assertRaises(gate.Refusal): gate.admit(*args)
        args=inputs(); args[0]["limits"]["unfrozen_extra"] = 1
        with self.assertRaises(gate.Refusal): gate.admit(*args)

    def test_published_source_receipt_mutation_refused(self):
        args=inputs(); args[1]["source_readbacks"][0]["sha256"]="0"*64
        with self.assertRaises(gate.Refusal): gate.admit(*args)

    def test_wrong_repository_branch_and_activation_shape_refused(self):
        for key,value in (("repository","other/repository"),("branch","main"),
                          ("activation_commit","short")):
            args=inputs();args[1][key]=value
            with self.assertRaises(gate.Refusal):gate.admit(*args)


class JsonTests(unittest.TestCase):
    def test_exact_raw_hash_required(self):
        raw=b'{"only":"synthetic"}\n'
        self.assertEqual(gate.json_checked(raw,gate.sha(raw)),{"only":"synthetic"})
        with self.assertRaisesRegex(gate.Refusal,"raw hash"):
            gate.json_checked(raw+b" ",gate.sha(raw))

    def test_duplicate_json_key_rejected_at_all_depths(self):
        for raw in (b'{"a":1,"a":2}',b'{"nested":{"a":1,"a":2}}'):
            with self.assertRaisesRegex(gate.Refusal,"duplicate JSON"):
                gate.json_checked(raw,gate.sha(raw))

    def test_nonobject_input_rejected(self):
        raw=b'[1,2]'
        with self.assertRaisesRegex(gate.Refusal,"JSON object"):
            gate.json_checked(raw,gate.sha(raw))


class ReadTests(unittest.TestCase):
    def test_current_exact_file_pin_then_tampered_file_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"input"; raw=b"synthetic receipt bytes"; p.write_bytes(raw)
            pin={"path":str(p),"bytes":len(raw),"sha256":gate.sha(raw),"mode":p.stat().st_mode&0o7777}
            reads=gate.Reads();self.assertEqual(reads.pin(pin),raw)
            self.assertEqual(reads.charged,len(raw))
            p.write_bytes(b"changed receipt bytes")
            with self.assertRaises(gate.Refusal):reads.pin(pin)

    def test_leaf_and_ancestor_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d); p=directory/"input";p.write_bytes(b"synthetic")
            link=directory/"alias";link.symlink_to(p)
            ancestor=directory/"parent-alias";ancestor.symlink_to(directory,target_is_directory=True)
            for candidate in (link,ancestor/"input"):
                with self.subTest(path=candidate):
                    with self.assertRaises(gate.Refusal):gate.Reads().raw(candidate)

    def test_mutation_during_held_read_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"input";p.write_bytes(b"first synthetic receipt")
            real_read=gate.os.read
            def mutate(fd,count):
                raw=real_read(fd,count)
                p.write_bytes(b"second synthetic receipt expanded")
                return raw
            with patch.object(gate.os,"read",side_effect=mutate):
                with self.assertRaisesRegex(gate.Refusal,"custody changed"):
                    gate.Reads().raw(p)

    def test_short_read_perfile_cap_and_aggregate_budget_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"input";p.write_bytes(b"synthetic")
            with self.assertRaisesRegex(gate.Refusal,"bounded"):
                gate.Reads().raw(p,cap=3)
            with patch.object(gate.os,"read",return_value=b""):
                with self.assertRaisesRegex(gate.Refusal,"short"):
                    gate.Reads().raw(p)
            with patch.object(gate,"MAX_GATE_READ",3):
                with self.assertRaisesRegex(gate.Refusal,"reservation"):
                    gate.Reads().raw(p)


if __name__=="__main__":
    unittest.main()
