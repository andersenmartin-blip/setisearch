"""Close only the completed C030 diagnostic, preserve old files and bind the next route."""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;PHASE=HERE.parent;ROOT=HERE.parents[1];PREV=ROOT/'work_harps_20261104_c029_context'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+chr(10))
def main():
 assert not(PHASE/'GROUP_CLOSURE.json').exists(),'Preserve completed delivery'
 prior=read(PREV/'CONTINUATION_STATE.json');plan=read(HERE/'PLAN.json');summary=read(HERE/'results/SUMMARY.json');qa=read(HERE/'RESULTS_QA.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');publication=read(PHASE/'PROSPECTIVE_PUBLICATION_RECEIPT.json');nextmeta=read(PHASE/'scientific_review/NEXT_GROUP_METADATA.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 assert all(sha(ROOT/p)==h for p,h in prior['source_hashes'].items())
 assert all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items())
 assert all(sha(HERE/'results'/p)==h for p,h in read(HERE/'results/OUTPUT_HASHES.json').items())
 assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT' and qa['summary']['profile_slots']==32 and audit['checks_passed']==930
 assert nextmeta['core_overlap_group']=='C031'and nextmeta['selected_before_current_observed_values']and len(nextmeta['events'])==4
 nextaction=copy.deepcopy(nextmeta);nextaction.update(created_utc=now,kind='JOINT_PROFILE_CONTEXT_C031_HD126093',primary_evidence_route='JOINT_PROFILE_CONTEXT',new_diagnostic_executed=False,current_phase_closed=str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),prior_and_next_labels_unchanged=True,reopen_completed_groups=False,standing_authorization='User explicitly authorizes autonomous SETI continuation and GitHub updates including main and optical-harps-week-20261101. Preserve fixed methods and exact-head guards.',rubin_status='STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET',no_background_execution=True,native_scope_requirement='Restore four own native products and every original event/order raw container; fresh all72-order headers each. Retain all original centers,member-core bounds,own references,BERV,mapping stages and review cautions. Do not inherit C030 partial coverage or positive/low quality. Any common-center method must distinguish its core from the original members. Reused spectra/pixels and exposed epoch/raw evidence preclude independent/blind validation.')
 write(PHASE/'NEXT_ACTION.json',nextaction)
 q=qa['summary'];closure={'schema':'HARPS_C030_DIAGNOSTIC_CLOSURE_V1','created_utc':now,'status':'COMPLETE_FIXED_JOINT_CONTEXT_ALL_U_UNCHANGED','target':'HD126093','events':list(plan['events']),'current_codes':{e:'U'for e in plan['events']},'summary':summary,'numerical_audit':{k:audit[k]for k in ['status','checks_passed','scalar_values_compared','profiles_reconstructed','comparisons_reconstructed','bounded_input_records_reconstructed','preserved_raw_context_files_verified']},'quality_summary':q,'source_bindings_unchanged':len(plan['source_hashes']),'shared_C029_source_inputs':12,'additional_native_inputs_not_new_observations':4,'source_pixel_dependency_audit_sha256':sha(PHASE/'independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json'),'original_member_core_support_sha256':sha(PHASE/'independent_audit/MEMBER_CORE_SUPPORT.json'),'source_pixel_independence_claim':False,'common_core_covers_original_member_core_union':False,'directed_nonself_pairs_per_frame_region':25,'distinct_unordered_pairs_per_frame_region':15,'reciprocal_pairs':10,'new_observing_time_seconds':0,'new_archive_queries':0,'new_origin_assignments':0,'labels_changed':0,'new_C030_variants_planned':0,'successful_observed_executions':1,'next_original_queue_group':'C031','next_original_queue_row':66,'next_target':'HD126093','next_existing_epoch_count':6,'next_record_count':4,'next_discovery_product_count':4,'next_action_sha256':sha(PHASE/'NEXT_ACTION.json'),'fixed_plan_sha256':sha(HERE/'PLAN.json'),'full_result_report_sha256':sha(HERE/'RESULTS_REPORT.md')}
 write(PHASE/'GROUP_CLOSURE.json',closure)
 interpretation='''# Interpretation of completed C030 context

The fixed common core and surrounding pattern usually align better in barycentric coordinates. In each region, raw Pearson favors barycentric coordinates for24of25directed pairs and scaled RMS for25of25. The June25-to-June27relationship has slightly higher topocentric raw Pearson in both regions; it remains explicit. These25directed pairs are15unordered relationships with10reciprocal discovery pairs among six observations. This is a dependent descriptive diagnostic,not a physical-origin assignment.

Every original center and member core remains distinct. The common ±0.25 Å core does not contain the original-core union. All256profile/member support records retain50finite raw and scaled grid centers each,without any extra correlation or fit. Broad patterns and signed source values remain visible.

Ten order2frame profiles are partial at the broad boundary. They retain557–595finite centers and adequate support for normalization and comparisons. July16order2has an explicit low reference flag in both frames. All16original raw containers and all eight U/U/Uchains remain; no0261-specific blend caution transfers.

C030's exact diagnostic is closed while every physical U classification remains unresolved. C031 is a different original queue route,selected before current values. Its own four discovery/native products,original member cores,partial flank support,mapping and review history require a fresh method freeze. No completed diagnosis is reopened merely because U remains.
'''
 (PHASE/'scientific_review/RESULT_INTERPRETATION.md').write_text(interpretation)
 phase_readme='''# C030 / HD126093: complete

**Eight records, five discovery references, six existing observations, 32 profiles and 160 comparisons are complete. All eight records remain U; no qualified laser candidate.**

In each region, barycentric raw correlation is higher in24of25directed nonself pairs and normalized RMS lower in25of25. These are15unordered relationships with10reciprocal discovery pairs among six observations. The slightly higher topocentric June25-to-June27raw correlation is retained explicitly.

The common3867.13125Å core differs from every original member core. All original markers,bounds and256support records remain. Ten partial order2profiles preserve missing broad-edge data; July16order2has low flank reference flags in both frames. All16original raw containers and event-specific mapping/review chains remain exact.

[Full report and nine figures](analysis/RESULTS_REPORT.md) · [Separate numerical audit](independent_audit/NUMERICAL_AUDIT.json) · [Original-core support](independent_audit/MEMBER_CORE_SUPPORT.json) · [Source-index overlap](independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json) · [Closure](GROUP_CLOSURE.json) · [Next C031 route](NEXT_ACTION.json) · [Continuation state](CONTINUATION_STATE.json).

The public24-file method readback preceded current arithmetic. Separate reconstruction passes930checks over127,836values; all70method bindings remain exact. The64NPZ containers and9figures decode,and all figures were inspected by the same assistant. No separate-agent/human review,independent validation or new observing time is claimed.
'''
 (PHASE/'README.md').write_text(phase_readme)
 status='''## Aktuel SETI-status — C030 på HD126093 afsluttet (4. november 2026)

**Otte poster, fem referencer og seks eksisterende observationer er gennemgået: 32 profiler og 160 sammenligninger.** Alle otte poster forbliver uafklarede; ingen kvalificeret laserkandidat er etableret.

I både fælles kerne og omgivelser er korrelationen højere barycentrisk i24af25rettede sammenligninger og normaliseret RMS lavere i alle25. De repræsenterer15forskellige observationspar med10gensidige gentagelser,ikke25uafhængige observationer. Den ene undtagelse i korrelationen er dokumenteret. Den fælles kerne erstatter ikke de otte oprindelige kerner.

Separat efterregning består med930kontroller og127.836talværdier. Delvis dækning i orden2,lavt flankereferenceflag i juli og negative originalpunkter er bevaret sammen med alle16råudsnit. Tolv kildevinduer deler originalpunkter med C029; fire yderligere nativevinduer er kendte observationer. Næste punkt er **C031: fire poster og fire referencer**.

[**Fortsæt her**](CONTINUE_SETI.md) · [Rapport og ni figurer](work_harps_20261104_c030_context/analysis/RESULTS_REPORT.md) · [Aktuel tilstand](work_harps_20261104_c030_context/CONTINUATION_STATE.json)

---

'''
 continuation='''# Continue SETI from completed C030 / HD126093

Read [the current state](work_harps_20261104_c030_context/CONTINUATION_STATE.json),verify current GitHub heads and source hashes,and resume the exact next unfinished route. Earlier methods and numerical products remain preserved.

C030 is complete:32profiles,160comparisons,8original records and5discovery references on6existing observations. All8physical U labels remain. The metadata midpoint3867.13125Å common core differs from every original member core;256support records retain all original cores. Barycentric raw Pearson wins24of25directed nonself rows and scaled RMS25of25in each region. These25rows are15unordered relationships with10reciprocal pairs. Preserve the June25/June27correlation exception.

Ten native order2profiles have partial broad-edge coverage but sufficient normalization/common support. July16order2has low reference flags in both frames. All16raw containers and exact per-event mapping/review stages remain. Twelve C029source windows overlap and4additional June/July native windows reuse existing observations. No independence,blind validation,physical origin,qualified laser,measured linewidth or calibrated survey null is claimed.

Validation:3,344byte/header checks with360fresh header-order records;132compact synthetic checks;1,449separate scalar preflight checks over73,014values;930observed reconstruction checks over127,836values. All64NPZ containers and9figures decode; all figures inspected by the same assistant. All70frozen source bindings remain intact. One successful observed production execution.

## Exact next action: C031 at original row66

Use [NEXT_ACTION](work_harps_20261104_c030_context/NEXT_ACTION.json),selected before C030values. Four original members0264/0269/0277/0282 on HD126093 retain four own discovery references across six cohort observations. Proposed metadata midpoint3868.1499999999996Å is not a frozen method. Restore all four own native products and original raw contexts,freshly scan all72orders each,and freeze original/common core differences before current arithmetic. Order2may lose more broad-window and positive-flank support; retain missing,invalid,low and raw-only outcomes. Do not transfer C030coverage,mapping stages or absent blend cautions.

Completed original routesC001–C023,C028,C029,C030 and the ten exact baseline routes remain closed despite physical U. Do not replay normalization,mapping,spatial,registration,raw extraction or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET; no background science job is running.

## GitHub authorization and integration

The user already authorizes autonomous continuation and updates to GitHub,including main and optical-harps-week-20261101. Publish exact method before current values,preserve one-shot outputs,verify byte-exact delivery,pass exact-head CI,then merge with expected-head guards and fast-forward the work branch. Verify real current refs/PR state before continuing; receipt/state integration fields describe their creation time. No new permission question is required for this standing scope.

[Full report](work_harps_20261104_c030_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c030_context/GROUP_CLOSURE.json).

---

'''
 # Readable current prose; previous document bytes stay as the exact suffix.
 spacing={'in24af25rettede':'i 24 af 25 rettede','alle25':'alle 25','repræsenterer15forskellige':'repræsenterer 15 forskellige','med10gensidige':'med 10 gensidige','ikke25uafhængige':'ikke 25 uafhængige','med930kontroller og127.836talværdier':'med 930 kontroller og 127.836 talværdier','orden2':'orden 2','alle16råudsnit':'alle 16 råudsnit'}
 for a,b in spacing.items():status=status.replace(a,b)
 for name,prefix in [('README.md',status),('CONTINUE_SETI.md',continuation)]:
  f=ROOT/name;before=f.read_bytes();f.write_bytes(prefix.encode('utf8')+before);assert f.read_bytes().endswith(before)
 changed=[];preserved=0
 for path,h in prior['source_hashes'].items():
  current=sha(ROOT/path)
  if current==h:preserved+=1
  else:
   assert path in ['README.md','CONTINUE_SETI.md'];changed.append({'path':path,'previous_sha256':h,'current_sha256':current,'reason':'Authorized current C030 result and C031 handoff prepended; earlier bytes preserved as exact suffix and in Git.'})
 assert preserved==118 and len(changed)==2
 state={'schema':'SETI_CONTINUATION_STATE_V31_COMPLETED_C030_CONTEXT','created_utc':now,'entry_point':'CONTINUE_SETI.md','repository':'andersenmartin-blip/setisearch','science':copy.deepcopy(prior['science']),'previous_continuation_state':str((PREV/'CONTINUATION_STATE.json').relative_to(ROOT)),'previous_continuation_state_sha256':sha(PREV/'CONTINUATION_STATE.json'),'completed_harps_c030_context':{'summary':summary,'closure_path':str((PHASE/'GROUP_CLOSURE.json').relative_to(ROOT)),'report_path':str((HERE/'RESULTS_REPORT.md').relative_to(ROOT)),'audit_status':audit['status'],'audit_checks':audit['checks_passed'],'audit_scalar_values':audit['scalar_values_compared'],'quality':q,'source_pixel_independence_claim':False,'new_observing_time_seconds':0,'all_eight_current_U_unchanged':True},'completed_original_routes':prior['completed_original_routes']+['C030'],'completed_route_qualification':'Exact completed diagnostics and ten bounded baseline routes stay closed with physical U unchanged. C031 is the next distinct unfinished original route.','completed_exact_baseline_route_ids':prior['completed_exact_baseline_route_ids'],'completed_baseline_route_proof_path':prior['completed_baseline_route_proof_path'],'completed_baseline_route_proof_sha256':prior['completed_baseline_route_proof_sha256'],'next_action':nextaction,'rubin':copy.deepcopy(prior['rubin']),'checkpoint_integrity':{'baseline_commit':'c05e893a907b5feeefbb0002899dc5a298a0bd35','previous_state_source_hashes_checked':120,'previous_bound_sources_preserved':preserved,'authorized_current_document_changes':changed,'current_method_source_bindings_verified':70},'previous_integration':read(PHASE/'C029_INTEGRATION_RECEIPT.json'),'integration':{'status_at_state_creation':'RESULTS_READY_FOR_EXACT_PUBLICATION_AND_CI','standing_user_authorization':True,'main_and_existing_work_branch_authorized':True,'intended_main':'main','intended_work_branch':'optical-harps-week-20261101','required_before_merge':'Exact delivery readback and successful final-head CI,then expected-head guarded merge and work-branch fast-forward. Inspect GitHub PR/refs for actual later integration state.'},'publication':{'prospective_commit':publication['publication_commit'],'prospective_readback_files':publication['files_verified'],'delivery_branch':'codex/seti-c030-20261104','workflow':'Publish exact results,verify final-head test checks,merge under standing authorization with expected-head guards.','results_receipt_path':str((PHASE/'RESULTS_PUBLICATION_RECEIPT.json').relative_to(ROOT))},'execution':{'current_computation_complete':True,'successful_observed_executions':1,'background_science_jobs_running':False,'unattended_search_configured':False,'new_archive_queries':0}}
 full_inputs={r['path']for r in read(PHASE/'inputs/INPUT_INVENTORY.json')['files']}
 bindings={path:h for path,h in plan['source_hashes'].items()if path not in full_inputs}
 tracked=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard',str(PHASE.relative_to(ROOT))],cwd=ROOT,text=True).splitlines()
 for path in sorted(set(tracked)|{'README.md','CONTINUE_SETI.md'}):
  if path.endswith('/CONTINUATION_STATE.json')and path.startswith(str(PHASE.relative_to(ROOT))+'/'):continue
  if path.endswith('/RESULTS_PUBLICATION_RECEIPT.json'):continue
  f=ROOT/path
  if f.is_file():bindings[path]=sha(f)
 state['source_hashes']=dict(sorted(bindings.items()));assert state['science']==prior['science'];write(PHASE/'CONTINUATION_STATE.json',state)
 assert all(sha(ROOT/p)==h for p,h in state['source_hashes'].items())
 print(json.dumps({'status':'COMPLETE_C030_DELIVERY','state_bindings':len(bindings),'previous_sources_preserved':preserved,'previous_sources_changed':len(changed),'next_group':'C031','next_records':4,'numerical_checks':audit['checks_passed'],'scalar_values':audit['scalar_values_compared']},indent=2))
if __name__=='__main__':main()
