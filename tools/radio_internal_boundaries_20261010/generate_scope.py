"""Prepare final joined-boundary scope from source/receipt metadata only.

No NumPy, HDF5, observation arrays, candidate JSON, searches or synthetic
geometry algorithms are imported or executed. Run after all helper sources
are final and independently source reviewed, before public freeze.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[2]
TOOLS="tools/radio_internal_boundaries_20261010"
RESULTS="results/radio_internal_boundaries_20261010"
SCANS=["epoch1_on","epoch1_off","epoch2_on","epoch2_off","epoch3_on","epoch3_off"]
CHUNKS=[153,154,155,157,158]
PAIRS=[(153,154),(154,155),(157,158)]
N=1048576
SCRIPT=TOOLS+"/boundary_search.py"
QA=TOOLS+"/qa_saved.py"
AUDIT=TOOLS+"/source_cell_audit.py"
SUMMARY=TOOLS+"/summarize_saved.py"
PACKAGE=TOOLS+"/package_saved.py"
ACTIVATION=TOOLS+"/ACTIVATION_SCOPE.json"
ACTIVATION_SHA="2dfaf1f5da871b0ab4d0e773b44805a84d3bbf004062d61b07ab8daa3ca45a9d"
SELECTION_SHA="3b447a80d662289fef3e5d4574a2f725808c2952db768814462e407bb56bc36b"
METHOD="median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)"
VERSIONS={"numpy":"2.3.5","scipy":"1.17.0","matplotlib":"3.10.8","h5py":"3.15.1","hdf5plugin":"7.1.0"}
METHOD_PINS={
    "tools/radio_fresh_band_20261009/source_manifest.json":"d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c",
    "tools/radio_fresh_band_20261009/fresh_search.py":"1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102",
    "pilot_engine_20261008/detector.py":"1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45",
    "tools/radio_gap_drift_20261010/gap_search.py":"b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58"}
ORIGINAL_NUMERIC={
    "radio_next_bands_20261010":("60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4","f189abc0a27503cbf2a35b1c63626ef2d3847728894a0a4fcfce9b16da36800b"),
    "radio_rolling_bands_20261010":("9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a","eeb7e59b899401b010f664cce849ce5af199aa9c4d065bdfd7a0efb72fea57cf"),
    "radio_native158_20261010":("2e3b2401d1295f0864d2a2e3f8030b5860c7352a6881e25dce81ff11a3f11c23","b555254fe3ae14d1ad09169ce79060eae1cbb1b26406ea36a7093c452b288beb")}


def confined(name):
    p=Path(name)
    if p.is_absolute() or ".." in p.parts or not (ROOT/p).resolve().is_relative_to(ROOT):
        raise ValueError("Need root-relative confined metadata paths")
    return ROOT/p


def pin(name):
    b=confined(name).read_bytes()
    return {"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)}


def load(name):return json.loads(confined(name).read_text())


def main():
    cpu=time.process_time();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default=str(ROOT/TOOLS/"scope.json"));args=parser.parse_args()
    output=Path(args.output).resolve()
    if output!=ROOT/TOOLS/"scope.json" or output.exists():raise ValueError("One final fixed scope generation; preserve existing bytes")
    act=load(ACTIVATION)
    if pin(ACTIVATION)["sha256"]!=ACTIVATION_SHA:raise ValueError("Prospective activation changed")
    selection=act["immutable_metadata_selection"]
    canonical=(json.dumps(selection,sort_keys=True,separators=(",",":"))+"\n").encode()
    if hashlib.sha256(canonical).hexdigest()!=SELECTION_SHA:raise ValueError("All three pair selections must be fixed together")
    if (selection["native_pairs"]!=[list(p) for p in PAIRS] or selection["joined_reference_core_q"]!=[255,256]
        or selection["native_channel_count"]!=N or selection["joined_channel_count"]!=2*N
        or not act["zero_cost_continuation_authorized"] or act["numeric_CPU_cap_s_per_pair"]!=120
        or act["stage_CPU_planning_allocation_s"]!=600 or not act["source_values_previously_acquired_and_exposed"]):
        raise ValueError("New family/finite resource authorization differs")
    pinned={}
    required=[SCRIPT,QA,AUDIT,SUMMARY,PACKAGE,TOOLS+"/REPRODUCTION.md",TOOLS+"/generate_scope.py",
        TOOLS+"/SUMMARY_PACKAGE_SOURCE_REVIEW.json",
        TOOLS+"/QA_SOURCE_AUDIT_INDEPENDENT_SOURCE_REVIEW.json",
        TOOLS+"/RESOURCE_HARDENING_METADATA_RECEIPT.json",
        TOOLS+"/FEASIBILITY.md",TOOLS+"/FEASIBILITY_METADATA_RECEIPT.json",ACTIVATION,
        TOOLS+"/analysis_inputs.json",RESULTS+"/PUBLIC_RESOURCE_LEDGER.json",
        "tools/radio_fresh_band_20261009/source_manifest.json","tools/radio_fresh_band_20261009/fresh_search.py",
        "tools/radio_gap_drift_20261010/gap_search.py","pilot_engine_20261008/detector.py",
        "results/radio_full_safe_20261010/ENVIRONMENT_RESTORATION.json"]
    for name in required:pinned[name]=pin(name)
    if any(pinned[name]["sha256"]!=sha for name,sha in METHOD_PINS.items()):
        raise ValueError("Frozen original source/numerical method identity changed")
    for name in (SCRIPT,QA,AUDIT,SUMMARY,PACKAGE,TOOLS+"/generate_scope.py"):
        ast.parse(confined(name).read_text())
    historical=load("tools/radio_fresh_band_20261009/source_manifest.json")
    inputs=load(TOOLS+"/analysis_inputs.json")
    if set(inputs)!={str(c) for c in CHUNKS}:raise ValueError("Need exactly five retained native chunk contracts")
    chunk_contracts={};sources={}
    for chunk in CHUNKS:
        c=dict(inputs[str(chunk)])
        if set(c)!={"source_manifest_path","acquisition_script_path","acquisition_scope_path","compact_directory",
                   "acquisition_summary_path","acquisition_QA_path","original_numeric_scope_path","original_numeric_script_path"}:
            raise ValueError("Unexpected metadata context keys")
        for key,name in tuple(c.items()):
            confined(name)
            if key.endswith("_path"):
                p=pin(name);pinned[name]=p;c[key[:-5]+"_sha256"]=p["sha256"]
        namespace=Path(c["original_numeric_scope_path"]).parent.name
        if (c["original_numeric_scope_sha256"],c["original_numeric_script_sha256"])!=ORIGINAL_NUMERIC[namespace]:
            raise ValueError("Original native-family code/scope identity changed")
        s=load(c["source_manifest_path"]);a=load(c["acquisition_summary_path"]);q=load(c["acquisition_QA_path"])
        acqscope=load(c["acquisition_scope_path"])
        if (s["native_chunk_index"]!=chunk or s["physical_channel_interval_half_open"]!=[chunk*N,(chunk+1)*N]
            or [x["label"] for x in s["sources"]]!=SCANS or [x["role"].upper() for x in s["sources"]]!=["ON","OFF"]*3
            or a["status"]!="COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
            or a["source_manifest_sha256"]!=c["source_manifest_sha256"] or a["script_sha256"]!=c["acquisition_script_sha256"]
            or a["scope_sha256"]!=c["acquisition_scope_sha256"] or a["source_channel0"]!=chunk*N
            or a["physical_channel_interval_half_open"]!=s["physical_channel_interval_half_open"]
            or q["status"]!="PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
            or q["source_chunk_id"]!=chunk
            or q["source_manifest_sha256"]!=c["source_manifest_sha256"] or q["acquisition_result_sha256"]!=c["acquisition_summary_sha256"]
            or q["counts"]!={"source_requests":96,"compact_files":6,"retained_compressed_chunks":96,
                              "decoded_rows":96,"decoded_values_authenticated":100663296}
            or acqscope["native_chunk_index"]!=chunk or acqscope["source_manifest"]!=c["source_manifest_path"]
            or acqscope["output_directory"]!=c["compact_directory"]):raise ValueError("Native acquisition identity/status differs")
        for name,sha in acqscope["pinned_files"].items():
            p=pin(name)
            if p["sha256"]!=sha or (name in pinned and p!=pinned[name]):raise ValueError("Acquisition dependency differs")
            pinned[name]=p
        for item,old in zip(s["sources"],historical["sources"]):
            if any(item[k]!=old[k] for k in ("label","role","url","etag","source_file_bytes","current_header")):
                raise ValueError("Same historical six source headers required")
            rows=item["chunks"]
            if (len(rows)!=16 or [x["time_row"] for x in rows]!=list(range(16))
                or any(x["chunk_origin"]!=[i,0,chunk*N] or x["decoded_size"]!=4*N or x["filter_mask"]!=0
                       or x["stored_size"]<=0 or x["byte_offset"]<0 or x["byte_offset"]+x["stored_size"]>item["source_file_bytes"]
                       or x["byte_range"]!=f"bytes={x['byte_offset']}-{x['byte_offset']+x['stored_size']-1}"
                       for i,x in enumerate(rows))):raise ValueError("Need exact source range descriptors")
        files=a["decoded_files"]
        if len(files)!=6 or len({x["scan_id"] for x in files})!=6 or {x["scan_id"] for x in files}!=set(SCANS):
            raise ValueError("Exactly six unique compact metadata identities required")
        qfiles={x["scan_id"]:x for x in q["files"]}
        for f in files:
            if (f["source_channel0"]!=chunk*N or f["shape"]!=[16,1,N] or f["bytes"]<=0
                or len(f["decoded_rows"])!=16 or [x["time_row"] for x in f["decoded_rows"]]!=list(range(16))
                or any(x["decoded_bytes"]!=4*N or len(x["decoded_sha256"])!=64 for x in f["decoded_rows"])
                or qfiles[f["scan_id"]]["file_sha256"]!=f["file_sha256"] or qfiles[f["scan_id"]]["bytes"]!=f["bytes"]):
                raise ValueError("All original compact/row metadata pins required")
        c.update(source_channel_interval_half_open=[chunk*N,(chunk+1)*N],
            compact_files_and_96_decoded_row_pins=files)
        chunk_contracts[str(chunk)]=c;sources[chunk]=s
    pairs={}
    for left,right in PAIRS:
        ls,rs=sources[left],sources[right]
        if ls["physical_channel_interval_half_open"][1]!=rs["physical_channel_interval_half_open"][0]:raise ValueError("Pair not adjacent")
        if any(any(l[k]!=r[k] for k in ("label","role","url","etag","source_file_bytes","current_header"))
               for l,r in zip(ls["sources"],rs["sources"])):raise ValueError("Six paired headers/source identities differ")
        pid=f"pair{left}_{right}";directory=f"{RESULTS}/{pid}/measurement"
        pairs[pid]={"source_chunk_ids":[left,right],"source_channel0":left*N,"source_channel_count":2*N,
            "physical_channel_interval_half_open":[left*N,(right+1)*N],"joined_reference_core_q":[255,256],
            "original_native_reference_cores":[{"source_chunk_id":left,"source_native_core_q":255},{"source_chunk_id":right,"source_native_core_q":0}],
            "reference_channel_intervals_half_open":[[right*N-4096,right*N],[right*N,right*N+4096]],
            "measurement_directory":directory,"QA_receipt_path":f"{RESULTS}/{pid}/review/QA_RECEIPT.json",
            "QA_required_status":"PASS_COMPLETE_SAVED_JOINED_BOUNDARY_OUTPUTS",
            "execution_required_status":"COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY",
            "expected_scan_tiles":6,"expected_profile_count":9}
    qa158="results/radio_native158_20261010/review/qa_saved_native_batch.py"
    audit158="results/radio_native158_20261010/review/source_cell_audit.py"
    pinned[qa158]=pin(qa158);pinned[audit158]=pin(audit158)
    gate={"original_scope_sha256":chunk_contracts['158']["original_numeric_scope_sha256"],
        "original_script_sha256":chunk_contracts['158']["original_numeric_script_sha256"],
        "saved_QA_script_sha256":pinned[qa158]["sha256"],"source_audit_script_sha256":pinned[audit158]["sha256"],
        "source_audit_receipt_path":"results/radio_native158_20261010/review/SOURCE_CELL_QA_RECEIPT.json",
        "jobs":[{"batch_id":b,"execution_receipt_path":f"results/radio_native158_20261010/chunk158/batch_{b:02d}/measurement/EXECUTION_RECEIPT.json",
            "QA_receipt_path":f"results/radio_native158_20261010/chunk158/batch_{b:02d}/measurement/QA_RECEIPT.json"} for b in (1,2)],
        "late_receipt_binding":"Read each exact metadata byte sequence once; derive admitted JSON/SHA/bytes from it before source access; INPUT_PINS saves these identities; final readback required"}
    scope={"schema":"SETI_THREE_JOINED_INTERNAL_BOUNDARY_PAIRS_V1","script_path":SCRIPT,"script_sha256":pinned[SCRIPT]["sha256"],
        "scope_generator_sha256":pin(TOOLS+"/generate_scope.py")["sha256"],"qa_script_path":QA,"qa_script_sha256":pinned[QA]["sha256"],
        "source_audit_script_path":AUDIT,"source_audit_script_sha256":pinned[AUDIT]["sha256"],
        "summary_script_path":SUMMARY,"summary_script_sha256":pinned[SUMMARY]["sha256"],
        "package_script_path":PACKAGE,"package_script_sha256":pinned[PACKAGE]["sha256"],
        "activation_path":ACTIVATION,"activation_sha256":ACTIVATION_SHA,"metadata_selection_canonical_SHA256":SELECTION_SHA,
        "immutable_metadata_selection":selection,"native_pairs":[list(p) for p in PAIRS],"pair_ids":list(pairs),
        "native_channel_count":N,"joined_channel_count":2*N,"joined_reference_core_q":[255,256],
        "rows_per_scan":16,"scan_order":SCANS,"origin_scan_order":SCANS[::2],"fch1_hz":1876464843.75,
        "df_hz":-2.835503418452676,"tsamp_s":17.986224128,"core_channel_count":4096,"crop_halo_channels":4000,
        "expected_scan_tiles_per_pair":6,"carriers_per_ON_per_pair":8192,"drift_grid":{"first_hz_s":-4,"last_hz_s":4,"count":763},
        "widths_channels":[1,3],"valid_hypotheses_per_carrier":1526,"rank_count_per_ON_per_pair":20,"display_suppression_channels":3,
        "expected_profile_count_per_pair":9,"profile_halfwidth_channels":64,"fixed_profile_shift_channels":0,
        "joined_profile_normalization_method":METHOD,"legacy_patch_normalization_field_semantics":"saved_full_chunk_row_medians is joined-pair median, not either old native median",
        "CPU_cap_s_per_pair":120,"wall_cap_s_per_pair":1800,"memory_cap_bytes_per_pair":4*1024**3,
        "saved_QA_CPU_cap_s_per_pair":20,"saved_QA_wall_cap_s_per_pair":300,"saved_QA_memory_cap_bytes_per_pair":2*1024**3,
        "source_audit_CPU_cap_s":60,"source_audit_wall_cap_s":300,"source_audit_memory_cap_bytes":4*1024**3,
        "summary_CPU_cap_s":20,"summary_wall_cap_s":1800,"summary_memory_cap_bytes":2*1024**3,
        "package_CPU_cap_s":40,"package_wall_cap_s":1800,"package_memory_cap_bytes":4*1024**3,
        "package_workspace_cap_bytes":8*1024**3,
        "stage_CPU_planning_allocation_s":600,"stage_numeric_reserved_CPU_s":360,
        "stage_prep_QA_package_CPU_s":{"preparation":60,"QA":120,"packaging_publication":60},
        "aggregate_active_memory_cap_bytes":4*1024**3,"active_workspace_cap_bytes":8*1024**3,"numeric_pairs_serial":True,
        "analysis_attempts_per_pair":1,"numeric_retry_authorized":False,"old_holdouts_reopened":False,
        "protected_old_native_chunks_not_read":[156,159],"original_scopes_terminal_statuses_and_outputs_modified":False,
        "OFF_veto":False,"blind_or_independent_validation":False,"calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,
        "runtime_package_versions":VERSIONS,"new_HTTP_requests":0,"new_BODY_bytes":0,"cost_DKK":0,
        "pinned_dependency_files":pinned,"chunk_contracts":chunk_contracts,"pair_contracts":pairs,"runtime_158_admission":gate,
        "output_directories":[p["measurement_directory"] for p in pairs.values()],
        "source_audit_receipt_path":RESULTS+"/review/SOURCE_CELL_QA_RECEIPT.json",
        "source_audit_required_status":"PASS_27_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE",
        "source_audit_policy":"each of30 unique native compacts decoded once;480 unique row hashes checked;36file/576row provenance occurrences retained;27patch334368raw-cell occurrences verified",
        "expected_counts_if_complete":{"maps":18,"tile_normalization_JSONs":18,"carrier_ON_entries":73728,"hypothesis_combinations":112508928,
            "top20_records":180,"profiles":27,"scan_profiles":162,"time_rows":2592,"raw_patch_cell_occurrences":334368,
            "unique_compact_files":30,"unique_decoded_rows":480,"compact_file_input_occurrences":36,"decoded_row_input_occurrences":576},
        "profile_identity_fields":["pair_id","track_id"],"ranking":"Each pair/ON only: original lexsort(-robust_score,absolutechannel),greedy separation>3 across both boundary cores; no cross-pair/old-family ranking",
        "detector":"Pinned detector.search_scan, raw joinedfloat32 input, original core4096 preprocessing/501filter,763drifts,width1/3,absolute-source np.rint and strict tieupdates unchanged",
        "compact_loader":"Call pinned fresh.load_power separately per nativechunk/label; nativeCOUNT1Mi andC0 validate exactsourceattrs,fileSHA,all96rowSHA/chunk; preallocated joinedfloat32 buffer, no prescaling",
        "profile_function":"Pinned old gap.fixed_profiles arithmetic; onlyjoinedC0/COUNT2Mi andisolatednormalizationpath rebound; exact selectedzero-shift frequencies/drifts/widths, all6scans16rows129channels",
        "original254_coverage_union_claim":"Conditional on verified savedcoverage of all254 originalfields AND successful new boundaryfamily; originalscopes/statuses neverrewritten",
        "future_original158_receipts_required_only_for_pair157_158":True,
        "source_values_exposed_before_this_new_family":True,"one_historical_visit":True,
        "limitations":["New referencehypotheses on already exposed2016-03-17 onevisit data;notblindorindependentvalidation",
            "Originalq1..254 rankings/statuses/arrays immutable;newq255/q256 families separate, nooldrescore",
            "Joined2Mi profilemedian differsfromoldnative normalization; no score/mean calibration or direct residualequivalence claim",
            "Pairs share controls and154sourcevalues;correlated hypotheses/profiles/celloccurrences, not independentphysicalsignals",
            "ONselectionconditional;ON/OFFnotexchangeable null;small movingOFFresidual doesnot exclude nearby stationaryOFFstructure",
            "No OFFveto,sky/origin/RFIclassification,calibratedSNR/FAP/flux/EIRP/sensitivity,generalnullorqualifiedcandidate",
            "No sourceGET/body,protected156/159orotherunretainedneighbors;wholeoriginalsourceMD5stillunverified",
            "Unioncoverage claims conditional on originalsaved254 coverage verification plus complete newfamily;onlyfixed763drifts,width1/3",
            "Finiteonceonly120CPU/pair cap mayleavepartial;preservecheckpoints/failure receipts;no numericretry"]}
    for name,p in pinned.items():
        if pin(name)!=p:raise ValueError("Metadata/helper changed during scope generation")
    with output.open("x") as handle:
        handle.write(json.dumps(scope,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"scope_sha256":pin(TOOLS+"/scope.json")["sha256"],"script_sha256":scope["script_sha256"],
        "scope_generator_sha256":scope["scope_generator_sha256"],"metadata_generation_CPU_s":time.process_time()-cpu}))

if __name__=="__main__":main()
