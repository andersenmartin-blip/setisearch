"""Create the current checkpoint from saved results; no acquisition or analysis."""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PREVIOUS=REPO/'work_harps_20261102_berv_followup/CONTINUATION_STATE.json'
PREVIOUS_SHA='4ed1befca06ba7a147b6653e735e40206bbac19a1915e1e9943c6b7d3d6533a6'
DOCS={'CONTINUE_SETI.md','README.md','OPTICAL_AND_RUBIN_WEEK_PLANS_2026-11-01.md','work_harps_20261101/v2/RESTORE.md'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
assert sha(PREVIOUS)==PREVIOUS_SHA
old=read(PREVIOUS);changed=[];same=0
for p,h in old['source_hashes'].items():
 actual=sha(REPO/p)
 if actual==h:same+=1
 else:
  assert p in DOCS,p
  changed.append({'path':p,'previous_sha256':h,'current_sha256':actual,'reason':'Explicit current-document update; all previous scientific files unchanged.'})
assert {r['path']for r in changed}==DOCS
save(ROOT/'PREVIOUS_SOURCE_DELTA.json',{'previous_state':str(PREVIOUS.relative_to(REPO)),'previous_state_sha256':PREVIOUS_SHA,'previous_sources':len(old['source_hashes']),'unchanged_sources':same,'intentional_current_document_changes':changed,'unexpected_changes':[]})
freeze=read(ROOT/'PREFLIGHT_FREEZE.json')['files']
for p,x in freeze.items():assert sha(REPO/p)==x['sha256'],p
out=read(ROOT/'comparison/results/OUTPUT_HASHES.json')
for p,h in out.items():assert sha(ROOT/'comparison/results'/p)==h,p
prior=REPO/'work_harps_20261102_berv_followup/prospective_comparison/results'
oldout=read(prior/'OUTPUT_HASHES.json')
for p,h in oldout.items():assert sha(prior/p)==h,p
s=copy.deepcopy(old)
s['schema']='SETI_CONTINUATION_STATE_V6_COMPLETED_MAY_QUALITY'
s['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
s['previous_continuation_state']=str(PREVIOUS.relative_to(REPO));s['previous_continuation_state_sha256']=PREVIOUS_SHA
s['completed_harps_may_quality_followup']={
 'status':'COMPLETE_ONE_PRODUCT_POSTHOC_QUALITY_PHASE_ALL_TEN_REMAIN_U','directory':ROOT.name,
 'summary':read(ROOT/'comparison/results/SUMMARY.json'),
 'header_requests':1,'payload_requests':1,'http_200_each':True,'retries':0,'redirects':0,'substitutions':0,
 'input_dp_id':'ADP.2017-05-21T01:01:50.278','raw_progenitor':'HARPS.2017-05-20T02:21:45.847',
 'input_bytes':5264640,'input_sha256':'03f551de48d9acc207612e6683ff0d0b07f3d0f2b04e16a24289073e4e51b7af',
 'berv_km_s':-9.84628486624399,'discovery_absolute_berv_delta_km_s':[36.19495827827739,37.08746856262959],
 'discovery_displacement_resolution_elements':[13.884339285152732,14.226705078425963],
 'HD122640_available_span_km_s_unchanged':40.3634787209574,
 'new_local_continuum_low_profiles':0,'new_profiles':12,'finite_positive_ERR_samples':0,
 'blue_barycentric_r_range':[0.9559329246701215,0.9791491242640842],
 'blue_topocentric_r_range':[-0.31291121287268986,0.15346022647926627],
 'blue_continuum_noise_proxy_ratio_range_rounded':[4.04,6.38],
 'V2E2_0235_barycentric_r':0.47524412758736656,'V2E2_0235_topocentric_r':-0.2989426748665057,
 'V2E2_0235_central_excursion':'Not reproduced at comparable normalized amplitude; whole-core correlation is not spike replication. Raw charge/photon ambiguity remains.',
 'interpretation':'Improved local quality at large geometric displacement supports stable barycentric morphology for five correlated blue records in three wavelength groups. No physical-origin or repeat classifier was applied.',
 'independent_numerical_checks':1571,'independent_scalar_comparisons':15096,
 'independent_header_checks':27,'independent_payload_header_checks':44,
 'audit_timing':'Final acquisition preflight report overlapped root header execution; prior source review and root exact-release check occurred before request. This overlap is retained explicitly in acquisition_audit.',
 'qualified_candidate':False,'qualified_null':False,'main_survey_changed':False,
 'report':str((ROOT/'comparison/results/README.md').relative_to(REPO)),
 'scientific_review':str((ROOT/'scientific_review/ACTUAL_SCIENTIFIC_REVIEW.json').relative_to(REPO))}
s['next_action']={
 'kind':'PREPARE_QUANTITATIVE_SPATIAL_SUPPORT_DIAGNOSTIC_EXISTING_V2E2_0235_RAW',
 'handoff_path':str((ROOT/'scientific_review/NEXT_STEP.md').relative_to(REPO)),
 'event':'V2E2-0235','target':'HD122640','discovery_dp_id':'ADP.2023-02-23T01:01:36.791',
 'raw_id':'HARPS.2023-02-22T07:40:53.531','ancillary_id':'ADP.2023-02-23T01:01:36.792',
 'native_order':50,'native_pixel':956,'registered_detector_row':3139,'registered_detector_column':2323.7701943175816,
 'action':'Verify saved raw/native evidence and exact archived inputs; freeze central cutout, flank-trained trace template, coordinate-selected controls, background and spatial residual metrics before analysis. Quantify on-trace versus compact off-trace support. No old classifier rerun, no new May epoch or origin promotion. Retain U if ambiguous.',
 'scope':'One separate posthoc diagnostic of already-saved discovery data. A fresh bounded method is needed; this checkpoint does not execute it.',
 'next_diagnostic_frozen':False,'next_diagnostic_executed':False,
 'new_archive_requests_planned':0,'new_May_products_selected':0,
 'remaining_saved_metadata_pool':{'total':15,'May2017':8,'January2018':7,'automatic_execution_queue':False},
 'rubin_status':'STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET','rubin_remaining_unique_main_capacity':310,
 'no_background_execution':True,
 'standing_authorization':'The user requested autonomous continuation and public GitHub documentation. Prepare and execute the concrete bounded diagnostic without unnecessary permission requests; scientific freezes are not user-approval gates.'}
s['harps_next_metadata_handoff']={'status':'SUPERSEDED_BY_COMPLETED_MAY_QUALITY_PHASE','historical_handoff':str((PREVIOUS.parent/'next_followup/HANDOFF.json').relative_to(REPO)),'current_next_action':s['next_action']['handoff_path']}
s['after_pending_raw_review']=[
 'Completed all669 raw reviews, all35 mapping diagnoses, two normalization followups and original336-event/4370-profile epoch comparison; do not replay.',
 'Completed Rubin188+2 objects, only2primary/4secondary numerical objects with overlap; min50 unmet, no qualified null; current data route stopped.',
 'Completed two reference phases: prior2spectra/24profiles and separate1spectrum/12profiles, sixHD122640records each. FourHD135204records remain uncovered and all10U unchanged.',
 'Next: one bounded spatial-support diagnostic for the saved V2E2-0235 discovery raw order50, after a new exact method freeze. No automatic May expansion.']
s['limits']=[
 'Original300-exposure full-spectrum search and669 dispositions unchanged; three additional archival spectra are targeted follow-up inputs, not three new full-spectrum searches.',
 'All10 studied U labels remain; correlated blue events form three wavelength groups, not five independent detections.',
 'This quality phase is explicitly posthoc. Selection used saved average metadata SNR, and all twelve outcomes are retained.',
 'Current12profiles have no low-continuum flag, but ERR has no finite positive samples. Ratios and fits are descriptive, not calibrated SNR or significance.',
 'The closed earlier May22 reference still has ten low-continuum blue profiles; no previous result was removed or replaced.',
 'Barycentric coherence is not a stellar-rest-frame or physical-origin determination; stellar RV, instrumental era, wavelength and extraction effects remain.',
 'V2E2-0235 whole-core r=.475 does not reproduce the sharp discovery spike. Its charge/photon ambiguity is unresolved; nonrepetition alone cannot classify it.',
 'No global sensitivity, calibrated false-alarm rate, physical-origin qualification, or calibrated null.',
 'Rubin remains alert-selected bounded feasibility: only2primary/4secondary numerical objects, overlapping populations, min50 unmet and quality/cadence/Gaia caveats unchanged.',
 'Audits are independent calculations/AI reviews, not human peer review or independent telescope observations.']
s['quality_followup_archives']={'input':read(ROOT/'preservation/SCIENCE_INPUTS_MANIFEST.json'),'profiles':read(ROOT/'preservation/PROFILE_EVIDENCE_MANIFEST.json'),'restore_existing_references':str((ROOT/'preservation/restore_reference_cache.py').relative_to(REPO))}
s['publication']={'branches':['main','optical-harps-week-20261101'],'turn_baseline_commit':'d750ea5a716035311c028836f7e3a565b7bb1827','prospective_method_commit':'d8e16e5586d0538b0733b41ae1d497b0fd0aaeef','verified_header_commit':'81e33f8cc97fac06565129e563bd7c8b0f97f264','exact_input_commit_before_new_arrays':'318b4201273aad853899c52dfe2a3e025bb686e6','results_receipt_path':str((ROOT/'RESULTS_PUBLICATION_RECEIPT.json').relative_to(REPO)),'receipt_created_after_results_commit':True,'previous_checkpoint_publication':old['publication']}
assert s['science']==old['science'] and s['input_archives']==old['input_archives'] and s['profile_archive']==old['profile_archive']
paths=set(old['source_hashes'])|{str(PREVIOUS.relative_to(REPO))}
paths.update(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',ROOT.name],cwd=REPO,text=True).splitlines())
paths-={str((ROOT/n).relative_to(REPO))for n in ['CONTINUATION_STATE.json','RESULTS_PUBLICATION_RECEIPT.json']}
s['source_hashes']={p:sha(REPO/p)for p in sorted(paths)}
s['checkpoint_integrity']={'source_files_bound':len(paths),'previous_state_unchanged':True,'previous_sources':len(old['source_hashes']),'previous_sources_unchanged':same,'explicit_current_document_changes':sorted(DOCS),'unexpected_previous_source_changes':0,'frozen_files_unchanged':len(freeze),'new_measurement_outputs_unchanged':len(out),'prior_measurement_outputs_unchanged':len(oldout),'all_original_dispositions_unchanged':True,'all_prior_archive_registrations_preserved':True,'science_results_independently_audited':True}
save(ROOT/'CONTINUATION_STATE.json',s)
print(json.dumps({'sources':len(paths),'previous_unchanged':same,'intentional_docs_changed':len(changed),'state_sha256':sha(ROOT/'CONTINUATION_STATE.json')},indent=2))
