"""Read-only post-search aggregation and byte-preserving evidence packaging."""
from pathlib import Path
import hashlib,json,shutil,zipfile,sys
from datetime import datetime,timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
BU=ROOT/'work_bu'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,j):
    with Path(p).open('x') as f:json.dump(j,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
plan=read(BU/'BU_PARTIAL_PLAN.json');ph=sha(BU/'BU_PARTIAL_PLAN.json');scans=[]
for s in plan['scans']:scans.append(dict(scan=s['scan'],role=s['role'],target=s['target'],archive_id=s['archive_id'],local_hits=0,track_combinations=0,maximum_local_ess=-1,peak=None))
batches=[];maps_checked=0;total_tracks=0
for n in range(1,5):
    exe=BU/f'execution/batch{n}';out=Path(f'/dev/shm/seti_bu_partial_20261031/batch{n}/contents')
    child=read(exe/'payload/RESULT.json');capture=read(exe/'ACTUAL_RECEIPT.json');parent=read(exe/'PARENT_EXPORT_VERIFICATION.json');review=read(BU/f'review/BATCH{n}_INDEPENDENT_REVIEW.json');batch=read(out/'BATCH_COMPLETE.json')
    assert child['status']==capture['status']==parent['status']=='PASS'
    assert capture['actual_exit_code']==0 and capture['stdout_eof'] and sha(exe/'payload/RESULT.json')==capture['result_sha256']
    assert review['status']=='PASS_BOUNDED_INDEPENDENT_REVIEW' and review['plan_sha256']==batch['plan_sha256']==ph
    assert review['batch_complete_sha256']==sha(out/'BATCH_COMPLETE.json')
    assert batch['q_list']==plan['batch_q_lists'][n-1]
    assert child['archive']['sha256']==sha(exe/'payload/EVIDENCE.zip')
    for q in batch['results']:
        for s in q['scans']:
            dst=scans[s['scan']];dst['local_hits']+=s['local_hits'];dst['track_combinations']+=s['track_trials'];total_tracks+=s['track_trials']
            with np.load(out/f'q{q["q"]:03d}/scan{s["scan"]}_grid.npz',allow_pickle=False) as grid:
                for w in s['width_searches']:
                    width=w['width_channels'];a=grid[f'max_ess_width_{width}'];assert np.isfinite(a).all();mx=float(a.max());assert mx==w['maximum_local_ess'];assert mx<10;maps_checked+=len(a)
                    if mx>dst['maximum_local_ess']:
                        k=int(np.argmax(a));ri=int(grid[f'max_drift_index_width_{width}'][k]);center=int(grid[f'centers_width_{width}'][k]);scope=plan['scans'][s['scan']]
                        dst['maximum_local_ess']=mx;dst['peak']=dict(q=q['q'],width_channels=width,native_center=center,drift_hz_s=float(grid['drift_hz_s'][ri]),frequency_mhz=scope['fch1_mhz']+center*scope['df_hz']/1e6)
    batches.append(dict(batch=n,q_list=batch['q_list'],track_combinations=batch['track_trials'],ON_seed_rows=review['ON_seed_rows_all_semantically_reviewed'],capture_status=capture['status'],parent_export_status=parent['status'],independent_review_status=review['status'],actual_exit_code=0,stdout_eof=True,child_wall_seconds=child['wall_seconds'],archive_bytes=child['archive']['bytes'],archive_sha256=child['archive']['sha256'],archive_path=str(exe/'payload/EVIDENCE.zip'),independent_review_sha256=sha(BU/f'review/BATCH{n}_INDEPENDENT_REVIEW.json'),process_output_yielded_to_session=True))
assert total_tracks==1443348480 and sum(s['local_hits'] for s in scans)==0
summary=dict(schema='SETI_BU_PARTIAL_FIRST_SEARCH_RESULT_V1',status='COMPLETED_FIVE_SCAN_PARTIAL_EXPLORATORY_SEARCH',completed_utc=datetime.now(timezone.utc).isoformat(),target='HIP44295',primary_id=65133,public_freeze_commit=read(BU/'PUBLIC_FREEZE_RECEIPT_BU.json')['public_commit_sha'],plan_sha256=ph,
    first_detector_search_of_previously_acquired_2016_data=True,previously_decoded_data=True,new_observation_epochs=0,scans=scans,batches=batches,q_list=list(range(1,33)),correlated_track_combinations=total_tracks,ON_correlated_track_combinations=866009088,
    frequency_max_mhz=2301.844024658203,frequency_min_mhz=2301.477816514671,channel_bin_width_mhz=0.3662109375,
    all_scan_catalog_hits=0,ON_catalog_hits=0,maximum_local_ess=max(s['maximum_local_ess'] for s in scans),threshold_ess=10,
    stored_per_center_maxima_checked=maps_checked,all_stored_maxima_finite_and_below_threshold=True,
    review=dict(independent_scalar_checks=5760,independent_calibration_vectors=1920,maximum_sampled_scalar_error=0,maximum_sampled_calibration_error=0,independent_native_anchor_pairs_checked=20480,normalized_support_values_exactly_reconstructed_first_batch=3276800,nonempty_real_associations_tested=0,limits='Bounded direct numerical review, not an independent second full search. Empty catalogs provide no nonempty astronomical association test.'),
    complete_OFF_support=False,missing_scan=5,full_cadence_candidate_assessment='NOT_EVALUABLE_MISSING_OFF5',new_original_technical_coverage_mhz_visits=0,new_original_unique_archive_ids=0,authoritative_unique_archive_ids=486,authoritative_technical_MHz_visits=268.50128173828125,queue_advanced=False,global_false_alarm_probability=None,calibrated_sensitivity=None,
    power_contact_scope='All five full native arrays were normalized, including unscreened channels. Only q1..32 carrier cores were searched; unsearched channels are not power-unseen or held out.',
    interpretation='No threshold crossing under the frozen local-ESS family in this finite partial band. This is neither a complete-cadence null result nor an extraterrestrial detection or sensitivity bound.',
    historical_failures_preserved=True,background_science_jobs_running=False,
    continuation=dict(next_unsearched_q=33,remaining_safe_q=list(range(33,254)),next_proposed_q=list(range(33,65)),requires_new_prospective_scope=True,original_missing_input='Complete OFF scan5 plus original acquisition proof/repeat remain outstanding; no archive bypass authorized.'))
write(BU/'SUMMARY_BU.json',summary)
print(json.dumps(summary,indent=2))
