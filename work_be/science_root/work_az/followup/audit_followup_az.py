"""Independent postfollowup audit; no production grouping/normalization imports."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,math,os,sys
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
B=Path(__file__).resolve().parent;W=B.parent.parent
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def arrays(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def exact(a,b):return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
SCOPE=B/'INDEPENDENT_REVIEW_SCOPE_FROZEN_AZ.json'
def new(path,value):
 with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def freeze():
 producer=B/'PLAN_FROZEN_AZ.json';plan=read(producer)
 for name,digest in plan['source_sha256'].items():assert sha(B/name)==digest
 source={'audit_followup_az.py':sha(__file__),'review_source/oracles_independent_ad.py':sha(B/'review_source/oracles_independent_ad.py')}
 value={'schema':'SETI_AZ_INDEPENDENT_FOLLOWUP_REVIEW_SCOPE_V1','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HIP44295','primary_id':65133,'source_sha256':source,'producer_plan_sha256':sha(producer),'producer_source_sha256':plan['source_sha256'],'timing_disclosure':'AZ producer and independent reviewer rules are frozen before any current archivevisit65133 powers or detector/followup outcomes. Parent checkpoint powers concern other archive IDs and remain preserved historical evidence. This reviewer has not loaded any current native arrays, triage NPZs, local windows or followup outcomes. Execution requires explicit AFTER TRIAGE GO, numeric PASS and hash-bound actual exit0 producer/numeric receipts.','current_archive_visit_65133_powers_read':False,'reviewer_current_raw_triage_or_followup_artifacts_read_before_scope':False,'parent_archive_IDs_powers_previously_read':True,'math_review_rules_inherited_unchanged_from_AW':True,'scope':['All triage accounting rows and exact1/2/3ON/neighborhood counts','Every interval component/member array and maximum-sourceESS/lowest-row representative plus topselection/no-backfill','All selected raw and normalized local pixels via independently sorted anchors with disclosed shared np.interp replay','All selected original/fixed-frequency scalar sums,rowcontributions,calibrations,geometry and concentration metrics','Separate actual plot visualQA remains required'],'release':'Require root AFTER TRIAGE GO with exact protocol,result directories,numeric review and actual producer/numeric receipt hashes before target artifact reads.','limits':['No independent full-grid accumulation oracle claim.','Empirical scores are not Gaussian significance,globalFAP or astronomical sensitivity.','Prospective fixed-frequency controls remain descriptive; no flags/counts/ranking changes,automatic veto or physical origin assignment.']}
 new(SCOPE,value);print(json.dumps({'status':'REVIEW_SCOPE_FROZEN_BEFORE_CURRENT_VISIT_POWERS','scope_sha256':sha(SCOPE),'source_sha256':source}),flush=True)
def check_scope():
 scope=read(SCOPE)
 for name,digest in scope['source_sha256'].items():assert sha(B/name)==digest
 assert sha(B/'PLAN_FROZEN_AZ.json')==scope['producer_plan_sha256']
 for name,digest in scope['producer_source_sha256'].items():assert sha(B/name)==digest
 return scope
def smoke():
 scope=check_scope();p=B/'review_source/oracles_independent_ad.py';spec=importlib.util.spec_from_file_location('ao_review_smoke_oracle',p);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 y=np.arange(16*128,dtype=np.float32).reshape(16,128);off=np.zeros(16,dtype=np.int32);centers=np.array([32,64,96],dtype=np.int32);checks=0
 for width in (1,3,9,33):
  got=oracle.fsum_tracks(y,off,centers,width)
  expected=np.array([math.fsum(float(y[t,c+d]) for t in range(16) for d in range(-width//2+1,width//2+1)) for c in centers])
  assert exact(got,expected);checks+=len(centers)
 new(B/'INDEPENDENT_REVIEW_SYNTHETIC_SMOKE_AZ.json',{'status':'PASS','HIP44295_powers_read':False,'power_flag_scope':'AZ archivevisit65133 only; parent powers concern other archive IDs','current_archive_visit_65133_powers_read':False,'AU_target_values_read_during_smoke':False,'historical_HIP76603_AO_AP_powers_previously_read':True,'historical_HIP77052_AQ_powers_previously_read':True,'historical_HIP77060_AR_powers_previously_read':True,'historical_HIP105932_AS_powers_previously_read':True,'historical_HIP110951_AT_powers_previously_read':True,'scope_sha256':sha(SCOPE),'independent_scalar_fixture_cases':checks,'shared_source_paths_changed':False})
 print(json.dumps({'status':'SYNTHETIC_SMOKE_PASS','cases':checks}),flush=True)
def gate(go_path):
 scope=check_scope();assert read(B/'INDEPENDENT_REVIEW_SYNTHETIC_SMOKE_AZ.json')['status']=='PASS'
 go_path=Path(go_path).resolve();go=read(go_path);assert go['authorized'] is True and go['root_after_triage'] is True
 protocol=Path(go['protocol_path']).resolve();resultdir=Path(go['followup_results_directory']).resolve();detector=Path(go['detector_results_directory']).resolve();review=Path(go['numeric_review_path']).resolve()
 assert protocol==W/'work_az/PROTOCOL_BOUND_AZ.json' and resultdir==B/'results' and detector==W/'work_az/results'
 pins={str(go_path):sha(go_path),str(SCOPE):sha(SCOPE)}
 for path,key in [(protocol,'protocol_sha256'),(review,'numeric_review_sha256'),(resultdir/'FOLLOWUP_RESULT_AZ.json','followup_result_sha256'),(Path(go['numeric_actual_tool_path']).resolve(),'numeric_actual_tool_sha256'),(Path(go['followup_actual_tool_path']).resolve(),'followup_actual_tool_sha256')]:
  assert sha(path)==go[key],('Root expected hash differs',str(path));pins[str(path)]=go[key]
 numeric_actual=read(go['numeric_actual_tool_path']);followup_actual=read(go['followup_actual_tool_path'])
 for receipt in (numeric_actual,followup_actual):assert receipt.get('actual_exit_code',receipt.get('exit_code'))==0
 assert followup_actual['result_sha256']==go['followup_result_sha256']
 numeric=read(review);assert numeric['status']=='PASS' and numeric['protocol_sha256']==go['protocol_sha256']
 return scope,go,protocol,resultdir,detector,review,pins
def run(args):
 scope,go,protocol,resultdir,detector,review,launch_pins=gate(args.parent_go)
 p=read(protocol);r=read(resultdir/'FOLLOWUP_RESULT_AZ.json');g=read(resultdir/'GROUPING_AZ.json');rv=read(review)
 assert rv['status']=='PASS' and rv['protocol_sha256']==r['protocol_sha256']==sha(protocol)
 assert p['target']==r['target']=='HIP44295' and p['primary_id']==r['primary_id']==65133
 pins={str(x):sha(x) for x in [Path(__file__),protocol,review,resultdir/'FOLLOWUP_RESULT_AZ.json',resultdir/'GROUPING_AZ.json',resultdir/'ALL_GROUP_MEMBERS_AZ.npz']}
 pins.update(launch_pins)
 planpath=B/'PLAN_FROZEN_AZ.json';plan=read(planpath);assert r['plan_sha256']==sha(planpath);pins[str(planpath)]=sha(planpath)
 for name,digest in plan['source_sha256'].items():assert sha(B/name)==digest;pins[str(B/name)]=digest
 publication_receipt_checks=[]
 for item in r['publications']:
  assert sha(item['path'])==item['sha256'];pins[item['path']]=item['sha256']
  receiptpath=Path(item['publication_receipt_path']);assert receiptpath==Path(item['path']).with_suffix('.publication.json')
  assert sha(receiptpath)==item['publication_receipt_sha256'];pins[str(receiptpath)]=item['publication_receipt_sha256'];pr=read(receiptpath)
  assert pr['status']=='PASS' and pr['format']=='npz' and pr['all_publication_checks_pass'] and pr['no_overwrite_repair_or_retry']
  assert pr['destination']==item['path'] and pr['stage_validation']==pr['published_validation']
  for validation in (pr['stage_validation'],pr['published_validation']):assert validation['CRC_verified'] and validation['exact_typed_arrays_verified']
  assert pr['stage']['sha256']==pr['published']['sha256']==item['sha256'] and pr['stage']['size_bytes']==pr['published']['size_bytes']==item['bytes']==Path(item['path']).stat().st_size
  assert (pr['stage']['device'],pr['stage']['inode'])!=(pr['published']['device'],pr['published']['inode'])
  assert not Path(pr['staging_path']).is_relative_to(B)
  publication_receipt_checks.append({'path':item['path'],'receipt_sha256':sha(receiptpath),'stage_published_byte_identity':True,'exact_typed_array_validation_recorded':True,'private_staging_independent_inode':True})
 tpath=detector/'all_ON_forced_triage.npz';assert sha(tpath)==rv['input_and_source_sha256_before_after'][str(tpath)];pins[str(tpath)]=sha(tpath)
 t=arrays(tpath);members=arrays(resultdir/'ALL_GROUP_MEMBERS_AZ.npz');scopes=p['scans']
 n=len(t['seed_ess']);supported=np.all(t['forced_status']==1,axis=1);flags=t['narrow_off_flag'];off=flags.any(axis=1);eligible=supported&~off
 assert np.array_equal(flags[:,[1,3,5]],t['forced_max_ess'][:,[1,3,5]]>=5.) and not flags[:,[0,2,4]].any()
 es=t['forced_center_ess'][:,[0,2,4]];ns=t['forced_max_ess'][:,[0,2,4]];en=(es>=10.).sum(axis=1);nn=(ns>=10.).sum(axis=1)
 c=r['counts']['exact_ON_classes'];c3=r['counts']['all3ON']
 assert c3['ON_catalog_rows']==n and c3['fully_supported_rows']==int(supported.sum()) and c3['any_OFF_flag_rows']==int(off.sum())
 assert c['fully_supported_noOFF_rows']==int(eligible.sum())
 for count in range(4):
  assert c[f'fully_supported_noOFF_exact_ON_count_{count}_rows']==int((eligible&(en==count)).sum())
  assert c[f'fully_supported_noOFF_neighborhood_ON_count_{count}_rows']==int((eligible&(nn==count)).sum())
 assert c3['exact_center_all3ON_noOFF_rows']==int((eligible&(en==3)).sum())
 assert c3['inclusive_neighborhood_all3ON_noOFF_rows']==int((eligible&(nn==3)).sum())
 assert c3['neighborhood_only_all3ON_noOFF_rows']==int((eligible&(nn==3)&(en!=3)).sum())
 definitions=[('all3ON','exact_center',eligible&(en==3)),('all3ON','neighborhood_only',eligible&(nn==3)&(en!=3))]+[('intermittent',f'exact_{k}_ON',eligible&(en==k)) for k in (1,2,3)]
 expected_member_keys=set();group_checks=[];group_members={};step=8./838.;ref=scopes[0]
 for namespace,label,mask in definitions:
  rows=np.flatnonzero(mask);intervals=[]
  for row in rows:
   source=int(t['seed_source_scan'][row]);width=int(t['seed_width_channels'][row]);gap=(ref['tref_midpoint_mjd']-scopes[source]['tref_midpoint_mjd'])*86400
   radius=math.ceil(1+.5*step*abs(gap)/abs(ref['df_hz']));center=int(t['predicted_center'][row,0]);intervals.append((center-width//2-radius,center+width//2+radius,source,int(row)))
  intervals.sort();components=[];current=[];upper=None
  for lo,hi,source,row in intervals:
   if upper is None or lo>upper:
    if current:components.append(current)
    current=[row];upper=hi
   else:current.append(row);upper=max(upper,hi)
  if current:components.append(current)
  table=[x for x in g['all3ON_groups' if namespace=='all3ON' else 'intermittent_groups'] if x['class']==label]
  assert len(table)==len(components)
  for gid,component in enumerate(components):
   key=('all3ON__' if namespace=='all3ON' else 'intermittent__')+label+'_'+str(gid);expected_member_keys.add(key)
   assert exact(members[key],np.asarray(component,dtype=np.int64));group=table[gid];assert group['group_id']==gid and group['template_rows']==len(component)
   winner=max(component,key=lambda row:(float(t['seed_ess'][row]),-row));assert group['representative_global_seed_row']==winner
   rep=group['representative'];assert rep['source_ESS']==float(t['seed_ess'][winner]) and rep['source_scan']==int(t['seed_source_scan'][winner])
   for field,keyfield in [('projected_centers_six_scans','predicted_center'),('forced_center_ESS_six_scans','forced_center_ess'),('forced_neighborhood_ESS_six_scans','forced_max_ess'),('narrow_OFF_flags_six_scans','narrow_off_flag'),('broad_context_max_ESS_six_scans','broad_max_ess')]:assert np.array_equal(np.asarray(rep[field]),t[keyfield][winner])
   component_set=set(component);iv=[x for x in intervals if x[3] in component_set];lo=min(x[0] for x in iv);hi=max(x[1] for x in iv);assert group['reference_channel_interval_inclusive']==[lo,hi]
   freqs=sorted([ref['fch1_mhz']+lo*ref['df_hz']/1e6,ref['fch1_mhz']+hi*ref['df_hz']/1e6]);assert group['reference_frequency_limits_mhz']==freqs
   group_checks.append({'namespace':namespace,'class':label,'group_id':gid,'member_rows':len(component),'source_ESS_winner_row':winner});group_members[(namespace,label,gid)]=component
 assert set(members)==expected_member_keys
 expected_selected=[]
 for origin,choices in [('all3ON',[x for x in g['all3ON_groups'] if x['class']=='exact_center']),('intermittent1or2ON',[x for x in g['intermittent_groups'] if x['exact_ON_count'] in (1,2)])]:
  if choices:
   winner=max(choices,key=lambda x:(float(t['seed_ess'][x['representative_global_seed_row']]),-x['representative_global_seed_row']));expected_selected.append((origin,winner['class'],winner['group_id'],winner['representative_global_seed_row']))
 actual=[(x['origin'],x['group']['class'],x['group']['group_id'],x['group']['representative_global_seed_row']) for x in r['selected_representatives']]
 assert actual==expected_selected and len(actual)==r['selected_group_count']
 expected_selection_counts={'total':len(actual),'exact3ON':sum(x[0]=='all3ON' for x in actual),'exact1or2ON':sum(x[0]=='intermittent1or2ON' for x in actual)}
 assert r['actual_AZ_selection_counts']==g['actual_AZ_selection_counts']==expected_selection_counts
 # Independent sorted-anchor reconstruction; shared np.interp replay disclosed.
 oraclepath=B/'review_source/oracles_independent_ad.py';pins[str(oraclepath)]=sha(oraclepath)
 spec=importlib.util.spec_from_file_location('followup_independent_normalizer',oraclepath);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 local=[arrays(resultdir/f'SELECTED_{k+1}_SIX_SCAN_LOCAL_ARRAYS_AZ.npz') for k in range(len(actual))];checks=[];fixedchecks=[];maxerr=0.;raw_pixels=norm_pixels=0;metric_records=0
 for s in scopes if local else []:
  j=s['scan'];native=Path(p['root'])/s['native_path'];assert sha(native)==s['input_sha256'];pins[str(native)]=s['input_sha256'];raw=np.load(native,mmap_mode='r',allow_pickle=False);y,_,_,_=oracle.normalize_independently(raw,4096)
  gridpath=detector/f'scan{j}_grid.npz';assert sha(gridpath)==rv['input_and_source_sha256_before_after'][str(gridpath)];pins[str(gridpath)]=sha(gridpath);grid=arrays(gridpath)
  for k,item in enumerate(r['selected_representatives']):
   lo=item['window_lo'];hi=item['window_hi_exclusive'];rep=item['group']['representative'];row=item['group']['representative_global_seed_row'];width=rep['width_channels'];ri=rep['drift_index'];center=int(t['predicted_center'][row,j]);values=local[k]
   assert exact(values['native_channels'],np.arange(lo,hi,dtype=np.int32));assert exact(values[f'raw_scan{j}'],np.asarray(raw[:,lo:hi]));assert exact(values[f'normalized_scan{j}'],np.asarray(y[:,lo:hi]));raw_pixels+=16*(hi-lo);norm_pixels+=16*(hi-lo)
   offsets=np.rint(rep['drift_hz_s']*(np.arange(16)-7.5)*s['dt_seconds']/s['df_hz']).astype(np.int32);channels=center+offsets
   assert np.array_equal(channels,values[f'original_integer_channels_scan{j}']) and np.array_equal(offsets,grid['offsets'][ri])
   nr=[math.fsum(float(y[trow,int(ch)-width//2+d]) for d in range(width)) for trow,ch in enumerate(channels)]
   rr=[math.fsum(float(raw[trow,int(ch)-width//2+d]) for d in range(width)) for trow,ch in enumerate(channels)]
   assert values[f'normalized_row_contributions_scan{j}'].tolist()==nr and values[f'raw_row_contributions_scan{j}'].tolist()==rr
   sr=item['scans'][j];assert sr['normalized_original_track']['row_contributions']==nr and sr['raw_original_track']['row_contributions']==rr
   cal=grid[f'calibration_width_{width}'][ri];assert sr['calibration_median']==cal[0] and sr['calibration_scale']==cal[1]
   score=(math.fsum(nr)-float(cal[0]))/float(cal[1]);reference=float(t['forced_center_ess'][row,j]);error=abs(score-reference);assert score==sr['recovered_ESS'] and error<=1e-4+5e-6*abs(reference);maxerr=max(maxerr,error)
   assert sr['fch1_mhz']==s['fch1_mhz'] and sr['df_hz']==s['df_hz']
   checks.append({'selection_number':k+1,'scan':j,'scalar_score':score,'reference_forced_score':reference,'absolute_score_error':error})
   source=scopes[rep['source_scan']];frequency=source['fch1_mhz']+int(rep['channel_at_midpoint'])*source['df_hz']/1e6;fixedcenter=int(np.rint((frequency-s['fch1_mhz'])*1e6/s['df_hz']));fixedchannels=np.full(16,fixedcenter,dtype=np.int32);fc=sr['fixed_frequency_companion']
   zero=np.flatnonzero(grid['drift_hz_s']==0.);assert len(zero)==1;zi=int(zero[0]);assert np.all(grid['offsets'][zi]==0)
   assert fc['zero_drift_index']==zi and fc['drift_hz_s']==0. and fc['width_channels']==width and fc['mapped_center_channel']==fixedcenter and fc['source_frequency_MHz']==frequency
   assert item['fixed_frequency_MHz']==frequency and item['fixed_centers_six_scans'][j]==fixedcenter
   assert fc['mapped_frequency_MHz']==s['fch1_mhz']+fixedcenter*s['df_hz']/1e6 and np.array_equal(local[k][f'fixed_integer_channels_scan{j}'],fixedchannels)
   assert fc['inherited_fixed_companion_rule_frozen_before_current_target_powers'] is True and fc['descriptive_background_control_only'] is True and fc['automatic_veto'] is False and fc['physical_origin_assigned'] is False
   supported=fixedcenter-width//2>=0 and fixedcenter+width//2<raw.shape[1]
   metricitems=[sr['normalized_original_track'],sr['raw_original_track']]
   if supported:
    assert fc['status']=='MEASURED';fn=[math.fsum(float(y[trow,fixedcenter-width//2+d]) for d in range(width)) for trow in range(16)];fr=[math.fsum(float(raw[trow,fixedcenter-width//2+d]) for d in range(width)) for trow in range(16)]
    fcal=grid[f'calibration_width_{width}'][zi];fixedscore=(math.fsum(fn)-float(fcal[0]))/float(fcal[1]);assert fc['empirical_score']==fixedscore and fc['calibration_median']==fcal[0] and fc['calibration_scale']==fcal[1]
    assert fc['normalized_track']['row_contributions']==fn and fc['raw_track']['row_contributions']==fr and local[k][f'fixed_normalized_row_contributions_scan{j}'].tolist()==fn and local[k][f'fixed_raw_row_contributions_scan{j}'].tolist()==fr
    metricitems.extend([fc['normalized_track'],fc['raw_track']])
   else:assert fc['status']=='UNSUPPORTED_NATIVE_BAND' and 'empirical_score' not in fc
   for m in metricitems:
    rows=m['row_contributions'];pos=[v for v in rows if v>0];ps=math.fsum(pos);assert m['total']==math.fsum(rows) and m['positive_row_count']==len(pos) and m['positive_contribution_sum']==ps and m['maximum_positive_row_fraction']==(max(pos)/ps if ps>0 else None);metric_records+=1
   fixedchecks.append({'selection_number':k+1,'scan':j,'source_frequency_MHz':frequency,'mapped_center_channel':fixedcenter,'zero_rate_index':zi,'status':fc['status'],'scalar_score':fc.get('empirical_score')})
  del raw,y,grid
 assert len(fixedchecks)==6*len(actual)==r['fixed_frequency_companion_checks']
 assert r['new_examined_MHz_visits']==r['new_independent_epochs']==r['accepted_SETI_candidates']==0 and r['physical_origin']=='UNRESOLVED'
 for path,d in pins.items():assert sha(path)==d,('Changed input',path)
 report={'schema':'SETI_AZ_INDEPENDENT_FOLLOWUP_REVIEW_V1','status':'PASS','reviewer':'Independent AV auditor; actual executor recorded in tool receipt','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_scope_sha256':sha(SCOPE),'review_scope_timing_disclosure':scope['timing_disclosure'],'root_after_triage_authorization_sha256':sha(args.parent_go),'result_sha256':sha(resultdir/'FOLLOWUP_RESULT_AZ.json'),'protocol_sha256':sha(protocol),'all_files_sha256_before_after':pins,'publication_receipt_checks':publication_receipt_checks,'all_triage_accounting_rows_checked':n,'eligible_noOFF_rows':int(eligible.sum()),'all_interval_components_and_memberships_checked':group_checks,'all_group_membership_arrays_checked':len(members),'all_AZ_representative_rankings_checked':len(group_checks),'AV_selected_identities_checked':actual,'actual_AZ_selection_counts_verified':expected_selection_counts,'raw_window_pixels_exact_verified':raw_pixels,'normalized_window_pixels_exact_verified':norm_pixels,'selected_scalar_track_checks':checks,'prospective_fixed_frequency_companion_checks':fixedchecks,'total_track_metric_records_checked':metric_records,'maximum_selected_score_error':maxerr,'all_sourceESS_ranking_tie_breaks_and_no_backfill_checked':True,'limits':['All current triage accounting/component membership was checked; no independent full detectorgrid accumulation claim.','Local windows and selected tracks only. Normalization uses independently sorted anchors and shared np.interp fullpixel replay; separate bounded scalar interpolation was performed by the pinned oracle.','Prospective fixed-frequency background controls do not change original flags/counts/ranking and do not assign physical origin or automatic veto.','No accepted SETI candidate, physical origin, intrinsic linewidth, astronomical sensitivity or FAP is established.','Actual plot visual QA is separate.']}
 with (B/'INDEPENDENT_FOLLOWUP_REVIEW_AZ.json').open('x') as out:json.dump(report,out,indent=2,sort_keys=True,allow_nan=False);out.write('\n')
 print(json.dumps({'status':'PASS','rows':n,'groups':len(group_checks),'tracks':len(checks),'maximum_score_error':maxerr,'review_sha256':sha(B/'INDEPENDENT_FOLLOWUP_REVIEW_AZ.json')}),flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('action',choices=['freeze','smoke','run']);q.add_argument('--parent-go');a=q.parse_args()
 if a.action=='freeze':freeze()
 elif a.action=='smoke':smoke()
 else:
  assert a.parent_go,'Explicit hash-bound root AFTER TRIAGE release required';run(a)
