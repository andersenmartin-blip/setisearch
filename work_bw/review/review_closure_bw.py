"""Independent BW closure of one sealed q254 five-scan partial search.

No production numerical code is imported or recomputed. The sealed ZIP supplies
all saved maxima, catalogs and association values. Direct numerical checks come
from the separately captured bounded audit. Missing OFF5 remains unqualified.
Run only after production and its independent numerical audit have closed.
"""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse,hashlib,io,json,os,signal,time,zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2];BW=ROOT/'work_bw'
WIDTHS=(1,3,9,33);STRIDES=(1,1,2,8)
STATES=('REJECTED_AVAILABLE_OFF','INCOMPLETE_OFF_COVERAGE','THREE_ON_FAIL','UNSUPPORTED')
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads(Path(path).read_text())
def need(ok,message):
    if not ok:raise ValueError(message)
def load_npz(raw):
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:return {key:z[key] for key in z.files}
def same(a,b):return np.array_equal(a,b,equal_nan=True) if a.dtype.kind=='f' else np.array_equal(a,b)
def write(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def pins(plan):
    for path,digest in plan['source_sha256'].items():need(sha(path)==digest,'Frozen source changed')
    for scope in plan['scans']:
        need(sha(scope['path'])==scope['input_sha256'] and sha(scope['header_path'])==scope['header_sha256'],'Canonical/header input changed')
    for pin in plan['metadata_evidence']:need(sha(pin['path'])==pin['sha256'],'Metadata evidence changed')
def capture_check(folder):
    c=read(folder/'ACTUAL_RECEIPT.json');r=read(folder/'payload/RESULT.json')
    need(c['status']==r['status']=='PASS','Captured process failed')
    need(c['actual_exit_code']==0 and c['child_wait_completed'] and c['stdout_eof'] and c['natural_stdout_eof'],'Process not naturally closed')
    need(not c['killed'] and c['descendant_cleanup_completed'] and c['remaining_live_descendants']==[],'Process cleanup incomplete')
    need(sha(folder/'payload/RESULT.json')==c['result_sha256']==c['terminal_stdout_json']['result_sha256'],'Captured result differs')
    need(sha(folder/'STDOUT.log')==c['log_sha256']==c['observed_stdout_sha256'],'Captured stdout differs')
    need(c['source_pins_verified_before'] and c['source_pins_verified_after'],'Source binding missing')
    return c,r
def classify(center,maximum,valid):
    supported=valid[:,:5].all(axis=1)
    on3=(valid[:,[0,2,4]]&(center[:,[0,2,4]]>=10)).all(axis=1)
    off=(valid[:,[1,3]]&(maximum[:,[1,3]]>=5)).any(axis=1)
    state=np.full(len(valid),'UNSUPPORTED',dtype='<U28')
    state[supported&~on3]='THREE_ON_FAIL';state[supported&on3&off]='REJECTED_AVAILABLE_OFF';state[supported&on3&~off]='INCOMPLETE_OFF_COVERAGE'
    return supported,on3,off,state
def closure(plan,ph):
    began=time.monotonic();pins(plan)
    freeze=read(BW/'PUBLIC_FREEZE_RECEIPT_BW.json');serial=read(BW/'execution/SERIAL_RUN_RESULT.json')
    need(freeze['plan_sha256']==serial['plan_sha256']==ph and freeze['exact_readback_verified'] and freeze['before_execution'],'Public freeze differs')
    need(plan['core_q_list']==[254] and plan['batch_q_lists']==[[254]],'Prospective q254 scope differs')
    need(serial['status']=='PASS' and serial['all_planned_batches_completed'] and serial['attempted_batches']==[1] and len(serial['completed_batches'])==1 and not serial['errors'],'Serial continuation not complete')
    maximum=[-float('inf')]*5;tracks=[0]*5;hits=[0]*5;maps=0;all_q=[];batches=[];three_on_coordinates=[]
    totals=dict(scalar=0,vectors=0,anchors=0,reconstructed_values=0,forced_slots=0,ON_seed_rows=0,three_ON_rows=0)
    states={key:0 for key in STATES};max_scalar=max_calib=max_forced=0.
    for n in (1,):
        base=BW/f'execution/batch{n}';c,r=capture_check(base);parent=read(base/'PARENT_EXPORT_VERIFICATION.json')
        need(parent['status']=='PASS','Parent export failed')
        need(all(r[k] for k in ('source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after')),'Worker pins incomplete')
        need(r['source_pins_before']==r['source_pins_after']==r['final_source_pins_after_export'],'Worker source changed')
        need(r['input_pins_before']==r['input_pins_after']==r['final_input_pins_after_export'],'Worker input changed')
        ac,ar=capture_check(BW/f'audit_execution/batch{n}');reviewpath=BW/f'review/BATCH{n}_INDEPENDENT_REVIEW.json';review=read(reviewpath)
        need(ar['source_and_input_pins_unchanged'] and sha(reviewpath)==ar['review']['sha256'],'Captured independent review changed')
        need(sha(BW/f'audit_execution/batch{n}/payload/INDEPENDENT_REVIEW.json')==sha(reviewpath),'Independent review copies differ')
        need(review['status']=='PASS_BOUNDED_INDEPENDENT_REVIEW' and review['plan_sha256']==ph and review['all_saved_output_files_unchanged_during_review'],'Independent review failed/binding differs')
        need(sha(reviewpath)==serial['completed_batches'][n-1]['independent_review_sha256'],'Serial review binding differs')
        totals['scalar']+=review['independent_scalar_audit_sums'];totals['vectors']+=review['independent_calibration_vectors'];totals['forced_slots']+=review['independent_selected_forced_measurement_slots']
        totals['anchors']+=review['normalization_review'].get('independent_native_anchor_pairs_checked',0);totals['reconstructed_values']+=review['normalization_review'].get('normalized_support_values_exactly_reconstructed',0)
        max_scalar=max(max_scalar,review['maximum_scalar_sum_error']);max_calib=max(max_calib,review['maximum_calibration_error']);max_forced=max(max_forced,review['maximum_selected_forced_ess_error'])
        archivepath=base/'payload/EVIDENCE.zip';digest=sha(archivepath);need(digest==r['archive']['sha256']==parent['archive']['sha256'],'Archive hash differs')
        batchstates={key:0 for key in STATES};batchseeds=0
        with zipfile.ZipFile(archivepath) as z:
            names=z.namelist();need(len(names)==len(set(names)),'Duplicate archive names')
            members=json.loads(z.read('ARCHIVE_MANIFEST.json'))['members'];need(members==r['archive']['members']==parent['archive']['members'],'Archive manifests differ')
            need(set(names)=={m['path'] for m in members}|{'ARCHIVE_MANIFEST.json'},'Unexpected archive membership')
            need(z.testzip() is None,'Archive CRC test failed')
            for m in members:
                p=PurePosixPath(m['path']);need(not p.is_absolute() and '..' not in p.parts,'Unsafe member');raw=z.read(m['path'])
                need(len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256'],'Archive CRC/size/hash differs')
            raw=z.read('BATCH_COMPLETE.json');batch=json.loads(raw);qs=plan['batch_q_lists'][n-1]
            need(hashlib.sha256(raw).hexdigest()==review['batch_complete_sha256'] and batch['q_list']==review['q_list']==qs,'Batch/review scope differs')
            need(batch['plan_sha256']==ph and batch['track_trials']==len(qs)*45104640 and len(batch['results'])==len(qs),'Batch plan/count differs')
            need(batch['complete_OFF_support'] is False and batch['original_coverage_credit']==0,'Original coverage was advanced')
            all_q+=qs
            for q,item in zip(qs,batch['results']):
                need(item['q']==q and json.loads(z.read(f'q{q:03d}/PARTIAL_Q_COMPLETE.json'))==item and len(item['scans'])==5,'Q record differs')
                cats=[]
                for i,s in enumerate(item['scans']):
                    need(s['scan']==i and s['track_trials']==9020928,'Scan identity/trial count differs');tracks[i]+=s['track_trials'];hits[i]+=s['local_hits']
                    cat=load_npz(z.read(f'q{q:03d}/scan{i}_catalog.npz'));grid=load_npz(z.read(f'q{q:03d}/scan{i}_grid.npz'));cats.append(cat)
                    need(len(cat['ess'])==s['local_hits'] and all(len(a)==len(cat['ess']) for a in cat.values()),'Catalog column counts differ')
                    need([w['width_channels'] for w in s['width_searches']]==list(WIDTHS),'Width set differs')
                    need(np.isfinite(cat['ess']).all() and (cat['ess']>=10).all(),'Catalog score below threshold or nonfinite')
                    for w in s['width_searches']:
                        width=w['width_channels'];need(width in WIDTHS,'Unknown width');values=grid[f'max_ess_width_{width}'];maps+=len(values);need(np.isfinite(values).all(),'Nonfinite score maxima')
                        need(np.array_equal(grid[f'centers_width_{width}'],np.arange(q*4096,(q+1)*4096,STRIDES[WIDTHS.index(width)])),'Saved grid centers differ')
                        peak=float(values.max());need(peak==w['maximum_local_ess'],'Summary maximum differs');maximum[i]=max(maximum[i],peak)
                        mask=cat['width_channels']==width;need(int(mask.sum())==w['catalog_local_hits'],'Width catalog count differs')
                        centers=cat['channel_at_midpoint'][mask];need(((centers>=q*4096)&(centers<(q+1)*4096)&((centers-q*4096)%w['stride']==0)).all(),'Catalog center outside searched core/stride')
                        idx=(centers-q*4096)//w['stride'];need((cat['ess'][mask]<=values[idx]).all(),'Catalog exceeds score maximum')
                a=load_npz(z.read(f'q{q:03d}/PARTIAL_ASSOCIATION.npz'));seeds={k:np.concatenate([cats[i][k] for i in (0,2,4)]) for k in cats[0]}
                seeds['source_scan']=np.concatenate([np.full(len(cats[i]['ess']),i,dtype=np.int8) for i in (0,2,4)])
                count=len(seeds['ess']);batchseeds+=count;totals['ON_seed_rows']+=count
                for k,v in seeds.items():need(same(v,a['seed_'+k]),'Association source identity differs')
                center=a['forced_center_local_ess'];mx=a['forced_neighborhood_max_local_ess'];valid=a['forced_valid']
                need(center.shape==mx.shape==valid.shape==(count,6),'Association geometry differs')
                need(np.isnan(center[:,5]).all() and np.isnan(mx[:,5]).all() and not valid[:,5].any() and (a['predicted_native_center'][:,5]==-1).all(),'Missing OFF5 substituted')
                need(np.isfinite(center[valid]).all() and np.isfinite(mx[valid]).all(),'Nonfinite supported association')
                supported,on3,off,status=classify(center,mx,valid)
                for key,value in [('available_scans_supported',supported),('three_ON_pass',on3),('available_OFF_veto',off),('candidate_status',status)]:need(same(a[key],value),'Association classification differs')
                need(not a['complete_OFF_support'].any(),'Full OFF qualification impossible')
                counts={key:int((status==key).sum()) for key in STATES};need(counts==item['association']['status_counts'] and count==item['association']['ON_local_catalog_rows'],'Association count differs')
                need(int(on3.sum())==item['association']['three_ON_pass_rows'],'Three-ON count differs')
                for key in STATES:states[key]+=counts[key];batchstates[key]+=counts[key]
                totals['three_ON_rows']+=int(on3.sum())
                for row in np.flatnonzero(on3):three_on_coordinates.append(dict(batch=n,q=q,row=int(row)))
        need(batchstates==review['status_counts'] and batchseeds==review['ON_seed_rows_all_semantically_reviewed'],'Per-batch independent classifications differ')
        need(sha(archivepath)==digest,'Archive changed during review')
        batches.append(dict(batch=n,archive_sha256=digest,archive_bytes=archivepath.stat().st_size,members_fully_CRC_size_SHA256_verified=len(members),production_capture_sha256=sha(base/'ACTUAL_RECEIPT.json'),independent_capture_sha256=sha(BW/f'audit_execution/batch{n}/ACTUAL_RECEIPT.json'),independent_review_sha256=sha(reviewpath),both_actual_exit_codes=0,both_natural_stdout_eof=True))
    need(all_q==[254] and sum(tracks)==45104640,'Whole continuation scope differs')
    need(maps==5*(4096+4096+2048+512),'Stored maximum count differs')
    need(totals['scalar']==180 and totals['vectors']==60 and totals['anchors']==20480 and totals['reconstructed_values']==983040,'Independent audit totals differ')
    need(sum(hits[i] for i in (0,2,4))==totals['ON_seed_rows'],'ON seed total differs')
    pins(plan);need(sha(BW/'BW_PARTIAL_PLAN.json')==ph,'Plan changed')
    return dict(schema='SETI_BW_INDEPENDENT_FINAL_CLOSURE_REVIEW_V1',status='PASS_PARTIAL_EXPLORATORY_CLOSURE',completed_utc=datetime.now(timezone.utc).isoformat(),reviewer_source_sha256=sha(__file__),plan_sha256=ph,public_freeze_commit=freeze['public_commit_sha'],closed_production_captures=1,closed_independent_review_captures=1,closed_archives_independently_verified=batches,frozen_sources_and_inputs_still_exact=True,q_list=all_q,correlated_track_combinations=sum(tracks),ON_correlated_track_combinations=sum(tracks[i] for i in (0,2,4)),channel_bin_width_mhz=4096*abs(plan['scans'][0]['df_hz'])/1e6,all_scan_catalog_hits=sum(hits),per_scan_catalog_hits=hits,ON_seed_rows=totals['ON_seed_rows'],stored_per_center_maxima_rechecked=maps,per_scan_maximum_local_ess=maximum,maximum_local_ess=max(maximum),threshold_ess=10,status_counts=states,three_ON_rows=totals['three_ON_rows'],three_ON_coordinates=three_on_coordinates,independent_audit_totals=totals,maximum_independent_sampled_scalar_error=max_scalar,maximum_independent_sampled_calibration_error=max_calib,maximum_independent_sampled_forced_score_error=max_forced,complete_OFF_support=False,full_cadence_candidate_assessment='NOT_EVALUABLE_MISSING_OFF5',original_coverage_credit=0,historical_authority_unchanged=True,wall_seconds=time.monotonic()-began,limits=['One sealed ZIP checked member-by-member and all saved catalogs/maxima/classifications rechecked.','Previous bounded numerical reviews reused with exact captured natural-exit receipts; no second full search.','No additional power analysis or full detector replay is performed by this closure.','Catalog/association rows overlap and are not independent candidates.','No calibrated FAP, sensitivity, extraterrestrial origin or full-cadence qualification.'])

def summary_binding(summary_path):
    """Compare a finished aggregate with the independent closure and prior BV."""
    summary_path=Path(summary_path).resolve()
    need(summary_path==BW/'SUMMARY_BW.json','Unexpected summary path')
    s=read(summary_path);c=read(BW/'review/FINAL_CLOSURE_REVIEW_BW.json')
    p=read(BW/'BW_PARTIAL_PLAN.json');prior=read(ROOT/'work_bv/SUMMARY_BV.json')
    need(c['status']=='PASS_PARTIAL_EXPLORATORY_CLOSURE','Independent closure failed')
    need(s['plan_sha256']==c['plan_sha256']==sha(BW/'BW_PARTIAL_PLAN.json'),'Plan binding differs')
    for sk,ck in [('new_correlated_track_combinations','correlated_track_combinations'),('new_ON_correlated_track_combinations','ON_correlated_track_combinations'),('new_carrier_bin_width_mhz','channel_bin_width_mhz'),('all_scan_catalog_rows','all_scan_catalog_hits'),('ON_seed_rows','ON_seed_rows'),('maximum_local_ess','maximum_local_ess'),('partial_status_counts','status_counts'),('q_list','q_list')]:
        need(s[sk]==c[ck],'Aggregate differs: '+sk)
    need([r['catalog_rows'] for r in s['scans']]==c['per_scan_catalog_hits'],'Per-scan catalog counts differ')
    need([r['maximum_local_ess'] for r in s['scans']]==c['per_scan_maximum_local_ess'],'Per-scan maxima differ')
    need(len(s['scans'])==5 and all(r['correlated_track_combinations']==9020928 for r in s['scans']),'Per-scan trial counts differ')
    for index,(scan,scope) in enumerate(zip(s['scans'],p['scans'])):
        need(scan['scan']==index and all(scan[k]==scope[k] for k in ('role','target','archive_id')),'Per-scan identity differs')
    audit=c['independent_audit_totals']
    for sk,ck in [('scalar_checks','scalar'),('calibration_vectors','vectors'),('selected_forced_measurement_slots','forced_slots')]:
        need(s['independent_review'][sk]==audit[ck],'Audit count differs: '+sk)
    norm=s['independent_review']['normalization_review']
    need(norm['independent_native_anchor_pairs_checked']==audit['anchors'] and norm['normalized_support_values_exactly_reconstructed']==audit['reconstructed_values'],'Normalization audit counts differ')
    need(s['new_q_count']==1 and s['new_scan_q_count']==5,'New scope differs')
    combined=s['combined_BU_BV_BW'];previous=prior['combined_BU_BV']
    need(combined['q_list']==previous['q_list']+c['q_list']==list(range(1,255)),'Combined scope differs')
    need(combined['q_count']==254 and combined['scan_q_count']==1270,'Combined q counts differ')
    need(combined['correlated_track_combinations']==previous['correlated_track_combinations']+c['correlated_track_combinations']==11456578560,'Combined tracks differ')
    need(combined['carrier_bin_width_mhz']==previous['carrier_bin_width_mhz']+c['channel_bin_width_mhz']==2.90679931640625,'Combined bin bandwidth differs')
    need(combined['parent_BV_summary_sha256']==sha(ROOT/'work_bv/SUMMARY_BV.json'),'Cumulative parent binding differs')
    need(combined['all_scan_catalog_rows']==prior['all_scan_catalog_rows']+c['all_scan_catalog_hits'],'Combined catalog count differs')
    need(combined['maximum_local_ess']==max(prior['maximum_local_ess'],c['maximum_local_ess']),'Combined maximum differs')
    need(combined['partial_status_counts']=={key:prior['partial_status_counts'][key]+c['status_counts'][key] for key in STATES},'Combined classifications differ')
    need(combined['frequency_max_mhz']==p['scans'][0]['fch1_mhz']+4096*p['scans'][0]['df_hz']/1e6 and combined['frequency_min_mhz']==p['scans'][0]['fch1_mhz']+(255*4096-1)*p['scans'][0]['df_hz']/1e6,'Combined frequency bounds differ')
    need(s['missing_scan']==5 and s['complete_OFF_support'] is False and s['full_cadence_candidate_assessment']=='NOT_EVALUABLE_MISSING_OFF5','Missing control overclaimed')
    need(s['new_original_technical_coverage_mhz_visits']==s['new_original_unique_archive_ids']==s['new_archive_requests']==s['new_observation_epochs']==0 and not s['queue_advanced'],'Original coverage/access claims differ')
    need(s['authoritative_unique_archive_ids']==486 and s['authoritative_technical_MHz_visits']==268.50128173828125,'Historical authority changed')
    need(s['global_false_alarm_probability'] is None and s['calibrated_sensitivity'] is None and not s['background_science_jobs_running'],'Qualification/process claims differ')
    return dict(schema='SETI_BW_INDEPENDENT_SUMMARY_BINDING_REVIEW_V1',status='PASS_SUMMARY_MATCHES_INDEPENDENT_CLOSURE',completed_utc=datetime.now(timezone.utc).isoformat(),summary_sha256=sha(summary_path),closure_sha256=sha(BW/'review/FINAL_CLOSURE_REVIEW_BW.json'),reviewer_source_sha256=sha(__file__),plan_sha256=c['plan_sha256'],combined_BU_BV_BW_correlated_tracks=combined['correlated_track_combinations'],combined_carrier_bin_width_mhz=combined['carrier_bin_width_mhz'],complete_OFF_support=False,original_coverage_credit=0,qualification='Partial descriptive coverage correction; no full-cadence result or calibrated FAP/sensitivity.')

def alarm(signum,frame):
    raise TimeoutError('Independent saved-result closure exceeded 120-second wall bound')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,help='Bind the completed aggregate after the closure exists')
    args=parser.parse_args()
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,120)
    if args.summary:
        result=summary_binding(args.summary);target=BW/'review/SUMMARY_BINDING_REVIEW_BW.json'
    else:
        plan_path=BW/'BW_PARTIAL_PLAN.json'
        result=closure(read(plan_path),sha(plan_path));target=BW/'review/FINAL_CLOSURE_REVIEW_BW.json'
    write(target,result);signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps(dict(status=result['status'],path=str(target),sha256=sha(target),maximum_local_ess=result.get('maximum_local_ess'),catalog_hits=result.get('all_scan_catalog_hits'),ON_seed_rows=result.get('ON_seed_rows'),states=result.get('status_counts'))),flush=True)
