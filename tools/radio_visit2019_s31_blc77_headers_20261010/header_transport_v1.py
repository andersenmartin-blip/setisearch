"""Once-only opaque S2019 session31/BLC77 initial prefix capture.

Inert on import. Six fixed HEADs and at most six exact8192-byte prefixes only.
No HDF5/NumPy/parser/value API, adaptive cache miss, retry or redirect.
Every returned byte is counted and emitted as a flushed <=1024-byte base64
piece before a local write. This transport does not qualify source geometry.
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
TOOLS = "tools/radio_visit2019_s31_blc77_headers_20261010"
RESULTS = "results/radio_visit2019_s31_blc77_headers_20261010"
CADENCE_PATH = TOOLS + "/SIX_SOURCE_IDENTITIES.json"
CADENCE_SHA = "a992552c80c081a7d865e85a125a924b91749f8af594f505e01ff4d1e272f388"
BINDING_PATH = "tools/radio_visit2019_blc66_headers_20261010/proofs/OWNER_GUARD_SOURCE_BINDING.json"
PREFIX_BYTES, BODY_CAP = 8192, 49152
WORKSPACE_CAP, OUTPUT_CAP, STDOUT_CAP = 12884901888, 33554432, 786432
OWNER_ROOT = Path("/workspace/scratch/5bf3860dacd6")
SHARED_ROOTS = (Path("/workspace/scratch/a8d1e29996d0"), OWNER_ROOT)
OWNER_GUARDS = ('analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock', 'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', 'analysis/s2017_full_band/results/ACTIVE_SCIENCE_SLOT_1_FLOCK.lock', 'analysis/s2017_full_band/results/REVIEW_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch01_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch02_ACTIVE_FLOCK.lock', 'analysis/s2017_full_band/results/batch03_ACTIVE_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_FAMILY_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', 'analysis/s2017_next_native/ACTIVE_SCIENCE_SLOT_1_FLOCK.lock')
CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 600, 536870912
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
        emit({"record_type": "SETI_INITIAL_PREFIX_METADATA_SNAPSHOT_V1",
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
    raise ResourceLimitExceeded("Initial prefix transport resource cap reached")

def usage():
    return {"process_CPU_seconds_including_imports": time.process_time(),
            "wall_seconds_since_module_start": time.monotonic() - WALL_STARTED,
            "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}

def headers(response):
    return {key: response.headers.get(key) for key in
            ("ETag", "Content-Length", "Content-Range", "Content-Encoding", "Last-Modified", "Accept-Ranges")}

def strong_etag(value):
    return isinstance(value, str) and re.fullmatch(r'"[^"\x00-\x20\x7f]+"', value) is not None

def source_request(opener, item, method, request_headers, record, result, output):
    if RESOURCE_LIMIT_HIT:
        raise ResourceLimitExceeded("No request after resource deadline")
    key = "HEAD_requests_attempted" if method == "HEAD" else "prefix_GET_requests_attempted"
    result[key] += 1
    require(result[key] <= 6 and result["HEAD_requests_attempted"] + result["prefix_GET_requests_attempted"] <= 12,
            "Request cap exceeded")
    record.update(source_id=item["source_id"], url=item["url"], method=method, attempt=1,
                  state="RESERVED_BEFORE_REQUEST", started_UTC=utc(), request_headers=request_headers,
                  BODY_reserved_upper_bound_bytes=PREFIX_BYTES if method == "GET" else 0,
                  body_bytes_returned_to_application=0)
    # Both disk attempt accounting and bounded parent-visible evidence precede HTTP.
    save(output / "HEADER_RESULT.json", result)
    emit({"record_type":"SETI_INITIAL_PREFIX_REQUEST_RESERVED_V1", "stage_id":TOOLS.split("/")[1],
          "source_id":item["source_id"], "method":method, "url":item["url"],
          "request_headers":request_headers, "BODY_reserved_upper_bound_bytes":record["BODY_reserved_upper_bound_bytes"]})
    request = urllib.request.Request(item["url"], method=method, headers=request_headers)
    try:
        return opener.open(request, timeout=20)
    except urllib.error.HTTPError as error:
        record.update(status=error.code, final_url=error.geturl(), response_headers=headers(error),
                      state="FAILED_CLOSED_NO_RETRY", error_type=type(error).__name__)
        error.close()  # Error body is not read; no retry or follow-up.
        raise


def run_source(item, opener, result, output):
    source_dir = output / item["source_id"]
    source_dir.mkdir(exist_ok=False)
    record = {"source_id":item["source_id"], "url":item["url"], "ordered_index":item["ordered_index"],
              "filename_target":item["expected_source_name"], "candidate_role":item["candidate_role"],
              "status":"NOT_ATTEMPTED", "HEAD":{}, "prefix_GET":{}, "prefix_bytes":PREFIX_BYTES,
              "metadata_parser_executed":False, "spectral_values_read":False, "dataset_value_API_used":False,
              "native_acquisition_admission":"BLOCKED", "independent_validation_admission":"BLOCKED",
              "protected_source_registry_status":"UNRESOLVED", "geometry":None, "midpoint":None,
              "prefix_BODY_bytes_received":0, "prefix_BODY_bytes_retained_on_disk":0,
              "prefix_stdout_piece_count":0}
    result["sources"].append(record)
    save(source_dir / "HEADER_RECEIPT.json", record)
    prefix_path = source_dir / "PREFIX.bin"
    observed = bytearray()
    started = time.monotonic()
    try:
        head = record["HEAD"]
        with source_request(opener,item,"HEAD",{"Accept-Encoding":"identity"},head,result,output) as response:
            head.update(status=response.status, final_url=response.geturl(), response_headers=headers(response))
            require(response.status == 200 and response.geturl() == item["url"], "HEAD exact URL/status mismatch")
            size_text, etag = response.headers.get("Content-Length"), response.headers.get("ETag")
            require(isinstance(size_text,str) and re.fullmatch(r"[1-9][0-9]*",size_text), "Positive exact HEAD file length required")
            file_size = int(size_text)
            require(file_size >= PREFIX_BYTES and strong_etag(etag), "HEAD size/strong ETag rejected")
            require(response.headers.get("Content-Encoding","identity").lower() == "identity", "Encoded HEAD refused")
            require(item["catalog_file_bytes"] is None or file_size == item["catalog_file_bytes"], "Catalog/HEAD length mismatch")
            head.update(state="PASS_HEAD_METADATA_PIN", source_file_bytes=file_size, etag=etag)
        save(source_dir / "HEAD_RECEIPT.json",head,expose=True)
        save(output / "HEADER_RESULT.json",result)
        get = record["prefix_GET"]
        request_headers = {"Accept-Encoding":"identity", "Range":"bytes=0-8191", "If-Match":etag}
        with source_request(opener,item,"GET",request_headers,get,result,output) as response:
            get.update(status=response.status,final_url=response.geturl(),response_headers=headers(response),
                       source_file_bytes=file_size,etag=etag)
            save(source_dir / "PREFIX_RECEIPT.json",get,expose=True)
            require(response.status == 206 and response.geturl() == item["url"]
                    and response.headers.get("ETag") == etag
                    and response.headers.get("Content-Range") == f"bytes 0-8191/{file_size}"
                    and response.headers.get("Content-Length") == str(PREFIX_BYTES)
                    and response.headers.get("Content-Encoding","identity").lower() == "identity",
                    "Exact prefix range/ETag/size/encoding rejected before BODY")
            with prefix_path.open("xb") as retained:
                def accept_returned(piece):
                    # Actual returned accounting and memory retention precede ANY disk write.
                    offset = len(observed)
                    observed.extend(piece)
                    record["prefix_BODY_bytes_received"] += len(piece)
                    result["application_BODY_bytes_received"] += len(piece)
                    get["body_bytes_returned_to_application"] += len(piece)
                    require(len(observed) <= PREFIX_BYTES and result["application_BODY_bytes_received"] <= BODY_CAP,
                            "Unexpected excess returned BODY; no continuation")
                    for part_start in range(0,len(piece),1024):
                        part = piece[part_start:part_start+1024]
                        emit({"record_type":"SETI_INITIAL_PREFIX_PIECE_V1", "stage_id":TOOLS.split("/")[1],
                              "source_id":item["source_id"], "offset":offset+part_start, "bytes":len(part),
                              "sha256":sha(part), "data_base64":base64.b64encode(part).decode("ascii")})
                        record["prefix_stdout_piece_count"] += 1
                    try:
                        n = retained.write(piece)
                        require(n == len(piece), "Short retained-prefix write")
                        retained.flush()
                        os.fsync(retained.fileno())
                        record["prefix_BODY_bytes_retained_on_disk"] += len(piece)
                    except BaseException as error:
                        record["retention_failure"] = {"error_type":type(error).__name__, "error":str(error),
                                                       "returned_bytes_counted_before_write":True}
                        raise PreservationFailure("Returned prefix disk retention failed; stop all new HTTP") from error
                    save(source_dir / "PREFIX_RECEIPT.json",get)
                    save(output / "HEADER_RESULT.json",result)
                while len(observed) < PREFIX_BYTES:
                    remaining = PREFIX_BYTES - len(observed)
                    try:
                        piece = response.read1(min(1024,remaining))
                    except http.client.IncompleteRead as error:
                        if error.partial:
                            accept_returned(error.partial)
                        raise
                    if not piece:
                        break
                    accept_returned(piece)
        require(len(observed) == PREFIX_BYTES, "Truncated exact prefix")
        prefix = prefix_path.read_bytes()
        require(prefix == bytes(observed), "Retained/returned opaque prefix differs")
        record["retained_prefix"] = {"path":str(prefix_path.relative_to(ROOT)), "bytes":len(prefix), "sha256":sha(prefix)}
        get["state"] = "PASS_EXACT_8192_PREFIX_RETAINED"
        record["status"] = "PREFIX_COMPLETE_METADATA_PARSE_DEFERRED_NO_VALUES_ADMISSION"
    except (ResourceLimitExceeded, MemoryError, PreservationFailure) as error:
        record.update(status="RESOURCE_OR_PRESERVATION_FAILURE_NO_RETRY",error_type=type(error).__name__,error=str(error))
        raise
    except Exception as error:
        if RESOURCE_LIMIT_HIT:
            raise ResourceLimitExceeded("Resource exception wrapped during prefix attempt") from error
        record.update(status="PREFIX_TRANSPORT_INCOMPLETE_NO_RETRY",error_type=type(error).__name__,error=str(error))
        if isinstance(error,OSError) and not isinstance(error,urllib.error.URLError):
            raise PreservationFailure("Local prefix/receipt preservation failed; no further HTTP") from error
    finally:
        record["returned_prefix_observation"] = {"bytes":len(observed),"sha256":sha(observed),
                                               "stdout_piece_count":record["prefix_stdout_piece_count"]}
        # Preserve all returned-byte and header evidence in the parent stream before final disk operations.
        emit({"record_type":"SETI_INITIAL_PREFIX_OBSERVED_BYTES_V1", "stage_id":TOOLS.split("/")[1],
              "source_id":item["source_id"], **record["returned_prefix_observation"]})
        if prefix_path.exists():
            raw = prefix_path.read_bytes()
            record["retained_prefix"] = {"path":str(prefix_path.relative_to(ROOT)),"bytes":len(raw),"sha256":sha(raw)}
        for key,filename in (("HEAD","HEAD_RECEIPT.json"),("prefix_GET","PREFIX_RECEIPT.json")):
            if record[key] and record[key].get("state") == "RESERVED_BEFORE_REQUEST":
                record[key]["state"] = "FAILED_CLOSED_NO_RETRY"
            if record[key]:
                save(source_dir/filename,record[key],expose=True)
        record["wall_seconds"] = time.monotonic()-started
        save(source_dir/"HEADER_RECEIPT.json",record,expose=True)
        save(output/"HEADER_RESULT.json",result)

def base_admission(args):
    require(args.root_go_header_metadata_only, "Explicit root metadata-only GO required")
    require(re.fullmatch(r"[0-9a-f]{40}", args.public_freeze_commit), "Public source freeze required")
    require(re.fullmatch(r"[0-9a-f]{64}", args.expected_root_admission_sha256), "Late root admission SHA required")
    actual_wrapper = sha(Path(__file__).read_bytes())
    require(actual_wrapper == args.expected_wrapper_sha256, "Wrapper pin differs")
    scope_path = Path(args.scope).resolve()
    require(scope_path == relative_path(TOOLS + "/initial_scope.json"), "Exact new scope path required")
    scope_raw = scope_path.read_bytes()
    require(sha(scope_raw) == args.expected_scope_sha256, "Scope SHA changed")
    scope = json.loads(scope_raw)
    require(scope["schema"] == "SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_SCOPE_V1"
            and scope["prefix_bytes"] == PREFIX_BYTES
            and scope["wrapper_sha256"] == actual_wrapper, "Scope/code binding differs")
    require(scope["wrapper_path"] == TOOLS + "/header_transport_v1.py"
            and Path(__file__).resolve() == relative_path(scope["wrapper_path"]), "Wrapper namespace differs")
    require(scope["output_directory"] == RESULTS + "/initial", "New output namespace differs")
    expected_limits = {"HEAD_requests": 6, "prefix_GET_requests": 6, "total_HTTP_requests": 12,
                       "prefix_bytes_per_source": PREFIX_BYTES, "application_BODY_cap_bytes": BODY_CAP,
                       "CPU_seconds": CPU_CAP, "wall_seconds": WALL_CAP, "memory_bytes": MEMORY_CAP,
                       "output_bytes": OUTPUT_CAP, "shared_workspace_bytes": WORKSPACE_CAP,
                       "retries": 0, "redirects": 0, "metadata_followup_requests": 0}
    require(scope["limits"] == expected_limits, "Finite stage limits differ")
    require(scope["source_values_admission"] == "BLOCKED_PROTECTED_REGISTRY_UNRESOLVED"
            and scope["native_acquisition_admission"] == "BLOCKED"
            and scope["independent_validation_admission"] == "BLOCKED"
            and scope["A_B"] == "FAIL_CLOSED_UNCHANGED"
            and scope["geometry"] is None and scope["midpoint"] is None, "Metadata-only/unset geometry required")
    require(scope["candidate_metadata_path"] == CADENCE_PATH
            and scope["candidate_metadata_sha256"] == CADENCE_SHA, "Fixed six identities required")
    cadence = pinned_json(CADENCE_PATH, CADENCE_SHA)
    require(cadence["schema"] == "SETI_VISIT2019_SESSION31_BLC77_EXACT_SIX_SOURCE_IDENTITIES_V1"
            and len(scope["sources"]) == len(cadence["files"]) == 6, "Exact fixed six sources required")
    require(scope["sources"] == cadence["files"], "Fixed source descriptors differ")
    require(len({x["url"] for x in scope["sources"]}) == 6
            and len({x["source_id"] for x in scope["sources"]}) == 6, "Six unique identities required")
    for i, item in enumerate(scope["sources"]):
        role = "ON" if i % 2 == 0 else "CONTROL"
        require(item["source_id"] == f"S2019_31_BLC77_{role}{i//2+1}_{77+i:04d}"
                and item["ordered_index"] == i+1 and item["candidate_role"] == role + "_CANDIDATE"
                and item["filename_MJD_integer"] == 58755 and item["catalog_file_bytes"] is None,
                "Fixed cadence identity differs")
        url = urllib.parse.urlsplit(item["url"])
        require(url.scheme == "https" and url.netloc == "bldata.berkeley.edu"
                and not url.query and not url.fragment
                and url.path == "/pipeline/AGBT19B_999_31/blc77/" + item["filename"]
                and item["filename"].endswith(".gpuspec.0000.h5"), "Exact primary archive identity required")
    require(scope["owner_root"] == str(OWNER_ROOT)
            and scope["owner_guard_relative_paths"] == list(OWNER_GUARDS)
            and scope["shared_workspace_roots"] == [str(p) for p in SHARED_ROOTS], "Actual owner/shared guard roots required")
    require(scope["root_admission_path"] == RESULTS + "/ROOT_ADMISSION.json"
            and Path(args.root_admission).resolve() == relative_path(scope["root_admission_path"]),
            "Exact late root admission path required")
    for name, expected in scope["pinned_dependency_files"].items():
        raw = relative_path(name).read_bytes()
        require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"], "Frozen metadata dependency differs")
    return scope, actual_wrapper


def tree_bytes(root):
    total = 0
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in files:
            path = Path(parent) / name
            try:
                total += path.lstat().st_size
            except FileNotFoundError as error:
                raise ValueError("Shared workspace changed during byte gate") from error
    return total



def admitted_root_and_guards(args, scope, result, output, held):
    admission = pinned_json(scope["root_admission_path"], args.expected_root_admission_sha256)
    require(admission["schema"] == "SETI_VISIT2019_S31_BLC77_ROOT_INITIAL_PREFIX_ADMISSION_V1"
            and admission["status"] == "PASS_FINITE_PREFIX_ONLY_NO_REPLAY_ROOT_ADMISSION"
            and admission["stage_id"] == TOOLS.split("/")[1]
            and admission["scope_sha256"] == args.expected_scope_sha256
            and admission["wrapper_sha256"] == args.expected_wrapper_sha256
            and admission["source_public_freeze_commit"] == args.public_freeze_commit,
            "Root exact source freeze admission differs")
    require(admission["source_only_peer_receipt_path"] ==
            RESULTS + "/proofs/INITIAL_PREFIX_SOURCE_ONLY_REVIEW.json", "Exact initial source peer path required")
    peer = pinned_json(admission["source_only_peer_receipt_path"],
                      admission["source_only_peer_receipt_sha256"])
    require(peer["schema"] == "SETI_VISIT2019_S31_BLC77_INITIAL_PREFIX_SOURCE_ONLY_REVIEW_V1"
            and peer["status"] == "PASS_SOURCE_ONLY_NO_HTTP_OR_VALUES"
            and peer["wrapper_sha256"] == args.expected_wrapper_sha256
            and peer["scope_sha256"] == args.expected_scope_sha256,
            "Exact source-only peer PASS required")
    require(admission["historical_request_eligibility_sha256"] ==
            scope["pinned_dependency_files"][TOOLS + "/HISTORICAL_REQUEST_ELIGIBILITY.json"]["sha256"],
            "Exact finite historical request proof binding required")
    fresh_pin = admission["fresh_ownership_and_request_check_pin"]
    require(set(fresh_pin) == {"path","bytes","sha256"}, "Exact fresh root-check pin required")
    fresh = pinned_json(fresh_pin["path"],fresh_pin["sha256"])
    require(relative_path(fresh_pin["path"]).stat().st_size == fresh_pin["bytes"]
            and fresh["stage_id"] == TOOLS.split("/")[1]
            and fresh["exact_source_URLs"] == [item["url"] for item in scope["sources"]]
            and fresh["known_exact_source_URL_hits"] == []
            and fresh["finite_scope_only_not_global_registry_certification"] is True,
            "Fresh finite root ownership/request proof does not bind exact six untouched URLs")
    require(admission["initial_prefix_only_authorized"] is True
            and admission["source_values_admission"] == "BLOCKED_PROTECTED_REGISTRY_UNRESOLVED"
            and admission["native_acquisition_admission"] == "BLOCKED"
            and admission["independent_validation_admission"] == "BLOCKED"
            and admission["protected_source_registry_complete"] is False
            and admission["known_exact_protected_URL_conflicts"] == []
            and admission["fresh_registry_check_no_matching_prior_source_requests"] is True
            and admission["fresh_owner_check_no_matching_external_data_phase"] is True
            and admission["global_owner_idle_claim"] is False, "Root metadata/protection/ownership limits differ")
    require(admission["this_stage_BODY_reserved_bytes"] == BODY_CAP
            and admission["prior_source_charges_refunded"] is False
            and admission["root_source_reservation_already_recorded"] is True,
            "Root conservative no-refund BODY reservation required")
    before, after, cap = (admission[k] for k in ("global_source_BODY_charged_before_stage",
            "global_source_BODY_charged_after_reservation", "global_source_BODY_cap_bytes"))
    require(all(type(x) is int and x >= 0 for x in (before, after, cap))
            and cap > 0 and after == before+BODY_CAP and after <= cap,
            "Root actual authorized global source BODY cap exceeded")
    require(admission["shared_workspace_roots"] == scope["shared_workspace_roots"]
            and admission["shared_workspace_bytes_cap"] == WORKSPACE_CAP
            and admission["workspace_preflight_PASS"] is True
            and type(admission["workspace_bytes_before_stage"]) is int
            and admission["workspace_bytes_before_stage"] + OUTPUT_CAP <= WORKSPACE_CAP,
            "Root12GiB shared workspace admission required")
    result["application_BODY_charged_upper_bound_bytes"] = BODY_CAP
    result["root_reservation_verified"] = True
    result["root_admission_sha256"] = args.expected_root_admission_sha256
    save(output / "HEADER_RESULT.json", result)
    binding = pinned_json(BINDING_PATH,scope["pinned_dependency_files"][BINDING_PATH]["sha256"])
    require(binding["owner_root"] == str(OWNER_ROOT)
            and binding["owner_guard_relative_paths"] == list(OWNER_GUARDS), "Owner guard binding differs")
    for expected in binding["source_files"]:
        source = OWNER_ROOT / expected["relative_path"]
        require(source.is_file() and not source.is_symlink(), "Actual pinned owner guard source required")
        raw = source.read_bytes()
        require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"],
                "Owner guard source changed; do not infer quiescence from an obsolete guard")
    # Existing owner guards only: no O_CREAT and no writes or invented path.
    for name in OWNER_GUARDS:
        path = OWNER_ROOT / name
        require(path.is_file() and not path.is_symlink(), "Actual existing owner guard required")
        require(path.resolve().is_relative_to(OWNER_ROOT), "Owner guard path escaped owner root")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        handle = os.fdopen(fd, "rb")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            handle.close()
            raise
        held.append(handle)
        a, b = os.fstat(handle.fileno()), path.stat(follow_symlinks=False)
        require((a.st_dev, a.st_ino) == (b.st_dev, b.st_ino), "Owner guard inode path changed")
    result["known_owner_kernel_guards_held"] = len(held)
    result["owner_guard_identity"] = [{"relative_path":n,
            "dev":os.fstat(h.fileno()).st_dev,"inode":os.fstat(h.fileno()).st_ino}
            for n,h in zip(OWNER_GUARDS,held)]
    result["fresh_registry_and_owner_admission"] = {
        "status": "ROOT_PINNED_FRESH_FINITE_NO_REPLAY_OWNERSHIP_ADMISSION",
        "root_admission_sha256": args.expected_root_admission_sha256,
        "runtime_additional_broad_metadata_scans": 0,
        "global_untouched_or_owner_idle_certification": False}
    actual = sum(tree_bytes(root) for root in SHARED_ROOTS)
    require(actual + OUTPUT_CAP <= WORKSPACE_CAP, "Actual12GiB shared workspace gate failed")
    result["actual_shared_workspace_bytes_before_prefix_transport"] = actual
    save(output / "HEADER_RESULT.json", result)
    return admission

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope",required=True)
    parser.add_argument("--expected-scope-sha256",required=True)
    parser.add_argument("--expected-wrapper-sha256",required=True)
    parser.add_argument("--public-freeze-commit",required=True)
    parser.add_argument("--root-admission",required=True)
    parser.add_argument("--expected-root-admission-sha256",required=True)
    parser.add_argument("--root-go-header-metadata-only",action="store_true")
    args = parser.parse_args()
    scope,wrapper_sha = base_admission(args)
    output = relative_path(scope["output_directory"])
    output.mkdir(parents=True,exist_ok=False)
    directory_fd = os.open(output,os.O_RDONLY|os.O_DIRECTORY)
    os.fsync(directory_fd)
    fcntl.flock(directory_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result = {"schema":"SETI_VISIT2019_INITIAL_PREFIX_TRANSPORT_RESULT_V1",
              "status":"INITIAL_PREFIX_ADMISSION_IN_PROGRESS","started_UTC":utc(),
              "scope_sha256":args.expected_scope_sha256,"wrapper_sha256":wrapper_sha,
              "source_public_freeze_commit":args.public_freeze_commit,"candidate_metadata_sha256":CADENCE_SHA,
              "prefix_bytes":PREFIX_BYTES,"HEAD_requests_attempted":0,"prefix_GET_requests_attempted":0,
              "application_BODY_bytes_received":0,"application_BODY_charged_upper_bound_bytes":0,
              "root_reservation_verified":False,"BODY_reservation_refunded":False,"sources":[],
              "metadata_followup_requests":0,"retries":0,"redirects":0,"metadata_parser_executed":False,
              "spectral_values_read":False,"dataset_value_API_used":False,"nativeband_requests":0,
              "geometry":None,"midpoint":None,"source_values_admission":"BLOCKED_PROTECTED_REGISTRY_UNRESOLVED",
              "native_acquisition_admission":"BLOCKED","independent_validation_admission":"BLOCKED",
              "qualified_sky_pilot":False,"A_B":"FAIL_CLOSED_UNCHANGED","cost_DKK":0,
              "all_six_exact_prefix_pairs_complete":False}
    save(output/"HEADER_RESULT.json",result)
    for signum in (signal.SIGALRM,signal.SIGXCPU,signal.SIGTERM,signal.SIGHUP,signal.SIGINT):
        signal.signal(signum,deadline)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP-1,CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    signal.alarm(max(1,int(WALL_CAP-(time.monotonic()-WALL_STARTED))))
    held,code = [],2
    try:
        admitted_root_and_guards(args,scope,result,output,held)
        opener = urllib.request.build_opener(NoRedirect())
        result["status"] = "INITIAL_PREFIX_TRANSPORT_ATTEMPT_IN_PROGRESS"
        for item in scope["sources"]:
            run_source(item,opener,result,output)
        complete = len(result["sources"]) == 6 and all(
            item["status"] == "PREFIX_COMPLETE_METADATA_PARSE_DEFERRED_NO_VALUES_ADMISSION"
            and item["HEAD"].get("state") == "PASS_HEAD_METADATA_PIN"
            and item["prefix_GET"].get("state") == "PASS_EXACT_8192_PREFIX_RETAINED"
            and item["retained_prefix"]["bytes"] == PREFIX_BYTES for item in result["sources"])
        result["all_six_exact_prefix_pairs_complete"] = complete
        result["status"] = ("COMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_VALUES_ADMISSION" if complete
                            else "INCOMPLETE_INITIAL_PREFIX_TRANSPORT_ONLY_NO_RETRY")
        require(sha(Path(__file__).read_bytes()) == wrapper_sha
                and sha(Path(args.scope).read_bytes()) == args.expected_scope_sha256,"Code/scope changed during run")
        pinned_json(CADENCE_PATH,CADENCE_SHA)
        pinned_json(scope["root_admission_path"],args.expected_root_admission_sha256)
        for name,expected in scope["pinned_dependency_files"].items():
            raw=relative_path(name).read_bytes()
            require(len(raw)==expected["bytes"] and sha(raw)==expected["sha256"],"Frozen dependency changed during run")
        require(tree_bytes(output) <= OUTPUT_CAP,"Metadata output cap exceeded")
        require(sum(tree_bytes(root) for root in SHARED_ROOTS) <= WORKSPACE_CAP,"Final shared workspace cap exceeded")
        for name,handle in zip(OWNER_GUARDS,held):
            a,b=os.fstat(handle.fileno()),(OWNER_ROOT/name).stat(follow_symlinks=False)
            require((a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),"Owner guard changed during prefix run")
        measured=usage()
        require(measured["process_CPU_seconds_including_imports"] <= CPU_CAP
                and measured["wall_seconds_since_module_start"] <= WALL_CAP
                and measured["peak_RSS_bytes"] <= MEMORY_CAP,"Measured resource cap exceeded")
        code=0 if complete else 2
    except BaseException as error:
        result.update(status="FAILED_CLOSED_INITIAL_PREFIX_TRANSPORT_ONLY_NO_RETRY",
                      error_type=type(error).__name__,error=str(error))
        code=2
    finally:
        # Stop repeated external termination signals during finite evidence/guard cleanup.
        for signum in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):
            signal.signal(signum,signal.SIG_IGN)
        try:
            result["measured_resources"]=usage()
            result["finished_UTC"]=utc()
            result["known_owner_guards_held_until_after_final_receipt"]=len(held)
            result_raw=save(output/"HEADER_RESULT.json",result,expose=True)
            final=usage()
            cap_pass=(final["process_CPU_seconds_including_imports"] <= CPU_CAP
                      and final["wall_seconds_since_module_start"] <= WALL_CAP
                      and final["peak_RSS_bytes"] <= MEMORY_CAP)
            if not cap_pass:
                result["status"]="FAILED_CLOSED_FINAL_RESOURCE_GATE_NO_RETRY"
                result["measured_resources"]=final
                result_raw=save(output/"HEADER_RESULT.json",result,expose=True)
                code=2
            execution={"status":result["status"],"HEADER_RESULT_sha256":sha(result_raw),
                       "scope_sha256":args.expected_scope_sha256,"wrapper_sha256":wrapper_sha,
                       "source_public_freeze_commit":args.public_freeze_commit,
                       "root_admission_sha256":args.expected_root_admission_sha256,
                       "measured_resources_after_result_serialization":final,"resource_caps_satisfied":cap_pass,
                       "application_BODY_charged_upper_bound_bytes":result["application_BODY_charged_upper_bound_bytes"],
                       "application_BODY_bytes_received":result["application_BODY_bytes_received"],
                       "root_reservation_verified":result["root_reservation_verified"],
                       "source_values_admission":"BLOCKED_PROTECTED_REGISTRY_UNRESOLVED", "no_retry":True,
                       "metadata_parser_executed":False,"stdout_bytes_before_execution_snapshot":STDOUT_BYTES}
            save(output/"EXECUTION_RECEIPT.json",execution,expose=True)
        finally:
            for handle in reversed(held):
                handle.close()
            os.close(directory_fd)
            signal.alarm(0)
    emit({"record_type":"SETI_INITIAL_PREFIX_TERMINAL_V1", "stage_id":TOOLS.split("/")[1],
          "status":result["status"],"BODY_received":result["application_BODY_bytes_received"],
          "BODY_charged_upper_bound":result["application_BODY_charged_upper_bound_bytes"],
          "HEAD_attempts":result["HEAD_requests_attempted"],"GET_attempts":result["prefix_GET_requests_attempted"],
          "no_retry":True,"geometry":None})
    return code

if __name__ == "__main__":
    raise SystemExit(main())
