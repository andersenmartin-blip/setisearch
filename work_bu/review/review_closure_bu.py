"""Independent post-search BU closure review using closed archive bytes only."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib, io, json, os, zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BU=ROOT/'work_bu'

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())
def need(ok,message):
    if not ok:raise ValueError(message)

def main():
    summary=read(BU/'SUMMARY_BU.json'); summary_sha=sha(BU/'SUMMARY_BU.json')
    plan=read(BU/'BU_PARTIAL_PLAN.json'); ph=sha(BU/'BU_PARTIAL_PLAN.json')
    freeze=read(BU/'PUBLIC_FREEZE_RECEIPT_BU.json')
    need(ph==summary['plan_sha256']==freeze['plan_sha256'],'Plan identity differs')
    need(freeze['exact_readback_verified'] and freeze['before_execution'],'Public freeze missing')
    for path,digest in plan['source_sha256'].items():need(sha(path)==digest,'Frozen source changed: '+path)
    for scope in plan['scans']:
        need(sha(scope['path'])==scope['input_sha256'],'Canonical input changed')
        need(sha(scope['header_path'])==scope['header_sha256'],'Header changed')
    for pin in plan['metadata_evidence']:need(sha(pin['path'])==pin['sha256'],'Metadata evidence changed')
    maximum=[-np.inf]*5; tracks=[0]*5; hits=[0]*5; maps=0; batches=[]; totals={'scalar':0,'vectors':0,'anchors':0,'reconstructed_values':0,'forced_slots':0}; all_q=[]
    for batch_number in range(1,5):
        base=BU/f'execution/batch{batch_number}'
        capture=read(base/'ACTUAL_RECEIPT.json'); parent=read(base/'PARENT_EXPORT_VERIFICATION.json'); result=read(base/'payload/RESULT.json')
        reviewpath=BU/f'review/BATCH{batch_number}_INDEPENDENT_REVIEW.json';review=read(reviewpath)
        need(capture['status']==parent['status']==result['status']=='PASS','Capture/export/result failure')
        need(capture['actual_exit_code']==0 and capture['child_wait_completed'] and capture['stdout_eof'] and capture['natural_stdout_eof'],'Child not naturally closed')
        need(not capture['killed'] and capture['descendant_cleanup_completed'] and capture['remaining_live_descendants']==[],'Child cleanup incomplete')
        need(sha(base/'payload/RESULT.json')==capture['result_sha256']==capture['terminal_stdout_json']['result_sha256'],'Result pin mismatch')
        need(sha(base/'STDOUT.log')==capture['log_sha256']==capture['observed_stdout_sha256'],'Captured stdout changed')
        need(capture['source_pins_verified_before'] and capture['source_pins_verified_after'],'Capture source pins incomplete')
        need(all(result[key] for key in ['source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after']),'Worker source/input pin check incomplete')
        need(result['source_pins_before']==result['source_pins_after']==result['final_source_pins_after_export'],'Worker source identities changed')
        need(result['input_pins_before']==result['input_pins_after']==result['final_input_pins_after_export'],'Worker input identities changed')
        need(review['status']=='PASS_BOUNDED_INDEPENDENT_REVIEW' and review['plan_sha256']==ph,'Independent review not bound/passing')
        need(review['all_saved_output_files_unchanged_during_review'],'Independent saved output changed')
        need(review['maximum_scalar_sum_error']==review['maximum_calibration_error']==0,'Reported bounded exactness differs')
        totals['scalar']+=review['independent_scalar_audit_sums'];totals['vectors']+=review['independent_calibration_vectors'];totals['forced_slots']+=review['independent_selected_forced_measurement_slots']
        totals['anchors']+=review['normalization_review'].get('independent_native_anchor_pairs_checked',0)
        totals['reconstructed_values']+=review['normalization_review'].get('normalized_support_values_exactly_reconstructed',0)
        archive_path=base/'payload/EVIDENCE.zip';archive_sha=sha(archive_path)
        need(archive_sha==result['archive']['sha256']==parent['archive']['sha256']==summary['batches'][batch_number-1]['archive_sha256'],'Archive digest mismatch')
        with zipfile.ZipFile(archive_path) as archive:
            names=archive.namelist();need(len(names)==len(set(names)),'Duplicate archive member')
            manifest=json.loads(archive.read('ARCHIVE_MANIFEST.json'));members=manifest['members']
            need(manifest['schema']=='SETI_BT_ARCHIVE_MANIFEST_V1' and members==parent['archive']['members']==result['archive']['members'],'Archive manifest differs')
            need(set(names)=={item['path'] for item in members}|{'ARCHIVE_MANIFEST.json'},'Archive membership differs')
            for item in members:
                path=PurePosixPath(item['path']);need(not path.is_absolute() and '..' not in path.parts,'Unsafe member')
                raw=archive.read(item['path'])
                need(len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],'Archive CRC/size/hash failure')
            batchraw=archive.read('BATCH_COMPLETE.json');batch=json.loads(batchraw)
            need(hashlib.sha256(batchraw).hexdigest()==review['batch_complete_sha256'],'Independent result binding differs')
            need(batch['q_list']==plan['batch_q_lists'][batch_number-1]==review['q_list'],'Batch q scope differs')
            all_q.extend(batch['q_list'])
            need(batch['track_trials']==360837120 and batch['plan_sha256']==ph,'Batch trial/plan mismatch')
            need(batch['complete_OFF_support'] is False and batch['original_coverage_credit']==0,'Partial coverage misclaimed')
            for complete in batch['results']:
                q=complete['q'];need(json.loads(archive.read(f'q{q:03d}/PARTIAL_Q_COMPLETE.json'))==complete,'Q nested record differs')
                need(complete['association']['ON_local_catalog_rows']==0 and complete['association']['complete_OFF_support'] is False,'Association scope differs')
                with np.load(io.BytesIO(archive.read(f'q{q:03d}/PARTIAL_ASSOCIATION.npz')),allow_pickle=False) as arrays:
                    need(arrays['forced_center_local_ess'].shape==(0,6) and arrays['forced_valid'].shape==(0,6),'Empty association six-slot shape differs')
                    need(arrays['complete_OFF_support'].size==0 and arrays['candidate_status'].size==0,'Unexpected real association')
                for scan in complete['scans']:
                    i=scan['scan'];tracks[i]+=scan['track_trials'];hits[i]+=scan['local_hits']
                    need(scan['local_hits']==0 and scan['track_trials']==9020928,'Scan trials/hits differ')
                    with np.load(io.BytesIO(archive.read(f'q{q:03d}/scan{i}_catalog.npz')),allow_pickle=False) as cat:
                        need(all(cat[key].size==0 for key in cat.files),'Nonempty catalog exists')
                    with np.load(io.BytesIO(archive.read(f'q{q:03d}/scan{i}_grid.npz')),allow_pickle=False) as grid:
                        for w in scan['width_searches']:
                            values=grid[f'max_ess_width_{w["width_channels"]}'];maps+=len(values)
                            need(np.isfinite(values).all() and (values<10).all(),'Stored maximum crosses threshold or is nonfinite')
                            peak=float(values.max());need(peak==w['maximum_local_ess'],'Summary maximum differs')
                            maximum[i]=max(maximum[i],peak)
        need(sha(archive_path)==archive_sha,'Archive changed during closure review')
        batches.append({'batch':batch_number,'archive_sha256':archive_sha,'archive_bytes':archive_path.stat().st_size,'members_fully_CRC_size_SHA256_verified':len(members),'capture_sha256':sha(base/'ACTUAL_RECEIPT.json'),'independent_review_sha256':sha(reviewpath),'natural_stdout_eof':True,'actual_exit_code':0})
    need(all_q==list(range(1,33)),'Q coverage differs')
    need(sum(tracks)==summary['correlated_track_combinations']==1443348480,'Total trials differ')
    need(sum(tracks[i] for i in (0,2,4))==summary['ON_correlated_track_combinations']==866009088,'ON trials differ')
    need(maps==summary['stored_per_center_maxima_checked']==1720320,'Maximum map count differs')
    need(maximum==[s['maximum_local_ess'] for s in summary['scans']] and hits==[0]*5,'Overall maxima/catalog counts differ')
    need(sum(hits)==summary['all_scan_catalog_hits']==summary['ON_catalog_hits']==0,'Total hits differ')
    need(32*4096*abs(plan['scans'][0]['df_hz'])/1e6==summary['channel_bin_width_mhz']==0.3662109375,'Channel bin bandwidth differs')
    need(summary['complete_OFF_support'] is False and summary['missing_scan']==5 and summary['full_cadence_candidate_assessment']=='NOT_EVALUABLE_MISSING_OFF5','Incomplete cadence misclassified')
    need(summary['new_original_technical_coverage_mhz_visits']==summary['new_original_unique_archive_ids']==0 and not summary['queue_advanced'],'Original coverage advanced')
    need(summary['authoritative_unique_archive_ids']==486 and summary['authoritative_technical_MHz_visits']==268.50128173828125,'Historical authority differs')
    need(totals=={'scalar':5760,'vectors':1920,'anchors':20480,'reconstructed_values':3276800,'forced_slots':0},'Independent audit totals differ')
    need(summary['review']['nonempty_real_associations_tested']==0,'Empty real-data associations overclaimed')
    need(sha(BU/'SUMMARY_BU.json')==summary_sha and sha(BU/'BU_PARTIAL_PLAN.json')==ph,'Summary or plan changed')
    return {'schema':'SETI_BU_INDEPENDENT_FINAL_CLOSURE_REVIEW_V1','status':'PASS_PARTIAL_EXPLORATORY_CLOSURE','completed_utc':datetime.now(timezone.utc).isoformat(),'reviewer_source_sha256':sha(__file__),'summary_sha256':summary_sha,'plan_sha256':ph,'public_freeze_commit':freeze['public_commit_sha'],'frozen_sources_and_inputs_still_exact':True,'closed_captures_verified':4,'closed_archives_independently_verified':batches,'q_list':all_q,'correlated_track_combinations':sum(tracks),'ON_correlated_track_combinations':sum(tracks[i] for i in (0,2,4)),'channel_bin_width_mhz':0.3662109375,'all_scan_catalog_hits':0,'stored_per_center_maxima_rechecked':maps,'per_scan_maximum_local_ess':maximum,'maximum_local_ess':max(maximum),'threshold_ess':10,'independent_audit_totals':totals,'nonempty_real_associations_tested':0,'complete_OFF_support':False,'full_cadence_candidate_assessment':'NOT_EVALUABLE_MISSING_OFF5','original_coverage_credit':0,'historical_authority_unchanged':True,'limits':['No second full search performed; prior bounded numerical reviews reused and their exact receipts verified.','All4closedZIPs independently checked member-by-member for CRC/size/SHA256; every savedmaximum andcatalog rechecked.','No nonempty real association occurred; this does not qualify nonempty astronomical association behavior.','Missing OFF5 prevents full-cadence qualification; no FAP, sensitivity, origin or complete-cadence null claim.','Frozen source review originally covered earlierwrapper hash; finalwrapper delta reviewed by root beforefreeze, and finalfrozenpins remain exact.']}

if __name__=='__main__':
    result=main();path=BU/'review/FINAL_CLOSURE_REVIEW_BU.json'
    with path.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'path':str(path),'sha256':sha(path),'tracks':result['correlated_track_combinations'],'maximum_local_ess':result['maximum_local_ess']}))
