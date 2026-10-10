#!/usr/bin/env python3
"""Prepare finite future postprocessing metadata; no saved outcomes are opened."""
from pathlib import Path
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[2]
TOOLS="tools/radio_saved_stages_20261010"
STAGES={
 "rolling155157":("radio_rolling_bands_20261010",[155,157],"9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a","5acdb2f9c42b5e7ce58437d30ea9527763f8f821","RADIO_ROLLING_BANDS_REPORT_2026-10-10.md","SETI_ROLLING_BANDS_RESULTS_2026-10-10.zip"),
 "native158":("radio_native158_20261010",[158],"2e3b2401d1295f0864d2a2e3f8030b5860c7352a6881e25dce81ff11a3f11c23","a8803167e7963a507454083bf116965253bfe83a","RADIO_NATIVE158_REPORT_2026-10-10.md","SETI_NATIVE158_RESULTS_2026-10-10.zip"),
}

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    started=time.process_time();out=ROOT/(TOOLS+"/POSTPROCESSING_SCOPE.json")
    if out.exists(): raise ValueError("Prospective postprocessing scope is created once only")
    configs={};pins={};sizes={}
    def pin(name,expected=None):
        path=ROOT/name;sha=digest(path)
        if expected is not None and sha!=expected: raise ValueError("Original metadata/code pin differs: "+name)
        if name in pins and pins[name]!=sha: raise ValueError("Conflicting original dependency pin")
        pins[name]=sha;sizes[name]=path.stat().st_size
        return sha
    for name in ("common_json.py","summarize_saved.py","package_saved.py","plots_saved_stages.py","png_publish.py","generate_postprocessing_scope.py","REPRODUCTION.md","SOURCE_ONLY_POSTPROCESSING_REVIEW.json"):
        pin(TOOLS+"/"+name)
    pin("tools/radio_next_bands_20261010/plots_qualified_saved.py",
        "f122449e317d90b8c08f7c259e193c014022b76c44828f470942551b39564f3c")
    for stage_id,(name,chunks,scope_sha,freeze,report,archive) in STAGES.items():
        tools="tools/"+name;results="results/"+name
        scope_path=tools+"/scope.json";pin(scope_path,scope_sha)
        scope=json.loads((ROOT/scope_path).read_bytes())
        activation=tools+"/ACTIVATION_SCOPE.json";pin(activation)
        wrapper=tools+"/native_search.py";pin(wrapper,scope["script_sha256"])
        for path,sha in scope["pinned_dependency_files"].items(): pin(path,sha)
        qa=results+"/review/qa_saved_native_batch.py";audit=results+"/review/source_cell_audit.py"
        acq_qa=results+"/review/qa_completed_acquisition.py"
        qa_sha,audit_sha=pin(qa),pin(audit);pin(acq_qa)
        jobs=[]
        for c in chunks:
            for b in (1,2):
                directory=f"{results}/chunk{c}/batch_{b:02d}/measurement"
                jobs.append({"source_chunk_id":c,"batch_id":b,"measurement_directory":directory,
                    "QA_receipt_path":directory+"/QA_RECEIPT.json","required_original_status":"COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY",
                    "required_QA_status":"PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS","fixed_batch_q":scope["immutable_metadata_selection"]["batch_q"][b-1]})
        configs[stage_id]={"source_chunk_ids":chunks,"tools_directory":tools,"results_directory":results,
            "activation_path":activation,"numerical_scope_path":scope_path,"numerical_scope_sha256":scope_sha,
            "numerical_wrapper_path":wrapper,"numerical_wrapper_sha256":scope["script_sha256"],
            "original_scientific_freeze_commit":freeze,"selection_canonical_sha256":scope["metadata_selection_canonical_SHA256"],
            "numeric_CPU_cap_s":2000,"numeric_wall_cap_s":2400,"numeric_memory_cap_bytes":4294967296,
            "local_QA_script_path":qa,"local_QA_script_sha256":qa_sha,"acquisition_QA_script_path":acq_qa,"acquisition_QA_script_sha256":pins[acq_qa],
            "source_audit_script_path":audit,"source_audit_script_sha256":audit_sha,"source_audit_receipt_path":results+"/review/SOURCE_CELL_QA_RECEIPT.json",
            "source_audit_PASS_status":f"PASS_{18*len(chunks)}_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE",
            "acquisition_QA_scope_binding_key":"common_four_batch_scope_sha256" if len(chunks)==2 else "common_two_batch_scope_sha256",
            "summary_directory":results+"/summary","summary_input_pins_path":results+"/SUMMARY_INPUT_PINS.json",
            "report_path":report,"report_title":"fast driftsøgning i native udsnit "+", ".join(map(str,chunks)),
            "archive_filename":archive,"jobs":jobs,"figures_directory":results+"/figures",
            "figure_paths":[results+"/figures/STAGE_COVERAGE.png",results+"/figures/STAGE_FIXED_PROFILE_MEANS.png"],
            "plot_receipt_path":results+"/figures/PLOTTING_RECEIPT.json",
            "plot_script_path":TOOLS+"/plots_saved_stages.py","plot_script_sha256":pins[TOOLS+"/plots_saved_stages.py"],
            "expected_complete_maps":762*len(chunks),"expected_complete_profiles":18*len(chunks),
            "expected_carrier_origin_entries":3121152*len(chunks),"expected_evaluated_hypothesis_combinations":4762877952*len(chunks),
            "summary_CPU_cap_s":40,"summary_wall_cap_s":1800,"package_CPU_cap_s":120,"package_wall_cap_s":1800,
            "plot_CPU_cap_s":60,"plot_wall_cap_s":1800,"plot_memory_cap_bytes":4294967296,
            "raw_HDF5_archives_external_only":True,"no_preflight_recovery_assumptions":True}
    data={"schema":"SETI_FINITE_ROLLING_SAVED_POSTPROCESSING_SCOPE_V1","status":"PROSPECTIVE_POSTPROCESSING_NOT_RUN",
        "mode":"ORIGINAL_COMPLETE_ONLY_SAVED_POSTPROCESSING","stage_configs":configs,
        "pinned_dependency_files":pins,"pinned_dependency_file_bytes":sizes,
        "prepared_without_opening_saved_signal_results":True,"detector_or_profile_runs":0,"new_telescope_HTTP_requests":0,
        "future_outcome_hashes_are_supplied_only_in_later_explicit_input_pins":True,
        "one_historical_visit":True,"calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,"origin_classification":False,
        "original_numeric_failure_exception_admission":False,"original_full_source_file_MD5_verified":False,
        "public_git_transport_bytepart_max_bytes":10485759,"public_freeze_and_root_GO_required_before_execution":True}
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({"path":str(out.relative_to(ROOT)),"bytes":out.stat().st_size,"sha256":digest(out),"metadata_CPU_seconds":time.process_time()-started}))

if __name__=="__main__": main()
