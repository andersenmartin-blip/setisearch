"""Create-only full-process meter and live stdout relay for exact typed metadata fragments.

Inert on import. No network, HDF5 or numerical API. The exact frozen child is
started once; its actual exit/status stays distinct from whole-resource PASS.
Returned metadata pieces reach the parent tool stream before the local stdout log.
"""
from __future__ import annotations
import time
WALL_STARTED = time.monotonic()
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_visit2019_typed_completion_20261010"
RESULTS = "results/radio_visit2019_typed_completion_20261010"
WORKER = ROOT / TOOLS / "fetch_typed_round.py"
CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 300, 536870912
STDOUT_CAP, STDERR_CAP = 4194304, 65536
TERMINATION_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


class ExternalTermination(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__("Outer launcher received termination signal " + str(signum))


def terminate_into_cleanup(signum, frame):
    raise ExternalTermination(signum)


def protect_final_cleanup():
    for signum in TERMINATION_SIGNALS:
        signal.signal(signum, signal.SIG_IGN)


def require(test, message):
    if not test:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pin(path):
    raw = path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),"sha256":sha(raw)}


def write_new(path,obj):
    raw = (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def signal_group(pid, signum):
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass


def relay_and_reap(child, stdout_log, stderr_log, receipt):
    """Drain bounded byte streams live and wait4 the actual PID once through close."""
    selector = selectors.DefaultSelector()
    streams = {"stdout":child.stdout,"stderr":child.stderr}
    counts = {"stdout":0,"stderr":0}
    caps = {"stdout":STDOUT_CAP,"stderr":STDERR_CAP}
    logs = {"stdout":stdout_log,"stderr":stderr_log}
    status,used,timeout,killed,termination_started = None,None,False,False,None
    for name,stream in streams.items():
        os.set_blocking(stream.fileno(),False)
        selector.register(stream,selectors.EVENT_READ,name)
    try:
        while status is None or selector.get_map():
            elapsed = time.monotonic()-WALL_STARTED
            if not timeout and elapsed > WALL_CAP:
                timeout=True
                termination_started=time.monotonic()
                signal_group(child.pid,signal.SIGTERM)
            elif timeout and not killed and time.monotonic()-termination_started > 2:
                killed=True
                signal_group(child.pid,signal.SIGKILL)
            for key,event in selector.select(0.05):
                try:
                    raw=os.read(key.fileobj.fileno(),8192)
                except BlockingIOError:
                    continue
                name=key.data
                if not raw:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                counts[name]+=len(raw)
                receipt["live_stream_bytes_observed"]=dict(counts)
                require(counts[name] <= caps[name],"Bounded child stream cap exceeded")
                if name == "stdout":
                    # Immediate parent-visible preservation precedes local log IO.
                    sys.stdout.buffer.write(raw)
                    sys.stdout.buffer.flush()
                written=logs[name].write(raw)
                require(written == len(raw),"Short child stream log write")
                logs[name].flush()
                os.fsync(logs[name].fileno())
            if status is None:
                try:
                    found,actual_status,actual_usage=os.wait4(child.pid,os.WNOHANG)
                except InterruptedError:
                    continue
                if found:
                    status,used=actual_status,actual_usage
                    child.returncode=os.waitstatus_to_exitcode(status)
                    receipt["actual_child_return_code"]=child.returncode
                    receipt["whole_child_process_CPU_seconds_including_imports_and_close"]=used.ru_utime+used.ru_stime
                    receipt["whole_child_peak_RSS_bytes"]=used.ru_maxrss*1024
        return status,used,timeout,killed,counts
    finally:
        selector.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope",required=True)
    parser.add_argument("--expected-launcher-sha256",required=True)
    parser.add_argument("--expected-wrapper-sha256",required=True)
    parser.add_argument("--expected-scope-sha256",required=True)
    parser.add_argument("--public-freeze-commit",required=True)
    parser.add_argument("--launcher-public-freeze-commit",required=True)
    parser.add_argument("--expected-root-admission-sha256",required=True)
    parser.add_argument("--root-go-typed-metadata-only",action="store_true")
    args=parser.parse_args()
    require(args.root_go_typed_metadata_only,"Explicit root finite-prefix GO required")
    for value in (args.expected_launcher_sha256,args.expected_wrapper_sha256,args.expected_scope_sha256,
                  args.expected_root_admission_sha256):
        require(re.fullmatch(r"[0-9a-f]{64}",value),"Exact SHA256 required")
    for value in (args.public_freeze_commit,args.launcher_public_freeze_commit):
        require(re.fullmatch(r"[0-9a-f]{40}",value),"Exact public commit required")
    SCOPE=Path(args.scope).resolve()
    require(SCOPE.parent==ROOT/TOOLS/"scopes", "Exact completion scope path required")
    scope_raw=SCOPE.read_bytes()
    require(sha(scope_raw)==args.expected_scope_sha256,"Exact completion scope pin required")
    scope=json.loads(scope_raw)
    require(scope["schema"]=="SETI_VISIT2019_FIXED_TYPED_METADATA_FETCH_SCOPE_V1"
            and re.fullmatch(r"round_[0-9]{2}",scope["round_id"])
            and SCOPE.name==scope["round_id"]+".json", "Exact round namespace required")
    INITIAL=ROOT/RESULTS/scope["round_id"]
    OUTPUT=ROOT/RESULTS/(scope["round_id"]+"_command_attempt")
    ADMISSION=ROOT/RESULTS/(scope["round_id"]+"_ROOT_ADMISSION.json")
    require(scope["root_admission_path"]==str(ADMISSION.relative_to(ROOT))
            and scope["output_directory"]==str(INITIAL.relative_to(ROOT)),"Exact dynamic transport paths required")
    self_pin,worker_pin,scope_pin,admission_pin=(pin(Path(__file__).resolve()),pin(WORKER),pin(SCOPE),pin(ADMISSION))
    require(self_pin["sha256"] == args.expected_launcher_sha256,"Launcher pin changed")
    require(worker_pin["sha256"] == args.expected_wrapper_sha256 and scope_pin["sha256"] == args.expected_scope_sha256,
            "Frozen worker/scope changed")
    require(admission_pin["sha256"] == args.expected_root_admission_sha256,"Root admission pin changed")
    admission_raw=ADMISSION.read_bytes()
    require(sha(admission_raw) == admission_pin["sha256"],"Admission changed before parse")
    admission=json.loads(admission_raw)
    require(admission.get("schema") == "SETI_VISIT2019_TYPED_METADATA_ROUND_ROOT_ADMISSION_V1"
            and admission.get("status") == "PASS_FIXED_TYPED_METADATA_ONLY_NO_REPLAY_ROOT_ADMISSION"
            and admission.get("scope_sha256") == args.expected_scope_sha256
            and admission.get("wrapper_sha256") == args.expected_wrapper_sha256
            and admission.get("source_public_freeze_commit") == args.public_freeze_commit
            and admission.get("typed_metadata_only_authorized") is True,"Exact active root admission required")
    peer_pin=admission["source_only_peer_receipt_pin"]
    peer_path=ROOT/peer_pin["path"]
    require(peer_path.resolve()==ROOT/TOOLS/"SOURCE_ONLY_REVIEW.json","Exact transport peer path required")
    peer_raw=peer_path.read_bytes()
    require(len(peer_raw)==peer_pin["bytes"] and sha(peer_raw)==peer_pin["sha256"],"Peer receipt pin changed")
    peer=json.loads(peer_raw)
    require(peer.get("schema")=="SETI_VISIT2019_TYPED_METADATA_TRANSPORT_SOURCE_ONLY_REVIEW_V1"
            and peer.get("status")=="PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES"
            and peer.get("launcher_sha256")==self_pin["sha256"]
            and peer.get("wrapper_sha256")==worker_pin["sha256"],"Exact launcher/code source peer binding required")
    require(not INITIAL.exists(),"Initial directory exists; no launch or retry")
    resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1))
    OUTPUT.mkdir(exist_ok=False)
    directory_fd=os.open(OUTPUT,os.O_RDONLY|os.O_DIRECTORY)
    fcntl.flock(directory_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.fsync(directory_fd)
    cmd=[sys.executable,str(WORKER),"--scope",str(SCOPE),
         "--expected-scope-sha256",args.expected_scope_sha256,"--expected-wrapper-sha256",args.expected_wrapper_sha256,
         "--public-freeze-commit",args.public_freeze_commit,"--expected-root-admission-sha256",args.expected_root_admission_sha256,"--root-go-typed-metadata-only"]
    receipt={"schema":"SETI_VISIT2019_FULL_CHILD_COMMAND_RESOURCE_RECEIPT_V1",
             "status":"CREATE_ONLY_COMMAND_ATTEMPT_IN_PROGRESS","started_UTC":utc(),"launcher":self_pin,
             "worker":worker_pin,"scope":scope_pin,"root_admission":admission_pin,
             "source_public_freeze_commit":args.public_freeze_commit,
             "launcher_public_freeze_commit":args.launcher_public_freeze_commit,
             "CPU_cap_seconds_including_launcher_and_child":CPU_CAP,"whole_launch_wall_cap_seconds":WALL_CAP,
             "per_process_peak_RSS_cap_bytes":MEMORY_CAP,"command":cmd,"child_started":False,"retry":False,
             "source_values_admission":"BLOCKED_PROTECTED_REGISTRY_UNRESOLVED",
             "actual_process_termination_only_no_invented_external_tool_session":True,
             "stdout_relay_before_local_log":True,"live_stream_bytes_observed":{"stdout":0,"stderr":0}}
    write_new(OUTPUT/"LAUNCH_INPUT_RECEIPT.json",receipt)
    child=None
    return_code=2
    try:
        for signum in TERMINATION_SIGNALS:
            signal.signal(signum,terminate_into_cleanup)
        env=os.environ.copy()
        env["PYTHONUNBUFFERED"]="1"
        with (OUTPUT/"STDOUT.txt").open("xb") as stdout_log,(OUTPUT/"STDERR.txt").open("xb") as stderr_log:
            launched=time.monotonic()
            old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,TERMINATION_SIGNALS)
            try:
                child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                                       preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_SETMASK,old_mask))
                receipt["child_started"]=True
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
            status,used,timeout,killed,counts=relay_and_reap(child,stdout_log,stderr_log,receipt)
            child_wall=time.monotonic()-launched
            actual_return_code=os.waitstatus_to_exitcode(status)
            self_usage=resource.getrusage(resource.RUSAGE_SELF)
            child_cpu=used.ru_utime+used.ru_stime
            launcher_cpu=self_usage.ru_utime+self_usage.ru_stime
            child_rss,launcher_rss=used.ru_maxrss*1024,self_usage.ru_maxrss*1024
            outer_wall=time.monotonic()-WALL_STARTED
            cap_pass=(not timeout and child_cpu+launcher_cpu <= CPU_CAP and child_wall <= WALL_CAP
                      and outer_wall <= WALL_CAP and max(child_rss,launcher_rss) <= MEMORY_CAP)
        receipt.update({"status":"PASS_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED" if cap_pass
                                  else "FAIL_FULL_PROCESS_RESOURCE_CAPS_ORIGINAL_STATUS_PRESERVED",
                        "actual_child_return_code":actual_return_code,
                        "actual_child_exit_code":os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
                        "actual_child_terminating_signal":os.WTERMSIG(status) if os.WIFSIGNALED(status) else None,
                        "child_wall_timeout":timeout,"child_group_SIGKILL_after_timeout":killed,
                        "whole_child_process_CPU_seconds_including_imports_and_close":child_cpu,
                        "launcher_process_CPU_seconds_including_imports_before_receipt":launcher_cpu,
                        "combined_process_CPU_seconds_before_receipt":child_cpu+launcher_cpu,
                        "whole_child_wall_seconds_until_reaped":child_wall,
                        "launcher_wall_seconds_since_module_start_before_receipt":outer_wall,
                        "whole_child_peak_RSS_bytes":child_rss,"launcher_peak_RSS_bytes":launcher_rss,
                        "resource_caps_satisfied":cap_pass,"live_stream_bytes_observed":counts,
                        "resource_PASS_does_not_imply_complete_metadata_fragments_or_source_values_admission":True})
        for path in (INITIAL/"EXECUTION_RECEIPT.json",INITIAL/"FETCH_RESULT.json"):
            if path.is_file():
                raw=path.read_bytes()
                require(len(raw) <= 2*1024**2,"Child metadata receipt cap exceeded")
                receipt[path.name]={"pin":{"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),"sha256":sha(raw)},
                                    "original_status":json.loads(raw).get("status")}
        for path,expected in ((Path(__file__).resolve(),self_pin),(WORKER,worker_pin),(SCOPE,scope_pin),(ADMISSION,admission_pin)):
            require(pin(path) == expected,"Pinned launch input changed during process")
        receipt["output_pins"]=[pin(OUTPUT/"STDOUT.txt"),pin(OUTPUT/"STDERR.txt")]
        return_code=0 if cap_pass else 2
    except BaseException as error:
        protect_final_cleanup()
        if isinstance(error,ExternalTermination):
            receipt["external_launcher_termination_signal"]=error.signum
        if child is not None and child.returncode is None:
            signal_group(child.pid,signal.SIGKILL)
            try:
                _,status,used=os.wait4(child.pid,0)
                child.returncode=os.waitstatus_to_exitcode(status)
                receipt["actual_child_return_code"]=child.returncode
                receipt["whole_child_process_CPU_seconds_including_imports_and_close"]=used.ru_utime+used.ru_stime
                receipt["whole_child_peak_RSS_bytes"]=used.ru_maxrss*1024
            except ChildProcessError:
                receipt["child_reaping_evidence_unavailable"]=True
        receipt.update(status="FAILED_CLOSED_OUTER_METER_NO_RETRY",error_type=type(error).__name__,
                       error=str(error),resource_caps_satisfied=False)
    finally:
        protect_final_cleanup()
        receipt["finished_UTC"]=utc()
        # Output this exact final metadata serialization before local receipt IO.
        raw=(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
        import base64
        print(json.dumps({"record_type":"SETI_TYPED_METADATA_OUTER_RECEIPT_V1",
                          "serialization_bytes":len(raw),"serialization_sha256":sha(raw),
                          "data_base64":base64.b64encode(raw).decode("ascii")}),flush=True)
        try:
            write_new(OUTPUT/"COMMAND_RESOURCES.json",receipt)
        finally:
            os.close(directory_fd)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
