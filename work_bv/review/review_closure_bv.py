"""Independent BV closure and explicitly post-hoc complete three-ON remeasurement.

No production numerical code is imported. Closed ZIPs are the result authority;
saved normalized supports are used for additional direct numerical checks.
"""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib,io,json,math,os,signal,time,zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2];BV=ROOT/'work_bv'
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
    freeze=read(BV/'PUBLIC_FREEZE_RECEIPT_BV.json');serial=read(BV/'execution/SERIAL_RUN_RESULT.json')
    need(freeze['plan_sha256']==serial['plan_sha256']==ph and freeze['exact_readback_verified'] and freeze['before_execution'],'Public freeze differs')
    need(serial['status']=='PASS' and serial['all_planned_batches_completed'] and serial['attempted_batches']==list(range(1,29)) and not serial['errors'],'Serial continuation not complete')
    maximum=[-float('inf')]*5;tracks=[0]*5;hits=[0]*5;maps=0;all_q=[];batches=[];three_on_coordinates=[]
    totals=dict(scalar=0,vectors=0,anchors=0,reconstructed_values=0,forced_slots=0,ON_seed_rows=0,three_ON_rows=0)
    states={key:0 for key in STATES};max_scalar=max_calib=max_forced=0.
    for n in range(1,29):
        base=BV/f'execution/batch{n}';c,r=capture_check(base);parent=read(base/'PARENT_EXPORT_VERIFICATION.json')
        need(parent['status']=='PASS','Parent export failed')
        need(all(r[k] for k in ('source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after')),'Worker pins incomplete')
        need(r['source_pins_before']==r['source_pins_after']==r['final_source_pins_after_export'],'Worker source changed')
        need(r['input_pins_before']==r['input_pins_after']==r['final_input_pins_after_export'],'Worker input changed')
        ac,ar=capture_check(BV/f'audit_execution/batch{n}');reviewpath=BV/f'review/BATCH{n}_INDEPENDENT_REVIEW.json';review=read(reviewpath)
        need(ar['source_and_input_pins_unchanged'] and sha(reviewpath)==ar['review']['sha256'],'Captured independent review changed')
        need(sha(BV/f'audit_execution/batch{n}/payload/INDEPENDENT_REVIEW.json')==sha(reviewpath),'Independent review copies differ')
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
                    need(np.isfinite(cat['ess']).all() and (cat['ess']>=10).all(),'Catalog score below threshold or nonfinite')
                    for w in s['width_searches']:
                        width=w['width_channels'];values=grid[f'max_ess_width_{width}'];maps+=len(values);need(np.isfinite(values).all(),'Nonfinite score maxima')
                        peak=float(values.max());need(peak==w['maximum_local_ess'],'Summary maximum differs');maximum[i]=max(maximum[i],peak)
                        mask=cat['width_channels']==width;need(int(mask.sum())==w['catalog_local_hits'],'Width catalog count differs')
                        idx=(cat['channel_at_midpoint'][mask]-q*4096)//w['stride'];need((cat['ess'][mask]<=values[idx]).all(),'Catalog exceeds score maximum')
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
        batches.append(dict(batch=n,archive_sha256=digest,archive_bytes=archivepath.stat().st_size,members_fully_CRC_size_SHA256_verified=len(members),production_capture_sha256=sha(base/'ACTUAL_RECEIPT.json'),independent_capture_sha256=sha(BV/f'audit_execution/batch{n}/ACTUAL_RECEIPT.json'),independent_review_sha256=sha(reviewpath),both_actual_exit_codes=0,both_natural_stdout_eof=True))
    need(all_q==list(range(33,254)) and sum(tracks)==9968125440,'Whole continuation scope differs')
    need(maps==221*5*(4096+4096+2048+512),'Stored maximum count differs')
    need(totals['scalar']==39780 and totals['vectors']==13260 and totals['anchors']==20480 and totals['reconstructed_values']==3276800,'Independent audit totals differ')
    need(sum(hits[i] for i in (0,2,4))==totals['ON_seed_rows'],'ON seed total differs')
    pins(plan);need(sha(BV/'BV_PARTIAL_PLAN.json')==ph,'Plan changed')
    return dict(schema='SETI_BV_INDEPENDENT_FINAL_CLOSURE_REVIEW_V1',status='PASS_PARTIAL_EXPLORATORY_CLOSURE',completed_utc=datetime.now(timezone.utc).isoformat(),reviewer_source_sha256=sha(__file__),plan_sha256=ph,public_freeze_commit=freeze['public_commit_sha'],closed_production_captures=28,closed_independent_review_captures=28,closed_archives_independently_verified=batches,frozen_sources_and_inputs_still_exact=True,q_list=all_q,correlated_track_combinations=sum(tracks),ON_correlated_track_combinations=sum(tracks[i] for i in (0,2,4)),channel_bin_width_mhz=221*4096*abs(plan['scans'][0]['df_hz'])/1e6,all_scan_catalog_hits=sum(hits),per_scan_catalog_hits=hits,ON_seed_rows=totals['ON_seed_rows'],stored_per_center_maxima_rechecked=maps,per_scan_maximum_local_ess=maximum,maximum_local_ess=max(maximum),threshold_ess=10,status_counts=states,three_ON_rows=totals['three_ON_rows'],three_ON_coordinates=three_on_coordinates,independent_audit_totals=totals,maximum_independent_sampled_scalar_error=max_scalar,maximum_independent_sampled_calibration_error=max_calib,maximum_independent_sampled_forced_score_error=max_forced,complete_OFF_support=False,full_cadence_candidate_assessment='NOT_EVALUABLE_MISSING_OFF5',original_coverage_credit=0,historical_authority_unchanged=True,wall_seconds=time.monotonic()-began,limits=['All28ZIPs checked member-by-member and all catalogs/maxima/classifications rechecked.','Previous bounded numerical reviews reused with exact captured natural-exit receipts; no second full search.','All three-ON rows receive a separately labelled post-hoc direct numerical review.','Catalog/association rows overlap and are not independent candidates.','No calibrated FAP, sensitivity, extraterrestrial origin or full-cadence qualification.'])
def direct_vector(y,offsets,centers,width):
    total=np.zeros(len(centers),dtype=np.float64)
    for row,offset in enumerate(offsets):
        for delta in range(-(width//2),width//2+1):total+=y[row,centers+int(offset)+delta].astype(np.float64)
    return total
def scalar(y,offsets,center,width):
    return math.fsum(float(y[row,center+int(offset)+delta]) for row,offset in enumerate(offsets) for delta in range(-(width//2),width//2+1))
def posthoc(plan,ph,closed):
    began=time.monotonic();rows_out=[];calibration_cache={};context={};maxcal=maxscore=0.;scalar_tracks=0
    rates=np.linspace(-4,4,839);offsets=np.rint(rates[:,None]*(np.arange(16)-7.5)[None,:]*plan['scans'][0]['dt_seconds']/plan['scans'][0]['df_hz']).astype(np.int32)
    for coord in closed['three_ON_coordinates']:
        batch,q,row=coord['batch'],coord['q'],coord['row'];key=(batch,q)
        if key not in context:
            base=Path(f'/dev/shm/seti_bv_partial_20261031/batch{batch}/contents');prepared=read(base/'NORMALIZED_INPUTS_COMPLETE.json');complete=read(base/f'q{q:03d}/PARTIAL_Q_COMPLETE.json')
            ap=base/f'q{q:03d}/PARTIAL_ASSOCIATION.npz';need(sha(ap)==complete['association']['publication']['sha256'],'Posthoc association bytes differ')
            a=load_npz(ap.read_bytes());supports=[];grids=[];bound=[(str(ap),sha(ap))]
            for s,record in zip(plan['scans'],prepared['scans']):
                yp=Path(record['normalized_support_path']);need(sha(yp)==record['normalized_support_sha256'],'Posthoc support differs');supports.append(np.load(yp,mmap_mode='r',allow_pickle=False));bound.append((str(yp),sha(yp)))
                gp=base/f'q{q:03d}/scan{s["scan"]}_grid.npz';pub=next(x for x in complete['scans'][s['scan']]['publications'] if x['path'].endswith('_grid.npz'));need(sha(gp)==pub['sha256'],'Posthoc grid differs');grids.append(load_npz(gp.read_bytes()));bound.append((str(gp),sha(gp)))
            context[key]=(prepared,a,supports,grids,bound)
        prepared,a,supports,grids,bound=context[key];src=int(a['seed_source_scan'][row]);ri=int(a['seed_drift_index'][row]);width=int(a['seed_width_channels'][row]);frequency=float(a['seed_frequency_at_midpoint_mhz'][row]);rate=float(a['seed_drift_hz_s'][row]);need(rate==rates[ri],'Posthoc rate differs')
        measured=[]
        for s,record,y,g in zip(plan['scans'],prepared['scans'],supports,grids):
            scan=s['scan'];gap=(s['tref_midpoint_mjd']-plan['scans'][src]['tref_midpoint_mjd'])*86400
            predicted=int(np.rint((frequency+rate*gap/1e6-s['fch1_mhz'])*1e6/s['df_hz']));local=predicted-record['support_start'];radius=int(np.ceil(1+.5*(rates[1]-rates[0])*abs(gap)/abs(s['df_hz'])))
            need(predicted==int(a['predicted_native_center'][row,scan]) and bool(a['forced_valid'][row,scan]),'Posthoc projected coordinate/support differs')
            ck=(q,scan,width,ri)
            if ck not in calibration_cache:
                centers=np.arange(q*4096,(q+1)*4096,STRIDES[WIDTHS.index(width)],dtype=np.int32)-record['support_start'];v=direct_vector(y,offsets[ri],centers,width);median=float(np.median(v));scale=float(1.4826*np.median(np.abs(v-median)));need(scale>0 and math.isfinite(scale),'Posthoc calibration invalid')
                err=float(np.max(np.abs(np.array([median,scale])-g[f'calibration_width_{width}'][ri])));need(err<5e-5,'Independent full calibration vector differs');maxcal=max(maxcal,err);calibration_cache[ck]=(median,scale)
            median,scale=calibration_cache[ck];sums=np.array([scalar(y,offsets[ri],local+d,width) for d in range(-radius,radius+1)]);scalar_tracks+=len(sums);scores=(sums-median)/scale;measured_center=float(scores[radius]);measured_max=float(scores.max())
            stored=np.array([a['forced_center_local_ess'][row,scan],a['forced_neighborhood_max_local_ess'][row,scan]]);actual=np.array([measured_center,measured_max]);error=float(np.max(np.abs(actual-stored)));need(error<=5e-5/scale+1e-12,'Posthoc forced score differs');maxscore=max(maxscore,error)
            for threshold in (5,10):need(np.array_equal(actual>=threshold,stored>=threshold),'Posthoc threshold classification changed')
            measured.append(dict(scan=scan,role=s['role'],predicted_native_center=predicted,neighborhood_radius_channels=radius,independent_center_ess=measured_center,independent_neighborhood_max_ess=measured_max,stored_center_ess=float(stored[0]),stored_neighborhood_max_ess=float(stored[1])))
        on3=all(measured[i]['independent_center_ess']>=10 for i in (0,2,4));off=any(measured[i]['independent_neighborhood_max_ess']>=5 for i in (1,3))
        need(on3 and off and a['candidate_status'][row]=='REJECTED_AVAILABLE_OFF','Three-ON rejection not independently confirmed')
        need(np.isnan(a['forced_center_local_ess'][row,5]) and not a['forced_valid'][row,5],'Missing OFF5 substituted')
        rows_out.append(dict(**coord,source_scan=src,width_channels=width,drift_hz_s=rate,frequency_mhz=frequency,measurements=measured,three_ON_pass=True,available_OFF_veto=True,status='REJECTED_AVAILABLE_OFF',complete_OFF_support=False))
    for prepared,a,supports,grids,bound in context.values():
        for path,digest in bound:need(sha(path)==digest,'Posthoc saved evidence changed')
    need(len(rows_out)==closed['three_ON_rows'],'Posthoc row selection incomplete');pins(plan);need(sha(BV/'BV_PARTIAL_PLAN.json')==ph,'Posthoc plan changed')
    return dict(schema='SETI_BV_POSTHOC_ALL_THREE_ON_REVIEW_V1',status='PASS_ALL_THREE_ON_ROWS_REJECTED_BY_AVAILABLE_OFF',completed_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=ph,reviewer_source_sha256=sha(__file__),selection='Post-hoc selection of every saved three_ON_pass row across all28 frozen completed batches; no row omitted, no thresholds changed.',three_ON_rows_reviewed=len(rows_out),five_scan_measurement_slots=len(rows_out)*5,direct_scalar_tracks=scalar_tracks,independently_recomputed_calibration_vectors=len(calibration_cache),maximum_calibration_error=maxcal,maximum_forced_ess_error=maxscore,all_three_ON_and_available_OFF_rejections_reproduced=True,complete_OFF_support=False,global_FAP=None,calibrated_sensitivity=None,frequency_min_mhz=min((r['frequency_mhz'] for r in rows_out),default=None),frequency_max_mhz=max((r['frequency_mhz'] for r in rows_out),default=None),minimum_ON_threshold_margin=min((r['measurements'][i]['independent_center_ess']-10 for r in rows_out for i in (0,2,4)),default=None),minimum_available_OFF_veto_margin=min((max(r['measurements'][i]['independent_neighborhood_max_ess'] for i in (1,3))-5 for r in rows_out),default=None),rows=rows_out,wall_seconds=time.monotonic()-began,limits=['This is an explicitly post-hoc validation of saved results, not new held-out data or an additional search.','Direct sums and full selected calibration vectors are independent of production kernel; normalization and saved input lineage remain inherited.','Overlapping source rows and widths do not constitute independent candidates.','Available OFF rejection does not identify a unique physical interference origin.','Missing OFF5 remains missing; no complete-cadence qualification or calibrated FAP/sensitivity.'])
def alarm(signum,frame):raise TimeoutError('Independent final review finite wall limit')
if __name__=='__main__':
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,180)
    plan=read(BV/'BV_PARTIAL_PLAN.json');ph=sha(BV/'BV_PARTIAL_PLAN.json');closed=closure(plan,ph)
    signal.setitimer(signal.ITIMER_REAL,120);extra=posthoc(plan,ph,closed);signal.setitimer(signal.ITIMER_REAL,0)
    ep=BV/'review/THREE_ON_REVIEW_BV.json';write(ep,extra);closed['posthoc_three_ON_review']=dict(path=str(ep),sha256=sha(ep),status=extra['status'],rows=extra['three_ON_rows_reviewed'])
    cp=BV/'review/FINAL_CLOSURE_REVIEW_BV.json';write(cp,closed)
    print(json.dumps(dict(status=closed['status'],closure_sha256=sha(cp),posthoc_sha256=sha(ep),tracks=closed['correlated_track_combinations'],catalog_hits=closed['all_scan_catalog_hits'],ON_seed_rows=closed['ON_seed_rows'],maximum_ess=closed['maximum_local_ess'],states=closed['status_counts'],posthoc_rows=extra['three_ON_rows_reviewed'],calibration_vectors=extra['independently_recomputed_calibration_vectors'],posthoc_scalar_tracks=extra['direct_scalar_tracks'],posthoc_max_score_error=extra['maximum_forced_ess_error'],posthoc_wall_seconds=extra['wall_seconds'],closure_wall_seconds=closed['wall_seconds'])),flush=True)
