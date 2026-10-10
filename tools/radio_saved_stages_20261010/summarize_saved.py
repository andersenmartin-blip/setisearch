#!/usr/bin/env python3
"""Summarize one explicitly configured COMPLETE-only saved stage after root GO.

No HDF5/NPZ data is opened. Per-chunk/batch/ON rankings remain separate.
An original FAILED job is never admitted by this helper.
"""
from pathlib import Path
import argparse, hashlib, json, os, resource, signal, time
import common_json as saved

ROOT=Path(__file__).resolve().parents[2]
POST_SCOPE="tools/radio_saved_stages_20261010/POSTPROCESSING_SCOPE.json"
CPU_CAP,WALL_CAP,MEMORY_CAP=40,1800,4*1024**3
ALLOWED={
 "rolling155157":("radio_rolling_bands_20261010",(155,157),"9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a"),
 "native158":("radio_native158_20261010",(158,),"2e3b2401d1295f0864d2a2e3f8030b5860c7352a6881e25dce81ff11a3f11c23"),
}

def file_pin(path):
    raw=path.read_bytes()
    return {"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}

def configure(reader,stage_id,expected_post_sha):
    post=reader.load(POST_SCOPE)
    if reader.pins[POST_SCOPE]!=expected_post_sha or post["mode"]!="ORIGINAL_COMPLETE_ONLY_SAVED_POSTPROCESSING":
        raise ValueError("Exact prospective saved-postprocessing scope required")
    config=post["stage_configs"][stage_id]
    name,chunks,scope_sha=ALLOWED[stage_id]
    if (config["source_chunk_ids"]!=list(chunks) or config["results_directory"]!="results/"+name
            or config["tools_directory"]!="tools/"+name or config["numerical_scope_path"]!="tools/"+name+"/scope.json"
            or config["numerical_scope_sha256"]!=scope_sha or config["numeric_CPU_cap_s"]!=2000
            or config["numeric_wall_cap_s"]!=2400 or config["numeric_memory_cap_bytes"]!=MEMORY_CAP):
        raise ValueError("Prospective stage configuration changed")
    for path,sha in post["pinned_dependency_files"].items():
        p=(reader.root/path).resolve()
        if not p.is_relative_to(reader.root) or file_pin(p)["sha256"]!=sha:
            raise ValueError("Frozen postprocessing code/metadata dependency differs: "+path)
    saved.configure(config)
    return post,config,chunks

def required_inputs(config,chunks):
    names={POST_SCOPE,config["activation_path"],config["numerical_scope_path"],config["source_audit_receipt_path"]}
    stage=config["results_directory"]
    for c in chunks:
        names.update((f"{stage}/chunk{c}/arrays/ACQUISITION_RESULT.json",f"{stage}/chunk{c}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json"))
        for b in (1,2):
            prefix=f"{stage}/chunk{c}/batch_{b:02d}/measurement/"
            names.update(prefix+n for n in ("INPUT_PINS.json","DRIFT_CHECKPOINT.json","DRIFT_TOP20.json",
                         "FIXED_TOP3_PROFILES.json","NORMALIZATION.json","EXECUTION_RECEIPT.json","QA_RECEIPT.json"))
    if len(names)!=4+16*len(chunks):
        raise ValueError("Internal finite saved-input index changed")
    return names

def geometry(activation,scope,config,chunks):
    selection=scope["immutable_metadata_selection"]
    canonical=(json.dumps(selection,sort_keys=True,separators=(",",":"))+"\n").encode()
    batches=2*len(chunks)
    suffix="all_four_complete" if len(chunks)==2 else "both_complete"
    if (saved.sha256(canonical)!=config["selection_canonical_sha256"]
            or scope["metadata_selection_canonical_SHA256"]!=config["selection_canonical_sha256"]
            or activation["immutable_metadata_selection"]!=selection
            or activation["metadata_selection_canonical_SHA256"]!=config["selection_canonical_sha256"]
            or selection["native_chunk_indices"]!=list(chunks)
            or selection["physical_chunk_intervals_half_open"]!=[[c*1048576,(c+1)*1048576] for c in chunks]
            or selection["full_safe_q_ascending"]!=list(range(1,255))
            or selection["batch_q"]!=[list(range(1,128)),list(range(128,255))]
            or selection["core_channels"]!=4096 or selection["read_halo_channels"]!=4000
            or selection["scan_order"]!=list(saved.SCANS) or selection["widths_channels"]!=[1,3]
            or scope["source_chunk_ids"]!=list(chunks) or scope["source_chunk_channel_count"]!=1048576
            or scope["expected_scan_tiles_per_batch"]!=381 or scope["valid_hypotheses_per_carrier"]!=1526
            or scope["widths_channels"]!=[1,3] or scope["drift_grid"]!={"first_hz_s":-4,"last_hz_s":4,"count":763}
            or scope["expected_total_scan_tiles_if_"+suffix]!=381*batches
            or scope["expected_total_ON_carrier_origin_entries_if_"+suffix]!=1560576*batches
            or scope["expected_total_hypothesis_entries_if_"+suffix]!=2381438976*batches
            or scope["expected_total_profiles_if_"+suffix]!=9*batches
            or scope["CPU_cap_s_per_batch"]!=2000 or scope["wall_cap_s_per_batch"]!=2400
            or scope["memory_cap_bytes_per_batch"]!=MEMORY_CAP):
        raise ValueError("Original prospective numeric geometry/counts/resources changed")
    return selection

def source_audit(reader,scope,config,profiles,chunks):
    path=config["source_audit_receipt_path"]
    qa=reader.load(path)
    n=len(profiles)
    counts={"compact_files":6*len(chunks),"decoded_rows":96*len(chunks),"patches":n,
            "scan_profiles":6*n,"time_rows":96*n,"raw_cells_bitwise_checked":12384*n}
    if (qa["status"]!=config["source_audit_PASS_status"] or qa["counts"]!=counts
            or qa["freeze_commit"]!=config["original_scientific_freeze_commit"]
            or qa["public_scope_sha256"]!=config["numerical_scope_sha256"]
            or qa["public_wrapper_sha256"]!=scope["script_sha256"]
            or qa["audit_script_sha256"]!=config["source_audit_script_sha256"]
            or qa["profile_identity_fields"]!=["source_chunk_id","batch_id","track_id"]):
        raise ValueError("Actual pinned complete source-cell QA required")
    checks={(c["source_chunk_id"],c["batch_id"],c["track_id"]):c for c in qa["patch_checks"]}
    if len(qa["patch_checks"])!=n or len(checks)!=n or set(checks)!={tuple(p["identity"]) for p in profiles}:
        raise ValueError("Source-cell QA composite profile identities differ")
    for p in profiles:
        c=checks[tuple(p["identity"])]
        prefix=f'{config["results_directory"]}/chunk{p["source_chunk_id"]}/batch_{p["batch_id"]:02d}/measurement/'
        if (c["bitwise_identical"] is not True or c["raw_cells"]!=12384
                or c["patch_sha256"]!=p["patch_provenance"]["sha256"]
                or c["raw_cell_bytes_SHA256"]!=c["independent_source_cell_bytes_SHA256"]
                or c["source_execution_receipt_sha256"]!=reader.pins[prefix+"EXECUTION_RECEIPT.json"]
                or c["source_profiles_JSON_sha256"]!=reader.pins[prefix+"FIXED_TOP3_PROFILES.json"]):
            raise ValueError("Raw source audit differs from unchanged selected patch provenance")
    return {"status":qa["status"],"receipt_path":path,"receipt_sha256":reader.pins[path],
            "counts":counts,"audit_script_sha256":qa["audit_script_sha256"],"original_full_source_MD5_verified":False}

def render_report(summary,config):
    n=saved.number
    lines=["# SETI: "+config["report_title"],"","**10. oktober 2026.** Alle de fastlåste numeriske grupper sluttede COMPLETE én gang og har bestået de krævede kontroller af gemte outputs og kildeceller.",
      f'Der er gemt {summary["completed_scan_tiles"]:,} ON-felter og {summary["profile_count"]} faste top-3-profiler.'.replace(",","."),"",
      "Alle seks scanninger er fra ét historisk besøg den 17. marts 2016. Ranglisterne forbliver separate pr. native udsnit, gruppe og ON-scanning; profilidentiteten er (source_chunk_id, batch_id, track_id). Antallet af udvalgte spor er ikke antallet af uafhængige fysiske signaler.","",
      f'{summary["ON_carrier_origin_entries"]:,} ON-referencekanal/originkombinationer er evalueret med 1.526 gyldige drift/breddehypoteser hver: {summary["evaluated_hypothesis_combinations"]:,} hypotesekombinationer.'.replace(",","."),
      "For hver referencekanal gemmes maksimumscore og vindende drift/bredde med verificeret hypoteseantal. Dækningen er 254/256 referencefelter (99,21875 %) i hvert af disse udsnit, alene for de 763 drifthastigheder fra −4 til +4 Hz/s og bredde 1/3. De to randfelter er usøgte; haloer er ikke yderligere carrier-dækning eller uafhængige forsøg.","",
      f'En særskilt kildecellekontrol matcher {summary["joint_source_cell_QA"]["counts"]["raw_cells_bitwise_checked"]:,} råcelleforekomster i {summary["profile_count"]} udklip bit for bit mod de kompakte kilder.'.replace(",","."),
      "Overlap mellem udklip kan gentage fysiske celler. Kompakt- og rækkehashes erstatter ikke de store originale HDF5-kilders fulde MD5, som fortsat ikke er verificeret.","",
      "| Udsnit | Gruppe | Felter | Profiler | CPU-sekunder | Vægtid, sekunder | Maksimal RSS, bytes |","| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for b in summary["batches"]:
        r=b["execution_resources"]
        lines.append(f'| {b["source_chunk_id"]} | {b["batch_id"]} | {b["completed_scan_tiles"]} | {b["profile_count"]} | {n(r["process_CPU_seconds_including_imports"],3)} | {n(r["wall_seconds_including_imports"],3)} | {r["peak_RSS_bytes"]} |')
    lines += ["","Den oprindelige grænse er 2.000 CPU-sekunder, 2.400 sekunders vægtid og 4 GiB RAM pr. numerisk gruppe. Arbejdsallokeringer er planlægning, ikke en abonnementsbalance eller global stopgrænse. Der bruges ingen betalte ressourcer eller nye teleskopbytes i opsummeringen.","",
      "| Udsnit | Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |","| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for p in summary["profiles"]:
        before=p["adjacent_preceding_OFF"]
        lines.append(f'| {p["source_chunk_id"]} | {p["batch_id"]} | {saved.SHORT[p["originating_scan"]]}/{p["display_rank_within_batch_and_ON"]} | {n(p["reference_frequency_hz"]/1e6)} | {n(p["drift_hz_s"])} | {p["width_channels"]} | {n(p["origin_ON"]["mean_center_minus_flank"])} | {n(before["mean_center_minus_flank"] if before else None)} | {n(p["adjacent_following_OFF"]["mean_center_minus_flank"])} |')
    lines += ["","Tabellen viser gemte middelresidualer af normaliseret centereffekt minus de bevægelige flankkanalers median inden for ±64 kanaler med absolut offset større end tre. Detektorens robuste rangscore er en anden størrelse end denne profilmiddelresidual. Alle seks uændrede spor bevares i JSON/CSV. ON1 har kun efterfølgende OFF i sekvensen; ON2/ON3 har både forudgående og efterfølgende OFF.",
      "En lille residual på det præcise OFF-spor fastslår ikke fravær af nærliggende OFF-struktur. Profilerne er udvalgt efter ON-rangscore og forbliver uafklarede. Ingen OFF-forskydning, ny score, rangliste eller profil genberegnes af opsummeringen.","",
      "A/B forbliver FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts samt beskyttede udsnit 156/159 er lukkede. Der er ikke beregnet kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed. Der fastslås ingen signaloprindelse, kvalificeret SETI-kandidat, generelt nulresultat eller uafhængighed mellem hypoteser, spor, udsnit eller scanninger.",
      f'Original kode/scope blev fastlåst ved `{config["original_scientific_freeze_commit"]}` med scope-SHA256 `{config["numerical_scope_sha256"]}` før de nye kildeværdier. Dette skaber ikke en uafhængig besøgsobservation. Den senere gemte-JSON-opsummering er bundet til postprocesseringsscope `{summary["postprocessing_scope_sha256"]}` ved `{summary["public_postprocessing_freeze_commit"]}` og kvitterer for alle input- og outputhashes.',"",
      f'[Dækningsfigur]({config["figure_paths"][0]}) · [Faste profilmidler]({config["figure_paths"][1]})',""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",default=str(ROOT));p.add_argument("--stage-id",choices=sorted(ALLOWED),required=True)
    p.add_argument("--pins",required=True);p.add_argument("--expected-postprocessing-scope-sha256",required=True)
    p.add_argument("--postprocessing-freeze-commit",required=True)
    p.add_argument("--root-authorized-summary-read",action="store_true")
    a=p.parse_args()
    if not a.root_authorized_summary_read: raise SystemExit("Root GO required before result reads")
    if len(a.postprocessing_freeze_commit)!=40 or any(c not in "0123456789abcdef" for c in a.postprocessing_freeze_commit):
        raise ValueError("Exact public postprocessing freeze commit required")
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    def deadline(sig,frame): raise TimeoutError("Saved summary cap exceeded")
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.alarm(WALL_CAP)
    root=Path(a.root).resolve();reader=saved.PinnedJSON(root,Path(a.pins))
    post,config,chunks=configure(reader,a.stage_id,a.expected_postprocessing_scope_sha256)
    required=required_inputs(config,chunks)
    if set(reader.pins)!=required: raise ValueError("Exact finite saved-input index required")
    activation,scope=reader.load(config["activation_path"]),reader.load(config["numerical_scope_path"])
    if reader.pins[config["numerical_scope_path"]]!=config["numerical_scope_sha256"]: raise ValueError("Numeric scope differs")
    selection=geometry(activation,scope,config,chunks)
    acquisitions={str(c):saved.acquisition_metadata(reader,scope,c) for c in chunks}
    batches=[saved.load_batch(reader,scope,c,b,selection,acquisitions[str(c)]) for c in chunks for b in (1,2)]
    for b in batches:
        prefix=f'{config["results_directory"]}/chunk{b["source_chunk_id"]}/batch_{b["batch_id"]:02d}/measurement/'
        reader.load(prefix+"NORMALIZATION.json")
        execution=reader.load(prefix+"EXECUTION_RECEIPT.json")
        qa=reader.load(prefix+"QA_RECEIPT.json")
        if (not b["execution_complete"] or b["profile_count"]!=9 or b["QA_status"]!="PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
                or execution["saved_normalization_sha256"]!=reader.pins[prefix+"NORMALIZATION.json"]
                or qa["qa_script_sha256"]!=config["local_QA_script_sha256"]):
            raise ValueError("Original COMPLETE and actual matching output QA required for every group")
    if any(a["acquisition_source_QA_status"]!="PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS" for a in acquisitions.values()):
        raise ValueError("All actual acquisition source QAs required")
    profiles=[p for b in batches for p in b["profiles"]]
    if len(profiles)!=18*len(chunks) or len({tuple(p["identity"]) for p in profiles})!=len(profiles): raise ValueError("Profile triple identities differ")
    audit=source_audit(reader,scope,config,profiles,chunks)
    coverage={str(c):{"by_ON":{s:{"completed_q":list(range(1,255)),"completed_core_count":254,"completed_reference_channels":254*4096,"completed_fraction":254/256} for s in saved.ONS}} for c in chunks}
    tiles=381*len(batches);entries=tiles*4096
    summary={"schema":"SETI_CONFIGURED_ORIGINAL_COMPLETE_SAVED_SUMMARY_V1","status":"COMPLETE_AUDITED_SAVED_STAGE",
      "stage_id":a.stage_id,"source_chunk_ids":list(chunks),"fully_audited_summary_complete":True,
      "all_original_numeric_executions_COMPLETE":True,"original_execution_statuses_rewritten":False,
      "completed_scan_tiles":tiles,"profile_count":len(profiles),"ON_carrier_origin_entries":entries,
      "evaluated_hypothesis_combinations":entries*1526,"coverage":{"by_chunk":coverage},"batches":batches,"profiles":profiles,
      "profile_identity_fields":["source_chunk_id","batch_id","track_id"],"batch_rankings_separate_no_global_reranking":True,
      "acquisition_metadata":acquisitions,"joint_source_cell_QA":audit,
      "public_code_freeze_commit":config["original_scientific_freeze_commit"],"common_execution_scope_sha256":config["numerical_scope_sha256"],
      "postprocessing_scope_sha256":reader.pins[POST_SCOPE],"metadata_selection_canonical_SHA256":config["selection_canonical_sha256"],
      "public_postprocessing_freeze_commit":a.postprocessing_freeze_commit,
      "one_historical_visit":True,"visit_date":"2016-03-17","calibrated_SNR_FAP_flux_EIRP_or_sensitivity":False,
      "OFF_veto":False,"origin_classification":False,"qualified_sky_pilot":False,"independent_trials_claim":False,
      "general_null_result_claim":False,"A_B":"FAIL_CLOSED_UNCHANGED","old_holdouts_reopened":False,
      "original_full_source_file_MD5_verified":False,"new_telescope_HTTP_requests":0,"new_telescope_BODY_bytes":0}
    if set(reader.opened)!=required: raise ValueError("All required pinned JSONs must be bound")
    reader.unchanged()
    out=root/config["summary_directory"];report=root/config["report_path"]
    if not out.resolve().is_relative_to(root) or not report.resolve().is_relative_to(root): raise ValueError("Project output paths required")
    out.mkdir(parents=True,exist_ok=False)
    saved.dump_json(out/"SAVED_SUMMARY.json",summary);saved.write_csv(out/"PROFILE_SUMMARY.csv",profiles);report.write_text(render_report(summary,config))
    reader.unchanged()
    measured={"process_CPU_seconds_including_imports":time.process_time(),"wall_seconds_including_imports":time.monotonic()-started,
              "peak_RSS_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    if measured["process_CPU_seconds_including_imports"]>CPU_CAP or measured["wall_seconds_including_imports"]>WALL_CAP or measured["peak_RSS_bytes"]>MEMORY_CAP: raise TimeoutError("Measured summary cap exceeded")
    receipt={"status":"PASS_PINNED_COMPLETE_ONLY_JSON_SUMMARY_NO_NUMERIC_RERUN","stage_id":a.stage_id,
      "script_sha256":file_pin(Path(__file__))["sha256"],"input_pins_sha256":reader.pins_sha,"opened_inputs":reader.opened,
      "postprocessing_scope_sha256":reader.pins[POST_SCOPE],"output_hashes":{str(q.relative_to(root)):file_pin(q)["sha256"] for q in (out/"SAVED_SUMMARY.json",out/"PROFILE_SUMMARY.csv",report)},
      "public_postprocessing_freeze_commit":a.postprocessing_freeze_commit,
      "HDF5_or_NPZ_opened":False,"detector_rerun":False,"global_reranking":False,"original_statuses_rewritten":False,**measured}
    saved.dump_json(out/"SUMMARY_EXECUTION_RECEIPT.json",receipt);signal.alarm(0)
    print(json.dumps({"status":receipt["status"],"stage_id":a.stage_id,"profiles":len(profiles),"tiles":tiles,**measured}))

if __name__=="__main__": main()
