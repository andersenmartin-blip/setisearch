#!/usr/bin/env python3
"""Build the current checkpoint from exact saved outputs; never acquire/reanalyse data."""
from pathlib import Path
import copy, datetime, hashlib, json, subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PREVIOUS=REPO/'work_seti_20261102_accelerated/CONTINUATION_STATE.json'
PREVIOUS_SHA='07983bf69b1f2bd210e807331f1ceeb73de505e0cd06c5d27d697ece839593a7'
CURRENT_DOCS={'CONTINUE_SETI.md','README.md','OPTICAL_AND_RUBIN_WEEK_PLANS_2026-11-01.md','work_harps_20261101/v2/RESTORE.md'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
assert sha(PREVIOUS)==PREVIOUS_SHA
old=read(PREVIOUS)
changes=[];unchanged=0
for p,h in old['source_hashes'].items():
 actual=sha(REPO/p)
 if actual==h:unchanged+=1
 else:
  assert p in CURRENT_DOCS, f'Unexpected change to previous checkpoint source: {p}'
  changes.append({'path':p,'previous_sha256':h,'current_sha256':actual,'reason':'Explicit current-document update for completed BERV follow-up; historical outputs unchanged.'})
assert {x['path'] for x in changes}==CURRENT_DOCS
save(ROOT/'PREVIOUS_SOURCE_DELTA.json',{'schema':'SETI_PREVIOUS_CHECKPOINT_DELTA_V1','previous_state':str(PREVIOUS.relative_to(REPO)),'previous_state_sha256':PREVIOUS_SHA,'previous_sources':len(old['source_hashes']),'unchanged_sources':unchanged,'intentional_current_document_changes':changes,'unexpected_changes':[]})
freeze=read(ROOT/'science_acquisition/PREFLIGHT_FREEZE.json')['files']
for p,d in freeze.items():assert sha(REPO/p)==d['sha256'],p
outputs=read(ROOT/'prospective_comparison/results/OUTPUT_HASHES.json')
for p,h in outputs.items():assert sha(ROOT/'prospective_comparison/results'/p)==h,p
state=copy.deepcopy(old)
state['schema']='SETI_CONTINUATION_STATE_V5_COMPLETED_HARPS_BERV'
state['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
state['previous_continuation_state']=str(PREVIOUS.relative_to(REPO))
state['previous_continuation_state_sha256']=PREVIOUS_SHA
state['completed_harps_berv_followup']={
 'directory':ROOT.name,
 'status':'COMPLETE_FIXED_DESCRIPTIVE_COMPARISON_ALL_TEN_REMAIN_U',
 'summary':read(ROOT/'prospective_comparison/results/SUMMARY.json'),
 'metadata_queries_actual':3,'successful_metadata_queries':2,'new_HD122640_metadata_products':18,'new_HD135204_metadata_products':0,
 'header_requests_actual':3,'verified_new_headers':2,'spectra_downloaded':2,'science_bytes':10529280,
 'failed_attempts_preserved':['metadata_search/RESULTS.md','header_acquisition/RESULTS.md'],
 'prospective_technical_amendments':['metadata_search_v2/AMENDMENT.md','header_acquisition_v2/AMENDMENT.md'],
 'HD122640_BERV_span_old_km_s':2.2379098704629,'HD122640_BERV_span_current_km_s':40.3634787209574,
 'HD135204_BERV_span_current_km_s':1.714121120020998,
 'large_displacement_May_blue_profiles_low_continuum':10,
 'January_blue_barycentric_r_range':[0.9608552432996504,0.9742630271689526],
 'interpretation':'January is coherent for five correlated blue event records but only 0.78–1.13 nominal resolution elements from discovery. Large-separation May blue profiles have low local continuum. Neither is a clean origin determination. V2E2-0235 has weak correlation with both additional epochs; no label change.',
 'independent_actual_numerical_checks':2065,'independent_scalar_comparisons':29712,
 'new_qualified_candidates':0,'qualified_null':False,'main_survey_coverage_changed':False,
 'input_archive_manifest':str((ROOT/'science_acquisition/INPUT_ARCHIVE.json').relative_to(REPO)),
 'profile_evidence_manifest':str((ROOT/'prospective_comparison/PROFILE_EVIDENCE.json').relative_to(REPO)),
 'report':str((ROOT/'prospective_comparison/results/README.md').relative_to(REPO))}
# Technical-amendment files are referenced by exact existing paths.
state['completed_harps_berv_followup']['prospective_technical_amendments']=[str(p.relative_to(ROOT)) for p in [ROOT/'metadata_search_v2/PREFLIGHT_FREEZE.json',ROOT/'header_acquisition_v2/AMENDMENT_FREEZE.json']]
for p in state['completed_harps_berv_followup']['prospective_technical_amendments']:assert (ROOT/p).is_file(),p
handoff=read(ROOT/'next_followup/HANDOFF.json')
state['harps_next_metadata_handoff']=handoff
state['next_action']={
 'kind':'SEPARATE_POSTHOC_QUALITY_FOLLOWUP_PREFLIGHT',
 'directory_to_continue':str((ROOT/'next_followup').relative_to(REPO)),
 'action':'The completed two-spectrum run is closed. Prepare a separate prospective one-product May quality follow-up from saved metadata, freeze exact header checks, bounds and selection before new request, then separately release any payload/comparison under inherited fixed method. Do not replay completed requests or replace an epoch based on event-window outcomes.',
 'provisional_product':'ADP.2017-05-21T01:01:50.278',
 'provisional_raw':'HARPS.2017-05-20T02:21:45.847',
 'provisional_metadata_average_snr':77.8,
 'quality_caveat':'Average metadata SNR is not verified local blue-window quality; this next phase is motivated by completed results and explicitly posthoc.',
 'future_phase_frozen':False,'future_phase_acquired':False,
 'queue_ids_by_target':old['next_action']['queue_ids_by_target'],
 'rubin_completed_status':'LIMITED_FEASIBILITY_STUDY_MINIMUM50_NOT_MET',
 'rubin_remaining_unique_main_capacity':310,'no_background_execution':True,
 'standing_authorization':old['next_action']['standing_authorization']}
state['after_pending_raw_review']=[
 'Completed: all669 initial raw reviews, all35 fixed mapping diagnoses, two normalization followups and original336-event epoch comparison. Do not repeat as new science.',
 'Completed: Rubin188+2 main objects; only2primary/4secondary numerical objects, primary two included in secondary four; minimum50 unmet, no qualified null. The current alternate route is stopped.',
 'Completed: two new HD122640 archival inputs,12 event–epoch pairs,24 frame profiles, all10 labels unchanged. Four HD135204 events have no selected new epoch.',
 'Next: separate posthoc metadata-quality handoff under next_followup; no new phase frozen or executed yet.']
state['limits']=[
 'The original300-exposure full-spectrum survey coverage is unchanged; two additional archival spectra were used only for targeted follow-up.',
 'All original V2 labels are preserved:403A,46O,185U,35M,0N. Descriptive profiles, geometry and correlated event groups cannot assign physical origin.',
 'The original extension02 epoch analysis excluded earlier200 exposures; new follow-up reused exact discovery references without rerunning original100 or336-event pipeline.',
 'All10 May frame profiles for the five blue events have low continuum. The cleaner January epoch provides only0.78–1.13 nominal resolution elements from discovery.',
 'Neither new input has finite positive ERR values; fitted amplitudes and correlations are descriptive, not calibrated detection significance.',
 'No new HD135204 rows under the fixed query is not proof of archive-wide absence.',
 'Audits are numerical/AI checks, not independent telescope observations or human peer review.',
 'No global sensitivity, false-alarm rate, survey completeness, physical-origin qualification or calibrated null.',
 'Rubin remains a bounded alert-selected field, not an all-star or all-sky survey; only2primary/4secondary numerical objects, primary two contained in secondary four, minimum50 unmet.',
 'Rubin source and forced populations are overlapping and cannot be added. Historical cadence, missing quality and Gaia-coordinate caveats are unchanged.',
 'Future highest-SNR May selection is an explicitly posthoc question requiring its own prospective scope; metadata-average SNR is not a local-quality guarantee.']
state['publication']={
 'branches':['main','optical-harps-week-20261101'],
 'turn_baseline_commit':'cfc0aa5146237ab82db183008ce8b162ad37c71a',
 'method_and_selection_commit':'aae61901226d9329be8f8ce333066fa7c9b85954',
 'exact_input_commit_before_new_arrays':'3e5f38f15da4306d11d443f1e4cc89de925e2ddc',
 'results_receipt_path':str((ROOT/'RESULTS_PUBLICATION_RECEIPT.json').relative_to(REPO)),
 'receipt_created_after_results_commit':True,
 'previous_checkpoint_publication':old['publication']}
state['new_followup_archives']={
 'exact_science_inputs':read(ROOT/'science_acquisition/INPUT_ARCHIVE.json'),
 'exact_discovery_and_comparison_profiles':read(ROOT/'prospective_comparison/PROFILE_EVIDENCE.json')}
# Keep all26 earlier archive registrations and original profile archive unchanged.
assert state['input_archives']==old['input_archives'] and state['profile_archive']==old['profile_archive']
paths=set(old['source_hashes'])|{str(PREVIOUS.relative_to(REPO))}
paths.update(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',ROOT.name],cwd=REPO,text=True).splitlines())
paths.discard(str((ROOT/'CONTINUATION_STATE.json').relative_to(REPO)))
paths.discard(str((ROOT/'RESULTS_PUBLICATION_RECEIPT.json').relative_to(REPO)))
state['source_hashes']={p:sha(REPO/p) for p in sorted(paths)}
state['checkpoint_integrity']={
 'source_files_bound':len(paths),'previous_state_file_unchanged':True,
 'previous_source_files':len(old['source_hashes']),'previous_sources_unchanged':unchanged,
 'explicit_current_document_changes':sorted(CURRENT_DOCS),'unexpected_previous_source_changes':0,
 'frozen_science_preflight_files_unchanged':len(freeze),'original_measurement_outputs_unchanged':len(outputs),
 'earlier_input_archive_registrations_preserved':len(old['input_archives']),
 'science_results_independently_audited':True,
 'remote_verification_recorded_in_results_publication_receipt':True}
save(ROOT/'CONTINUATION_STATE.json',state)
print(json.dumps({'source_files':len(paths),'previous_sources_unchanged':unchanged,'explicit_current_document_updates':len(changes),'state_sha256':sha(ROOT/'CONTINUATION_STATE.json')},indent=2))
