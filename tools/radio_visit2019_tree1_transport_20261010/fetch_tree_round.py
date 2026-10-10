"""Once-only exact typed metadata fragments from a closed clean cache plan.

Inert on import. No HEAD or old prefix GET. A frozen list of authenticated typed fragments only.
No HDF5/NumPy/parser/value API, adaptive cache miss, retry or redirect.
Every returned byte is counted and emitted as a flushed <=1024-byte base64
piece before a local write. Only validated TREE/type1 headers or actual used-node extents may be requested.
Leaf raw-chunk pointers are never followed.
"""
from __future__ import annotations
import time
WALL_STARTED = time.monotonic()
import argparse
import base64
import datetime
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
TOOLS = "tools/radio_visit2019_tree1_transport_20261010"
RESULTS = "results/radio_visit2019_tree1_transport_20261010"
BINDING_PATH = "tools/radio_visit2019_blc66_headers_20261010/proofs/OWNER_GUARD_SOURCE_BINDING.json"
MAX_BODY, MAX_REQUESTS = 1048576, 192
WORKSPACE_CAP, OUTPUT_CAP, STDOUT_CAP = 12884901888, 33554432, 4194304
OWNER_ROOT = Path("/workspace/scratch/5bf3860dacd6")
SHARED_ROOTS = (Path("/workspace/scratch/a8d1e29996d0"), OWNER_ROOT)
OWNER_GUARDS = ('analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock', 'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', 'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_1_FLOCK.lock', 'analysis/s2017_full_band/results/REVIEW_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch01_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch02_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch03_ACTIVE_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_FAMILY_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_SCIENCE_SLOT_1_FLOCK.lock')
CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 600, 536870912
RESOURCE_LIMIT_HIT = False
STDOUT_BYTES = 0

class ResourceLimitExceeded(RuntimeError):
    pass

class PreservationFailure(RuntimeError):
    pass

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def serialized(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()

def emit(value):
    global STDOUT_BYTES
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    require(STDOUT_BYTES + len(raw) <= STDOUT_CAP, "Bounded stdout preservation cap exceeded")
    STDOUT_BYTES += len(raw)
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()

def save(path, value, expose=False):
    raw = serialized(value)
    require(len(raw) <= 2 * 1024 ** 2, "Metadata receipt serialization cap exceeded")
    if expose:
        # An actual-observation serialization, not a claim of successful disk retention.
        emit({"record_type": "SETI_TYPED_METADATA_SNAPSHOT_V1",
              "stage_id": TOOLS.split("/")[1], "intended_path": str(path.relative_to(ROOT)),
              "serialization_bytes": len(raw), "serialization_sha256": sha(raw),
              "data_base64": base64.b64encode(raw).decode("ascii")})
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return raw

def relative_path(name):
    require(isinstance(name, str) and name and not Path(name).is_absolute()
            and ".." not in Path(name).parts, "Repository-relative metadata path required")
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT), "Path escaped project root")
    return path

def pinned_json(name, expected):
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), "Exact metadata SHA256 required")
    raw = relative_path(name).read_bytes()
    require(len(raw) <= 2 * 1024 ** 2 and sha(raw) == expected, "Metadata input pin changed")
    return json.loads(raw)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Exact prefix source redirects prohibited")

def deadline(signum, frame):
    global RESOURCE_LIMIT_HIT
    RESOURCE_LIMIT_HIT = True
    raise ResourceLimitExceeded("Typed metadata transport resource cap reached")

def usage():
    return {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_since_module_start": time.monotonic() - WALL_STARTED,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}

def headers(response):
    return {key: response.headers.get(key) for key in
            ("ETag", "Content-Length", "Content-Range", "Content-Encoding", "Last-Modified", "Accept-Ranges")}

def strong_etag(value):
    return isinstance(value, str) and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', value) is not None

CACHE_LOADER_PATH = "tools/radio_visit2019_blc66_metadata_20261010/cache_admission.py"
TREE_LOADER_PATH = TOOLS+"/tree_cache_admission.py"


def canonical_sha(value):
    return sha(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode())


def parent_plan_admission(scope,loader,admitted,caches,extension):
    return extension.admit_tree_plan(scope,admitted,loader,caches)


def root_admission(args,scope,admitted,loader,result):
    root=loader.read_json({"path":scope["root_admission_path"],"bytes":relative_path(scope["root_admission_path"]).stat().st_size,"sha256":args.expected_root_admission_sha256},admitted)
    require(root["schema"]=="SETI_VISIT2019_TREE1_METADATA_ROUND_ROOT_ADMISSION_V1"
            and root["status"]=="PASS_FIXED_TREE1_METADATA_ONLY_NO_REPLAY_ROOT_ADMISSION"
            and root["stage_id"]==TOOLS.split("/")[1] and root["round_id"]==scope["round_id"]
            and root["scope_sha256"]==args.expected_scope_sha256
            and root["wrapper_sha256"]==args.expected_wrapper_sha256
            and root["source_public_freeze_commit"]==args.public_freeze_commit
            and {"path":scope["root_admission_path"],"bytes":relative_path(scope["root_admission_path"]).stat().st_size,"sha256":args.expected_root_admission_sha256}["sha256"]==args.expected_root_admission_sha256,
            "Exact live typed transport root admission required")
    peer=loader.read_json(root["source_only_peer_receipt_pin"],admitted)
    require(peer["schema"]=="SETI_VISIT2019_TREE1_METADATA_TRANSPORT_SOURCE_ONLY_REVIEW_V1"
            and peer["status"]=="PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES"
            and peer["wrapper_sha256"]==args.expected_wrapper_sha256
            and peer["launcher_sha256"]==scope["pinned_dependency_files"][TOOLS+"/launch_once.py"]["sha256"],
            "Exact transport source-only peer required")
    require(root["typed_metadata_only_authorized"] is True
            and root["source_values_admission"]=="BLOCKED_PROTECTED_REGISTRY_UNRESOLVED"
            and root["native_acquisition_admission"]==root["independent_validation_admission"]=="BLOCKED"
            and root["no_matching_external_metadata_or_data_phase"] is True
            and root["finite_request_history_in_scope_is_complete"] is True
            and root["global_owner_idle_claim"] is False
            and root["prior_source_charges_refunded"] is False
            and root["root_source_reservation_already_recorded"] is True,"Root ownership/protection/no-refund limits differ")
    body=scope["limits"]["application_BODY_cap_bytes"]
    before,after,cap=(root[k] for k in ("global_source_BODY_charged_before_stage","global_source_BODY_charged_after_reservation","global_source_BODY_cap_bytes"))
    require(all(type(x) is int and x >= 0 for x in (before,after,cap))
            and root["this_stage_BODY_reserved_bytes"]==body and after==before+body <= cap,"Exact conservative body reservation fails")
    result["root_reservation_verified"]=True;result["root_admission_sha256"]=args.expected_root_admission_sha256
    result["application_BODY_charged_upper_bound_bytes"]=body


def held_owner_guards(scope,loader,admitted,held):
    binding=loader.read_json(scope["owner_binding_pin"],admitted)
    require(binding["owner_root"]==str(OWNER_ROOT) and binding["owner_guard_relative_paths"]==list(OWNER_GUARDS),"Owner guard/source binding differs")
    for expected in binding["source_files"]:
        path=OWNER_ROOT/expected["relative_path"]
        require(path.is_file() and not path.is_symlink(),"Actual owner guard source required")
        raw=path.read_bytes();require(len(raw)==expected["bytes"] and sha(raw)==expected["sha256"],"Owner guard source changed")
    for name in OWNER_GUARDS:
        path=OWNER_ROOT/name
        require(path.is_file() and not path.is_symlink(),"Existing real owner guard required")
        h=os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),"rb")
        try:fcntl.flock(h.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:h.close();raise
        held.append(h)
        a,b=os.fstat(h.fileno()),path.stat(follow_symlinks=False)
        require((a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),"Owner guard inode changed")


def tree_bytes(root):
    total=0
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in files:total+=(Path(parent)/name).lstat().st_size
    return total


def run_request(cache,request,proposal,opener,result,output):
    request_dir=output/request["request_id"];request_dir.mkdir(exist_ok=False)
    a,n=proposal["offset"],proposal["length"];etag,size=cache["etag"],cache["file_size"]
    record={"request_id":request["request_id"],"source_id":cache["source_id"],"url":cache["url"],
            "method":"GET","attempt":1,"offset":a,"original_expected_length":n,
            "requested_interval_half_open":[a,a+n],"source_file_bytes":size,"etag":etag,
            "proposal_sha256":canonical_sha(proposal),"object_kind":proposal["object_kind"],
            "request_headers":{"Accept-Encoding":"identity","Range":f"bytes={a}-{a+n-1}","If-Match":etag},
            "BODY_reserved_upper_bound_bytes":n,"body_bytes_returned_to_application":0,
            "body_bytes_retained_on_disk":0,"state":"RESERVED_BEFORE_REQUEST","started_UTC":utc()}
    result["requests"].append(record)
    result["GET_requests_attempted"]+=1
    require(result["GET_requests_attempted"] <= MAX_REQUESTS,"GET request cap exceeded")
    save(request_dir/"GET_RECEIPT.json",record,expose=True);save(output/"FETCH_RESULT.json",result)
    fragment_path=request_dir/"FRAGMENT.bin";observed=bytearray()
    try:
        require(not RESOURCE_LIMIT_HIT,"No request after resource deadline")
        req=urllib.request.Request(cache["url"],method="GET",headers=record["request_headers"])
        try:response=opener.open(req,timeout=20)
        except urllib.error.HTTPError as error:
            record.update(status=error.code,final_url=error.geturl(),response_headers=headers(error));error.close();raise
        with response:
            record.update(status=response.status,final_url=response.geturl(),response_headers=headers(response))
            save(request_dir/"GET_RECEIPT.json",record,expose=True)
            require(response.status==206 and response.geturl()==cache["url"]
                    and response.headers.get("ETag")==etag
                    and response.headers.get("Content-Range")==f"bytes {a}-{a+n-1}/{size}"
                    and response.headers.get("Content-Length")==str(n)
                    and response.headers.get("Content-Encoding","identity").lower()=="identity",
                    "Exact206 range/ETag/size/encoding rejected beforeBODY")
            with fragment_path.open("xb") as retained:
                def returned(piece):
                    offset=len(observed);observed.extend(piece)
                    record["body_bytes_returned_to_application"]+=len(piece)
                    result["application_BODY_bytes_received"]+=len(piece)
                    require(len(observed)<=n and result["application_BODY_bytes_received"]<=result["application_BODY_charged_upper_bound_bytes"],"Excess returned BODY; stop")
                    for start in range(0,len(piece),1024):
                        part=piece[start:start+1024]
                        emit({"record_type":"SETI_TYPED_METADATA_PIECE_V1","stage_id":TOOLS.split("/")[1],
                              "round_id":result["round_id"],"request_id":request["request_id"],
                              "source_id":cache["source_id"],"fragment_offset":offset+start,"source_offset":a+offset+start,
                              "bytes":len(part),"sha256":sha(part),"data_base64":base64.b64encode(part).decode("ascii")})
                    try:
                        require(retained.write(piece)==len(piece),"Short fragment write")
                        retained.flush();os.fsync(retained.fileno());record["body_bytes_retained_on_disk"]+=len(piece)
                    except BaseException as error:raise PreservationFailure("Returned fragment retention failed; stop all HTTP") from error
                    save(request_dir/"GET_RECEIPT.json",record)
                while len(observed)<n:
                    try:piece=response.read1(min(1024,n-len(observed)))
                    except http.client.IncompleteRead as error:
                        if error.partial:returned(error.partial)
                        raise
                    if not piece:break
                    returned(piece)
        require(len(observed)==n,"Truncated typed fragment")
        raw=fragment_path.read_bytes();require(raw==bytes(observed),"Retained/returned fragment differs")
        record["retained_fragment"]={"path":str(fragment_path.relative_to(ROOT)),"bytes":len(raw),"sha256":sha(raw)}
        record["state"]="PASS_EXACT_TYPED_METADATA_FRAGMENT_RETAINED"
    except BaseException as error:
        record.update(state="FAILED_CLOSED_NO_RETRY",error_type=type(error).__name__,error=str(error))
        raise
    finally:
        record["returned_fragment_observation"]={"bytes":len(observed),"sha256":sha(observed)}
        raw=save(request_dir/"GET_RECEIPT.json",record,expose=True)
        # Standalone receipt excludes own-pin; global copy adds it after serialization.
        record["request_receipt_pin"]={"path":str((request_dir/"GET_RECEIPT.json").relative_to(ROOT)),"bytes":len(raw),"sha256":sha(raw)}
        save(output/"FETCH_RESULT.json",result)


def main():
    import types
    parser=argparse.ArgumentParser()
    parser.add_argument("--scope",required=True);parser.add_argument("--expected-scope-sha256",required=True)
    parser.add_argument("--expected-wrapper-sha256",required=True);parser.add_argument("--public-freeze-commit",required=True)
    parser.add_argument("--expected-root-admission-sha256",required=True)
    parser.add_argument("--root-go-tree1-metadata-only",action="store_true")
    args=parser.parse_args()
    require(args.root_go_tree1_metadata_only and re.fullmatch(r"[0-9a-f]{40}",args.public_freeze_commit),"Exact publicfreeze/rootGO required")
    for digest in (args.expected_scope_sha256,args.expected_wrapper_sha256,args.expected_root_admission_sha256):
        require(re.fullmatch(r"[0-9a-f]{64}",digest),"ExactSHA256required")
    scope_path=Path(args.scope).resolve();require(scope_path.parent==ROOT/TOOLS/"scopes","Exact new scope directory required")
    raw=scope_path.read_bytes();require(sha(raw)==args.expected_scope_sha256,"Scope pin changed")
    scope=json.loads(raw);require(scope["schema"]=="SETI_VISIT2019_FIXED_TREE1_METADATA_FETCH_SCOPE_V1"
            and re.fullmatch(r"round_[0-9]{2}",scope["round_id"]) and 1 <= int(scope["round_id"][-2:]) <=16
            and scope_path.name==scope["round_id"]+".json","Exact finite round scope required")
    actual_sha=sha(Path(__file__).read_bytes());require(actual_sha==args.expected_wrapper_sha256==scope["wrapper_sha256"]
            and scope["wrapper_path"]==TOOLS+"/fetch_tree_round.py","Exact transport code binding required")
    body=scope["limits"]["application_BODY_cap_bytes"]
    require(type(body) is int and 0<body<=MAX_BODY and scope["limits"]=={
            "CPU_seconds":CPU_CAP,"wall_seconds":WALL_CAP,"memory_bytes":MEMORY_CAP,
            "output_bytes":OUTPUT_CAP,"shared_workspace_bytes":WORKSPACE_CAP,
            "application_BODY_cap_bytes":body,"maximum_GET_requests":MAX_REQUESTS,
            "HEAD_requests":0,"retries":0,"redirects":0,"metadata_followup_requests":0},"Frozen finite limits differ")
    require(scope["output_directory"]==RESULTS+"/"+scope["round_id"]
            and scope["root_admission_path"]==RESULTS+"/"+scope["round_id"]+"_ROOT_ADMISSION.json"
            and scope["source_values_admission"]=="BLOCKED_PROTECTED_REGISTRY_UNRESOLVED"
            and scope["native_acquisition_admission"]==scope["independent_validation_admission"]=="BLOCKED",
            "New fixed metadata-only namespace required")
    for signum in (signal.SIGALRM,signal.SIGXCPU,signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(signum,deadline)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP-1,CPU_CAP));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    signal.alarm(max(1,int(WALL_CAP-(time.monotonic()-WALL_STARTED))))
    loader_pin=scope["pinned_dependency_files"][CACHE_LOADER_PATH]
    loader_raw=relative_path(CACHE_LOADER_PATH).read_bytes()
    require(len(loader_raw)==loader_pin["bytes"] and sha(loader_raw)==loader_pin["sha256"],"Cache-loader source pin changed")
    loader=types.ModuleType("_frozen_typed_completion_cache_admission");loader.__file__=str(ROOT/CACHE_LOADER_PATH)
    exec(compile(loader_raw,loader.__file__,"exec"),loader.__dict__)
    admitted={}
    for name,pin in scope["pinned_dependency_files"].items():
        require(name==pin["path"],"Dependencypathdiffers");loader.read_pin(pin,admitted)
    output=relative_path(scope["output_directory"]);output.mkdir(parents=True,exist_ok=False)
    directory_fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY);os.fsync(directory_fd);fcntl.flock(directory_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result={"schema":"SETI_VISIT2019_FIXED_TREE1_METADATA_FETCH_RESULT_V1","round_id":scope["round_id"],
            "status":"FIXED_TREE1_METADATA_ADMISSION_IN_PROGRESS","scope_sha256":args.expected_scope_sha256,
            "wrapper_sha256":actual_sha,"source_public_freeze_commit":args.public_freeze_commit,
            "root_admission_sha256":args.expected_root_admission_sha256,"requests":[],"GET_requests_attempted":0,
            "HEAD_requests_attempted":0,"application_BODY_bytes_received":0,"application_BODY_charged_upper_bound_bytes":0,
            "root_reservation_verified":False,"BODY_reservation_refunded":False,"spectral_values_read":False,
            "dataset_value_API_used":False,"payload_pointer_followed":False,"metadata_followup_requests":0,"retries":0,"redirects":0,
            "source_values_admission":"BLOCKED_PROTECTED_REGISTRY_UNRESOLVED","native_acquisition_admission":"BLOCKED",
            "independent_validation_admission":"BLOCKED","new_source_geometry_qualification":False,"cost_DKK":0}
    held=[];code=2
    try:
        root_admission(args,scope,admitted,loader,result)
        extension_pin=scope["pinned_dependency_files"][TREE_LOADER_PATH]
        extension_raw=loader.read_pin(extension_pin,admitted)
        extension=types.ModuleType("_frozen_tree1_cache_admission");extension.__file__=str(ROOT/TREE_LOADER_PATH)
        exec(compile(extension_raw,extension.__file__,"exec"),extension.__dict__)
        caches=loader.admit_cache_history(scope,admitted)
        caches=extension.admit_tree_cache_history(scope,admitted,loader,caches)
        requests=parent_plan_admission(scope,loader,admitted,caches,extension)
        held_owner_guards(scope,loader,admitted,held)
        require(sum(tree_bytes(p) for p in SHARED_ROOTS)+OUTPUT_CAP<=WORKSPACE_CAP,"Shared12GiBgatefailed")
        save(output/"FETCH_RESULT.json",result)
        opener=urllib.request.build_opener(NoRedirect())
        for cache,request,proposal in requests:run_request(cache,request,proposal,opener,result,output)
        require(result["application_BODY_bytes_received"]==body and len(result["requests"])==len(requests)
                and all(x["state"]=="PASS_EXACT_TYPED_METADATA_FRAGMENT_RETAINED" for x in result["requests"]),"Complete frozen request list not retained")
        for pin in list(admitted.values()):loader.read_pin(pin,admitted)
        require(sha(scope_path.read_bytes())==args.expected_scope_sha256 and sha(Path(__file__).read_bytes())==actual_sha,"Code/scope endpin changed")
        for name,h in zip(OWNER_GUARDS,held):
            a,b=os.fstat(h.fileno()),(OWNER_ROOT/name).stat(follow_symlinks=False)
            require((a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),"Guard identity changed")
        require(tree_bytes(output)<=OUTPUT_CAP and sum(tree_bytes(p) for p in SHARED_ROOTS)<=WORKSPACE_CAP,"Finaldiskgatefailed")
        result["status"]="COMPLETE_FIXED_TREE1_METADATA_FETCH_NO_VALUES_ADMISSION";code=0
    except BaseException as error:
        result.update(status="FAILED_CLOSED_FIXED_TREE1_METADATA_FETCH_NO_RETRY",error_type=type(error).__name__,error=str(error));code=2
    finally:
        for signum in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(signum,signal.SIG_IGN)
        try:
            result["measured_resources"]=usage();result["known_owner_guards_held_until_after_final_receipt"]=len(held)
            raw=save(output/"FETCH_RESULT.json",result,expose=True)
            u=usage();passed=u["process_CPU_seconds_including_imports"]<=CPU_CAP and u["wall_seconds_since_module_start"]<=WALL_CAP and u["peak_RSS_bytes"]<=MEMORY_CAP
            if not passed:
                result["status"]="FAILED_CLOSED_FINAL_RESOURCE_GATE_NO_RETRY";raw=save(output/"FETCH_RESULT.json",result,expose=True);code=2
            terminal={"status":result["status"],"FETCH_RESULT_sha256":sha(raw),"scope_sha256":args.expected_scope_sha256,
                      "wrapper_sha256":actual_sha,"source_public_freeze_commit":args.public_freeze_commit,
                      "root_admission_sha256":args.expected_root_admission_sha256,"resource_caps_satisfied":passed,"no_retry":True,
                      "application_BODY_bytes_received":result["application_BODY_bytes_received"],
                      "application_BODY_charged_upper_bound_bytes":result["application_BODY_charged_upper_bound_bytes"],
                      "measured_resources_after_result_serialization":u,"spectral_values_read":False,"dataset_value_API_used":False,"payload_pointer_followed":False}
            save(output/"EXECUTION_RECEIPT.json",terminal,expose=True)
        finally:
            for h in reversed(held):h.close()
            os.close(directory_fd);signal.alarm(0)
    return code

if __name__=="__main__":raise SystemExit(main())
