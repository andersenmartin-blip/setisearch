"""Close the exact completed C033 diagnostic and preserve the next public handoff."""
from pathlib import Path
import copy, datetime, hashlib, json

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
PREV=ROOT/'work_harps_20261105_c031_context'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    assert not(PHASE/'GROUP_CLOSURE.json').exists(),'Preserve completed delivery'
    prior_path=PREV/'PUBLIC_CONTINUATION_STATE.json';prior=read(prior_path)
    plan=read(HERE/'PLAN.json');summary=read(HERE/'results/SUMMARY.json');qa=read(HERE/'RESULTS_QA.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');publication=read(PHASE/'PROSPECTIVE_PUBLICATION_RECEIPT.json');nextmeta=read(PHASE/'scientific_review/NEXT_GROUP_METADATA.json')
    assert all(sha(ROOT/p)==h for p,h in prior['source_hashes'].items())
    assert all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items())
    assert all(sha(HERE/'results'/p)==h for p,h in read(HERE/'results/OUTPUT_HASHES.json').items())
    assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT'and audit['checks_passed']==791 and audit['scalar_values_compared']==110049
    assert publication['files_verified']==25 and publication['all_exact']and publication['observed_arrays_read']==0
    assert nextmeta['core_overlap_group']=='C034'and nextmeta['queue_rows'][0]['queue_index']=='73'and nextmeta['events']==['V2E2-0271']
    assert nextmeta['selected_before_current_observed_values']and nextmeta['proposed_anchor_dp_id']=='ADP.2025-05-30T01:00:44.357'
    assert nextmeta['proposed_anchor_berv_km_s']!=plan['anchor_berv_km_s']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    nextaction=copy.deepcopy(nextmeta)
    nextaction.update(created_utc=now,kind='JOINT_PROFILE_CONTEXT_C034_HD126093',primary_evidence_route='JOINT_PROFILE_CONTEXT',new_diagnostic_executed=False,current_phase_closed=str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),prior_and_next_labels_unchanged=True,reopen_completed_groups=False,standing_authorization='User directly approved publication and requested continuation in the same public SETI repository.',rubin_status='STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET',no_background_execution=True,native_scope_requirement='Restore the singleton0271 own May29 native/raw products and original event/order containers;freshly scan all72 orders. Retain its exact4312.202499999999 air Angstrom center and own negative BERV;do not transfer C033 April anchor,orders 3/4,full support,low-reference outcomes,mapping stages or 0274 caution.')
    write(PHASE/'NEXT_ACTION.json',nextaction)
    closure=dict(schema='HARPS_C033_DIAGNOSTIC_CLOSURE_V1',created_utc=now,status='COMPLETE_FIXED_JOINT_CONTEXT_ALL_U_UNCHANGED',target='HD126093',events=list(plan['events']),current_codes={e:'U'for e in plan['events']},summary=summary,numerical_audit={k:audit[k]for k in ['status','checks_passed','scalar_values_compared','profiles_reconstructed','comparisons_reconstructed','bounded_input_records_reconstructed','preserved_raw_context_files_verified']},quality_summary=qa['summary'],source_bindings_unchanged=len(plan['source_hashes']),same_physical_C031_source_ids=9,actual_shared_C031_source_index_windows=0,additional_native_product_order_sources_not_new_observations=5,source_pixel_dependency_audit_sha256=sha(PHASE/'independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json'),original_member_core_support_sha256=sha(PHASE/'independent_audit/MEMBER_CORE_SUPPORT.json'),source_pixel_independence_claim=False,common_core_covers_original_member_core_union=False,individual_original_cores_matching_common=2,directed_nonself_pairs_per_frame_region=20,distinct_unordered_pairs_per_frame_region=14,reciprocal_pairs=6,new_observing_time_seconds=0,new_archive_queries=0,new_origin_assignments=0,labels_changed=0,new_C033_variants_planned=0,successful_observed_executions=1,next_original_queue_group='C034',next_original_queue_row=73,next_target='HD126093',next_record_count=1,next_discovery_product_count=1,next_action_sha256=sha(PHASE/'NEXT_ACTION.json'),fixed_plan_sha256=sha(HERE/'PLAN.json'),full_result_report_sha256=sha(HERE/'RESULTS_REPORT.md'),public_method_commit=publication['publication_commit'],public_method_readback_files=publication['files_verified'],public_method_precedes_current_arithmetic=True,C031_PR28_merged=True)
    write(PHASE/'GROUP_CLOSURE.json',closure)
    (PHASE/'scientific_review/RESULT_INTERPRETATION.md').write_text('''# Completed C033 interpretation

All four physical U labels remain. Both common core and surrounding raw correlations favor barycentric coordinates in all 20 directed nonself comparisons. Normalized RMS favors barycentric coordinates in 19/20 core and 17/20 surrounding rows. Preserve the metric disagreements and the reciprocal May pair. These are 14 unordered relationships with six reciprocal discovery pairs among six observations, not 20 independent confirmations.

All 28 profiles have full finite support and positive reference divisors; eight have low-reference flags. Fourteen profiles retain nonpositive original samples. All original member cores, mapping chains and eight raw contexts remain. The 0274/order4 compact off-trace deposit caution does not dispose of its broader centered component and is not transferred to another record.

Current windows in nine shared physical source IDs do not share source indices with C031. Five native/order sources are additional reused product/order contexts. The six observations and earlier C033 epoch/raw values were already exposed; disjoint windows do not create blind validation. No new observing time, physical-origin assignment, qualified laser or calibrated survey null follows.

The public 25-file method readback preceded current arithmetic. One production run completed this exact diagnostic. Separate arithmetic and visual review were by the same assistant. C034 is next by original queue index, selected before C033 values; it must retain its own May reference and BERV. Completed exact routes remain closed despite U.
''')
    (PHASE/'README.md').write_text('''# C033 / HD126093: complete

**Four records, four discovery references, six existing observations, 28 profiles and 128 comparisons. All four remain U; no qualified laser candidate.**

Raw correlation favors barycentric coordinates in 20/20 directed nonself comparisons for both common core and surroundings. Normalized RMS favors it in 19/20 core and 17/20 surrounding rows. They represent 14 unordered relationships with six reciprocal discovery pairs. All metric disagreements remain explicit.

All 28 profiles have full finite support and positive references. Eight low-reference flags, signed nonpositive original samples, all original mapping stages, eight raw containers and the record-specific 0274 caution remain. Separate reconstruction passes 791 checks over 110,049 values. All 50 NPZ containers and six fixed scientific PNGs decode and were inspected by the same assistant.

[Report and six figures](analysis/RESULTS_REPORT.md) · [Numerical audit](independent_audit/NUMERICAL_AUDIT.json) · [Source-index dependency](independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json) · [Closure](GROUP_CLOSURE.json) · [Next C034 route](NEXT_ACTION.json) · [Continuation state](CONTINUATION_STATE.json).

All 25 public method files were read back exactly before current arithmetic. No independent human/agent review, blind validation or added observing time is claimed. C031 PR #28 is merged and its work branch was synchronized before the current freeze. Integrate current results only after exact delivery verification and passing final-head CI under the existing direct publication approval.
''')
    status='''## SETI-status — C033 på HD126093 afsluttet (5. november 2026)

**Fire poster, fire referencer og seks eksisterende observationer: 28 profiler og 128 sammenligninger. Alle fire forbliver uafklarede; ingen kvalificeret laserkandidat.**

Råkorrelationen er bedst barycentrisk i alle 20 rettede sammenligninger for både kerne og omgivelser. Normaliseret RMS er bedst barycentrisk i 19/20 og 17/20; undtagelserne er dokumenteret. De 20 rettede rækker repræsenterer 14 forskellige observationspar. Fuld støtte, otte lave referenceniveauer, negative originalpunkter og den særskilte 0274-bemærkning er bevaret.

Separat efterregning består med 791 kontroller over 110.049 talværdier. Alle 25 metodefiler blev offentliggjort og læst tilbage nøjagtigt før beregningen. C031 PR #28 er flettet, og arbejdsgrenen er synkroniseret. Næste køpunkt er **C034: én post ved 4312,2025 Å med sin egen maj-reference**.

[Fortsæt her](CONTINUE_SETI.md) · [Rapport og seks figurer](work_harps_20261105_c033_context/analysis/RESULTS_REPORT.md) · [Aktuel tilstand](work_harps_20261105_c033_context/CONTINUATION_STATE.json). Godkendelsen til offentliggørelse og fortsættelse er registreret. Ingen baggrundssøgning kører.

---

'''
    continuation='''# Continue SETI from completed C033 / HD126093

Read [the current state](work_harps_20261105_c033_context/CONTINUATION_STATE.json), verify live GitHub refs and source hashes, and resume the exact next unfinished original route. Earlier method freezes and outputs remain preserved.

C033 is complete: original records 0265/0270/0274/0279, four own discovery references, six reused observations, 28 profiles and 128 comparisons. All four physical U labels remain. Raw Pearson is higher barycentrically in 20/20 directed nonself rows in both regions; normalized RMS is lower in 19/20 core and 17/20 surrounding rows. These are 14 unordered relationships and 6 reciprocal discovery pairs among six observations. Preserve all metric disagreements, including the reciprocal May surrounding pair.

All 28 profiles have full 601-point finite raw/scaled support and positive references. Eight low-reference flags and 14 profiles with nonpositive original samples remain; ERR has no positive finite support. All eight original mapping chains are true. All eight original raw containers and 112 member-support records remain. The 0274 own order 4 possible off-trace deposit/blend caution is distinct from its broad centered component and is not transferred. Two original cores match the common 3880.35±0.25 core; two differ. No original-core-union fit or origin claim follows.

Nine physical source IDs are shared with C031 but their current original-index windows are disjoint; five native/order IDs are additional reused contexts. Earlier C033 epoch/raw values and six observations were already exposed, so no source-pixel independence or blind validation is claimed. The public 25-file method readback preceded current values. Separate reconstruction passes 791 checks over 110,049 values; 50 NPZ containers and 6 fixed PNGs decode and all figures were inspected by the same assistant. One successful production execution; no calibrated significance, linewidth, sensitivity, qualified laser or survey null.

## Exact next action: C034 at original queue row 73

Use [NEXT_ACTION](work_harps_20261105_c033_context/NEXT_ACTION.json), selected before C033 values. Singleton V2E2-0271 on HD126093 retains exact original 4312.202499999999 air Å center and its own May 29 discovery ADP.2025-05-30T01:00:44.357 with its own negative BERV. Restore its own native/raw inputs, scan all 72 native orders and freeze its separate geometry and reference handling. Do not transfer C033 April anchor, orders 3/4, support, low flags, mapping stages or 0274 caution. C032 remains pending later in original queue order.

Completed exact C001–C023, C028–C031, C033 and ten earlier bounded baseline diagnoses remain closed despite physical U. Do not replay extraction, mapping, registration, normalization, spatial or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET. No background science job is running.

## Publication and integration

The current direct user message approves publication and requests continuation. C031 PR #28 passed exact-head CI and merged at 922b78780f690b70d9560956008818152e92f422; main and optical-harps-week-20261101 were synchronized before this method. Earlier C031 publication holds are historical. Publish exact C033 results, verify the public snapshot and passing final-head CI, then merge with expected-head guards and synchronize the work branch. Verify real PR/refs; creation-time state fields do not assert later integration already happened.

[Full report](work_harps_20261105_c033_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261105_c033_context/GROUP_CLOSURE.json).

---

'''
    before={}
    for name,prefix in [('README.md',status),('CONTINUE_SETI.md',continuation)]:
        f=ROOT/name;before[name]=f.read_bytes();f.write_bytes(prefix.encode()+before[name]);assert f.read_bytes().endswith(before[name])
    changed=[];preserved=0
    for p,h in prior['source_hashes'].items():
        if sha(ROOT/p)==h:preserved+=1
        else:
            assert p in before
            changed.append(dict(path=p,previous_sha256=h,current_sha256=sha(ROOT/p),reason='Authorized C033 current status and C034 handoff prepended; previous bytes preserved exactly as suffix and in Git.'))
    assert preserved==134 and len(changed)==2
    state=dict(schema='SETI_CONTINUATION_STATE_V33_COMPLETED_C033_CONTEXT',created_utc=now,entry_point='CONTINUE_SETI.md',repository='andersenmartin-blip/setisearch',science=copy.deepcopy(prior['science']),previous_continuation_state=str(prior_path.relative_to(ROOT)),previous_continuation_state_sha256=sha(prior_path),completed_harps_c033_context=dict(summary=summary,closure_path=str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),report_path=str((HERE/'RESULTS_REPORT.md').relative_to(ROOT)),audit_status=audit['status'],audit_checks=audit['checks_passed'],audit_scalar_values=audit['scalar_values_compared'],quality=qa['summary'],source_pixel_independence_claim=False,new_observing_time_seconds=0,all_four_current_U_unchanged=True),completed_original_routes=prior['completed_original_routes']+['C033'],completed_route_qualification='Completed exact diagnostics and ten earlier bounded baseline routes stay closed despite U. C034 is next by original queue index; C032 remains pending later.',completed_exact_baseline_route_ids=prior['completed_exact_baseline_route_ids'],completed_baseline_route_proof_path=prior['completed_baseline_route_proof_path'],completed_baseline_route_proof_sha256=prior['completed_baseline_route_proof_sha256'],next_action=nextaction,rubin=copy.deepcopy(prior['rubin']),checkpoint_integrity=dict(baseline_commit='922b78780f690b70d9560956008818152e92f422',previous_public_state_source_hashes_checked=136,previous_bound_sources_preserved=preserved,authorized_current_document_changes=changed,current_method_source_bindings_verified=len(plan['source_hashes'])),previous_integration=read(PHASE/'C031_INTEGRATION_RECEIPT.json'),integration=dict(status_at_state_creation='C033_RESULTS_READY_FOR_EXACT_PUBLICATION_AND_FINAL_HEAD_CI',current_direct_user_publication_approval=True,intended_main='main',intended_work_branch='optical-harps-week-20261101',required_before_merge='Exact delivery snapshot verification, successful final-head CI,expected-head merge guard,and work-branch fast-forward. Inspect actual PR/refs for later integration state.'),publication=dict(prospective_commit=publication['publication_commit'],prospective_readback_files=publication['files_verified'],prospective_before_current_arithmetic=True,delivery_branch='codex/seti-c033-20261105',results_receipt_path=str((PHASE/'RESULTS_PUBLICATION_RECEIPT.json').relative_to(ROOT))),execution=dict(current_computation_complete=True,successful_observed_executions=1,background_science_jobs_running=False,unattended_search_configured=False,new_archive_queries=0))
    full_inputs={r['path']for r in read(PHASE/'inputs/INPUT_INVENTORY.json')['files']}
    bindings={p:h for p,h in plan['source_hashes'].items()if p not in full_inputs}
    for f in sorted(PHASE.rglob('*')):
        if not f.is_file()or f.name in ['CONTINUATION_STATE.json','RESULTS_PUBLICATION_RECEIPT.json']or str(f.relative_to(ROOT))in full_inputs or '__pycache__'in f.parts:continue
        bindings[str(f.relative_to(ROOT))]=sha(f)
    for p in ['README.md','CONTINUE_SETI.md']:bindings[p]=sha(ROOT/p)
    state['source_hashes']=dict(sorted(bindings.items()));assert state['science']==prior['science']
    write(PHASE/'CONTINUATION_STATE.json',state);assert all(sha(ROOT/p)==h for p,h in state['source_hashes'].items())
    print(json.dumps(dict(status='COMPLETE_C033_DELIVERY',state_bindings=len(bindings),previous_sources_preserved=preserved,next_group='C034',next_records=1,numerical_checks=audit['checks_passed'],scalar_values=audit['scalar_values_compared']),indent=2))

if __name__=='__main__':main()
