"""Close the local C031 diagnostic and preserve an exact, unpublished handoff."""
from pathlib import Path
import copy, datetime, hashlib, json, subprocess

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
PREV=ROOT/'work_harps_20261104_c030_context'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    assert not(PHASE/'GROUP_CLOSURE.json').exists(),'Preserve completed delivery'
    prior=read(PREV/'CONTINUATION_STATE.json');plan=read(HERE/'PLAN.json');summary=read(HERE/'results/SUMMARY.json');qa=read(HERE/'RESULTS_QA.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');nextmeta=read(PHASE/'scientific_review/NEXT_GROUP_METADATA.json');freeze=read(PHASE/'LOCAL_FREEZE_RECEIPT.json')
    assert all(sha(ROOT/p)==h for p,h in prior['source_hashes'].items())
    assert all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items())
    assert all(sha(HERE/'results'/p)==h for p,h in read(HERE/'results/OUTPUT_HASHES.json').items())
    assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT'and qa['summary']['profile_slots']==28 and audit['checks_passed']==791
    assert nextmeta['core_overlap_group']=='C033'and nextmeta['selected_before_current_observed_values']and len(nextmeta['events'])==4
    assert read(HERE/'ROOT_RELEASE.json')['public_method_publication_verified']is False
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    nextaction=copy.deepcopy(nextmeta)
    nextaction.update(created_utc=now,kind='JOINT_PROFILE_CONTEXT_C033_HD126093',primary_evidence_route='JOINT_PROFILE_CONTEXT',new_diagnostic_executed=False,current_phase_closed=str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),prior_and_next_labels_unchanged=True,reopen_completed_groups=False,publication_status='C031_PUBLICATION_BLOCKED_PENDING_DIRECT_USER_APPROVAL',local_science_execution_authorized=True,rubin_status='STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET',no_background_execution=True,native_scope_requirement='Four own discovery products and eight original event/order raw contexts;fresh all72-order headers per product. C033 is selected by original queue order ahead of C032. Freeze its own geometry,mapping stages and quality rules before values. Do not rerun C031 or transfer its missing/low flags.')
    write(PHASE/'NEXT_ACTION.json',nextaction)
    closure=dict(schema='HARPS_C031_LOCAL_DIAGNOSTIC_CLOSURE_V1',created_utc=now,status='COMPLETE_LOCAL_FIXED_JOINT_CONTEXT_ALL_U_UNCHANGED',target='HD126093',events=list(plan['events']),current_codes={e:'U'for e in plan['events']},summary=summary,numerical_audit={k:audit[k]for k in ['status','checks_passed','scalar_values_compared','profiles_reconstructed','comparisons_reconstructed','bounded_input_records_reconstructed','preserved_raw_context_files_verified']},quality_summary=qa['summary'],source_bindings_unchanged=len(plan['source_hashes']),shared_C030_source_inputs=14,additional_native_inputs_not_new_observations=0,source_pixel_dependency_audit_sha256=sha(PHASE/'independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json'),original_member_core_support_sha256=sha(PHASE/'independent_audit/MEMBER_CORE_SUPPORT.json'),source_pixel_independence_claim=False,common_core_covers_original_member_core_union=False,directed_nonself_pairs_per_frame_region=20,distinct_unordered_pairs_per_frame_region=14,reciprocal_pairs=6,new_observing_time_seconds=0,new_archive_queries=0,new_origin_assignments=0,labels_changed=0,new_C031_variants_planned=0,successful_observed_executions=1,next_original_queue_group='C033',next_original_queue_row=67,next_target='HD126093',next_existing_epoch_count=6,next_record_count=4,next_discovery_product_count=4,next_action_sha256=sha(PHASE/'NEXT_ACTION.json'),fixed_plan_sha256=sha(HERE/'PLAN.json'),full_result_report_sha256=sha(HERE/'RESULTS_REPORT.md'),public_method_publication_verified=False,public_preregistration_claim=False,local_method_commit=freeze['local_method_commit'],local_method_readback_files=freeze['files_verified'],GitHub_C031_upload_blocked=True,GitHub_C030_PR27_merged=True)
    write(PHASE/'GROUP_CLOSURE.json',closure)
    interpretation='''# C031 interpretation

All four physical classifications remain unresolved. The fixed core and surrounding pattern each favor barycentric raw correlation and normalized RMS in 19 of 20 directed nonself comparisons. These are 14 distinct unordered relationships, with six reciprocal discovery pairs among six existing observations. The May 30-to-May 29 core exception and June 25-to-June 27 surrounding exception remain explicit. No physical cause or qualified laser is established.

Eight order-2 frame profiles retain partial broad support. Two barycentric profiles have insufficient positive-side source support and retain raw data only. The July topocentric order-2 profile has a positive but low reference. Missing values are not replaced by another frame's values. All eight original raw containers and every mapping stage, original member boundary and event-specific uncertainty remain.

The exact local method preceded current arithmetic. Public disclosure was blocked by automatic review; no public preregistration is claimed. The completed C031 diagnostic stays closed while its public upload awaits direct approval. C033 at original queue row 67 is the next distinct route. C032 remains pending later in original queue order. There is no background science execution.
'''
    (PHASE/'scientific_review/RESULT_INTERPRETATION.md').write_text(interpretation)
    (PHASE/'README.md').write_text('''# C031 / HD126093: complete locally

**Four records, four discovery references, six existing observations, 28 profiles and 128 comparisons. All four remain U; no qualified laser candidate.**

The common core and surrounding pattern each favor barycentric correlation and normalized RMS in 19 of 20 directed nonself comparisons, representing 14 distinct unordered relationships. Two different topocentric exceptions are documented. Eight partial order-2 profiles, two raw-only barycentric profiles, one low topocentric reference and all eight original raw containers are retained.

Separate scalar reconstruction passes 791 checks over 109,709 values. All 50 NPZ containers and six fixed scientific PNGs decode. The method was fixed in a local Git commit before values; public GitHub upload was blocked by automatic approval review. No public preregistration or independent human/agent review is claimed.

[Full report and six figures](analysis/RESULTS_REPORT.md) · [Numerical audit](independent_audit/NUMERICAL_AUDIT.json) · [Closure](GROUP_CLOSURE.json) · [Next C033 route](NEXT_ACTION.json) · [Continuation state](CONTINUATION_STATE.json) · [Local execution decision](LOCAL_EXECUTION_DECISION.json).
''')
    status='''## Lokal SETI-status — C031 afsluttet (5. november 2026)

**Fire poster på HD126093 er gennemgået: 28 profiler og 128 sammenligninger fra seks eksisterende observationer. Alle fire er fortsat uafklarede; ingen kvalificeret laserkandidat.**

Separat efterregning består med 791 kontroller over 109.709 talværdier. Begge mål er bedst barycentrisk i 19 af 20 rettede sammenligninger for både kerne og omgivelser; de repræsenterer 14 forskellige observationspar. Undtagelser, delvis dækning, to rå-profiler uden gyldig normalisering og ét lavt referenceniveau er bevaret.

C030 PR #27 er flettet på GitHub, og den tidligere arbejdsgren er synkroniseret. **C031 er afsluttet lokalt og afventer direkte godkendelse til offentliggørelse**, fordi automatisk godkendelseskontrol afviste upload. Metoden blev låst lokalt før beregningen; der hævdes ingen offentlig forhåndsregistrering.

[Fortsæt her](CONTINUE_SETI.md) · [Lokal rapport og seks figurer](work_harps_20261105_c031_context/analysis/RESULTS_REPORT.md) · [Lokal tilstand](work_harps_20261105_c031_context/CONTINUATION_STATE.json). Næste oprindelige køpunkt er C033 med fire poster. Ingen baggrundssøgning kører.

---

'''
    continuation='''# Continue SETI from completed local C031 / HD126093

Read [the current local state](work_harps_20261105_c031_context/CONTINUATION_STATE.json) and verify real GitHub refs before any publication. Earlier states, methods and outputs remain preserved.

C031 is complete: four original records 0264/0269/0277/0282, four discovery references, six reused observations, 28 profiles and 128 comparisons. All four physical U labels remain. Separate reconstruction passes 791 checks over 109,709 values. All 50 NPZ containers and six fixed scientific PNGs decode; the same assistant inspected all figures. Original raw evidence and mapping stages remain exact.

The core and surrounding pattern each favor barycentric raw correlation and normalized RMS in 19 of 20 directed nonself comparisons. These are 14 unordered relationships and six reciprocal discovery pairs among only six observations. Preserve the distinct May core and June surroundings exceptions. Eight native order-2 profiles are partial; June 27 and July 16 barycentric order-2 profiles are raw-only; July 16 topocentric order 2 has a low reference. All 112 original-member support records remain. No qualified laser, physical origin, blind validation or calibrated null is claimed.

## Public disclosure hold

C030 PR #27 was merged at 48dc62d0b2fb063254f57f3135ce794a560a0000; main and optical-harps-week-20261101 were synchronized there. Automatic approval review blocked C031 push twice, requiring fresh direct authorization for this specific public disclosure despite prior standing permissions. Do not bypass that restriction. C031 has a verified LOCAL method commit before observed arithmetic and makes no public-preregistration claim. Publish only after the requested direct user approval; then run exact-head CI and use guarded integration. Inspect live refs: this local note does not imply C031 was uploaded.

## Next original science route: C033, queue row 67

Use [the exact metadata handoff](work_harps_20261105_c031_context/NEXT_ACTION.json), selected before C031 values. Four original records 0265/0270/0274/0279 retain four own discovery references at proposed metadata midpoint 3880.35 air Å on HD126093. The midpoint is not a new frozen method. Restore own native/raw products, scan all 72 native orders per discovery and freeze original/common geometry and quality handling. Do not transfer C031 partial-coverage, missing-flank or low-reference outcomes. C033 is next by original queue index; C032 remains pending later in that ordering.

Completed exact C001–C023, C028–C031 and the ten earlier bounded baseline diagnoses remain closed despite physical U. Do not replay extraction, mapping, registration, normalization, spatial or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET. No background science job is running.

[Full local report](work_harps_20261105_c031_context/analysis/RESULTS_REPORT.md) · [Local closure](work_harps_20261105_c031_context/GROUP_CLOSURE.json).

---

'''
    previous_bytes={}
    for name,prefix in [('README.md',status),('CONTINUE_SETI.md',continuation)]:
        f=ROOT/name;previous_bytes[name]=f.read_bytes();f.write_bytes(prefix.encode()+previous_bytes[name]);assert f.read_bytes().endswith(previous_bytes[name])
    changed=[];preserved=0
    for p,h in prior['source_hashes'].items():
        if sha(ROOT/p)==h:preserved+=1
        else:
            assert p in previous_bytes
            changed.append(dict(path=p,previous_sha256=h,current_sha256=sha(ROOT/p),reason='Local C031 status and C033 handoff prepended; prior exact bytes preserved as suffix and in Git. Public C031 upload is blocked.'))
    assert preserved==145 and len(changed)==2
    state=dict(schema='SETI_CONTINUATION_STATE_V32_COMPLETED_LOCAL_C031_CONTEXT',created_utc=now,entry_point='CONTINUE_SETI.md',repository='andersenmartin-blip/setisearch',science=copy.deepcopy(prior['science']),previous_continuation_state=str((PREV/'CONTINUATION_STATE.json').relative_to(ROOT)),previous_continuation_state_sha256=sha(PREV/'CONTINUATION_STATE.json'),completed_harps_c031_context=dict(summary=summary,closure_path=str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),report_path=str((HERE/'RESULTS_REPORT.md').relative_to(ROOT)),audit_status=audit['status'],audit_checks=audit['checks_passed'],audit_scalar_values=audit['scalar_values_compared'],quality=qa['summary'],source_pixel_independence_claim=False,new_observing_time_seconds=0,all_four_current_U_unchanged=True),completed_original_routes=prior['completed_original_routes']+['C031'],completed_route_qualification='Every exact completed diagnostic remains closed despite physical U. C033 is next by original queue index; C032 remains pending later in queue.',completed_exact_baseline_route_ids=prior['completed_exact_baseline_route_ids'],completed_baseline_route_proof_path=prior['completed_baseline_route_proof_path'],completed_baseline_route_proof_sha256=prior['completed_baseline_route_proof_sha256'],next_action=nextaction,rubin=copy.deepcopy(prior['rubin']),checkpoint_integrity=dict(baseline_commit='48dc62d0b2fb063254f57f3135ce794a560a0000',previous_state_source_hashes_checked=147,previous_bound_sources_preserved=preserved,authorized_current_local_document_changes=changed,current_method_source_bindings_verified=len(plan['source_hashes'])),previous_integration=read(PHASE/'C030_INTEGRATION_RECEIPT.json'),integration=dict(status_at_state_creation='COMPLETE_LOCAL_C031_PUBLIC_UPLOAD_BLOCKED_PENDING_DIRECT_USER_APPROVAL',C030_PR27_merged=True,main_and_optical_work_branch_at_C030_baseline='48dc62d0b2fb063254f57f3135ce794a560a0000',do_not_publish_C031_without_fresh_user_approval=True,required_after_publication_approval='Byte-exact public readback,successful final-head CI,expected-head guarded merge and work-branch fast-forward.'),publication=dict(public_method_publication_verified=False,public_preregistration_claim=False,local_method_commit=freeze['local_method_commit'],local_method_readback_files=freeze['files_verified'],intended_delivery_branch='codex/seti-c031-20261105',C031_currently_uploaded=False,approval_block_record=str((PHASE/'LOCAL_EXECUTION_DECISION.json').relative_to(ROOT))),execution=dict(current_computation_complete=True,successful_observed_executions=1,background_science_jobs_running=False,unattended_search_configured=False,new_archive_queries=0))
    full_inputs={r['path']for r in read(PHASE/'inputs/INPUT_INVENTORY.json')['files']}
    bindings={p:h for p,h in plan['source_hashes'].items()if p not in full_inputs}
    for f in sorted(PHASE.rglob('*')):
        if not f.is_file()or f.name=='CONTINUATION_STATE.json' or str(f.relative_to(ROOT))in full_inputs or '__pycache__'in f.parts:continue
        bindings[str(f.relative_to(ROOT))]=sha(f)
    for p in ['README.md','CONTINUE_SETI.md']:bindings[p]=sha(ROOT/p)
    state['source_hashes']=dict(sorted(bindings.items()));assert state['science']==prior['science']
    write(PHASE/'CONTINUATION_STATE.json',state)
    assert all(sha(ROOT/p)==h for p,h in state['source_hashes'].items())
    print(json.dumps(dict(status='COMPLETE_LOCAL_C031_DELIVERY',state_bindings=len(bindings),previous_sources_preserved=preserved,previous_local_root_document_changes=len(changed),next_group='C033',public_C031_upload=False),indent=2))

if __name__=='__main__':main()
