"""Summarize a closed, audited prefix without performing any signal search."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work_bj'
def read(path):return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batches',type=int,required=True)
    args=parser.parse_args();assert 1<=args.batches<=12
    start=read(WORK/'execution/CAMPAIGN_START_BJ.json');records=[]
    for number in range(1,args.batches+1):
        path=WORK/'execution'/f'batch{number:02d}'/'BATCH_CLOSED_BJ.json';entry=read(path)
        assert entry['batch']==number and entry['q_list']==list(range(25+(number-1)*8,33+(number-1)*8))
        for kind in ('search_actual','audit_actual','audit_result','complete_result'):
            assert sha(entry[kind+'_path'])==entry[kind+'_sha256']
        actual=read(entry['search_actual_path']);auditactual=read(entry['audit_actual_path']);audit=read(entry['audit_result_path'])
        for receipt in (actual,auditactual):
            assert receipt['actual_exit_code']==0 and receipt['stdout_eof'] and receipt['child_wait_completed'] and receipt['capture_error'] is None
            assert receipt['prereg_github_commit']==start['prereg_github_commit']
            assert sha(receipt['result_path'])==receipt['result_sha256']
            assert sha(receipt['log_path'])==receipt['log_sha256']==receipt['observed_stdout_sha256']
        assert audit['status']=='PASS_CLOSED_BOUNDED_REAL_RESULTS'
        records.append(entry)
    prior=read(ROOT/'work_bi/results/REAL_SEARCH_SUMMARY_BI.json')['cumulative_BG_BH_BI']
    q=[q for entry in records for q in entry['q_list']]
    tracks=sum(entry['total_track_trials'] for entry in records)
    snapshot={'schema':'SETI_BJ_AUDITED_PREFIX_CHECKPOINT_V1','created_utc':datetime.now(timezone.utc).isoformat(),
        'status':'CLOSED_AUDITED_PREFIX_OF_FROZEN_TWELVE_BATCH_CAMPAIGN','completed_prefix_batches':len(records),
        'planned_batches':12,'prereg_github_commit':start['prereg_github_commit'],'q_list':q,
        'completed_scan_band_searches':len(q)*6,'total_correlated_track_trials_including_OFF':tracks,
        'ON_catalog_rows':sum(entry['ON_catalog_rows'] for entry in records),
        'passing_flags':sum(entry['passing_flags'] for entry in records),
        'cumulative_completed_band_count':len(prior['q_list'])+len(q),
        'cumulative_correlated_track_trials_including_OFF':prior['total_correlated_track_trials_including_OFF']+tracks,
        'cumulative_channel_bin_bandwidth_Hz':prior['technical_channel_bin_bandwidth_Hz']+len(q)*4096*2.7939677238464355,
        'campaign_complete_marker_present':(WORK/'results/CAMPAIGN_COMPLETE_BJ.json').is_file(),
        'campaign_stop_marker_present':(WORK/'results/CAMPAIGN_STOP_BJ.json').is_file(),
        'batch_results':records,'new_archive_requests':0,'new_independent_observations':0,'new_unique_archive_ID_credit':0,
        'qualification':'Descriptive local-q ESS on previously exposed historical data; correlated track counts are not independent tests or new observational coverage.',
        'binary_results_status':'Retained locally for the final combined campaign package; this checkpoint records only closed audited results.'}
    path=WORK/'checkpoints'/f'AFTER_{args.batches:02d}_BATCHES_BJ.json';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:json.dump(snapshot,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'path':str(path),'completed_prefix_batches':len(records),'new_bands':len(q),'cumulative_completed_band_count':snapshot['cumulative_completed_band_count'],'ON_catalog_rows':snapshot['ON_catalog_rows'],'passing_flags':snapshot['passing_flags']}))
if __name__=='__main__':main()
