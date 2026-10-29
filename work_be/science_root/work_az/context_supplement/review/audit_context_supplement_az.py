"""Independent AZ exhaustive context audit, including an empty-pending case.

No producer import. Choices depend only on the closed main-followup queue.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,math,os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'runtime'))
import numpy as np
B=Path(__file__).resolve().parent
P=B.parent.parent
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def arrays(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def exact(a,b):return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
def metrics(values):
 rows=[float(v) for v in values];positive=[v for v in rows if v>0];positive_sum=math.fsum(positive)
 return {'row_contributions':rows,'total':math.fsum(rows),'positive_row_count':len(positive),'positive_contribution_sum':positive_sum,'maximum_positive_row_fraction':max(positive)/positive_sum if positive_sum>0 else None}
def rows(y,ch,w):return [math.fsum(float(y[t,int(c)+d]) for d in range(-(w//2),w//2+1)) for t,c in enumerate(ch)]
def identity(item):return (item['namespace'],item['class'],int(item['group_id']))
def rec_identity(rec):return (rec['origin'],rec['group']['class'],int(rec['group']['group_id']))
def run():
 resultpath=P/'context_supplement/results/FOLLOWUP_RESULT_CONTEXT_SUPPLEMENT_AZ.json';resultdir=resultpath.parent;r=read(resultpath);planpath=P/'context_supplement/PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json';plan=read(planpath)
 pins={str(Path(__file__)):sha(__file__),str(planpath):sha(planpath),str(resultpath):sha(resultpath)}
 for path,digest in plan['source_and_input_sha256'].items():assert sha(path)==digest;pins[path]=digest
 actual=P/'context_supplement/ACTUAL_TOOL_CONTEXT_SUPPLEMENT_AZ.json';receipt=read(actual)
 assert receipt['actual_exit_code']==0 and receipt['result_sha256']==sha(resultpath)
 assert read(P/'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json')['status']=='PASS'
 assert read(P/'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json')['result_sha256']==sha(P/'followup/results/FOLLOWUP_RESULT_AZ.json')
 pins[str(actual)]=sha(actual)
 oldpath=P/'followup/results/FOLLOWUP_RESULT_AZ.json';gpath=P/'followup/results/GROUPING_AZ.json'
 protocol=P/'PROTOCOL_BOUND_AZ.json';p=read(protocol);old=read(oldpath);g=read(gpath)
 pins[str(protocol)]=sha(protocol)
 assert r['status']=='COMPLETE' and r['target']==old['target']==p['target'] and r['primary_id']==old['primary_id']==p['primary_id']
 assert r['protocol_sha256']==sha(protocol) and r['parent_followup_result_sha256']==sha(oldpath) and r['parent_grouping_sha256']==sha(gpath) and r['plan_sha256']==sha(planpath)
 pending=sorted([x for x in old['local_context_backlog'] if not x['bounded_local_context_completed']],key=identity)
 pending_ids=[identity(x) for x in pending];assert len(set(pending_ids))==len(pending_ids)
 assert plan['pending_identities']==pending
 records=r['selected_representatives'];record_ids=[rec_identity(x) for x in records]
 assert record_ids==pending_ids and len(records)==r['supplementary_group_count']
 groups={}
 for origin,table in [('all3ON',g['all3ON_groups']),('intermittent1or2ON',g['intermittent_groups'])]:
  for group in table:
   key=(origin,group['class'],int(group['group_id']));assert key not in groups;groups[key]=group
 for rec in records:
  key=rec_identity(rec);assert rec['group']==groups[key]
  rep=rec['group']['representative'];source=p['scans'][rep['source_scan']];freq=source['fch1_mhz']+int(rep['channel_at_midpoint'])*source['df_hz']/1e6
  fixed=[int(np.rint((freq-s['fch1_mhz'])*1e6/s['df_hz'])) for s in p['scans']]
  assert rec['fixed_centers_six_scans']==fixed and rec['fixed_frequency_MHz']==freq
  centers=rep['projected_centers_six_scans'];assert rec['window_lo']==max(0,min(centers+fixed)-1024)
  assert rec['window_hi_exclusive']==min(p['scans'][0]['nchannels'],max(centers+fixed)+1025)
 overlay=r['local_context_backlog_overlay'];assert len(overlay)==len(old['local_context_backlog'])
 for before,after in zip(old['local_context_backlog'],overlay):
  expected=dict(before);expected['bounded_local_context_completed']=True;assert after==expected
 assert all(x['bounded_local_context_completed'] for x in overlay)
 assert r['pending_groups_after_overlay']==0 and r['all_groups_completed_after_overlay']==len(overlay)
 assert r['parent_scientific_flags_counts_grouping_and_selection_changed'] is False
 assert r['new_examined_MHz_visits']==r['new_independent_epochs']==r['accepted_SETI_candidates']==0 and r['physical_origin']=='UNRESOLVED'
 numericpath=P/'review/INDEPENDENT_DETECTOR_AZ.json';numeric=read(numericpath);assert numeric['status']=='PASS' and numeric['protocol_sha256']==sha(protocol);pins[str(numericpath)]=sha(numericpath)
 # Main output and all pre-existing prospective companion controls remain byte pinned.
 for path,digest in plan['source_and_input_sha256'].items():assert sha(path)==digest;pins[path]=digest
 publication_receipt_checks=[]
 for item in r['publications']:
  receiptpath=Path(item['publication_receipt_path']);assert receiptpath==Path(item['path']).with_suffix('.publication.json')
  assert sha(receiptpath)==item['publication_receipt_sha256'];pins[str(receiptpath)]=item['publication_receipt_sha256'];pr=read(receiptpath)
  assert pr['status']=='PASS' and pr['format']=='npz' and pr['all_publication_checks_pass'] and pr['no_overwrite_repair_or_retry']
  assert pr['destination']==item['path'] and pr['stage_validation']==pr['published_validation']
  for validation in (pr['stage_validation'],pr['published_validation']):assert validation['CRC_verified'] and validation['exact_typed_arrays_verified']
  assert pr['stage']['sha256']==pr['published']['sha256']==item['sha256']==sha(item['path']) and pr['stage']['size_bytes']==pr['published']['size_bytes']==item['bytes']==Path(item['path']).stat().st_size
  assert (pr['stage']['device'],pr['stage']['inode'])!=(pr['published']['device'],pr['published']['inode'])
  assert not Path(pr['staging_path']).is_relative_to(P)
  publication_receipt_checks.append({'path':item['path'],'receipt_sha256':sha(receiptpath),'stage_published_byte_identity':True,'exact_typed_array_validation_recorded':True,'private_staging_independent_inode':True})
 local={};publications={str(Path(x['path']).resolve()):x for x in r['publications']}
 for rec in records:
  lp=(resultdir/rec['array_filename']).resolve();assert lp.parent==resultdir and sha(lp)==publications[str(lp)]['sha256'];pins[str(lp)]=sha(lp);local[rec_identity(rec)]=arrays(lp)
 assert len(publications)==len(records)
 scalarchecks=[];fixedchecks=[];rawpixels=normpixels=metriccount=0;maxerr=0.;normalization=[]
 if records:
  tpath=P/'results/all_ON_forced_triage.npz';assert sha(tpath)==numeric['input_and_source_sha256_before_after'][str(tpath)];pins[str(tpath)]=sha(tpath);t=arrays(tpath)
  oraclepath=P/'followup/review_source/oracles_independent_ad.py';spec=importlib.util.spec_from_file_location('independent_ap_supplement_oracle',oraclepath);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle);pins[str(oraclepath)]=sha(oraclepath)
 for s in p['scans'] if records else []:
  j=s['scan'];native=Path(p['root'])/s['native_path'];assert sha(native)==s['input_sha256'];pins[str(native)]=s['input_sha256']
  raw=np.load(native,mmap_mode='r',allow_pickle=False);y,_,_,_=oracle.normalize_independently(raw,4096);normalization.append({'scan':j,**oracle.LAST_NORMALIZATION_REPORT})
  gridpath=P/f'results/scan{j}_grid.npz';assert sha(gridpath)==numeric['input_and_source_sha256_before_after'][str(gridpath)];pins[str(gridpath)]=sha(gridpath);grid=arrays(gridpath)
  for rec in records:
   key=rec_identity(rec);values=local[key];lo=rec['window_lo'];hi=rec['window_hi_exclusive'];rep=rec['group']['representative'];row=rec['group']['representative_global_seed_row'];w=rep['width_channels'];ri=rep['drift_index'];sr=rec['scans'][j]
   assert exact(values['native_channels'],np.arange(lo,hi,dtype=np.int32));assert exact(values[f'raw_scan{j}'],np.asarray(raw[:,lo:hi]));assert exact(values[f'normalized_scan{j}'],np.asarray(y[:,lo:hi]));rawpixels+=s['nrows']*(hi-lo);normpixels+=s['nrows']*(hi-lo)
   offsets=np.rint(rep['drift_hz_s']*(np.arange(s['nrows'])-(s['nrows']-1)/2)*s['dt_seconds']/s['df_hz']).astype(np.int32);assert np.array_equal(offsets,grid['offsets'][ri]) and grid['drift_hz_s'][ri]==rep['drift_hz_s']
   channels=int(t['predicted_center'][row,j])+offsets;assert np.array_equal(values[f'original_integer_channels_scan{j}'],channels)
   nr=rows(y,channels,w);rr=rows(raw,channels,w);assert sr['normalized_original_track']==metrics(nr) and sr['raw_original_track']==metrics(rr)
   assert values[f'normalized_row_contributions_scan{j}'].tolist()==nr and values[f'raw_row_contributions_scan{j}'].tolist()==rr
   cal=grid[f'calibration_width_{w}'][ri];assert [sr['calibration_median'],sr['calibration_scale']]==cal.tolist()
   score=(math.fsum(nr)-float(cal[0]))/float(cal[1]);reference=float(t['forced_center_ess'][row,j]);error=abs(score-reference);assert score==sr['recovered_ESS'] and reference==sr['forced_center_ESS'] and error==sr['absolute_ESS_error'] and error<=1e-4+5e-6*abs(reference);maxerr=max(maxerr,error)
   assert sr['scan']==j and sr['role']==s['role'] and sr['fch1_mhz']==s['fch1_mhz'] and sr['df_hz']==s['df_hz'] and sr['dt_seconds']==s['dt_seconds']
   fc=sr['fixed_frequency_companion'];center=rec['fixed_centers_six_scans'][j];zero=np.flatnonzero(grid['drift_hz_s']==0.);assert len(zero)==1;zi=int(zero[0]);assert np.all(grid['offsets'][zi]==0)
   assert fc['mapped_center_channel']==center and fc['source_frequency_MHz']==rec['fixed_frequency_MHz'] and fc['mapped_frequency_MHz']==s['fch1_mhz']+center*s['df_hz']/1e6
   assert fc['width_channels']==w and fc['drift_hz_s']==0. and fc['zero_drift_index']==zi and fc['descriptive_background_control_only'] is True and fc['automatic_veto'] is False and fc['physical_origin_assigned'] is False
   assert fc['supplementary_plan_frozen_before_this_run'] is True
   assert fc['prospective_before_AZ_powers'] is False and fc['inherited_fixed_companion_rule_frozen_before_current_target_powers'] is False
   fixedchannels=np.full(s['nrows'],center,dtype=np.int32);assert np.array_equal(values[f'fixed_integer_channels_scan{j}'],fixedchannels)
   supported=center-w//2>=0 and center+w//2<raw.shape[1]
   if supported:
    assert fc['status']=='MEASURED';fn=rows(y,fixedchannels,w);fr=rows(raw,fixedchannels,w);fcal=grid[f'calibration_width_{w}'][zi]
    assert fc['normalized_track']==metrics(fn) and fc['raw_track']==metrics(fr);assert values[f'fixed_normalized_row_contributions_scan{j}'].tolist()==fn and values[f'fixed_raw_row_contributions_scan{j}'].tolist()==fr
    assert [fc['calibration_median'],fc['calibration_scale']]==fcal.tolist();fixedscore=(math.fsum(fn)-float(fcal[0]))/float(fcal[1]);assert fc['empirical_score']==fixedscore;metriccount+=2
   else:assert fc['status']=='UNSUPPORTED_NATIVE_BAND' and 'empirical_score' not in fc;fixedscore=None
   metriccount+=2;scalarchecks.append({'identity':list(key),'scan':j,'scalar_score':score,'forced_center_reference':reference,'absolute_error':error});fixedchecks.append({'identity':list(key),'scan':j,'status':fc['status'],'score':fixedscore,'mapped_center_channel':center})
  del raw,y,grid
 assert len(scalarchecks)==len(fixedchecks)==6*len(records)
 assert r['local_track_checks']==len(scalarchecks) and r['fixed_frequency_companion_checks']==sum(x['status']=='MEASURED' for x in fixedchecks)
 assert r['maximum_selected_track_ESS_error']==maxerr
 for path,digest in pins.items():assert sha(path)==digest,('Input changed',path)
 report={'schema':'SETI_AZ_CONTEXT_SUPPLEMENT_INDEPENDENT_REVIEW_V1','status':'PASS','reviewer':'Independent AZ supplement auditor; actual executor recorded in tool receipt','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audit_source_sha256':sha(__file__),'producer_result_sha256':sha(resultpath),'producer_plan_sha256':sha(planpath),'target':p['target'],'primary_id':p['primary_id'],'pending_group_count_verified':len(records),'all_pending_identities_and_unchanged_representatives_verified':True,'preexisting_main_completions_and_prospective_controls_inherited_unchanged':True,'all_saved_raw_pixels_exact_verified':rawpixels,'all_saved_normalized_pixels_exact_verified':normpixels,'scalar_original_track_checks':scalarchecks,'fixed_frequency_companion_checks':fixedchecks,'total_track_metric_records_checked':metriccount,'maximum_original_ESS_error':maxerr,'normalization_reports':normalization,'input_and_source_sha256_before_after':pins,'publication_receipt_checks':publication_receipt_checks,'limits':r['limits']}
 out=B/'INDEPENDENT_CONTEXT_SUPPLEMENT_REVIEW_AZ.json'
 with out.open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print(json.dumps({'status':'PASS','groups':len(records),'original_tracks':len(scalarchecks),'fixed_tracks':len(fixedchecks),'raw_pixels':rawpixels,'normalized_pixels':normpixels,'maximum_ESS_error':maxerr,'review_sha256':sha(out)}),flush=True)
if __name__=='__main__':
 run()
