"""Disjoint synthetic children only; never invoke the real runtime collector."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("synthetic_runtime_capture_gate", HERE / "capture_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": gate.digest(raw),
            "mode": format(path.stat().st_mode & 0o7777, "04o")}


SUCCESS = '''import json,sys
args=dict(zip(sys.argv[1::2],sys.argv[2::2]))
raw=open(args['--contract'],'rb').read()
c=json.loads(raw)
out={'schema':'radio-runtime-metadata-capture-observation-v1','status':'OBSERVED_METADATA_ONLY',
     'capture_identity':c['capture_identity'],'contract_sha256':args['--contract-sha256'],
     'plan_sha256':args['--plan-sha256'],'authority':{'scientific_execution_authorized':False},
     'read_ledger':{'read_bytes':len(raw)}}
sys.stdout.write(json.dumps(out)+'\\n')
'''


class Fixture:
    def __init__(self, test, child=SUCCESS):
        self.temporary = tempfile.TemporaryDirectory(prefix="runtime-gate-SYNTHETIC-")
        test.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        self.output.mkdir(mode=0o700)
        self.child = self.root / "synthetic-child.py"
        self.child.write_text(child)
        self.child_contract = self.root / "synthetic-child-contract.json"
        self.child_contract.write_bytes(gate.canonical({"capture_identity": "b" * 64, "limits": {"read_bytes": 65536}}))
        self.plan = self.root / "synthetic-plan.json"
        self.plan.write_bytes(b"{}\n")
        self.activation = self.root / "synthetic-activation.json"
        python = Path(sys.executable).resolve()
        root_stat = self.output.stat()
        self.contract = {"schema": gate.SCHEMA, "capture_identity": "b" * 64,
            "evidence_domain": "synthetic-test-fixture",
            "source_pins": sorted([pin(HERE / "capture_gate.py"), pin(self.child), pin(self.child_contract), pin(self.plan)], key=lambda p:p["path"]),
            "runtime_pins": [pin(python)], "python_executable": str(python),
            "python_sha256": pin(python)["sha256"], "collector_path": str(self.child),
            "collector_contract_path": str(self.child_contract), "collector_contract_sha256": pin(self.child_contract)["sha256"],
            "plan_path": str(self.plan), "plan_sha256": pin(self.plan)["sha256"],
            "output_root": str(self.output), "output_root_identity": {"device":root_stat.st_dev,"inode":root_stat.st_ino,"mode":"0700"},
            "spent_path": str(self.output / "spent.json"), "activation_path": str(self.activation),
            "limits": {"wall_seconds": 6, "child_seconds": 2, "reap_seconds": 1,
                "artifact_bytes": 1024**2, "rss_bytes": 512*1024**2,
                "read_bytes":256*1024**2,"stream_bytes":131072,"sample_count":100}}
        self.build()

    def build(self):
        self.contract_raw = gate.canonical(self.contract)
        self.contract_sha = gate.digest(self.contract_raw)
        self.marker = {"schema":gate.MARKER_SCHEMA,"capture_identity":self.contract["capture_identity"],
            "prepared_commit":"1"*40,"prepared_tree":"2"*40,"contract_sha256":self.contract_sha,
            "engineering_only":True,"single_use":True}
        self.marker_raw = gate.canonical(self.marker)
        self.activation.write_bytes(self.marker_raw)
        self.proof = {"schema":gate.PROOF_SCHEMA,"repository":"andersenmartin-blip/setisearch",
            "branch":"m43-support-qualification","prepared_commit":"1"*40,"prepared_tree":"2"*40,
            "activation_commit":"3"*40,"activation_tree":"4"*40,"activation_parent":"1"*40,
            "activation_changed_path":"config/radio_runtime_metadata_capture_20261004a.activate.json",
            "contract_sha256":self.contract_sha,"capture_identity":self.contract["capture_identity"],
            "collector_contract_sha256":self.contract["collector_contract_sha256"],"plan_sha256":self.contract["plan_sha256"],
            "activation_sha256":gate.digest(self.marker_raw),"provenance":"EXPLICIT SYNTHETIC FIXTURE; no service receipts",
            "publication_files":[]}
        for p in self.contract["source_pins"]:
            raw = Path(p["path"]).read_bytes()
            self.proof["publication_files"].append({**p,"repository_path":"synthetic/"+Path(p["path"]).name,
                "content_base64":base64.b64encode(raw).decode(),
                "git_blob":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()})
        self.proof_raw = gate.canonical(self.proof)

    def run(self):
        return gate.run(self.contract_raw,self.contract_sha,self.proof_raw,gate.digest(self.proof_raw),
                        self.marker_raw,gate.digest(self.marker_raw))


class GateTests(unittest.TestCase):
    def test_one_successful_disjoint_child_and_full_raw_receipt(self):
        f=Fixture(self)
        result=f.run()
        self.assertEqual(result["report"]["status"],"OBSERVED_METADATA_ONLY")
        self.assertTrue(result["report"]["child_reaped"])
        self.assertTrue(result["report"]["selected_before_after_equal"])
        self.assertFalse(any(result["report"]["authority"].values()))
        self.assertEqual((f.output/"child.stderr.raw").read_bytes(),b"")
        self.assertEqual((f.output/"admission-witness.json").read_bytes(),f.proof_raw)
        self.assertLess(result["whole_scope_elapsed_seconds"],6)
        self.assertLess(result["report"]["joined_selected_read_conservative_bytes"],f.contract["limits"]["read_bytes"])
        self.assertEqual({row["path"] for row in result["final_scope"]["entries"]},
            {"spent.json","selected-runtime-before.json","selected-runtime-after.json","child.stdout.raw","child.stderr.raw","procfs-samples.json","supervisor-result.json","admission-witness.json"})

    def test_spent_identity_cannot_resume_or_rearm(self):
        f=Fixture(self); f.run()
        marker=(f.output/"spent.json").read_bytes()
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual((f.output/"spent.json").read_bytes(),marker)

    def test_public_scientific_domain_refuses_before_spend(self):
        f=Fixture(self);f.contract["evidence_domain"]="public-scientific-evidence";f.build()
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_no_default_or_extra_fields(self):
        f=Fixture(self);f.contract["qualified"]=True;f.build()
        with self.assertRaises(gate.Refusal):f.run()

    def test_runtime_pin_drift_refuses_before_spend(self):
        f=Fixture(self);f.plan.write_bytes(b"[]\n")
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_named_directory_substitution_refuses(self):
        f=Fixture(self);f.output.rename(f.root/"original-output");f.output.mkdir(mode=0o700)
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_fullcontent_publication_mismatch_refuses(self):
        f=Fixture(self);f.proof["publication_files"][0]["content_base64"]="eA==";f.proof_raw=gate.canonical(f.proof)
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_activation_wrong_parent_refuses(self):
        f=Fixture(self);f.proof["activation_parent"]="0"*40;f.proof_raw=gate.canonical(f.proof)
        with self.assertRaises(gate.Refusal):f.run()

    def test_marker_local_drift_refuses(self):
        f=Fixture(self);f.activation.write_bytes(b"{}\n")
        with self.assertRaises(gate.Refusal):f.run()
        self.assertFalse((f.output/"spent.json").exists())

    def test_spent_filename_cannot_be_reused_for_report(self):
        f=Fixture(self);f.contract["spent_path"]=str(f.output/"supervisor-result.json");f.build()
        with self.assertRaises(gate.Refusal):f.run()

    def test_limit_types_and_ceiling_reject(self):
        f=Fixture(self);f.contract["limits"]["child_seconds"]=True;f.build()
        with self.assertRaises(gate.Refusal):f.run()
        f.contract["limits"]["child_seconds"]=51;f.build()
        with self.assertRaises(gate.Refusal):f.run()

    def test_joined_read_reservation_refuses_insufficient_room(self):
        f=Fixture(self);f.contract["limits"]["read_bytes"]=1_000_000;f.build()
        with self.assertRaises(gate.Refusal):f.run()
        self.assertFalse((f.output/"spent.json").exists())

    def test_nonzero_child_retains_exact_stderr_and_is_spent(self):
        f=Fixture(self,"import sys\nsys.stderr.write('SYNTHETIC terminal failure\\n')\nraise SystemExit(7)\n")
        result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertEqual(result["report"]["child_exit_code"],7)
        self.assertEqual((f.output/"child.stderr.raw").read_bytes(),b"SYNTHETIC terminal failure\n")
        self.assertTrue((f.output/"spent.json").exists())

    def test_empty_stdout_cannot_be_success(self):
        f=Fixture(self,"pass\n");result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertTrue(result["report"]["failure"].startswith("CHILD_RECEIPT"))

    def test_fresh_child_deadline_kills_and_reaps(self):
        f=Fixture(self,"import time\ntime.sleep(10)\n")
        f.contract["limits"]["child_seconds"]=1;f.build()
        result=f.run()
        self.assertEqual(result["report"]["failure"],"CHILD_DEADLINE")
        self.assertTrue(result["report"]["child_reaped"])
        self.assertLess(result["whole_scope_elapsed_seconds"],4)

    def test_raw_stream_cap_is_terminal_and_retains_received_prefix(self):
        f=Fixture(self,"import sys\nsys.stdout.write('x'*200000)\nsys.stdout.flush()\n")
        result=f.run()
        self.assertEqual(result["report"]["failure"],"RAW_STREAM_CAP")
        self.assertEqual(len((f.output/"child.stdout.raw").read_bytes()),131073)
        self.assertTrue(result["report"]["child_reaped"])

    def test_child_selected_source_modification_is_terminal(self):
        child="import sys\na=dict(zip(sys.argv[1::2],sys.argv[2::2]))\nopen(a['--plan'],'wb').write(b'changed')\n"+SUCCESS
        f=Fixture(self,child);result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertTrue(result["report"]["failure"].startswith("TERMINAL_PIN_DRIFT"))
        self.assertIsNone(json.loads((f.output/"selected-runtime-after.json").read_bytes()))

    def test_reads_disallow_hardlinks_and_ancestor_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC-read-") as tmp:
            p=Path(tmp)/"one";p.write_bytes(b"1234");os.link(p,Path(tmp)/"two")
            with self.assertRaises(gate.Refusal):gate.Reads(10).file(str(p),10)
            p.unlink();(Path(tmp)/"two").unlink();p.write_bytes(b"1234")
            alias=Path(tmp)/"alias";alias.symlink_to(tmp,target_is_directory=True)
            with self.assertRaises(OSError):gate.Reads(10).file(str(alias/"one"),10)

    def test_exact_remaining_read_budget_cannot_overread(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC-read-") as tmp:
            p=Path(tmp)/"one";p.write_bytes(b"1234")
            reads=gate.Reads(4)
            self.assertEqual(reads.file(str(p),4)[0],b"1234")
            self.assertEqual(reads.bytes,4)
            with self.assertRaises(gate.Refusal):reads.file(str(p),4)

    def test_duplicate_json_pin_is_rejected(self):
        raw=b'{"x":1,"x":2}'
        with self.assertRaises(gate.Refusal):gate._json(raw,gate.digest(raw))


if __name__=="__main__":unittest.main(verbosity=2)
