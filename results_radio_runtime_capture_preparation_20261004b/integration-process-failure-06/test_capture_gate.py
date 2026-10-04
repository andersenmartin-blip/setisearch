"""Disjoint synthetic children only; never invoke the real runtime collector."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("synthetic_runtime_capture_gate", HERE / "capture_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": gate.digest(raw),
            "mode": format(path.stat().st_mode & 0o7777, "04o")}


SUCCESS = '''import json,sys,time
args=dict(zip(sys.argv[1::2],sys.argv[2::2]))
raw=open(args['--contract'],'rb').read()
c=json.loads(raw)
out={'schema':'radio-runtime-metadata-capture-observation-v1','status':'OBSERVED_METADATA_ONLY',
     'capture_identity':c['capture_identity'],'contract_sha256':args['--contract-sha256'],
     'plan_sha256':args['--plan-sha256'],'authority':{'scientific_execution_authorized':False},
     'read_ledger':{'read_bytes':len(raw)}}
sys.stdout.write(json.dumps(out)+'\\n')
sys.stdout.flush()
time.sleep(.08)
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
                "artifact_bytes": 2*1024**2, "rss_bytes": 512*1024**2,
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
            "activation_changed_path":"config/radio_runtime_metadata_capture_20261004b.activate.json",
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
    def test_retained_collision_never_admitted_without_kernel_handle(self):
        # Exact historical evidence, read only.  The original matcher admitted
        # all three unrelated caas-prefix-tra records solely on NSpid tail 6.
        observations=json.loads((HERE.parent / "results_radio_runtime_capture_repair_preparation_20261004a" / "basis" / "procfs-samples.json").read_bytes())
        class Inventory:
            def __init__(self, value): self.name=str(value).rsplit("/",1)[-1]
            def iterdir(self): return [Inventory("/proc/6")]
            def __truediv__(self, leaf): return "/proc/6/"+leaf
        for item in observations:
            status=base64.b64decode(item["status_base64"])
            process_stat=base64.b64decode(item["stat_base64"])
            class FixtureReads:
                def proc(self, path, cap): return status if path.endswith("/status") else process_stat
            with patch.object(gate,"Path",Inventory):
                with self.assertRaises(gate.Refusal):
                    gate._proc_observation(6,FixtureReads())

    def test_one_successful_disjoint_child_and_full_raw_receipt(self):
        f=Fixture(self)
        result=f.run()
        self.assertEqual(result["report"]["status"],"OBSERVED_METADATA_ONLY",result["report"]["failure"])
        self.assertTrue(result["report"]["child_reaped"])
        self.assertTrue(result["report"]["selected_before_after_equal"])
        self.assertFalse(any(result["report"]["authority"].values()))
        self.assertTrue(result["report"]["engineering_capture_authorized"])
        self.assertTrue(result["report"]["engineering_reservation_spent"])
        self.assertEqual(result["report"]["engineering_child_dispatches"],1)
        self.assertEqual((f.output/"child.stderr.raw").read_bytes(),b"")
        self.assertEqual((f.output/"admission-witness.json").read_bytes(),f.proof_raw)
        self.assertLess(result["whole_scope_elapsed_seconds"],6)
        self.assertLess(result["report"]["joined_selected_read_conservative_bytes"],f.contract["limits"]["read_bytes"])
        self.assertEqual({row["path"] for row in result["final_scope"]["entries"]},
            {"spent.json","selected-runtime-before.json","selected-runtime-after.json","child.stdout.raw","child.stderr.raw","procfs-samples.json","supervisor-result.json","admission-witness.json"})

    def test_tight_artifact_envelope_refuses_before_spend(self):
        f=Fixture(self);f.contract["limits"]["artifact_bytes"]=1024**2;f.build()
        with self.assertRaises(gate.Refusal):f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_frozen_collector_bytes_survive_path_swap_before_dispatch(self):
        f=Fixture(self,SUCCESS.replace(".08",".3"))
        original=f.child.read_bytes()
        real_popen=gate.subprocess.Popen
        dispatch=[]
        def swap_then_dispatch(command,**kwargs):
            dispatch.append(command)
            self.assertEqual(command[4],"-c")
            f.child.write_bytes(b"import sys,time\nprint('UNVERIFIED_PATH_BYTES')\nsys.stdout.flush()\ntime.sleep(.3)\n")
            try:
                child=real_popen(command,**kwargs)
                time.sleep(.015)
                return child
            finally:f.child.write_bytes(original)
        with patch.object(gate.subprocess,"Popen",side_effect=swap_then_dispatch):result=f.run()
        self.assertEqual(len(dispatch),1)
        self.assertEqual(result["report"]["status"],"OBSERVED_METADATA_ONLY",result["report"]["failure"])
        self.assertNotIn(b"UNVERIFIED_PATH_BYTES",(f.output/"child.stdout.raw").read_bytes())
        self.assertTrue(result["report"]["selected_before_after_equal"])

    def test_frozen_dispatch_preserves_main_module_file_and_argv(self):
        child=SUCCESS.replace("args=dict", "assert __file__==sys.argv[0]\nassert sys.modules[__name__].__dict__ is globals()\nargs=dict")
        f=Fixture(self,child);result=f.run()
        self.assertEqual(result["report"]["status"],"OBSERVED_METADATA_ONLY",result["report"]["failure"])
        self.assertEqual((f.output/"child.stderr.raw").read_bytes(),b"")

    def test_partial_group_evidence_cap_preserves_received_records_and_reaps(self):
        f=Fixture(self,SUCCESS.replace(".08",".4"))
        real_group=gate._group_observations
        received=[]
        class Entry:
            def __init__(self,number):self.name=str(number)
        class Inventory:
            def __enter__(self):return iter(Entry(n) for n in range(1,101))
            def __exit__(self,*args):return False
        def capped_group(directory,group_pid,reads,deadline,retained=None):
            class SyntheticReads:
                def proc_at(self,pid,leaf,cap):
                    fields=["S","500",str(group_pid),str(group_pid)]+["0"]*16
                    fields[17],fields[19]="1","101"
                    raw=str(pid).encode()+b" ("+b"x"*12000+b") "+" ".join(fields).encode()+b"\n"
                    reads.bytes+=len(raw);received.append(raw)
                    return raw
            with patch.object(gate.os,"scandir",return_value=Inventory()),patch.object(gate.os,"open",side_effect=lambda name,*args,**kwargs:int(name)),patch.object(gate.os,"close"):
                return real_group(directory,group_pid,SyntheticReads(),deadline,retained=retained)
        with patch.object(gate,"_group_observations",side_effect=capped_group):result=f.run()
        self.assertEqual(result["report"]["failure"],"PROCFS_EVIDENCE_CAP")
        self.assertTrue(result["report"]["child_reaped"])
        group=result["report"]["process_attribution"]["partial_sampling_attempt"]["group_snapshot"]
        self.assertTrue(group["remaining_process_records_unobserved"])
        self.assertFalse(group["membership_scan_complete"])
        self.assertEqual([base64.b64decode(x["stat_base64"]) for x in group["visible_process_stat_records"]],received)
        self.assertLessEqual(len(gate.canonical(group)),131072)
        self.assertLess(max(result["final_scope"]["logical_bytes"],result["final_scope"]["allocated_bytes"]),f.contract["limits"]["artifact_bytes"])

    def test_sample_aggregate_stops_before_next_observation_without_spill(self):
        f=Fixture(self,SUCCESS.replace(".08","1.4"))
        calls=[]
        raw_record=b"x"*70000
        def large_group(directory,group_pid,reads,deadline,retained=None):
            calls.append(group_pid)
            result={"observed_process_group_members":[group_pid],"visible_process_ids":[str(group_pid)],
                "visible_process_stat_records":[{"procfs_pid":group_pid,"stat_base64":base64.b64encode(raw_record).decode()}],
                "unavailable_process_records":[],"membership_scan_complete":True,
                "aggregate_descendant_absence_certified":False,"remaining_process_records_unobserved":False,
                "evidence_limit_bytes":131072}
            if retained is not None:retained["group_snapshot"]=result
            return result
        with patch.object(gate,"_group_observations",side_effect=large_group):result=f.run()
        self.assertEqual(result["report"]["failure"],"ARTIFACT_ENVELOPE")
        self.assertTrue(result["report"]["child_reaped"])
        samples=json.loads((f.output/"procfs-samples.json").read_bytes())
        self.assertEqual(len(samples),len(calls))
        for item in samples:self.assertEqual(base64.b64decode(item["visible_process_stat_records"][0]["stat_base64"]),raw_record)
        self.assertLess(max(result["final_scope"]["logical_bytes"],result["final_scope"]["allocated_bytes"]),f.contract["limits"]["artifact_bytes"])

    def test_cleanup_retains_both_sampling_and_terminal_received_failure_bytes(self):
        f=Fixture(self,SUCCESS.replace(".08",".3"))
        first=gate.Refusal("synthetic initial sample read failure")
        first.proc_read_evidence={"raw_received_base64":base64.b64encode(b"SAMPLE_RECEIVED_PREFIX").decode()}
        def failed_terminal(binding,waited,reads):
            binding.reaped=True
            terminal=gate.Refusal("synthetic terminal fdinfo read failure")
            terminal.proc_read_evidence={"raw_received_base64":base64.b64encode(b"TERMINAL_RECEIVED_PREFIX").decode()}
            raise terminal
        with patch.object(gate,"_proc_observation",side_effect=first),patch.object(gate.KernelChild,"mark_reaped",new=failed_terminal):result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertTrue(result["report"]["child_reaped"])
        receipt=result["report"]["process_attribution"]
        self.assertEqual(base64.b64decode(receipt["proc_read_failure"]["raw_received_base64"]),b"SAMPLE_RECEIVED_PREFIX")
        self.assertEqual(base64.b64decode(receipt["terminal_proc_read_failure"]["raw_received_base64"]),b"TERMINAL_RECEIVED_PREFIX")
        self.assertTrue(receipt["descriptors_closed"])
        self.assertLess(max(result["final_scope"]["logical_bytes"],result["final_scope"]["allocated_bytes"]),f.contract["limits"]["artifact_bytes"])

    def test_artifact_write_guard_rejects_before_open(self):
        f=Fixture(self)
        directory=os.open(f.output,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(gate.Refusal):
                gate._write_new(str(f.output/"child.stdout.raw"),b"x"*65536,directory,
                    artifact_limit=65536,spent_basename="spent.json")
            self.assertEqual(list(f.output.iterdir()),[])
        finally:os.close(directory)

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

    def test_closed_predecessor_activation_path_refuses_before_spend(self):
        f=Fixture(self)
        f.proof["activation_changed_path"]="config/radio_runtime_metadata_capture_20261004a.activate.json"
        f.proof_raw=gate.canonical(f.proof)
        with self.assertRaises(gate.Refusal): f.run()
        self.assertEqual(list(f.output.iterdir()),[])

    def test_new_fixed_activation_path_is_exact(self):
        f=Fixture(self)
        proof=gate.verify_publication(f.contract,f.contract_sha,f.proof_raw,
            gate.digest(f.proof_raw),f.marker_raw,gate.digest(f.marker_raw))
        self.assertEqual(proof["activation_changed_path"],
            "config/radio_runtime_metadata_capture_20261004b.activate.json")

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

    def test_wrong_running_parent_executable_refuses_before_spend(self):
        f=Fixture(self)
        original=gate.sys.executable
        try:
            gate.sys.executable="/SYNTHETIC-not-the-pinned-interpreter"
            with self.assertRaises(gate.Refusal):f.run()
        finally:
            gate.sys.executable=original
        self.assertEqual(list(f.output.iterdir()),[])

    def test_child_identity_mismatch_refuses_before_spend(self):
        f=Fixture(self)
        f.child_contract.write_bytes(gate.canonical({"capture_identity":"c"*64,"limits":{"read_bytes":65536}}))
        f.contract["collector_contract_sha256"]=pin(f.child_contract)["sha256"]
        f.contract["source_pins"]=[pin(f.child_contract) if p["path"]==str(f.child_contract) else p for p in f.contract["source_pins"]]
        f.build()
        with self.assertRaises(gate.Refusal):f.run()
        self.assertFalse((f.output/"spent.json").exists())

    def test_observed_descendant_closes_whole_child_group(self):
        f=Fixture(self,"import os,time\ntime.sleep(.08)\nif os.fork()==0:time.sleep(10)\nelse:time.sleep(10)\n")
        result=f.run()
        self.assertEqual(result["report"]["failure"],"DESCENDANT_OR_SAMPLED_RSS")
        self.assertTrue(result["report"]["child_reaped"])
        observations=json.loads((f.output/"procfs-samples.json").read_bytes())
        self.assertTrue(any(len(p.get("observed_process_group_members",[]))>1 for p in observations))

    def test_proc_read_cap_is_not_suppressed(self):
        reads=gate.Reads(1)
        # os.getpid() is local-namespace identity; this proc mount may expose
        # a different namespace. Use the kernel's own proc-visible self name.
        visible_self=os.readlink("/proc/self")
        self.assertTrue(visible_self.isdecimal())
        with self.assertRaises(gate.Refusal):reads.proc("/proc/"+visible_self+"/status",16384)
        self.assertLessEqual(reads.bytes,1)

    def test_successful_proc_samples_have_kernel_bindings_and_closed_descriptors(self):
        f=Fixture(self); result=f.run(); report=result["report"]
        self.assertEqual(report["status"],"OBSERVED_METADATA_ONLY",report["failure"])
        self.assertGreater(report["authenticated_procfs_samples"],0)
        self.assertTrue(report["process_attribution"]["descriptors_closed"])
        self.assertTrue(report["process_attribution"]["pidfd_terminal_observed"])
        self.assertFalse(report["aggregate_descendant_absence_certified"])
        observations=json.loads((f.output/"procfs-samples.json").read_bytes())
        for item in observations:
            self.assertTrue(item["attribution_authenticated"])
            fields=gate._fdinfo_identity(base64.b64decode(item["pidfd_fdinfo_before_base64"]))
            self.assertEqual(item["procfs_pid"],fields["pid"])
            self.assertEqual(item["child_namespace_pid"],fields["nspid"][-1])
            self.assertEqual(item["identity"]["session"],fields["pid"])
            self.assertNotEqual(item["identity"]["starttime"],139)

    def test_unavailable_visible_membership_cannot_be_positive(self):
        f=Fixture(self)
        failed={"observed_process_group_members":[],"visible_process_stat_records":[],
                "unavailable_process_records":[{"procfs_pid":999,"error":"PermissionError","errno":13}],
                "membership_scan_complete":False,"aggregate_descendant_absence_certified":False}
        with patch.object(gate,"_group_observations",return_value=failed): result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertTrue(result["report"]["child_reaped"])
        self.assertTrue(result["report"]["spent_forever"])

    def test_lost_identity_record_closes_and_reaps_without_positive_rss(self):
        f=Fixture(self)
        with patch.object(gate,"_proc_observation",side_effect=PermissionError("SYNTHETIC unreadable child status")):
            result=f.run()
        self.assertEqual(result["report"]["status"],"CLOSED_FAILED")
        self.assertEqual(result["report"]["authenticated_procfs_samples"],0)
        self.assertTrue(result["report"]["child_reaped"])
        self.assertTrue(result["report"]["process_attribution"]["descriptors_closed"])

    def test_executable_authority_uses_verified_before_object(self):
        f=Fixture(self)
        expected=gate._object_identity(os.stat(f.contract["python_executable"]))
        original_init=gate.KernelChild.__init__
        accepted=[]
        def observe_argument(instance,pid,verified_executable,reads,deadline):
            accepted.append(dict(verified_executable))
            return original_init(instance,pid,verified_executable,reads,deadline)
        with patch.object(gate.KernelChild,"__init__",observe_argument):result=f.run()
        self.assertEqual(result["report"]["status"],"OBSERVED_METADATA_ONLY",result["report"]["failure"])
        self.assertEqual(accepted,[expected])
        self.assertEqual(result["report"]["process_attribution"]["expected_executable_from_verified_before_read"],expected)


def identity_fixture(cross_namespace=True):
    parent_pid,child_pid=500,501
    parent_vector=[500,5] if cross_namespace else [500]
    child_vector=[501,6] if cross_namespace else [501]
    local_child=6 if cross_namespace else 501
    namespace={"device":7,"inode":42}
    executable={"device":8,"inode":99}
    parent={"pid":parent_pid,"nspid":parent_vector,"starttime":100,"namespace":namespace}
    status=("Name:\tSYNTHETIC-python\nTgid:\t501\nPid:\t501\nPPid:\t500\n"+
            "NSpid:\t"+"\t".join(map(str,child_vector))+"\n"+
            "NSpgid:\t"+"\t".join(map(str,child_vector))+"\n"+
            "NSsid:\t"+"\t".join(map(str,child_vector))+"\n"+
            "Threads:\t1\nVmRSS:\t10 kB\nVmHWM:\t12 kB\n").encode()
    fields=["S","500","501","501"]+["0"]*16
    fields[17],fields[19]="1","101"
    raw_stat=b"501 (SYNTHETIC-python) "+" ".join(fields).encode()+b"\n"
    return [status,raw_stat,{"pid":501,"nspid":child_vector},parent,local_child,namespace,executable,executable]


class IdentityTests(unittest.TestCase):
    def test_malformed_pidfd_fdinfo_retains_exact_received_bytes(self):
        binding=gate.KernelChild.__new__(gate.KernelChild)
        binding.receipt={};binding.fdinfo_dir=-1;binding.pidfd=9
        binding._active=lambda:None
        raw=b"Pid:\t501\nPid:\t777\nNSpid:\t501\t6\n"
        class SyntheticReads:
            def proc_at(self,directory,leaf,cap):return raw
        with self.assertRaises(gate.Refusal):binding._fdinfo(SyntheticReads())
        self.assertEqual(base64.b64decode(binding.receipt["last_pidfd_fdinfo_read_base64"]),raw)

    def test_identical_bytes_named_replacement_does_not_change_verified_object(self):
        with tempfile.TemporaryDirectory(prefix="SYNTHETIC-inode-replacement-") as tmp:
            path=Path(tmp)/"selected";path.write_bytes(b"same synthetic contents\n")
            objects={};gate._pin_file(pin(path),gate.Reads(100),verified_objects=objects)
            verified=objects[str(path)]
            path.rename(Path(tmp)/"held-prior");path.write_bytes(b"same synthetic contents\n")
            replacement=gate._object_identity(path.stat())
            self.assertNotEqual(verified,replacement)
            args=identity_fixture();args[6],args[7]=replacement,verified
            with self.assertRaises(gate.Refusal):gate._candidate_identity(*args)

    def test_same_namespace_exact_kernel_mapping_is_accepted(self):
        result=gate._candidate_identity(*identity_fixture(False))
        self.assertEqual(result["nspid"],[501])

    def test_cross_namespace_exact_kernel_mapping_is_accepted(self):
        result=gate._candidate_identity(*identity_fixture(True))
        self.assertEqual(result["nspid"],[501,6])

    def test_exact_three_historical_samples_reject_authentic_child_mapping(self):
        observations=json.loads((HERE.parent/"results_radio_runtime_capture_repair_preparation_20261004a"/"basis"/"procfs-samples.json").read_bytes())
        self.assertEqual(len(observations),3)
        for item in observations:
            args=identity_fixture(True)
            args[:2]=[base64.b64decode(item["status_base64"]),base64.b64decode(item["stat_base64"])]
            with self.assertRaises(gate.Refusal): gate._candidate_identity(*args)

    def test_same_numeric_tail_in_another_namespace_rejects(self):
        args=identity_fixture();args[5]={"device":7,"inode":43}
        with self.assertRaises(gate.Refusal): gate._candidate_identity(*args)

    def test_mismatched_full_namespace_vector_rejects(self):
        args=identity_fixture();args[0]=args[0].replace(b"NSpid:\t501\t6",b"NSpid:\t777\t6")
        with self.assertRaises(gate.Refusal): gate._candidate_identity(*args)

    def test_pid_reuse_starttime_cannot_be_promoted(self):
        args=identity_fixture(); prior=gate._candidate_identity(*args)
        args[1]=args[1].replace(b" 101\n",b" 102\n")
        with self.assertRaises(gate.Refusal): gate._candidate_identity(*args,previous=prior)

    def test_parent_session_group_wrapper_and_thread_mismatch_reject(self):
        edits=[(b"PPid:\t500",b"PPid:\t1"),(b"NSsid:\t501\t6",b"NSsid:\t0\t0"),
               (b"NSpgid:\t501\t6",b"NSpgid:\t777\t6"),(b"Threads:\t1",b"Threads:\t2")]
        for before,after in edits:
            args=identity_fixture();args[0]=args[0].replace(before,after)
            with self.subTest(before=before),self.assertRaises(gate.Refusal): gate._candidate_identity(*args)
        args=identity_fixture();args[6]={"device":8,"inode":100}
        with self.assertRaises(gate.Refusal):gate._candidate_identity(*args)

    def test_ambiguous_multiple_or_missing_fdinfo_identity_rejects(self):
        for raw in (b"Pid:\t501 777\nNSpid:\t501\t6\n",b"Pid:\t501\nPid:\t777\nNSpid:\t501\t6\n",
                    b"Pid:\t501\n",b"Pid:\t0\nNSpid:\t0\n",b"Pid:\t-1\nNSpid:\t-1\n"):
            with self.subTest(raw=raw),self.assertRaises(gate.Refusal):gate._fdinfo_identity(raw)

    def test_malformed_stat_or_duplicate_status_rejects(self):
        with self.assertRaises(gate.Refusal):gate._stat_identity(b"501 malformed")
        args=identity_fixture();args[0]+=b"Pid:\t777\n"
        with self.assertRaises(gate.Refusal):gate._candidate_identity(*args)

    def test_actual_tiny_child_pidfd_mapping_and_post_reap_closure(self):
        # Disjoint synthetic process only, never the collector or data reader.
        command=[str(Path(sys.executable).resolve()),"-I","-B","-S","-c","import time;time.sleep(.15)"]
        child=subprocess.Popen(command,start_new_session=True)
        reads=gate.Reads(8*1024**2); binding=None; reaped=False
        try:
            binding=gate.KernelChild(child.pid,gate._object_identity(os.stat(command[0])),reads,time.monotonic_ns()+2*10**9)
            observation=gate._proc_observation(binding,reads)
            self.assertTrue(observation["attribution_authenticated"])
            self.assertEqual(observation["identity"]["ppid"],binding.parent["pid"])
            self.assertEqual(observation["identity"]["namespace"],binding.parent["namespace"])
            waited,status,usage=os.wait4(child.pid,0);reaped=True;child.returncode=os.waitstatus_to_exitcode(status)
            binding.mark_reaped(waited,reads)
            with self.assertRaises(gate.Refusal):gate._proc_observation(binding,reads)
            fds=list(binding.fds);binding.close()
            for fd in fds:
                with self.assertRaises(OSError):os.fstat(fd)
            self.assertTrue(binding.receipt["pidfd_terminal_observed"])
            self.assertTrue(binding.receipt["descriptors_closed"])
        finally:
            if not reaped:
                child.kill();child.wait()
            if binding is not None:binding.close()

    def test_held_observation_readcap_cannot_overread_and_closes(self):
        command=[str(Path(sys.executable).resolve()),"-I","-B","-S","-c","import time;time.sleep(.15)"]
        child=subprocess.Popen(command,start_new_session=True)
        reads=gate.Reads(8*1024**2);binding=None
        try:
            binding=gate.KernelChild(child.pid,gate._object_identity(os.stat(command[0])),reads,time.monotonic_ns()+2*10**9)
            reads.limit=reads.bytes+1
            with self.assertRaises(gate.Refusal) as raised:gate._proc_observation(binding,reads)
            self.assertEqual(reads.bytes,reads.limit)
            self.assertEqual(raised.exception.proc_read_evidence["charged_bytes"],1)
            self.assertEqual(len(base64.b64decode(raised.exception.proc_read_evidence["raw_received_base64"])),1)
        finally:
            child.kill();child.wait()
            if binding is not None:binding.close()

    def test_closed_descriptor_never_rebinds_numeric_pid(self):
        binding=gate.KernelChild.__new__(gate.KernelChild)
        binding.closed=True;binding.reaped=False
        with self.assertRaises(gate.Refusal):binding._active()
        binding.closed=False;binding.reaped=True
        with self.assertRaises(gate.Refusal):binding._active()

    def test_group_raw_evidence_refuses_before_next_unbudgeted_read(self):
        class Entry:
            def __init__(self,number):self.name=str(number)
        class Inventory:
            def __enter__(self):return iter(Entry(n) for n in range(1,101))
            def __exit__(self,*args):return False
        class SyntheticReads:
            calls=0
            def proc_at(self,directory,leaf,cap):
                self.calls+=1
                fields=["S","500","501","501"]+["0"]*16
                fields[17],fields[19]="1","101"
                return str(directory).encode()+b" ("+b"x"*12000+b") "+" ".join(fields).encode()+b"\n"
        reads=SyntheticReads();retained={}
        with patch.object(gate.os,"scandir",return_value=Inventory()),patch.object(gate.os,"open",side_effect=lambda name,*args,**kwargs:int(name)),patch.object(gate.os,"close"):
            with self.assertRaises(gate.Refusal):
                gate._group_observations(-1,501,reads,time.monotonic_ns()+10**9,retained=retained)
        self.assertLess(reads.calls,10)
        self.assertLessEqual(len(gate.canonical(retained["group_snapshot"])),131072)
        self.assertFalse(retained["group_snapshot"]["membership_scan_complete"])
        self.assertTrue(retained["group_snapshot"]["remaining_process_records_unobserved"])

    def test_group_inventory_has_finite_deadline(self):
        directory=os.open('/proc',os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(gate.Refusal):
                gate._group_observations(directory,501,gate.Reads(100),0)
        finally:os.close(directory)

    def test_group_inventory_cap_does_not_scan_unbounded_entries(self):
        class Entry:
            def __init__(self,number):self.name=str(number)
        class Inventory:
            def __enter__(self):return iter(Entry(n) for n in range(1,5000))
            def __exit__(self,*args):return False
        with patch.object(gate.os,"scandir",return_value=Inventory()):
            with self.assertRaises(gate.Refusal):
                gate._group_observations(-1,501,gate.Reads(100),time.monotonic_ns()+10**9)


if __name__=="__main__":unittest.main(verbosity=2)
