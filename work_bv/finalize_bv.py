"""Aggregate the completed fixed BV search without changing its classifications."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; BV=ROOT/'work_bv'
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
plan=read(BV/'BV_PARTIAL_PLAN.json');ph=sha(BV/'BV_PARTIAL_PLAN.json');serial=read(BV/'execution/SERIAL_RUN_RESULT.json')
assert serial['status']=='PASS' and serial['all_planned_batches_completed'] and len(serial['completed_batches'])==28 and serial['plan_sha256']==ph
scans=[dict(scan=s['scan'],role=s['role'],target=s['target'],archive_id=s['archive_id'],local_hits=0,track_combinations=0,maximum_local_ess=-1,peak=None) for s in plan['scans']]
labels=['REJECTED_AVAILABLE_OFF','INCOMPLETE_OFF_COVERAGE','THREE_ON_FAIL','UNSUPPORTED'];counts={k:0 for k in labels};batches=[];nonempty=[];reviews=[];allqs=[]
for n,qs in enumerate(plan['batch_q_lists'],1):
    exe=BV/f'execution/batch{n}';out=Path(f'/dev/shm/seti_bv_partial_20261031/batch{n}/contents')
    child=read(exe/'payload/RESULT.json');capture=read(exe/'ACTUAL_RECEIPT.json');parent=read(exe/'PARENT_EXPORT_VERIFICATION.json');auditcap=read(BV/f'audit_execution/batch{n}/ACTUAL_RECEIPT.json');review=read(BV/f'review/BATCH{n}_INDEPENDENT_REVIEW.json');batch=read(out/'BATCH_COMPLETE.json')
    assert child['status']==capture['status']==parent['status']==auditcap['status']=='PASS'
    assert capture['actual_exit_code']==auditcap['actual_exit_code']==0 and capture['stdout_eof'] and auditcap['stdout_eof']
    assert sha(exe/'payload/RESULT.json')==capture['result_sha256'] and sha(exe/'payload/EVIDENCE.zip')==child['archive']['sha256']
    assert review['status']=='PASS_BOUNDED_INDEPENDENT_REVIEW' and review['plan_sha256']==batch['plan_sha256']==ph
    assert review['batch_complete_sha256']==sha(out/'BATCH_COMPLETE.json') and batch['q_list']==qs
    allqs+=qs;reviews.append(review)
    for q in batch['results']:
        a=q['association']
        for k in labels:counts[k]+=a['status_counts'][k]
        if a['ON_local_catalog_rows']:nonempty.append(dict(q=q['q'],ON_seed_rows=a['ON_local_catalog_rows'],three_ON_pass_rows=a['three_ON_pass_rows'],available_OFF_veto_rows=a['available_OFF_veto_rows'],status_counts=a['status_counts']))
        for s in q['scans']:
            dest=scans[s['scan']];dest['local_hits']+=s['local_hits'];dest['track_combinations']+=s['track_trials']
            w=max(s['width_searches'],key=lambda z:z['maximum_local_ess']);mx=w['maximum_local_ess']
            if mx>dest['maximum_local_ess']:
                width=w['width_channels']
                with np.load(out/f'q{q["q"]:03d}/scan{s["scan"]}_grid.npz',allow_pickle=False) as g:
                    v=g[f'max_ess_width_{width}'];k=int(np.argmax(v));assert float(v[k])==mx;ri=int(g[f'max_drift_index_width_{width}'][k]);center=int(g[f'centers_width_{width}'][k]);scope=plan['scans'][s['scan']]
                    dest['maximum_local_ess']=mx;dest['peak']=dict(q=q['q'],width_channels=width,native_center=center,drift_hz_s=float(g['drift_hz_s'][ri]),frequency_mhz=scope['fch1_mhz']+center*scope['df_hz']/1e6)
    batches.append(dict(batch=n,q_list=qs,track_combinations=batch['track_trials'],ON_seed_rows=review['ON_seed_rows_all_semantically_reviewed'],status_counts=review['status_counts'],production_status=capture['status'],parent_export_status=parent['status'],independent_capture_status=auditcap['status'],independent_review_status=review['status'],actual_production_exit_code=0,actual_review_exit_code=0,production_stdout_eof=True,review_stdout_eof=True,child_wall_seconds=child['wall_seconds'],archive_bytes=child['archive']['bytes'],archive_sha256=child['archive']['sha256'],archive_path=str(exe/'payload/EVIDENCE.zip'),independent_review_sha256=sha(BV/f'review/BATCH{n}_INDEPENDENT_REVIEW.json')))
assert allqs==list(range(33,254));total=sum(s['track_combinations'] for s in scans);assert total==9968125440
on_rows=sum(s['local_hits'] for s in scans if s['role']=='ON');assert on_rows==sum(counts.values())==sum(r['ON_seed_rows_all_semantically_reviewed'] for r in reviews)
summary=dict(schema='SETI_BV_REMAINING_SAFE_Q_RESULT_V1',status='COMPLETED_FIVE_SCAN_PARTIAL_CONTINUATION',completed_utc=datetime.now(timezone.utc).isoformat(),target='HIP44295',primary_id=65133,public_freeze_commit=read(BV/'PUBLIC_FREEZE_RECEIPT_BV.json')['public_commit_sha'],plan_sha256=ph,serial_result_sha256=sha(BV/'execution/SERIAL_RUN_RESULT.json'),serial_wall_seconds=serial['wall_seconds'],scans=scans,batches=batches,
    newly_searched_q=allqs,new_q_count=221,new_scan_q_count=1105,new_correlated_track_combinations=total,new_ON_correlated_track_combinations=sum(s['track_combinations'] for s in scans if s['role']=='ON'),new_carrier_bin_width_mhz=2.529144287109375,
    combined_BU_BV=dict(q_list=list(range(1,254)),q_count=253,scan_q_count=1265,correlated_track_combinations=11411473920,carrier_bin_width_mhz=2.895355224609375,frequency_max_mhz=plan['scans'][0]['fch1_mhz']+4096*plan['scans'][0]['df_hz']/1e6,frequency_min_mhz=plan['scans'][0]['fch1_mhz']+(254*4096-1)*plan['scans'][0]['df_hz']/1e6,BU_result_commit='4d0b0d44d23575fa486ab8c69559c246edd865a3'),
    all_scan_catalog_rows=sum(s['local_hits'] for s in scans),ON_seed_rows=on_rows,partial_status_counts=counts,nonempty_q=nonempty,maximum_local_ess=max(s['maximum_local_ess'] for s in scans),threshold_ess=10,available_OFF_flag_threshold_ess=5,
    review=dict(independent_scalar_checks=sum(r['independent_scalar_audit_sums'] for r in reviews),independent_calibration_vectors=sum(r['independent_calibration_vectors'] for r in reviews),independent_selected_forced_measurement_slots=sum(r['independent_selected_forced_measurement_slots'] for r in reviews),maximum_sampled_scalar_error=max(r['maximum_scalar_sum_error'] for r in reviews),maximum_sampled_calibration_error=max(r['maximum_calibration_error'] for r in reviews),maximum_selected_forced_ess_error=max(r['maximum_selected_forced_ess_error'] for r in reviews),independent_native_anchor_pairs_checked=reviews[0]['normalization_review']['independent_native_anchor_pairs_checked'],normalized_support_values_reconstructed_first_batch=reviews[0]['normalization_review']['normalized_support_values_exactly_reconstructed'],limits='All association rows semantically checked; bounded direct numerical samples, not a second full search. Additional three-ON posthoc review is reported separately.'),
    complete_OFF_support=False,missing_scan=5,full_cadence_candidate_assessment='NOT_EVALUABLE_MISSING_OFF5',global_false_alarm_probability=None,calibrated_sensitivity=None,new_observation_epochs=0,new_archive_requests=0,new_original_technical_coverage_mhz_visits=0,new_original_unique_archive_ids=0,authoritative_unique_archive_ids=486,authoritative_technical_MHz_visits=268.50128173828125,queue_advanced=False,historical_failures_preserved=True,background_science_jobs_running=False,
    interpretation='Correlated threshold-crossing rows are not independent candidates. No row passes the defined three-ON/available-OFF screen. This remains a five-scan partial analysis, not a complete-cadence null result, sensitivity bound or origin claim.',
    power_contact_scope='Previously decoded full native arrays were already normalized in BU; BV adds first detector scoring only in q33..253.',
    continuation=dict(remaining_prequalified_safe_q=[],excluded_boundary_q=[0,254,255],full_original_cadence_complete=False,missing_input='OFF scan5 remains incomplete; original remaining rows/repeat and complete acquisition proof require normal permitted archive access.',next_queued_targets=['HIP58684/65193','HIP59280/65205'],do_not_relabel_old_scored_data_as_new=True))
assert counts['INCOMPLETE_OFF_COVERAGE']==0 and counts['UNSUPPORTED']==0
with (BV/'SUMMARY_BV.json').open('x') as f:json.dump(summary,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
print(json.dumps(summary))
