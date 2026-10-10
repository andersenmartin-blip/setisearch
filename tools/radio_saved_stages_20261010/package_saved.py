#!/usr/bin/env python3
"""Once-only configured COMPLETE-stage ZIP; scientific arrays are opaque bytes.

Byte SHA/CRC routines copied from audited54b70209..., with no exceptional-status gate.
"""
import argparse,hashlib,json,os,re,resource,signal,shutil,time,zipfile,zlib
from pathlib import Path
import common_json as saved
import summarize_saved as summary_tool
ROOT=Path(__file__).resolve().parents[2]
POST_SCOPE=summary_tool.POST_SCOPE
CPU_CAP,WALL_CAP,MEMORY_CAP=120,1800,4*1024**3
WORKSPACE_CAP,PENDING_OUTPUT_RESERVE=8*1024**3,512*1024**2


CHUNK = 1024**2

TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".log", ".csv", ".sha256", ".svg"}

ALLOWED_SUFFIXES = TEXT_SUFFIXES | {".npz", ".png", ".jpg", ".jpeg", ".pdf", ".gz"}

EXCLUDED_COMPONENTS = {"__pycache__", ".git", ".cache", "cache", "wheels", "deps",
                       "private", "privatework", "library_helpers", "library_helpers_current", "packaging",
                       "archive_parts_10MiB", "archive"}

PRIVATE_PATTERNS = (
    re.compile(rb"\blibfile_[0-9a-f]{16,}\b"),
    re.compile(rb"\bfile_[0-9a-f]{16,}\b"),
    re.compile(rb"[?&](?:sig|token|access_token|X-Amz-Signature|X-Goog-Signature)=",
               re.IGNORECASE),
    re.compile(rb'"(?:reported_weekly_remaining_percent|reported_resets)"\s*:'),
)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()

def load_json(root, name, expected=None):
    raw = (root/name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected is not None and actual != expected:
        raise ValueError("Metadata pin differs: " + name)
    return json.loads(raw), {"sha256": actual, "bytes": len(raw)}

def relative_path(root, name):
    relative = Path(name)
    path = root/relative
    if (relative.is_absolute() or ".." in relative.parts or path.is_symlink()
            or not path.resolve().is_relative_to(root)):
        raise ValueError("Non-project path or symlink forbidden: " + name)
    return path

def public_text(path, name):
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return
    raw = path.read_bytes()
    if any(pattern.search(raw) for pattern in PRIVATE_PATTERNS):
        raise ValueError("Private opaque ID, signed credential URL or account counter in public payload: " + name)

def workspace_bytes(directory):
    total=0
    for current,dirs,files in os.walk(directory,followlinks=False):
        dirs[:]=[name for name in dirs if not (Path(current)/name).is_symlink()]
        for name in files:
            path=Path(current)/name
            if not path.is_symlink():
                total+=path.stat().st_size
    return total

def zip_info(name):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info._compresslevel = 1
    info.external_attr = 0o100644 << 16
    return info

def add_file(archive, root, name):
    path = root/name
    before = path.stat()
    h, crc, size = hashlib.sha256(), 0, 0
    with path.open("rb") as source, archive.open(zip_info(name), "w", force_zip64=True) as target:
        for block in iter(lambda: source.read(CHUNK), b""):
            target.write(block)
            h.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    after = path.stat()
    if (size != before.st_size or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError("Payload changed during ZIP creation: " + name)
    return {"path": name, "bytes": size, "sha256": h.hexdigest(), "member_CRC32_hex": f"{crc & 0xffffffff:08x}"}

def verify_archive(path, members):
    with zipfile.ZipFile(path, "r") as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate ZIP member")
        if set(archive.namelist()) != set(members):
            raise ValueError("ZIP member list differs from expected public payload")
        for name, expected in members.items():
            info = archive.getinfo(name)
            h, crc, size = hashlib.sha256(), 0, 0
            with archive.open(info, "r") as handle:
                for block in iter(lambda: handle.read(CHUNK), b""):
                    h.update(block)
                    crc = zlib.crc32(block, crc)
                    size += len(block)
            if (size != expected["bytes"] or info.file_size != size
                    or h.hexdigest() != expected["sha256"]
                    or f"{crc & 0xffffffff:08x}" != expected["member_CRC32_hex"]
                    or info.CRC != crc & 0xffffffff):
                raise ValueError("ZIP SHA256, size or member CRC differs: " + name)
    return len(members)


def inventory(root,config,summary,pins):
    stage=config["results_directory"]
    output={};batches={(b["source_chunk_id"],b["batch_id"]):b for b in summary["batches"]}
    profiles={tuple(p["identity"]):p for p in summary["profiles"]}
    if len(batches)!=2*len(config["source_chunk_ids"]) or len(profiles)!=18*len(config["source_chunk_ids"]):
        raise ValueError("Unique COMPLETE batch/profile identities required")
    for chunk in config["source_chunk_ids"]:
      for batch in (1,2):
        prefix=f"{stage}/chunk{chunk}/batch_{batch:02d}/measurement/"
        b=batches[(chunk,batch)]
        checkpoint,_=load_json(root,prefix+"DRIFT_CHECKPOINT.json",pins[prefix+"DRIFT_CHECKPOINT.json"])
        qs=list(range(1,128)) if batch==1 else list(range(128,255))
        done,complete=saved.checkpoint_summary(checkpoint,batch,qs,chunk*1048576,chunk)
        execution,_=load_json(root,prefix+"EXECUTION_RECEIPT.json",pins[prefix+"EXECUTION_RECEIPT.json"])
        qa,_=load_json(root,prefix+"QA_RECEIPT.json",b["QA_receipt_sha256"])
        counts={"maps":381,"normalization_files":381,"carrier_maximum_records":1560576,
                "top20_entries":60,"patches":9,"scan_profiles":54,"time_rows":864,
                "retained_raw_patch_cells":111456,"binary_and_normalization_hashes":771}
        if (not complete or checkpoint["completed_scan_tiles"]!=381 or b["execution_complete"] is not True
                or (root/(prefix+"FAILURE_RECEIPT.json")).exists()
                or execution["status"]!=saved.COMPLETE_STATUS or b["status"]!=saved.COMPLETE_STATUS
                or execution["saved_normalization_sha256"]!=pins[prefix+"NORMALIZATION.json"]
                or qa["status"]!="PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS" or qa["counts"]!=counts
                or qa["execution_receipt_sha256"]!=pins[prefix+"EXECUTION_RECEIPT.json"]
                or qa["checkpoint_sha256"]!=pins[prefix+"DRIFT_CHECKPOINT.json"]
                or qa["profile_JSON_sha256"]!=pins[prefix+"FIXED_TOP3_PROFILES.json"]
                or qa["top20_sha256"]!=pins[prefix+"DRIFT_TOP20.json"]
                or qa["INPUT_PINS_sha256"]!=pins[prefix+"INPUT_PINS.json"]
                or qa["qa_script_sha256"]!=config["local_QA_script_sha256"]
                or qa["public_scope_sha256"]!=config["numerical_scope_sha256"]
                or qa["public_wrapper_sha256"]!=config["numerical_wrapper_sha256"]
                or qa["freeze_commit"]!=config["original_scientific_freeze_commit"]):
            raise ValueError("Actual original COMPLETE/QA differs from audited saved summary")
        for e in checkpoint["completed_receipts"]:
            for name,hashkey,sizekey in (("path","sha256","bytes"),("normalization_path","normalization_sha256","normalization_bytes")):
                path=prefix+e[name]
                if path in output: raise ValueError("Duplicate saved map/normalization path")
                output[path]={"sha256":e[hashkey],"bytes":e[sizekey]}
        records,_=load_json(root,prefix+"FIXED_TOP3_PROFILES.json",pins[prefix+"FIXED_TOP3_PROFILES.json"])
        if len(records)!=9: raise ValueError("Nine unchanged fixed profiles required")
        for r in records:
            t=r["selected_track"];identity=(t["source_chunk_id"],t["batch_id"],t["track_id"])
            if identity[:2]!=(chunk,batch) or profiles[identity]["patch_provenance"]!=r["patch"]:
                raise ValueError("Saved summary/patch triple identities differ")
            name=prefix+r["patch"]["path"]
            if name in output: raise ValueError("Duplicate raw patch path")
            output[name]={"sha256":r["patch"]["sha256"],"bytes":r["patch"]["bytes"]}
    if len(output)!=(381*2+9)*len(batches): raise ValueError("Complete scientific inventory size differs")
    for name,pin in output.items():
        path=relative_path(root,name)
        if path.stat().st_size!=pin["bytes"] or digest(path)!=pin["sha256"]:
            raise ValueError("Opaque scientific payload differs: "+name)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",default=str(ROOT));p.add_argument("--stage-id",choices=sorted(summary_tool.ALLOWED),required=True)
    p.add_argument("--archive",required=True);p.add_argument("--expected-postprocessing-scope-sha256",required=True)
    p.add_argument("--postprocessing-freeze-commit",required=True)
    p.add_argument("--expected-summary-sha256",required=True);p.add_argument("--expected-summary-receipt-sha256",required=True)
    p.add_argument("--expected-report-sha256",required=True);p.add_argument("--extra-pins",required=True)
    p.add_argument("--expected-extra-pins-sha256",required=True);p.add_argument("--root-authorized-package-read",action="store_true")
    a=p.parse_args()
    if not a.root_authorized_package_read: raise SystemExit("Root GO required before result-byte reads")
    if len(a.postprocessing_freeze_commit)!=40 or any(c not in "0123456789abcdef" for c in a.postprocessing_freeze_commit):
        raise ValueError("Exact public postprocessing freeze commit required")
    started=time.monotonic();root=Path(a.root).resolve()
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    def deadline(sig,frame): raise TimeoutError("Saved-stage package CPU/wall cap exceeded")
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.alarm(WALL_CAP)
    post,post_pin=load_json(root,POST_SCOPE,a.expected_postprocessing_scope_sha256)
    config=post["stage_configs"][a.stage_id];stage=config["results_directory"]
    out=root/(stage+"/packaging");archive_path=Path(a.archive).resolve();temporary=archive_path.with_suffix(".zip.tmp")
    if archive_path.name!=config["archive_filename"] or archive_path.exists() or temporary.exists() or out.exists():
        raise ValueError("Exact unused once-only stage archive/output required")
    out.mkdir(parents=True,exist_ok=False)
    saved.dump_json(out/"PACKAGE_STARTED.json",{"status":"STARTED_ONCE_ONLY_ORIGINAL_COMPLETE_STAGE_BYTE_PACKAGE","script_sha256":digest(Path(__file__))})
    try:
        receipt_name=config["summary_directory"]+"/SUMMARY_EXECUTION_RECEIPT.json"
        receipt,receipt_pin=load_json(root,receipt_name,a.expected_summary_receipt_sha256)
        summary_name=config["summary_directory"]+"/SAVED_SUMMARY.json"
        summary,summary_pin=load_json(root,summary_name,a.expected_summary_sha256)
        pins,pins_pin=load_json(root,config["summary_input_pins_path"],receipt["input_pins_sha256"])
        reader=saved.PinnedJSON(root,root/config["summary_input_pins_path"])
        post,config,chunks=summary_tool.configure(reader,a.stage_id,a.expected_postprocessing_scope_sha256)
        required=summary_tool.required_inputs(config,chunks)
        if (set(pins)!=required or set(receipt["opened_inputs"])!=required
                or receipt["status"]!="PASS_PINNED_COMPLETE_ONLY_JSON_SUMMARY_NO_NUMERIC_RERUN"
                or receipt["stage_id"]!=a.stage_id or receipt["HDF5_or_NPZ_opened"] is not False
                or receipt["detector_rerun"] is not False or receipt["global_reranking"] is not False
                or receipt["original_statuses_rewritten"] is not False
                or summary["status"]!="COMPLETE_AUDITED_SAVED_STAGE" or summary["stage_id"]!=a.stage_id
                or summary["fully_audited_summary_complete"] is not True
                or summary["all_original_numeric_executions_COMPLETE"] is not True
                or summary["original_execution_statuses_rewritten"] is not False
                or summary["postprocessing_scope_sha256"]!=post_pin["sha256"]
                or summary["public_postprocessing_freeze_commit"]!=a.postprocessing_freeze_commit
                or receipt["public_postprocessing_freeze_commit"]!=a.postprocessing_freeze_commit
                or summary["completed_scan_tiles"]!=762*len(chunks) or summary["profile_count"]!=18*len(chunks)
                or summary["ON_carrier_origin_entries"]!=3121152*len(chunks)
                or summary["evaluated_hypothesis_combinations"]!=4762877952*len(chunks)):
            raise ValueError("Actual COMPLETE-only pinned summary required")
        admitted={}
        def admit(name,sha,size=None):
            relative_path(root,name)
            pin={"sha256":sha}
            if size is not None: pin["bytes"]=size
            if name in admitted and any(k in admitted[name] and admitted[name][k]!=v for k,v in pin.items()):
                raise ValueError("Conflicting admitted identity: "+name)
            admitted.setdefault(name,{}).update(pin)
        for name,sha in pins.items():
            data,actual=load_json(root,name,sha)
            if receipt["opened_inputs"][name]!=actual: raise ValueError("Pinned saved input bytes differ")
            admit(name,sha,actual["bytes"])
        scope,_=load_json(root,config["numerical_scope_path"],config["numerical_scope_sha256"])
        for name,pin in inventory(root,config,summary,pins).items(): admit(name,pin["sha256"],pin["bytes"])
        audit=summary_tool.source_audit(reader,scope,config,summary["profiles"],chunks)
        if audit!=summary["joint_source_cell_QA"]: raise ValueError("Actual source audit differs from summary")
        for name,sha in post["pinned_dependency_files"].items(): admit(name,sha)
        for name,sha in scope["pinned_dependency_files"].items(): admit(name,sha,scope["pinned_dependency_file_bytes"][name])
        admit(POST_SCOPE,post_pin["sha256"],post_pin["bytes"]);admit(summary_name,summary_pin["sha256"],summary_pin["bytes"])
        admit(receipt_name,receipt_pin["sha256"],receipt_pin["bytes"]);admit(config["summary_input_pins_path"],pins_pin["sha256"],pins_pin["bytes"])
        admit(config["report_path"],a.expected_report_sha256)
        admit("tools/radio_saved_stages_20261010/summarize_saved.py",receipt["script_sha256"])
        for name,sha in receipt["output_hashes"].items():
            if name!=config["report_path"]: admit(name,sha)
        if receipt["output_hashes"].get(summary_name)!=summary_pin["sha256"]: raise ValueError("Summary receipt output pin differs")
        extra_path=Path(a.extra_pins).resolve()
        if not extra_path.is_relative_to(root): raise ValueError("Project-relative late package pins required")
        extra,extra_pin=load_json(root,str(extra_path.relative_to(root)),a.expected_extra_pins_sha256)
        expected_extra=set(config["figure_paths"]+[config["plot_receipt_path"]]+[f"{stage}/chunk{c}/raw_checkpoint/RAW_CHECKPOINT_ARCHIVE_MANIFEST.json" for c in chunks])
        if set(extra)!=expected_extra: raise ValueError("Exactly the frozen figures and per-chunk external RAW manifests must be pinned")
        archives=[]
        for name,sha in extra.items(): admit(name,sha)
        plotted,_=load_json(root,config["plot_receipt_path"],extra[config["plot_receipt_path"]])
        if (plotted["status"]!="COMPLETE_TWO_ORIGINAL_COMPLETE_SAVED_JSON_FIGURES" or plotted["stage_id"]!=a.stage_id
                or plotted["source_chunk_ids"]!=list(chunks) or plotted["all_original_numeric_executions_COMPLETE"] is not True
                or plotted["original_execution_statuses_rewritten"] is not False or plotted["all_saved_output_QA_passed"] is not True
                or plotted["acquisition_source_QA_passed"] is not True or plotted["source_cell_audit"]!=audit
                or plotted["script_sha256"]!=config["plot_script_sha256"]
                or plotted["postprocessing_scope_sha256"]!=post_pin["sha256"]
                or plotted["postprocessing_freeze_commit"]!=a.postprocessing_freeze_commit
                or plotted["input_pins_sha256"]!=receipt["input_pins_sha256"]
                or plotted["opened_input_JSON"]!=receipt["opened_inputs"]
                or plotted["measured_CPU_within_cap"] is not True
                or not 0<plotted["process_CPU_seconds_including_imports"]<=config["plot_CPU_cap_s"]
                or not 0<plotted["wall_seconds_including_imports"]<=config["plot_wall_cap_s"]
                or not 0<plotted["peak_RSS_bytes"]<=config["plot_memory_cap_bytes"]
                or plotted["case_count"]!=summary["profile_count"] or plotted["actual_completed_map_receipts"]!=summary["completed_scan_tiles"]):
            raise ValueError("Actual complete plotting receipt must bind same saved inputs, source QA and frozen code")
        if len(plotted["plots"])!=2 or {p["path"] for p in plotted["plots"]}!=set(config["figure_paths"]):
            raise ValueError("Two exact future figure identities required")
        for plot in plotted["plots"]:
            if extra[plot["path"]]!=plot["sha256"] or relative_path(root,plot["path"]).stat().st_size!=plot["bytes"]:
                raise ValueError("Actual figure SHA/size must agree with its admitted plotting receipt")
        for c in chunks:
            name=f"{stage}/chunk{c}/raw_checkpoint/RAW_CHECKPOINT_ARCHIVE_MANIFEST.json"
            raw,_=load_json(root,name,extra[name])
            if (raw["status"]!="PASS_COMPLETE_OPAQUE_BYTE_COPY_ZIP_SHA_SIZE_ALL_MEMBER_SHA_CRC_READBACK"
                    or raw["source_chunk_id"]!=c or raw["public_scientific_freeze_commit"]!=config["original_scientific_freeze_commit"]
                    or raw["independent_acquisition_QA_sha256"]!=summary["acquisition_metadata"][str(c)]["acquisition_source_QA_receipt_sha256"]
                    or raw["HDF5_or_NPZ_decodes"]!=0 or raw["numerical_measurement_or_profile_runs"]!=0):
                raise ValueError("External RAW archive must bind actual verified acquisition")
            archives.append({"source_chunk_id":c,**raw["archive"],"manifest_path":name,"manifest_sha256":extra[name]})
        admit(str(extra_path.relative_to(root)),extra_pin["sha256"],extra_pin["bytes"])
        names=set(admitted)
        for prefix in ("tools/radio_saved_stages_20261010",config["tools_directory"],stage):
            for path in (root/prefix).rglob("*"):
                r=path.relative_to(root)
                if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES and not any(x in EXCLUDED_COMPONENTS for x in r.parts): names.add(r.as_posix())
        snapshot={}
        for name in sorted(names):
            path=relative_path(root,name)
            if any(x in EXCLUDED_COMPONENTS for x in Path(name).parts) or path.suffix.lower() in {".h5",".hdf5",".whl"}: raise ValueError("Excluded payload entered archive")
            public_text(path,name);snapshot[name]={"sha256":digest(path),"bytes":path.stat().st_size}
        for name,pin in admitted.items():
            if any(snapshot[name][k]!=v for k,v in pin.items()): raise ValueError("Snapshot differs from admitted identity: "+name)
        estimate=sum(p["bytes"] for p in snapshot.values())+8*1024**2
        used=workspace_bytes(root.parent)
        if used+estimate+PENDING_OUTPUT_RESERVE>WORKSPACE_CAP or shutil.disk_usage(root.parent).free<estimate+PENDING_OUTPUT_RESERVE:
            raise ValueError("Conservative8GiB workspace/free-space guard failed")
        archive_path.parent.mkdir(parents=True,exist_ok=True);entries=[];manifest_name=stage+"/packaging/PACKAGE_MANIFEST.json"
        with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
            for name in sorted(names):
                entry=add_file(archive,root,name)
                if any(entry[k]!=snapshot[name][k] for k in ("sha256","bytes")): raise ValueError("Payload changed during byte copy")
                entries.append(entry)
            manifest={"schema":"SETI_CONFIGURED_ORIGINAL_COMPLETE_STAGE_BYTE_PACKAGE_V1","stage_id":a.stage_id,"archive_filename":archive_path.name,
                "original_numeric_status":"ALL_COMPLETE_UNCHANGED","completed_scan_tiles":summary["completed_scan_tiles"],"completed_fixed_profiles":summary["profile_count"],
                "postprocessing_scope_sha256":post_pin["sha256"],"summary_sha256":summary_pin["sha256"],"summary_receipt_sha256":receipt_pin["sha256"],
                "public_postprocessing_freeze_commit":a.postprocessing_freeze_commit,
                "original_scientific_freeze_commit":config["original_scientific_freeze_commit"],"original_numerical_scope_sha256":config["numerical_scope_sha256"],
                "members":entries,"required_external_input_archives":archives,"manifest_excludes_own_SHA_and_CRC":True,
                "ZIP_SHA_only_in_external_receipt":True,"HDF5_or_wheels_embedded":False,"scientific_arrays_decoded":False,
                "detector_rerun":False,"one_historical_visit":True,"original_full_source_MD5_verified":False,"public_Git_bytepart_max_bytes":10485759}
            raw=(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode();archive.writestr(zip_info(manifest_name),raw)
        members={e["path"]:e for e in entries};members[manifest_name]={"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"member_CRC32_hex":f"{zlib.crc32(raw)&0xffffffff:08x}"}
        verified=verify_archive(temporary,members)
        for name,pin in snapshot.items():
            if digest(root/name)!=pin["sha256"] or (root/name).stat().st_size!=pin["bytes"]: raise ValueError("Admitted payload changed before final readback")
        if digest(extra_path)!=extra_pin["sha256"]: raise ValueError("Late package pin map changed")
        archive_sha,archive_bytes=digest(temporary),temporary.stat().st_size;temporary.replace(archive_path);(out/"PACKAGE_MANIFEST.json").write_bytes(raw)
        measured={"process_CPU_seconds_including_imports":time.process_time(),"wall_seconds_including_imports":time.monotonic()-started,"peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if measured["process_CPU_seconds_including_imports"]>CPU_CAP or measured["wall_seconds_including_imports"]>WALL_CAP or measured["peak_RSS_bytes"]>MEMORY_CAP: raise TimeoutError("Measured package caps exceeded")
        result={"status":"PASS_COMPLETE_STAGE_ZIP_ALL_MEMBERS_SHA_SIZE_CRC_READBACK","stage_id":a.stage_id,"archive_filename":archive_path.name,"archive_sha256":archive_sha,"archive_bytes":archive_bytes,
            "verified_members_including_manifest":verified,"script_sha256":digest(Path(__file__)),"scientific_arrays_decoded":False,"detector_rerun":False,"original_statuses_rewritten":False,**measured}
        saved.dump_json(out/"PACKAGE_RECEIPT.json",result);signal.alarm(0);print(json.dumps(result))
    except BaseException as exc:
        saved.dump_json(out/"PACKAGE_FAILURE_RECEIPT.json",{"status":"PACKAGE_FAILED_OR_PARTIAL_NO_RETRY","error_type":type(exc).__name__,"error":str(exc),"partial_archive_retained":temporary.exists() or archive_path.exists(),"retry_authorized":False,"scientific_arrays_decoded":False,"process_CPU_seconds_including_imports":time.process_time(),"wall_seconds":time.monotonic()-started})
        raise

if __name__=="__main__": main()
