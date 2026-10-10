"""Three new joined boundary families; import reads no files or observation values.

The old raw detector/ranking arithmetic and fixed-profile function are reused.
Only new joined geometry, provenance, and profile-denominator context are bound.
No main call, loader, NumPy import, search or profile computation occurs on import.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import re
import signal
import sys
import time
from types import SimpleNamespace

for _name in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_name]="1"
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
SCANS=("epoch1_on","epoch1_off","epoch2_on","epoch2_off","epoch3_on","epoch3_off")
ONS=SCANS[::2]
PAIRS={"153_154":(153,154),"154_155":(154,155),"157_158":(157,158)}
COUNT,JOINED_COUNT=1048576,2097152
FCH1,DF,TSAMP=1876464843.75,-2.835503418452676,17.986224128
WIDTHS,CORE_COUNT,CROP_HALO,TOP=(1,3),4096,4000,20
QS=(255,256)
CPU_CAP,WALL_CAP,MEMORY_CAP=120,1800,4*1024**3
FRESH_PATH="tools/radio_fresh_band_20261009/fresh_search.py"
DETECTOR_PATH="pilot_engine_20261008/detector.py"
GAP_PATH="tools/radio_gap_drift_20261010/gap_search.py"
ACTIVATION_PATH="tools/radio_internal_boundaries_20261010/ACTIVATION_SCOPE.json"
ACTIVATION_SHA="2dfaf1f5da871b0ab4d0e773b44805a84d3bbf004062d61b07ab8daa3ca45a9d"
SELECTION_SHA="3b447a80d662289fef3e5d4574a2f725808c2952db768814462e407bb56bc36b"
FRESH_SHA="1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102"
DETECTOR_SHA="1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45"
GAP_SHA="b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58"
VERSIONS={"numpy":"2.3.5","scipy":"1.17.0","matplotlib":"3.10.8","h5py":"3.15.1","hdf5plugin":"7.1.0"}
NORMALIZATION_METHOD="median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)"

class ResourceLimitExceeded(RuntimeError):
    pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024**2),b""):h.update(block)
    return h.hexdigest()

def save(path,value):
    target=Path(path);temporary=target.with_suffix(target.suffix+".tmp")
    with temporary.open("w") as handle:
        json.dump(value,handle,indent=2,allow_nan=False);handle.write("\n")
    temporary.replace(target)

def confined(name):
    p=Path(name)
    if p.is_absolute() or ".." in p.parts or not (ROOT/p).resolve().is_relative_to(ROOT):
        raise ValueError("Require root-relative confined paths")
    return ROOT/p

def check_pin(name,pin):
    p=confined(name)
    if p.stat().st_size!=pin["bytes"] or digest(p)!=pin["sha256"]:
        raise ValueError("Frozen input differs: "+name)

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def runtime_158_gate(scope,pair_id):
    pins={}
    if pair_id!="pair157_158":return pins
    gate=scope["runtime_158_admission"]
    original_scope=gate["original_scope_sha256"];original_script=gate["original_script_sha256"]
    if len(gate["jobs"])!=2 or {j["batch_id"] for j in gate["jobs"]}!={1,2}:
        raise ValueError("Exactly both original158 batches must be admitted")
    def read_once(name):
        raw=confined(name).read_bytes()
        pin={"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
        return json.loads(raw),pin
    for job in gate["jobs"]:
        e,epin=read_once(job["execution_receipt_path"])
        q,qpin=read_once(job["QA_receipt_path"]);esha=epin["sha256"]
        if (e.get("status")!="COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
            or e.get("source_chunk_id")!=158 or e.get("batch_id")!=job["batch_id"]
            or e.get("scope_sha256")!=original_scope or e.get("script_sha256")!=original_script
            or e.get("search_summary",{}).get("completed_scan_tiles")!=381
            or e.get("fixed_profile_summary",{}).get("profile_count")!=9
            or q.get("status")!="PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
            or q.get("source_chunk_id")!=158 or q.get("batch_id")!=job["batch_id"]
            or q.get("public_scope_sha256")!=original_scope
            or q.get("public_wrapper_sha256")!=original_script
            or q.get("execution_receipt_sha256")!=esha
            or q.get("qa_script_sha256")!=gate["saved_QA_script_sha256"]
            or q.get("counts")!={"maps":381,"normalization_files":381,"carrier_maximum_records":1560576,
                 "top20_entries":60,"patches":9,"scan_profiles":54,"time_rows":864,
                 "retained_raw_patch_cells":111456,"binary_and_normalization_hashes":771}):
            raise ValueError("Both original158 jobs require actual COMPLETE and authenticated saved QA")
        pins[job["execution_receipt_path"]]=epin;pins[job["QA_receipt_path"]]=qpin
    audit,apin=read_once(gate["source_audit_receipt_path"])
    if (audit.get("status")!="PASS_18_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE"
        or audit.get("public_scope_sha256")!=original_scope
        or audit.get("public_wrapper_sha256")!=original_script
        or audit.get("audit_script_sha256")!=gate["source_audit_script_sha256"]
        or audit.get("counts")!={"compact_files":6,"decoded_rows":96,"patches":18,
             "scan_profiles":108,"time_rows":1728,"raw_cells_bitwise_checked":222912}):
        raise ValueError("Original158 source-cell audit must pass before joined157158 source access")
    pins[gate["source_audit_receipt_path"]]=apin
    return pins

def load_contract(args):
    if digest(args.scope)!=args.expected_scope_sha256:raise ValueError("Scope differs from public freeze")
    scope=json.loads(Path(args.scope).read_text())
    if digest(__file__)!=scope["script_sha256"]:raise ValueError("Executable differs from freeze")
    expected={"schema":"SETI_THREE_JOINED_INTERNAL_BOUNDARY_PAIRS_V1","metadata_selection_canonical_SHA256":SELECTION_SHA,
      "native_pairs":[list(p) for p in PAIRS.values()],"pair_ids":["pair"+p for p in PAIRS],
      "native_channel_count":COUNT,"joined_channel_count":JOINED_COUNT,"joined_reference_core_q":list(QS),
      "rows_per_scan":16,"scan_order":list(SCANS),"origin_scan_order":list(ONS),"fch1_hz":FCH1,"df_hz":DF,"tsamp_s":TSAMP,
      "core_channel_count":CORE_COUNT,"crop_halo_channels":CROP_HALO,"expected_scan_tiles_per_pair":6,
      "carriers_per_ON_per_pair":8192,"drift_grid":{"first_hz_s":-4,"last_hz_s":4,"count":763},
      "widths_channels":list(WIDTHS),"valid_hypotheses_per_carrier":1526,"rank_count_per_ON_per_pair":TOP,
      "display_suppression_channels":3,"expected_profile_count_per_pair":9,"profile_halfwidth_channels":64,
      "fixed_profile_shift_channels":0,"CPU_cap_s_per_pair":CPU_CAP,"wall_cap_s_per_pair":WALL_CAP,
      "memory_cap_bytes_per_pair":MEMORY_CAP,"analysis_attempts_per_pair":1,"numeric_retry_authorized":False,
      "old_holdouts_reopened":False,"protected_old_native_chunks_not_read":[156,159],"original_scopes_terminal_statuses_and_outputs_modified":False,
      "OFF_veto":False,"blind_or_independent_validation":False,"calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,
      "runtime_package_versions":VERSIONS,"new_HTTP_requests":0,"new_BODY_bytes":0,"numeric_pairs_serial":True,
      "joined_profile_normalization_method":NORMALIZATION_METHOD}
    if any(scope.get(k)!=v for k,v in expected.items()):raise ValueError("Scope differs from implemented boundary family")
    pinned=scope["pinned_dependency_files"]
    for name,sha in {FRESH_PATH:FRESH_SHA,DETECTOR_PATH:DETECTOR_SHA,GAP_PATH:GAP_SHA,ACTIVATION_PATH:ACTIVATION_SHA}.items():
        if pinned.get(name,{}).get("sha256")!=sha:raise ValueError("Original method/source pin differs")
    for name,p in pinned.items():check_pin(name,p)
    for name,version in VERSIONS.items():
        if importlib.metadata.version(name)!=version:raise ValueError("Package differs: "+name)
    activation=json.loads((ROOT/ACTIVATION_PATH).read_text());selection=activation["immutable_metadata_selection"]
    canonical=(json.dumps(selection,sort_keys=True,separators=(",",":"))+"\n").encode()
    if (hashlib.sha256(canonical).hexdigest()!=SELECTION_SHA or selection!=scope["immutable_metadata_selection"]
        or not activation["zero_cost_continuation_authorized"]):raise ValueError("Full-power authorization/fixed selection differs")
    pair_id="pair"+args.pair;pair=scope["pair_contracts"][pair_id];chunks=PAIRS[args.pair];source0=chunks[0]*COUNT
    if (pair["source_chunk_ids"]!=list(chunks) or pair["source_channel0"]!=source0
        or pair["source_channel_count"]!=JOINED_COUNT or pair["joined_reference_core_q"]!=list(QS)
        or Path(args.outdir).resolve()!=confined(pair["measurement_directory"]).resolve()):
        raise ValueError("Use exact frozen pair geometry/output directory")
    sources={};acquisitions={};contexts={};anchor=None
    for chunk in chunks:
        context=scope["chunk_contracts"][str(chunk)];contexts[str(chunk)]=context
        s=json.loads(confined(context["source_manifest_path"]).read_text())
        a=json.loads(confined(context["acquisition_summary_path"]).read_text())
        q=json.loads(confined(context["acquisition_QA_path"]).read_text())
        if (s["native_chunk_index"]!=chunk or s["physical_channel_interval_half_open"]!=[chunk*COUNT,(chunk+1)*COUNT]
            or [x["label"] for x in s["sources"]]!=list(SCANS) or [x["role"].upper() for x in s["sources"]]!=["ON","OFF"]*3
            or a["status"]!="COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
            or a["source_manifest_sha256"]!=context["source_manifest_sha256"] or a["source_channel0"]!=chunk*COUNT
            or q["status"]!="PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
            or q["acquisition_result_sha256"]!=context["acquisition_summary_sha256"]
            or q["source_manifest_sha256"]!=context["source_manifest_sha256"]):
            raise ValueError("Source/acquisition/QA binding differs")
        files=a["decoded_files"]
        if len(files)!=6 or len({x["scan_id"] for x in files})!=6 or {x["scan_id"] for x in files}!=set(SCANS):
            raise ValueError("Exactly six unique native compacts required")
        if files!=context["compact_files_and_96_decoded_row_pins"]:raise ValueError("Frozen compact/row pins differ")
        for f in files:
            if (f["shape"]!=[16,1,COUNT] or f["source_channel0"]!=chunk*COUNT
                or [x["time_row"] for x in f["decoded_rows"]]!=list(range(16))
                or any(x["decoded_bytes"]!=COUNT*4 for x in f["decoded_rows"])):raise ValueError("Native compact row geometry differs")
        for item in s["sources"]:
            h=item["current_header"]["data_attributes"]
            if (h["tsamp"]!=TSAMP or h["fch1"]*1e6!=FCH1 or h["foff"]*1e6!=DF
                or item["current_header"]["dataset_shape"]!=[16,1,264503296]
                or item["current_header"]["dataset_chunks"]!=[1,1,COUNT]
                or item["current_header"]["dataset_dtype"]!="float32"):
                raise ValueError("Actual scan/source header geometry differs")
            rows=item["chunks"]
            if (len(rows)!=16 or [x["time_row"] for x in rows]!=list(range(16))
                or any(x["chunk_origin"]!=[i,0,chunk*COUNT] or x["decoded_size"]!=COUNT*4
                       or x["filter_mask"]!=0 or x["stored_size"]<=0 or x["byte_offset"]<0
                       or x["byte_offset"]+x["stored_size"]>item["source_file_bytes"]
                       or x["byte_range"]!=f"bytes={x['byte_offset']}-{x['byte_offset']+x['stored_size']-1}"
                       for i,x in enumerate(rows))):raise ValueError("Exact native payload descriptors differ")
        sources[str(chunk)]=s;acquisitions[str(chunk)]=a
    left,right=(sources[str(c)] for c in chunks)
    for l,r in zip(left["sources"],right["sources"]):
        if any(l[k]!=r[k] for k in ("label","role","url","etag","source_file_bytes","current_header")):
            raise ValueError("Paired sources/scans/headers must be identical")
    if left["physical_channel_interval_half_open"][1]!=right["physical_channel_interval_half_open"][0]:
        raise ValueError("Native physical intervals must be adjacent")
    anchor=float(min(x["current_header"]["data_attributes"]["tstart"] for x in left["sources"]))
    previous_end=-math.inf
    for item in left["sources"]:
        start=(item["current_header"]["data_attributes"]["tstart"]-anchor)*86400
        if start<previous_end:raise ValueError("Scans must retain actual chronological timing")
        previous_end=start+16*TSAMP
    admission=runtime_158_gate(scope,pair_id)
    return scope,pair,sources,acquisitions,contexts,anchor,source0,admission

def load_joined(fresh,sources,acquisitions,contexts,chunks):
    arrays={s:np.empty((16,JOINED_COUNT),dtype=np.float32) for s in SCANS};verified={}
    for side,chunk in enumerate(chunks):
        fresh.C0=chunk*COUNT;fresh.COUNT=COUNT;verified[str(chunk)]={}
        args=SimpleNamespace(compact_dir=str(confined(contexts[str(chunk)]["compact_directory"])))
        for label in SCANS:
            part,proof=fresh.load_power(args,sources[str(chunk)],acquisitions[str(chunk)],labels=(label,))
            arrays[label][:,side*COUNT:(side+1)*COUNT]=part[label]
            verified[str(chunk)].update(proof);del part,proof
    fresh.C0=chunks[0]*COUNT
    return arrays,verified

def normalization(arrays,source0,chunks,out):
    row_medians={s:np.median(arrays[s],axis=1).astype(np.float64) for s in SCANS}
    if any(not np.isfinite(v).all() or (v<=0).any() for v in row_medians.values()):raise ValueError("Invalid joined profile denominator")
    result={"method":NORMALIZATION_METHOD,"row_power_medians":{s:v.tolist() for s,v in row_medians.items()},
            "source_channel0":source0,"source_channel_count":JOINED_COUNT,"source_chunk_ids":list(chunks)}
    save(out/"NORMALIZATION.json",result);return result

def checkpoint(out,pair_id,qs,receipts):
    completed={scan:[r["reference_core_q"] for r in receipts if r["scan_id"]==scan] for scan in ONS}
    save(out/"DRIFT_CHECKPOINT.json",{"pair_id":pair_id,"fixed_pair_q":list(qs),"completed_scan_tiles":len(receipts),
         "expected_scan_tiles":6,"complete":len(receipts)==6,"completed_q_by_ON":completed,
         "completed_core_count_by_ON":{s:len(v) for s,v in completed.items()},"completed_receipts":receipts})

def run_search(fresh, arrays, source, anchor, out, pair_id, chunks, qs, source0):
    from pilot_engine_20261008 import detector
    if Path(detector.__file__).resolve() != (ROOT/DETECTOR_PATH).resolve():
        raise ValueError("Detector import resolved outside the pinned project")
    Scan, Config, search_scan = detector.Scan, detector.Config, detector.search_scan
    cfg = Config(widths=WIDTHS)
    drifts = np.linspace(-4.0, 4.0, 763)
    dt = np.arange(16)*TSAMP
    mismatch = float((drifts[1]-drifts[0])*dt[-1]/(2*abs(DF)))
    if mismatch > .5+1e-12:
        raise ValueError("Drift-grid half mismatch exceeds half a native channel")
    starts = tuple(q*CORE_COUNT for q in qs)
    all_results = {s: [] for s in ONS}
    receipts = []
    checkpoint(out, pair_id, qs, receipts)
    for tile_index, core_relative in enumerate(starts):
        first, stop = source0+core_relative, source0+core_relative+CORE_COUNT
        crop0, cropstop = core_relative-CROP_HALO, core_relative+CORE_COUNT+CROP_HALO
        for label in ONS:
            item = next(r for r in source["sources"] if r["label"] == label)
            h = item["current_header"]["data_attributes"]
            scan = Scan(label, "ON", arrays[label][:, crop0:cropstop], h["tstart"], TSAMP,
                        FCH1, DF, source0+crop0, np.arange(first, stop))
            frequencies = FCH1+DF*np.arange(first, stop)
            result, _ = search_scan(scan, frequencies, dt, drifts, cfg)
            if not np.isfinite(result["maximum_robust_box_track_score"]).all():
                raise ValueError("Nonfinite drift maxima")
            if not np.all(result["valid_hypothesis_count"] == 1526):
                raise ValueError("Incomplete drift hypotheses")
            numeric = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
            numeric["source_reference_channels"] = np.arange(first, stop)
            numeric["drift_grid_hz_s"] = drifts
            path = out/(label+"_tile_%02d_all_carriers.npz" % tile_index)
            np.savez(path, **numeric)
            normalization_path = out/(label+"_tile_%02d_normalization.json" % tile_index)
            save(normalization_path, result["normalization"])
            receipts.append({"scan_id": label, "tile_index": tile_index,
                "reference_core_q": qs[tile_index], "core_start_relative_channel": core_relative,
                "reference_channel_interval_half_open": [first, stop],
                "searched_carriers": CORE_COUNT, "valid_hypotheses_per_carrier": 1526,
                "path": path.name, "sha256": digest(path), "bytes": path.stat().st_size,
                "normalization_path": normalization_path.name, "normalization_sha256": digest(normalization_path),
                "normalization_bytes": normalization_path.stat().st_size})
            all_results[label].append(result)
            checkpoint(out, pair_id, qs, receipts)
            print("COMPLETED_INTERNAL_BOUNDARY_DRIFT_TILE", pair_id, label, tile_index, qs[tile_index], flush=True)
    tops = {}
    for label in ONS:
        results = all_results[label]
        scores = np.concatenate([r["maximum_robust_box_track_score"] for r in results])
        winning_drift = np.concatenate([r["winning_drift_hz_s"] for r in results])
        winning_width = np.concatenate([r["winning_width_channels"] for r in results])
        channels = np.concatenate([np.arange(source0+x, source0+x+CORE_COUNT) for x in starts])
        order = np.lexsort((channels, -scores))
        chosen = []
        for j in order:
            j = int(j)
            if all(abs(int(channels[j])-int(channels[k])) > 3 for k in chosen):
                chosen.append(j)
            if len(chosen) == TOP:
                break
        if len(chosen) != TOP:
            raise ValueError("Incomplete top20 display family")
        h = next(r["current_header"]["data_attributes"] for r in source["sources"] if r["label"] == label)
        ref = (h["tstart"]-anchor)*86400+.5*TSAMP
        tops[label] = [{"track_id": label+"_gap_drift_rank_%02d" % rank,
            "family": "internal_boundary_drift", "pair_id": pair_id,
            "source_chunk_id": chunks[0] if qs[j//CORE_COUNT] == 255 else chunks[1],
            "source_native_core_q": 255 if qs[j//CORE_COUNT] == 255 else 0, "originating_scan": label, "originating_role": "ON",
            "display_rank": rank, "source_reference_channel": int(channels[j]),
            "reference_frequency_hz": fresh.frequency(channels[j]),
            "reference_seconds_from_anchor": float(ref),
            "drift_hz_s": float(winning_drift[j]), "width_channels": int(winning_width[j]),
            "maximum_robust_box_track_score": float(scores[j]),
            "reference_core_tile": j//CORE_COUNT, "reference_core_q": qs[j//CORE_COUNT],
            "status": "EXPLORATORY_RANK_UNCLASSIFIED"}
            for rank, j in enumerate(chosen, 1)]
    save(out/"DRIFT_TOP20.json", tops)
    carriers = len(starts)*CORE_COUNT
    return tops, {"pair_id": pair_id, "source_chunk_ids": list(chunks), "completed_scan_tiles": len(receipts), "new_core_count": len(starts),
        "searched_q": list(qs), "carriers_per_ON": carriers,
        "new_channel_edge_bandwidth_per_ON_hz": carriers*abs(DF),
        "joined_channel_fraction_searched_this_pair": carriers/JOINED_COUNT,
        "previously_searched_reference_cores_in_this_new_family": 0,
        "completion_of_original_native_families_inferred": False,
        "reference_core_intervals_half_open": [[source0+x, source0+x+CORE_COUNT] for x in starts],
        "drift_grid_count": 763, "widths_channels": list(WIDTHS),
        "half_grid_mismatch_channels": mismatch, "display_suppression_channels": 3,
        "reference_time": "each ON's own first integration midpoint",
        "score_definition": "unchanged detector row-MAD standardized odd-box track sum / sqrt(Nrow*width)",
        "normalization": "each 4096-carrier static core, each row, unchanged 501-channel filtering",
        "normalization_receipt_layout": "Full unchanged normalization values persisted once per tile, checkpoint hash references"}


def partial_counts(out):
    values={"completed_scan_tiles":0,"completed_profiles":0}
    p=out/"DRIFT_CHECKPOINT.json"
    if p.is_file():
        d=json.loads(p.read_text());values.update(completed_scan_tiles=d["completed_scan_tiles"],completed_q_by_ON=d["completed_q_by_ON"],checkpoint_sha256=digest(p))
    p=out/"FIXED_TOP3_PROFILES.json"
    if p.is_file():values.update(completed_profiles=len(json.loads(p.read_text())),profile_checkpoint_sha256=digest(p))
    return values

def main():
    started=time.monotonic();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair",choices=tuple(PAIRS),required=True)
    for name in ("scope","expected-scope-sha256","outdir","freeze-commit"):parser.add_argument("--"+name,required=True)
    args=parser.parse_args();pair_id="pair"+args.pair
    if not re.fullmatch(r"[0-9a-f]{40}",args.freeze_commit):
        raise ValueError("Require exact public40hex freeze commit")
    expected=ROOT/"results/radio_internal_boundaries_20261010"/pair_id/"measurement"
    if Path(args.outdir).resolve()!=expected.resolve():raise ValueError("Require exact absolute resolved pair output path")
    out=Path(args.outdir).resolve();out.mkdir(parents=True,exist_ok=False)
    lock=ROOT/"results/radio_internal_boundaries_20261010/NUMERIC_ACTIVE.lock";locked=False
    def deadline(signum,frame):raise ResourceLimitExceeded("Joined boundary CPU/wall deadline reached")
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP));signal.alarm(WALL_CAP)
    try:
        fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);locked=True
        with os.fdopen(fd,"w") as handle:handle.write(pair_id+"\n")
        scope,pair,sources,acquisitions,contexts,anchor,source0,admission=load_contract(args);chunks=PAIRS[args.pair]
        source_inputs={str(c):{"source_manifest_sha256":contexts[str(c)]["source_manifest_sha256"],
           "acquisition_summary_sha256":contexts[str(c)]["acquisition_summary_sha256"],"acquisition_QA_sha256":contexts[str(c)]["acquisition_QA_sha256"],
           "compact_files_and_96_decoded_row_pins":acquisitions[str(c)]["decoded_files"]} for c in chunks}
        save(out/"INPUT_PINS.json",{"pair_id":pair_id,"scope_sha256":args.expected_scope_sha256,"script_sha256":digest(__file__),
          "source_chunk_ids":list(chunks),"source_channel0":source0,"source_channel_count":JOINED_COUNT,
          "source_inputs":source_inputs,"runtime_admission_receipts":admission,"public_freeze_commit":args.freeze_commit})
        global np
        import numpy as np
        fresh=load_module("unchanged_joined_native_loader",FRESH_PATH);old_gap=load_module("unchanged_joined_fixed_profiles",GAP_PATH)
        fresh.np=np;old_gap.np=np;old_gap.C0=source0;old_gap.COUNT=JOINED_COUNT
        old_gap.NORMALIZATION_PATH=(out/"NORMALIZATION.json").relative_to(ROOT).as_posix()
        arrays,verified=load_joined(fresh,sources,acquisitions,contexts,chunks)
        row_normalization=normalization(arrays,source0,chunks,out)
        tops,search_summary=run_search(fresh,arrays,sources[str(chunks[0])],anchor,out,pair_id,chunks,QS,source0)
        profile_summary=old_gap.fixed_profiles(arrays,sources[str(chunks[0])],row_normalization,tops,anchor,out)
        profile_summary.update(row_normalization_context="full joined2097152-channel float32 row median promoted tofloat64",
           time_profile_units="width-mean raw power/joined-pair row median minus fixed flank median",
           mean_profile_units="mean track-aligned joined-row-normalized power minus each row fixed flank median")
        for name,p in scope["pinned_dependency_files"].items():check_pin(name,p)
        for chunk in chunks:
            for record in acquisitions[str(chunk)]["decoded_files"]:
                path=confined(contexts[str(chunk)]["compact_directory"])/record["array_file"]
                if digest(path)!=record["file_sha256"] or path.stat().st_size!=record["bytes"]:raise ValueError("Compact input changed during joined search")
        for name,p in admission.items():check_pin(name,p)
        if digest(args.scope)!=args.expected_scope_sha256 or digest(__file__)!=scope["script_sha256"]:raise ValueError("Scope/script changed during job")
        measured={"process_CPU_seconds_including_imports":time.process_time(),"wall_seconds_including_imports":time.monotonic()-started,
           "peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        if measured["process_CPU_seconds_including_imports"]>CPU_CAP or measured["wall_seconds_including_imports"]>WALL_CAP or measured["peak_RSS_bytes"]>MEMORY_CAP:
            raise ResourceLimitExceeded("Measured use exceeds frozen joined boundary caps")
        if search_summary["completed_scan_tiles"]!=6 or profile_summary["profile_count"]!=9:raise ValueError("Incomplete boundary family")
        result={"status":"COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY","pair_id":pair_id,"source_chunk_ids":list(chunks),
          "source_channel0":source0,"source_channel_count":JOINED_COUNT,"fixed_pair_q":list(QS),"search_summary":search_summary,
          "fixed_profile_summary":profile_summary,"verified_source_inputs":verified,"scope_sha256":args.expected_scope_sha256,
          "script_sha256":digest(__file__),"source_inputs":source_inputs,"saved_normalization_sha256":digest(out/"NORMALIZATION.json"),
          "runtime_admission_receipts":admission,"public_freeze_commit":args.freeze_commit,"CPU_cap_s":CPU_CAP,"wall_cap_s":WALL_CAP,
          "memory_cap_bytes":MEMORY_CAP,"metadata_selection_canonical_SHA256":SELECTION_SHA,"MJD_anchor":anchor,
          "one_historical_visit":True,"blind_or_independent_validation":False,"qualified_sky_pilot":False,"OFF_veto_applied":False,
          "original_scopes_terminal_statuses_and_outputs_modified":False,"old_holdouts_reopened":False,"numeric_retry_authorized":False,
          "whole_original_source_MD5_verified":False,"new_HTTP_requests":0,"new_BODY_bytes":0,"cost_DKK":0,
          "calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,"limitations":scope["limitations"],**measured}
        save(out/"EXECUTION_RECEIPT.json",result)
        print(json.dumps({k:result[k] for k in ("status","pair_id","process_CPU_seconds_including_imports","wall_seconds_including_imports","peak_RSS_bytes")}),flush=True)
    except BaseException as exc:
        save(out/"FAILURE_RECEIPT.json",{"status":"INCOMPLETE_JOINED_BOUNDARY_NO_RETRY","pair_id":pair_id,"source_chunk_ids":list(PAIRS[args.pair]),
             "fixed_pair_q":list(QS),"error_type":type(exc).__name__,"error":str(exc),"retry_authorized":False,
             "partial_outputs_preserved":True,**partial_counts(out),"process_CPU_seconds_including_imports":time.process_time(),
             "wall_seconds_including_imports":time.monotonic()-started,"peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        raise
    finally:
        signal.alarm(0)
        if locked:lock.unlink()

if __name__=="__main__":main()
