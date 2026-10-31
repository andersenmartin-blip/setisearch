"""Bind the published aggregate to the independently reviewed closed results."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[2];BV=ROOT/'work_bv'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
s=read(BV/'SUMMARY_BV.json');c=read(BV/'review/FINAL_CLOSURE_REVIEW_BV.json');x=read(BV/'review/THREE_ON_REVIEW_BV.json');p=read(BV/'BV_PARTIAL_PLAN.json');bu=read(ROOT/'work_bu/SUMMARY_BU.json')
need(c['status']=='PASS_PARTIAL_EXPLORATORY_CLOSURE' and x['status']=='PASS_ALL_THREE_ON_ROWS_REJECTED_BY_AVAILABLE_OFF','Independent results not passed')
need(s['plan_sha256']==c['plan_sha256']==x['plan_sha256']==sha(BV/'BV_PARTIAL_PLAN.json'),'Plan binding differs')
for sk,ck in [('new_correlated_track_combinations','correlated_track_combinations'),('new_ON_correlated_track_combinations','ON_correlated_track_combinations'),('new_carrier_bin_width_mhz','channel_bin_width_mhz'),('all_scan_catalog_rows','all_scan_catalog_hits'),('ON_seed_rows','ON_seed_rows'),('maximum_local_ess','maximum_local_ess'),('partial_status_counts','status_counts'),('newly_searched_q','q_list')]:need(s[sk]==c[ck],'Aggregate differs: '+sk)
need([r['local_hits'] for r in s['scans']]==c['per_scan_catalog_hits'] and [r['maximum_local_ess'] for r in s['scans']]==c['per_scan_maximum_local_ess'],'Per-scan aggregate differs')
need(sum(r['track_combinations'] for r in s['scans'])==c['correlated_track_combinations'],'Per-scan trial total differs')
for scan,scope in zip(s['scans'],p['scans']):
    peak=scan['peak'];need(peak['frequency_mhz']==scope['fch1_mhz']+peak['native_center']*scope['df_hz']/1e6,'Peak frequency differs')
    need(peak['native_center']==524288 and peak['frequency_mhz']==2300.390625,'Declared common peak location differs')
review=s['review'];audit=c['independent_audit_totals']
for sk,ck in [('independent_scalar_checks','scalar'),('independent_calibration_vectors','vectors'),('independent_native_anchor_pairs_checked','anchors'),('independent_selected_forced_measurement_slots','forced_slots'),('normalized_support_values_reconstructed_first_batch','reconstructed_values')]:need(review[sk]==audit[ck],'Numerical audit count differs')
need(s['new_q_count']==221 and s['new_scan_q_count']==1105,'New carrier scope differs')
combined=s['combined_BU_BV'];need(combined['q_list']==bu['q_list']+c['q_list']==list(range(1,254)),'Combined carrier scope differs')
need(combined['correlated_track_combinations']==bu['correlated_track_combinations']+c['correlated_track_combinations']==11411473920,'Combined tracks differ')
need(combined['carrier_bin_width_mhz']==bu['channel_bin_width_mhz']+c['channel_bin_width_mhz']==2.895355224609375,'Combined bin bandwidth differs')
need(s['missing_scan']==5 and s['complete_OFF_support'] is False and s['full_cadence_candidate_assessment']=='NOT_EVALUABLE_MISSING_OFF5','Missing control overclaimed')
need(s['new_original_technical_coverage_mhz_visits']==s['new_original_unique_archive_ids']==0 and not s['queue_advanced'],'Original coverage advanced')
need(s['authoritative_unique_archive_ids']==486 and s['authoritative_technical_MHz_visits']==268.50128173828125,'Authority changed')
need(s['global_false_alarm_probability'] is None and s['calibrated_sensitivity'] is None and not s['background_science_jobs_running'],'Qualification/process claims differ')
need(x['three_ON_rows_reviewed']==c['three_ON_rows']==67 and c['status_counts']['REJECTED_AVAILABLE_OFF']==67,'Posthoc three-ON count differs')
need(x['all_three_ON_and_available_OFF_rejections_reproduced'] and x['maximum_calibration_error']==x['maximum_forced_ess_error']==0,'Posthoc numerical outcome differs')
result=dict(schema='SETI_BV_INDEPENDENT_SUMMARY_BINDING_REVIEW_V1',status='PASS_SUMMARY_MATCHES_INDEPENDENT_CLOSURE',completed_utc=datetime.now(timezone.utc).isoformat(),summary_sha256=sha(BV/'SUMMARY_BV.json'),closure_sha256=sha(BV/'review/FINAL_CLOSURE_REVIEW_BV.json'),posthoc_three_ON_sha256=sha(BV/'review/THREE_ON_REVIEW_BV.json'),reviewer_source_sha256=sha(__file__),plan_sha256=c['plan_sha256'],combined_BU_BV_correlated_tracks=combined['correlated_track_combinations'],combined_carrier_bin_width_mhz=combined['carrier_bin_width_mhz'],all_three_ON_rows_independently_rejected_by_available_OFF=67,common_peak_native_center=524288,common_peak_frequency_mhz=2300.390625,complete_OFF_support=False,original_coverage_credit=0,qualification='Descriptive partial results; common instrumental-looking location is not a proven origin attribution.')
target=BV/'review/SUMMARY_BINDING_REVIEW_BV.json'
with target.open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(dict(status=result['status'],sha256=sha(target),summary_sha256=result['summary_sha256'])),flush=True)
