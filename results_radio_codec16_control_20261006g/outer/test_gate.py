"""Pure admission tests. No native imports, subprocess, run_leaf, or produce."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("_codec16_G_outer_tested",Path(__file__).with_name("gate.py"))
gate_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_module)


class Fixture:
    def __init__(self,root):
        self.root=Path(root)
        source=self.root/"source"
        source.mkdir()
        output=self.root/"artifacts"
        output.mkdir()
        runtime=self.root/"runtime"
        runtime.mkdir()
        roles={}
        for role in sorted(gate_module.ROLE_KEYS):
            path=(runtime if role=="python" else source)/role
            path.write_bytes(("inert fixture "+role+"\n").encode())
            roles[role]=str(path)
        plan=dict(scope=dict(row_indices=list(range(16)),telescope_provenance=False,
            kind="controlled-source-shaped-codec-normalization"))
        Path(roles["plan"]).write_bytes(gate_module.canonical(plan))
        dispatch=dict(schema="codec16-fresh-engineering-dispatch-v1",scope_id="codec16-pure-test",
            plan_sha256=self.sha(roles["plan"]),input_manifest_sha256=self.sha(roles["input_manifest"]),
            selection_sha256=self.sha(roles["selection"]),runtime_prefix=str(runtime),
            outer_supervisor_scope_sha256=self.sha(roles["scope"]),engineering_execution_authorized=True)
        Path(roles["dispatch"]).write_bytes(gate_module.canonical(dispatch))
        pins=[]
        for path in roles.values():
            pin=gate_module.pin_record(path)
            pin["sha256"]=self.sha(path)
            pins.append(pin)
        self.config=dict(schema=gate_module.SCHEMA,scope_id="codec16-pure-test",roles=roles,
            pinned_files=sorted(pins,key=lambda p:p["path"]),inventory_roots=sorted([str(source),str(runtime)]),
            runtime_prefix=str(runtime),cwd=str(self.root),environment=dict(PYTHONDONTWRITEBYTECODE="1",
                OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1"),
            budgets=dict(gate_module.BUDGETS),artifacts=dict(root=str(output),leaf_output=str(output/"payload"),
                output_prefix=str(output/"leaf"),outer_report=str(output/"outer.json"),
                spent_marker=str(self.root/"spent.json")))
        self.write_inputs()

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def write_inputs(self):
        self.config_path=self.root/"config.json"
        self.config_path.write_bytes(gate_module.canonical(self.config))
        proof=dict(schema="radio-codec16-preread-G-v1",config_sha256=self.sha(self.config_path),
            scope_id=self.config["scope_id"],pinned_files_sha256=hashlib.sha256(gate_module.canonical(self.config["pinned_files"])).hexdigest(),
            all_reads_complete=True,readback=self.config["pinned_files"],
            read_bytes=sum(p["bytes"] for p in self.config["pinned_files"]))
        self.proof_path=self.root/"proof.json"
        self.proof_path.write_bytes(gate_module.canonical(proof))

    def load(self):
        return gate_module.Gate().load(str(self.config_path),self.config_path.stat().st_size,self.sha(self.config_path),
            str(self.proof_path),self.proof_path.stat().st_size,self.sha(self.proof_path))


class PureGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix="codec16-G-outer-pure-")
        self.fixture=Fixture(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_full_preread_admission_has_no_marker_or_dispatch(self):
        gate=self.fixture.load()
        gate.snapshot("PRE")
        gate.admission()
        self.assertEqual(gate.snapshots[0]["files"],13)
        self.assertEqual(gate.child_dispatches,0)
        self.assertFalse(gate.marker_created)
        self.assertFalse(Path(self.fixture.config["artifacts"]["spent_marker"]).exists())

    def test_proof_must_match_complete_independently_pinned_config(self):
        proof=json.loads(self.fixture.proof_path.read_bytes())
        proof["read_bytes"]-=1
        self.fixture.proof_path.write_bytes(gate_module.canonical(proof))
        with self.assertRaisesRegex(ValueError,"preread proof"):
            self.fixture.load()

    def test_modified_input_is_refused_before_marker(self):
        gate=self.fixture.load()
        Path(gate.config["roles"]["leaf_script"]).write_text("changed\n")
        with self.assertRaises(ValueError):
            gate.snapshot("PRE")
        self.assertFalse(gate.marker_created)

    def test_inode_replacement_same_bytes_is_refused(self):
        gate=self.fixture.load()
        target=Path(gate.config["roles"]["leaf_script"])
        replacement=target.with_name("replacement")
        replacement.write_bytes(target.read_bytes())
        replacement.replace(target)
        with self.assertRaisesRegex(ValueError,"identity"):
            gate.snapshot("PRE")

    def test_added_runtime_file_is_not_ignored(self):
        gate=self.fixture.load()
        (Path(gate.config["runtime_prefix"])/"new-loader-hook").write_text("inert\n")
        with self.assertRaisesRegex(ValueError,"inventory"):
            gate.snapshot("PRE")

    def test_spent_marker_is_exclusive_and_never_reused(self):
        gate=self.fixture.load()
        gate.snapshot("PRE")
        gate.admission()
        gate.acquire_marker()
        marker=Path(gate.config["artifacts"]["spent_marker"])
        self.assertTrue(marker.is_file())
        with self.assertRaises(FileExistsError):
            gate.acquire_marker()
        with self.assertRaisesRegex(ValueError,"already exists"):
            self.fixture.load()
        self.assertEqual(gate.child_dispatches,0)

    def test_parent_and_child_read_allocations_are_separate(self):
        gate=self.fixture.load()
        gate.read_bytes=gate_module.BUDGETS["parent_read_bytes"]
        with self.assertRaisesRegex(ValueError,"aggregate read"):
            gate.charge(1)
        self.assertEqual(gate_module.BUDGETS["child_read_reserve_bytes"],512*1024**2)

    def test_budget_types_cannot_be_boolean_or_floating_byte_values(self):
        self.fixture.config["budgets"]["child_cpu_seconds"]=80.0
        self.fixture.write_inputs()
        with self.assertRaisesRegex(ValueError,"allocation"):
            self.fixture.load()

    def test_record_never_promotes_manifest_snapshots_to_science_or_loader_custody(self):
        gate=self.fixture.load()
        result=gate.honest_record()
        for key in ("scientific_authority","scientific_readiness","complete_codec_certificate_issued",
                    "full_native_graph_qualified","full_native_io_custody","historical_runtime_loader_continuous_custody",
                    "read_charge_is_complete_parent_lifetime"):
            self.assertIs(result[key],False)
        self.assertEqual(result["archive_spectral_values_read"],0)

    def test_parent_active_deadline_refuses_reads(self):
        gate=self.fixture.load()
        gate.active_deadline=0
        with self.assertRaises(TimeoutError):
            gate.snapshot("PRE")

    def test_generated_read_rejects_symlink(self):
        gate=self.fixture.load()
        target=Path(gate.config["roles"]["scope"])
        link=self.fixture.root/"generated-link"
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError,"canonical"):
            gate.generated_bytes(link,1024)

    def test_original_F_components_are_byte_identical(self):
        original=Path(__file__).parents[2]/"previous/F/absolute_paths/workspace/scratch/da6462abff17/proc-io-preparation-20261006f/supervisor"
        copied=Path(__file__).with_name("supervisor")
        for name in ("leaf_supervisor.py","proc_custody.py","leaf_guard","leaf_guard.c",
                     "exec_seal.so","exec_seal.c","phase2_bootstrap.py"):
            self.assertEqual((original/name).read_bytes(),(copied/name).read_bytes(),name)


if __name__=="__main__":
    unittest.main(verbosity=2)
