"""Fresh G one-shot codec16 gate; import and --validate-only never launch.

Every claim is about the explicitly pinned manifest at complete pre/post
snapshots. This gate does not claim continuous native-loader byte custody,
complete native I/O attribution, a complete codec certificate, or science.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time
from types import ModuleType

SCHEMA = "radio-codec16-outer-gate-G-v1"
PIN_KEYS = {"path", "sha256", "bytes", "mode", "device", "inode", "mtime_ns", "ctime_ns"}
ROLE_KEYS = {"scope", "dispatch", "leaf_manifest", "leaf_script", "plan",
             "input_manifest", "selection", "python", "guard", "exec_seal",
             "phase2", "proc_custody", "leaf_supervisor"}
ARTIFACT_KEYS = {"root", "leaf_output", "output_prefix", "outer_report", "spent_marker"}
BUDGETS = dict(parent_wall_seconds=120, parent_active_seconds=110,
    parent_final_seconds=10, parent_read_bytes=2*1024**3,
    child_wall_seconds=90, child_cpu_seconds=80,
    child_address_space_bytes=512*1024**2, child_read_reserve_bytes=512*1024**2,
    artifact_bytes=192*1024**2, leaf_artifact_bytes=184*1024**2,
    outer_artifact_bytes=8*1024**2, supervisor_pin_read_bytes=32*1024**2,
    proc_metadata_read_bytes=16*1024**2, stream_each_bytes=1024**2,
    file_bytes=84*1024**2, sample_interval_seconds=0.5, cleanup_seconds=2)
CONFIG_KEYS = {"schema", "scope_id", "roles", "pinned_files", "inventory_roots",
               "runtime_prefix", "cwd", "artifacts", "environment", "budgets"}
CHUNK = 1024**2
HEX = re.compile(r"[0-9a-f]{64}")


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def path_absolute(raw, existing=True):
    if not isinstance(raw, str):
        raise ValueError("path must be a string")
    path = Path(raw)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("canonical absolute path required")
    if existing and not path.exists():
        raise ValueError("existing path required")
    return path


def pin_record(path):
    """Root helper: snapshot metadata only; root must independently read hashes."""
    path = path_absolute(str(path))
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("regular pinned file required")
    return dict(path=str(path), bytes=st.st_size, mode=st.st_mode,
                device=st.st_dev, inode=st.st_ino, mtime_ns=st.st_mtime_ns,
                ctime_ns=st.st_ctime_ns)


def metadata(st):
    return dict(bytes=st.st_size, mode=st.st_mode, device=st.st_dev,
                inode=st.st_ino, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)


class Gate:
    def __init__(self, started=None):
        self.started = time.monotonic() if started is None else started
        self.active_deadline = self.started+BUDGETS["parent_active_seconds"]
        self.final_deadline = self.started+BUDGETS["parent_wall_seconds"]
        self.read_bytes = 0
        self.config = None
        self.pins = {}
        self.retained = {}
        self.snapshots = []
        self.marker_created = False
        self.child_dispatches = 0
        self.config_sha256 = None
        self.proof_sha256 = None

    def check_time(self, final=False):
        if time.monotonic() >= (self.final_deadline if final else self.active_deadline):
            raise TimeoutError("parent final deadline" if final else "parent active deadline")

    def charge(self, count, final=False):
        self.check_time(final)
        self.read_bytes += count
        if self.read_bytes > BUDGETS["parent_read_bytes"]:
            raise ValueError("parent aggregate read byte ceiling crossed")

    def read(self, path, expected, retain=False, final=False):
        self.check_time(final)
        path = path_absolute(str(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size != expected["bytes"]:
                raise ValueError("pinned type/size differs before read")
            if expected["bytes"] > BUDGETS["parent_read_bytes"]-self.read_bytes:
                raise ValueError("parent read ceiling before read")
            if set(expected) == PIN_KEYS and metadata(before) != {k: expected[k] for k in PIN_KEYS-{ "path", "sha256"}}:
                raise ValueError("pinned file identity/mode/time differs before read")
            digest, kept, total = hashlib.sha256(), [], 0
            while True:
                block = os.read(fd, min(CHUNK, expected["bytes"]-total+1))
                if not block:
                    break
                self.charge(len(block), final)
                total += len(block)
                digest.update(block)
                if retain:
                    kept.append(block)
                if total > expected["bytes"]:
                    raise ValueError("pinned file grew during read")
            after = os.fstat(fd)
            now = path.lstat()
            if (metadata(before) != metadata(after) or metadata(after) != metadata(now)
                    or total != expected["bytes"] or digest.hexdigest() != expected["sha256"]):
                raise ValueError("full held readback or pathname identity differs")
            return b"".join(kept) if retain else None
        finally:
            os.close(fd)

    def authenticated_json(self, path, size, sha256):
        if type(size) is not int or not 0 < size <= 8*1024**2 or not isinstance(sha256, str) or not HEX.fullmatch(sha256):
            raise ValueError("bounded external JSON pin required")
        return parse(self.read(path, dict(bytes=size, sha256=sha256), retain=True))

    def load(self, config_path, config_bytes, config_sha256,
             proof_path, proof_bytes, proof_sha256):
        config = self.authenticated_json(config_path, config_bytes, config_sha256)
        proof = self.authenticated_json(proof_path, proof_bytes, proof_sha256)
        self.config_sha256, self.proof_sha256 = config_sha256, proof_sha256
        if not isinstance(config, dict) or set(config) != CONFIG_KEYS or config["schema"] != SCHEMA:
            raise ValueError("exact fresh G config schema required")
        if config["budgets"] != BUDGETS or any(type(config["budgets"][k]) is not type(v) for k,v in BUDGETS.items()):
            raise ValueError("exact explicit G allocation required")
        if not re.fullmatch(r"codec16-[a-z0-9-]{1,80}", config["scope_id"]):
            raise ValueError("fresh codec16 scope ID required")
        entries = config["pinned_files"]
        if not isinstance(entries, list) or not entries or len(entries) > 20000:
            raise ValueError("bounded complete manifest required")
        for pin in entries:
            if not isinstance(pin, dict) or set(pin) != PIN_KEYS:
                raise ValueError("exact full pin fields required")
            path_absolute(pin["path"])
            if (not isinstance(pin["sha256"], str) or not HEX.fullmatch(pin["sha256"])
                    or any(type(pin[k]) is not int or pin[k] < 0 for k in PIN_KEYS-{ "path", "sha256"})
                    or not stat.S_ISREG(pin["mode"]) or pin["path"] in self.pins):
                raise ValueError("invalid or duplicate immutable pin")
            self.pins[pin["path"]] = pin
        if entries != sorted(entries, key=lambda p:p["path"]):
            raise ValueError("manifest must be sorted by canonical path")
        roles = config["roles"]
        if not isinstance(roles, dict) or set(roles) != ROLE_KEYS or any(p not in self.pins for p in roles.values()):
            raise ValueError("all exact role paths must be independently pinned")
        if len(set(roles.values())) != len(ROLE_KEYS):
            raise ValueError("role paths must be distinct")
        for field in ("runtime_prefix", "cwd"):
            if not path_absolute(config[field]).is_dir():
                raise ValueError("existing canonical runtime/cwd directory required")
        if not Path(roles["python"]).is_relative_to(Path(config["runtime_prefix"])):
            raise ValueError("canonical regular Python must be within frozen runtime prefix")
        roots = config["inventory_roots"]
        if (not isinstance(roots, list) or roots != sorted(set(roots)) or len(roots) > 32
                or any(not path_absolute(p).is_dir() for p in roots)):
            raise ValueError("sorted canonical inventory roots required")
        if any(Path(a).is_relative_to(Path(b)) for a in roots for b in roots if a != b):
            raise ValueError("inventory roots must not overlap")
        environment = config["environment"]
        if (not isinstance(environment, dict) or not environment
                or any(not isinstance(k,str) or not isinstance(v,str) or "\x00" in k+v or "=" in k for k,v in environment.items())):
            raise ValueError("explicit string environment required")
        if (environment.get("PYTHONDONTWRITEBYTECODE") != "1" or any(environment.get(k)!="1" for k in
                ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"))):
            raise ValueError("frozen no-bytecode/single-thread environment required")
        artifacts = config["artifacts"]
        if not isinstance(artifacts,dict) or set(artifacts) != ARTIFACT_KEYS:
            raise ValueError("exact artifact paths required")
        paths = {k:path_absolute(v,existing=k=="root") for k,v in artifacts.items()}
        root = paths["root"]
        if not root.is_dir() or any(root.iterdir()):
            raise ValueError("fresh empty artifact root required")
        if (any(not paths[k].is_relative_to(root) for k in ("leaf_output", "output_prefix", "outer_report"))
                or any(paths[k].parent != root for k in ("leaf_output", "output_prefix", "outer_report"))
                or len(set(paths.values())) != len(paths)
                or paths["spent_marker"].is_relative_to(root)
                or not paths["spent_marker"].parent.is_dir()):
            raise ValueError("disjoint fresh artifact paths and external marker required")
        if any(paths[k].exists() for k in ARTIFACT_KEYS-{ "root"}):
            raise ValueError("artifact/marker already exists: one-shot refused")
        if any(root.is_relative_to(Path(p)) or paths["spent_marker"].is_relative_to(Path(p)) for p in roots):
            raise ValueError("artifacts and marker must be outside immutable inventory roots")
        manifest_sha = hashlib.sha256(canonical(entries)).hexdigest()
        required_proof = dict(schema="radio-codec16-preread-G-v1", config_sha256=config_sha256,
            scope_id=config["scope_id"], pinned_files_sha256=manifest_sha,
            all_reads_complete=True, readback=entries, read_bytes=sum(p["bytes"] for p in entries))
        if proof != required_proof or proof.get("all_reads_complete") is not True:
            raise ValueError("independently supplied complete preread proof differs")
        self.config = config
        return self

    def inventory(self, final=False):
        for raw in self.config["inventory_roots"]:
            root, observed = Path(raw), set()
            for directory, names, files in os.walk(root, followlinks=False):
                self.check_time(final)
                for name in names:
                    if not stat.S_ISDIR((Path(directory)/name).lstat().st_mode):
                        raise ValueError("symlink/special inventory directory refused")
                for name in files:
                    path = Path(directory)/name
                    if not stat.S_ISREG(path.lstat().st_mode):
                        raise ValueError("symlink/special inventory file refused")
                    observed.add(str(path))
            expected = {p for p in self.pins if Path(p).is_relative_to(root)}
            if observed != expected:
                raise ValueError("complete runtime/source inventory path set differs")

    def snapshot(self, phase, final=False):
        self.inventory(final)
        charge_before = self.read_bytes
        roles = self.config["roles"]
        keep = set(roles.values())-{roles["python"],roles["guard"],roles["exec_seal"]}
        for path,pin in self.pins.items():
            raw = self.read(path,pin,retain=phase=="PRE" and path in keep,final=final)
            if raw is not None:
                self.retained[path] = raw
        self.inventory(final)
        self.snapshots.append(dict(phase=phase, complete=True, files=len(self.pins),
            bytes_read=self.read_bytes-charge_before,
            manifest_sha256=hashlib.sha256(canonical(self.config["pinned_files"])).hexdigest()))

    def admission(self):
        roles = self.config["roles"]
        dispatch = parse(self.retained[roles["dispatch"]])
        expected = dict(schema="codec16-fresh-engineering-dispatch-v1",
            scope_id=self.config["scope_id"], plan_sha256=self.pins[roles["plan"]]["sha256"],
            input_manifest_sha256=self.pins[roles["input_manifest"]]["sha256"],
            selection_sha256=self.pins[roles["selection"]]["sha256"],
            runtime_prefix=self.config["runtime_prefix"],
            outer_supervisor_scope_sha256=self.pins[roles["scope"]]["sha256"],
            engineering_execution_authorized=True)
        if dispatch != expected or dispatch.get("engineering_execution_authorized") is not True:
            raise ValueError("separate fresh engineering dispatch/scope binding differs")
        plan = parse(self.retained[roles["plan"]])
        if (plan["scope"]["row_indices"] != list(range(16))
                or plan["scope"]["telescope_provenance"] is not False
                or plan["scope"]["kind"] != "controlled-source-shaped-codec-normalization"):
            raise ValueError("frozen source-shaped sixteen-row engineering scope required")
        self.check_time()

    def acquire_marker(self):
        self.check_time()
        marker = Path(self.config["artifacts"]["spent_marker"])
        fd = os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400)
        self.marker_created = True  # Never release/reuse after any later failure.
        try:
            payload = canonical(dict(schema="radio-codec16-spent-G-v1",scope_id=self.config["scope_id"],
                config_sha256=self.config_sha256,preread_proof_sha256=self.proof_sha256,
                pre_snapshot=self.snapshots[-1],scientific_authority=False))
            offset=0
            while offset<len(payload):
                count=os.write(fd,payload[offset:])
                if count<=0: raise OSError("marker short write")
                offset+=count
            os.fsync(fd)
        finally:
            os.close(fd)

    def load_supervisor(self):
        """Execute exact retained F source, without reopening its path."""
        roles=self.config["roles"]
        if "proc_custody" in sys.modules:
            raise ValueError("fresh proc_custody module namespace required")
        proc=ModuleType("proc_custody")
        proc.__file__=roles["proc_custody"]
        sys.modules["proc_custody"]=proc
        exec(compile(self.retained[proc.__file__],proc.__file__,"exec"),proc.__dict__)
        leaf=ModuleType("_codec16_G_pinned_leaf_supervisor")
        leaf.__file__=roles["leaf_supervisor"]
        sys.modules[leaf.__name__]=leaf
        exec(compile(self.retained[leaf.__file__],leaf.__file__,"exec"),leaf.__dict__)
        return leaf

    def limits(self):
        roles=self.config["roles"]
        limits=dict(child_wall_seconds=90,address_space_bytes=512*1024**2,
            cpu_seconds=80,per_file_bytes=84*1024**2,stdout_bytes=1024**2,
            stderr_bytes=1024**2,read_reserve_bytes=512*1024**2,
            artifact_bytes=192*1024**2,pin_read_budget_bytes=32*1024**2,
            proc_metadata_budget_bytes=16*1024**2,sample_interval_seconds=0.5,cleanup_seconds=2,
            artifact_root=self.config["artifacts"]["root"])
        for name,role in (("python","python"),("guard","guard"),("exec_seal","exec_seal"),("phase2","phase2")):
            limits[name+"_path"]=roles[role]
            limits[name+"_sha256"]=self.pins[roles[role]]["sha256"]
        return limits

    def argv(self):
        roles=self.config["roles"]
        result=[roles["python"],"-I","-B",roles["leaf_script"]]
        for option,role in (("dispatch","dispatch"),("leaf-manifest","leaf_manifest")):
            pin=self.pins[roles[role]]
            result.extend(["--"+option,pin["path"],"--"+option+"-bytes",str(pin["bytes"]),
                           "--"+option+"-sha256",pin["sha256"]])
        return result+["--output",self.config["artifacts"]["leaf_output"]]

    def generated_bytes(self, path, cap):
        """Capture generated bytes through one held ordinary file descriptor."""
        path=path_absolute(str(path))
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=cap:
                raise ValueError("bounded regular generated file required")
            parts,total=[],0
            while True:
                chunk=os.read(fd,min(CHUNK,cap-total+1))
                if not chunk: break
                self.charge(len(chunk),final=True)
                parts.append(chunk)
                total+=len(chunk)
                if total>cap: raise ValueError("generated file cap crossed")
            if metadata(before)!=metadata(os.fstat(fd)) or metadata(before)!=metadata(path.lstat()) or total!=before.st_size:
                raise ValueError("generated file changed during held read")
            return b"".join(parts)
        finally:
            os.close(fd)

    def supervisor_summary(self, leaf):
        custody=Path(self.config["artifacts"]["output_prefix"])
        custody=custody.with_name(custody.name+".custody.json")
        raw=self.generated_bytes(custody,BUDGETS["outer_artifact_bytes"])
        if parse(raw)!=leaf:
            raise ValueError("persisted original F custody differs from returned record")
        summary={key:leaf[key] for key in ("schema","status","failures","failure",
            "observation_limits","limits","guard_status","phase2_status","proc_resolution",
            "proc_observer_budget","terminal_proc","wait4","child_dispatches","child_reaped",
            "child_exit_code","guarded_leaf","pin_read_charge_bytes","proc_metadata_read_charge_bytes",
            "wait4_direct_child_ru_maxrss_bytes","output","opaque_child_read_reserve_bytes")}
        summary["raw_custody_pin"]=dict(path=str(custody),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        summary["raw_proc_live_samples_count"]=len(leaf["proc_samples"])
        summary["guard_status_parent_read_reservation_bytes"]=4096
        return summary

    def verify_outputs(self):
        output=Path(self.config["artifacts"]["leaf_output"])
        wanted={"controlled-encoder.h5","controlled-legacy.h5","codec16-receipt.json"}
        if not output.is_dir() or {p.name for p in output.iterdir()} != wanted:
            raise ValueError("exact codec16 output path set required")
        receipt_path=output/"codec16-receipt.json"
        raw=self.generated_bytes(receipt_path,2*1024**2)
        receipt=parse(raw)
        roles=self.config["roles"]
        plan=parse(self.retained[roles["plan"]])
        if (receipt.get("schema")!="codec16-controlled-partial-handoff-v1"
                or receipt.get("status")!="OBSERVED_ENGINEERING_ONLY"
                or receipt.get("scope_id")!=self.config["scope_id"]
                or receipt.get("plan_sha256")!=self.pins[roles["plan"]]["sha256"]
                or receipt.get("scope")!=plan["scope"]
                or receipt.get("dispatch_sha256")!=self.pins[roles["dispatch"]]["sha256"]
                or receipt.get("outer_supervisor_scope_sha256")!=self.pins[roles["scope"]]["sha256"]
                or receipt.get("runtime")!=plan["runtime_basis"]["versions"]
                or [p.get("row") for p in receipt.get("rows",[])]!=list(range(16))
                or any(p.get("selected_cells")!=65536 for p in receipt["rows"])
                or receipt.get("handoffs_observed")!=1
                or receipt.get("complete_codec_handoffs_required")!=12
                or any(receipt.get(k) is not False for k in ("telescope_provenance","archive_payload_verified",
                    "complete_codec_certificate_issued","scientific_readiness","scientific_allocation_charged"))):
            raise ValueError("receipt engineering scope/claim boundary differs")
        handoff=receipt.get("handoff",{})
        if (handoff.get("raw_row_sha256s")!=[p.get("native_descending_sha256") for p in receipt["rows"]]
                or handoff.get("normalized_row_sha256s")!=[p.get("normalized_sha256") for p in receipt["rows"]]
                or handoff.get("receiver_context_sha256")!=plan["scope"]["receiver_context_sha256"]
                or handoff.get("receiver_bank_sha256")!=plan["scope"]["receiver_bank_sha256"]):
            raise ValueError("receipt handoff/row metadata differs")
        files=receipt.get("hdf5_files",[])
        if {p.get("name") for p in files}!={"controlled-encoder.h5","controlled-legacy.h5"} or len(files)!=2:
            raise ValueError("exact HDF5 output receipt required")
        for info in files:
            if type(info.get("bytes")) is not int or not 0<info["bytes"]<=BUDGETS["file_bytes"] or not HEX.fullmatch(info.get("sha256","")):
                raise ValueError("HDF5 output pin/ceiling differs")
            self.read(output/info["name"],dict(bytes=info["bytes"],sha256=info["sha256"]),final=True)
        return dict(path=str(receipt_path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                    rows=16,handoffs=1,required_complete_handoffs=12)

    def artifact_snapshot(self):
        root=Path(self.config["artifacts"]["root"])
        st=root.lstat()
        logical=outer_logical=st.st_size
        allocated=outer_allocated=st.st_blocks*512
        marker=Path(self.config["artifacts"]["spent_marker"])
        marker_bytes=marker_allocated=0
        if marker.exists():
            st=marker.lstat()
            if not stat.S_ISREG(st.st_mode): raise ValueError("ordinary spent marker required")
            marker_bytes,marker_allocated=st.st_size,st.st_blocks*512
            logical+=marker_bytes
            allocated+=marker_allocated
            outer_logical+=marker_bytes
            outer_allocated+=marker_allocated
        leaf=Path(self.config["artifacts"]["leaf_output"])
        for directory,names,files in os.walk(root,followlinks=False):
            self.check_time(final=True)
            for name in names+files:
                path=Path(directory)/name
                st=path.lstat()
                if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
                    raise ValueError("nonordinary artifact refused")
                logical+=st.st_size
                allocated+=st.st_blocks*512
                if not path.is_relative_to(leaf):
                    outer_logical+=st.st_size
                    outer_allocated+=st.st_blocks*512
        leaf_max=max(logical-outer_logical,allocated-outer_allocated)
        if (max(logical,allocated)>BUDGETS["artifact_bytes"]
                or leaf_max>BUDGETS["leaf_artifact_bytes"]
                or max(outer_logical,outer_allocated)>BUDGETS["outer_artifact_bytes"]):
            raise ValueError("artifact aggregate/leaf/outer reservation crossed")
        return dict(logical_bytes=logical,allocated_bytes_snapshot=allocated,
            leaf_bytes_snapshot=leaf_max,outer_logical_bytes=outer_logical,
            outer_allocated_bytes_snapshot=outer_allocated,
            external_spent_marker_logical_bytes=marker_bytes,
            external_spent_marker_allocated_bytes_snapshot=marker_allocated)

    def honest_record(self):
        return dict(schema="radio-codec16-outer-result-G-v1",status="FAILED_CLOSED",
            scope_id=self.config["scope_id"] if self.config else None,
            config_sha256=self.config_sha256,preread_proof_sha256=self.proof_sha256,
            allocation=dict(BUDGETS),complete_manifest_snapshots=self.snapshots,
            parent_explicit_read_charge_bytes=self.read_bytes,
            opaque_child_read_reservation_bytes=BUDGETS["child_read_reserve_bytes"],
            read_charge_is_complete_parent_lifetime=False,
            parent_lifetime_initial_interpreter_loader_reads_not_accounted=True,
            historical_runtime_loader_continuous_custody=False,
            full_native_graph_qualified=False,full_native_io_custody=False,
            scientific_authority=False,scientific_readiness=False,
            complete_codec_certificate_issued=False,archive_spectral_values_read=0,
            fresh_marker_created=self.marker_created,child_dispatches=self.child_dispatches,
            control_scope="sixteen deterministic representative source-shaped rows; one partial handoff",
            controlled_codec_receipt=None,supervisor_result=None,failure=None)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("config","preread-proof"):
        parser.add_argument("--"+name,required=True)
        parser.add_argument("--"+name+"-bytes",type=int,required=True)
        parser.add_argument("--"+name+"-sha256",required=True)
    parser.add_argument("--validate-only",action="store_true")
    args=parser.parse_args(argv)
    gate=Gate()
    # The surrounding root must also supply an external 120-second deadline.
    # This backstop begins here, after the parent's own Python initialization.
    old_alarm=signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError("parent hard wall backstop")))
    signal.setitimer(signal.ITIMER_REAL,BUDGETS["parent_wall_seconds"])
    result=None
    try:
        gate.load(args.config,args.config_bytes,args.config_sha256,
                  args.preread_proof,args.preread_proof_bytes,args.preread_proof_sha256)
        gate.snapshot("PRE")
        gate.admission()
        if args.validate_only:
            result=gate.honest_record()
            result["status"]="SOURCE_AND_RUNTIME_PREREAD_ONLY_NO_DISPATCH"
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,old_alarm)
            print(json.dumps(result,sort_keys=True))
            return 0
        gate.acquire_marker()
        supervisor=gate.load_supervisor()
        leaf=supervisor.run_leaf(gate.argv(),gate.config["environment"],gate.config["cwd"],
            gate.config["artifacts"]["output_prefix"],gate.limits(),gate.active_deadline)
        gate.child_dispatches=leaf["child_dispatches"]
        result=gate.honest_record()
        result["supervisor_result"]={key:leaf[key] for key in
            ("schema","status","failure","failures","child_dispatches","child_reaped","child_exit_code","guarded_leaf")}
        stream_bytes=sum(info["received_bytes"] for info in leaf["output"].values())
        gate.charge(leaf["pin_read_charge_bytes"]+leaf["proc_metadata_read_charge_bytes"]+stream_bytes+4096,final=True)
        # Run a complete post readback even after a refused/killed leaf, while
        # the separately reserved finalization interval is still available.
        gate.snapshot("POST",final=True)
        result.update(gate.honest_record())
        result["supervisor_result"]=gate.supervisor_summary(leaf)
        if (leaf["status"]!="GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY"
                or leaf["child_dispatches"]!=1 or not leaf["child_reaped"]
                or not leaf["guarded_leaf"] or leaf["child_exit_code"]!=0):
            raise ValueError("single F guarded/reaped control leaf did not complete")
        result["controlled_codec_receipt"]=gate.verify_outputs()
        result["artifact_snapshot_before_outer_record"]=gate.artifact_snapshot()
        result["status"]="CONTROLLED_CODEC16_PARTIAL_HANDOFF_OBSERVED"
    except BaseException as exc:
        result=gate.honest_record() if result is None else result
        result["status"]="FAILED_CLOSED"
        result["failure"]=type(exc).__name__+": "+str(exc)[:1000]
    result["parent_explicit_read_charge_bytes"]=gate.read_bytes
    result["parent_elapsed_seconds"]=time.monotonic()-gate.started
    if gate.marker_created and gate.config:
        try:
            gate.check_time(final=True)
            destination=Path(gate.config["artifacts"]["outer_report"])
            payload=canonical(result)
            if len(payload)>BUDGETS["outer_artifact_bytes"]:
                raise ValueError("outer result byte cap crossed")
            snapshot=gate.artifact_snapshot()
            if (max(snapshot["logical_bytes"],snapshot["allocated_bytes_snapshot"])+len(payload)+4096>BUDGETS["artifact_bytes"]
                    or max(snapshot["outer_logical_bytes"],snapshot["outer_allocated_bytes_snapshot"])+len(payload)+4096>BUDGETS["outer_artifact_bytes"]):
                raise ValueError("outer persistence reservation crossed")
            with destination.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException as exc:
            result["status"]="FAILED_CLOSED"
            result["failure"]=(result.get("failure") or "")+";outer_persistence_"+type(exc).__name__+":"+str(exc)[:300]
    signal.setitimer(signal.ITIMER_REAL,0)
    signal.signal(signal.SIGALRM,old_alarm)
    report=Path(gate.config["artifacts"]["outer_report"]) if gate.config and gate.marker_created else None
    print(json.dumps(dict(status=result["status"],scope_id=result["scope_id"],
        child_dispatches=result["child_dispatches"],fresh_marker_created=result["fresh_marker_created"],
        failure=result["failure"],outer_report=str(report) if report else None),sort_keys=True))
    return 0 if result["status"]=="CONTROLLED_CODEC16_PARTIAL_HANDOFF_OBSERVED" else 1


if __name__=="__main__":
    raise SystemExit(main())
