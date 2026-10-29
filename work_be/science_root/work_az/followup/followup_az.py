"""AV inherited grouping and bounded local windows; no data before --parent-go."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,math,os,sys
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from inherited_grouping_ab import group_catalog
from continuous_normalization_ac import normalize
import publication
B=Path(__file__).resolve().parent
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def arrays(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def publish(p,values):
 p=Path(p);receipt=publication.publish_npz(values,p)
 receiptpath=p.with_suffix('.publication.json');new(receiptpath,receipt)
 return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'publication_receipt_path':str(receiptpath),'publication_receipt_sha256':sha(receiptpath)}
def representative(t,row,intermittent=False):
 r={'source_scan':int(t['seed_source_scan'][row]),'channel_at_midpoint':int(t['seed_channel_at_midpoint'][row]),'width_channels':int(t['seed_width_channels'][row]),'drift_index':int(t['seed_drift_index'][row]),'drift_hz_s':float(t['seed_drift_hz_s'][row]),'frequency_at_midpoint_mhz':float(t['seed_frequency_at_midpoint_mhz'][row]),'source_ESS':float(t['seed_ess'][row]),'projected_centers_six_scans':t['predicted_center'][row].astype(int).tolist(),'forced_center_ESS_six_scans':t['forced_center_ess'][row].tolist(),'forced_neighborhood_ESS_six_scans':t['forced_max_ess'][row].tolist(),'narrow_OFF_flags_six_scans':t['narrow_off_flag'][row].tolist(),'broad_context_max_ESS_six_scans':t['broad_max_ess'][row].tolist()}
 if intermittent:r['exact_ON_threshold_passing_scans']=[j for j in (0,2,4) if t['forced_center_ess'][row,j]>=10.]
 return r
def grouping(t,scopes):
 assert all(2*math.ceil(4.*16*s['dt_seconds']/abs(s['df_hz']))+1==839 for s in scopes),'Inherited interval grouping requires the839-rate geometry'
 g,m=group_catalog(t,scopes)
 inherited_selected=copy.deepcopy(g['selected'])
 g['original_all3ON_selected']=copy.deepcopy(g['original_all3ON_selected'])
 g['original_intermittent_selected']=copy.deepcopy(g['original_intermittent_selected'])
 # Counts, interval components and original AB representatives are retained.
 # The inherited AO prepower rule chooses max source seedESS, then lowest global row.
 for namespace,groups in [('all3ON',g['all3ON_groups']),('intermittent',g['intermittent_groups'])]:
  for item in groups:
   key=('intermittent__' if namespace=='intermittent' else 'all3ON__')+item['class']+'_'+str(item['group_id'])
   rows=m[key];row=max((int(x) for x in rows),key=lambda x:(float(t['seed_ess'][x]),-x))
   item['inherited_AB_representative_global_seed_row']=item['representative_global_seed_row']
   item['inherited_AB_representative']=item['representative']
   item['representative_global_seed_row']=row;item['representative']=representative(t,row,namespace=='intermittent')
   es=t['forced_center_ess'][row,[0,2,4]];ns=t['forced_max_ess'][row,[0,2,4]]
   item['representative_minimum_ON_ESS']=float(np.min(ns if item['class']=='neighborhood_only' else es))
   if namespace=='intermittent':item.update(exact_ON_count=int((es>=10.).sum()),representative_peak_active_ON_ESS=float(max(es)),representative_second_ON_ESS=float(sorted(es)[-2]))
 # Historical original selectors are recorded for traceability but not AZ choice.
 g.pop('selected');g['inherited_AB_selected_descriptive_only']=inherited_selected
 candidates=[('all3ON',[x for x in g['all3ON_groups'] if x['class']=='exact_center']),('intermittent1or2ON',[x for x in g['intermittent_groups'] if x['exact_ON_count'] in (1,2)])]
 selected=[]
 for origin,choices in candidates:
  if choices:
   winner=max(choices,key=lambda x:(x['representative']['source_ESS'],-x['representative_global_seed_row']))
   selected.append({'origin':origin,'group':winner})
 g['selected']=selected;g['AN_selection_rule']='At most one exact3ON frequency component and one exact1or2ON component. Rank maximum source seedESS then lowest global seed row. No backfill and no interval-disjointness requirement in prepower plan.'
 g['intermittent_counts']['inherited_AB_selected_intermittent_frequency_groups']=g['intermittent_counts'].pop('selected_intermittent_frequency_groups')
 g['legacy_selector_count_note']='The inherited_AB_selected_intermittent_frequency_groups field describes the unchanged AB legacy selector, not actual AZ local selections.'
 g['actual_AZ_selection_counts']={'total':len(selected),'exact3ON':sum(s['origin']=='all3ON' for s in selected),'exact1or2ON':sum(s['origin']=='intermittent1or2ON' for s in selected)}
 return g,m
def row_metrics(y,channels,width,lo):
 h=width//2
 assert len(channels)==len(y) and all(int(c)-h-lo>=0 and int(c)+h-lo<y.shape[1] for c in channels)
 rows=[math.fsum(float(v) for v in y[r,int(c)-h-lo:int(c)+h+1-lo]) for r,c in enumerate(channels)]
 positive=[v for v in rows if v>0];pt=math.fsum(positive)
 return {'row_contributions':rows,'total':math.fsum(rows),'positive_row_count':len(positive),'positive_contribution_sum':pt,'maximum_positive_row_fraction':max(positive)/pt if pt>0 else None}
def fixed_geometry(rep,scopes,j):
 source=scopes[rep['source_scan']];frequency=source['fch1_mhz']+int(rep['channel_at_midpoint'])*source['df_hz']/1e6
 dst=scopes[j];center=int(np.rint((frequency-dst['fch1_mhz'])*1e6/dst['df_hz']))
 return frequency,center
def fixed_companion(raw,y,grid,rep,scopes,j):
 frequency,center=fixed_geometry(rep,scopes,j);width=int(rep['width_channels']);nr=raw.shape[0]
 zero=np.flatnonzero(grid['drift_hz_s']==0.);assert len(zero)==1;zi=int(zero[0]);assert np.all(grid['offsets'][zi]==0)
 channels=np.full(nr,center,dtype=np.int32);supported=center-width//2>=0 and center+width//2<raw.shape[1]
 record={'status':'MEASURED' if supported else 'UNSUPPORTED_NATIVE_BAND','source_frequency_MHz':frequency,'mapped_center_channel':center,'mapped_frequency_MHz':scopes[j]['fch1_mhz']+center*scopes[j]['df_hz']/1e6,'width_channels':width,'drift_hz_s':0.,'zero_drift_index':zi,'inherited_fixed_companion_rule_frozen_before_current_target_powers':True,'descriptive_background_control_only':True,'automatic_veto':False,'physical_origin_assigned':False}
 if supported:
  nm=row_metrics(y,channels,width,0);rm=row_metrics(raw,channels,width,0);cal=grid[f'calibration_width_{width}'][zi];assert np.isfinite(cal).all() and cal[1]>0
  record.update(normalized_track=nm,raw_track=rm,calibration_median=float(cal[0]),calibration_scale=float(cal[1]),empirical_score=(nm['total']-float(cal[0]))/float(cal[1]))
 return record,channels
def freeze():
 files=[B/'followup_az.py',B/'inherited_grouping_ab.py',B/'continuous_normalization_ac.py',B/'plot_context_az.py',B/'SOURCE_ADAPTATIONS_AZ.json',B/'publication.py']
 new(B/'PLAN_FROZEN_AZ.json',{'schema':'SETI_AZ_BOUNDED_FOLLOWUP_PLAN_V1','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'HIP44295_powers_read':False,'power_flag_scope':'AZ archivevisit65133 only; parent powers concern other archive IDs','current_archive_visit_65133_powers_read':False,'current_AZ_detector_or_followup_outcomes_read':False,'historical_HIP76603_AO_AP_powers_previously_read':True,'source_sha256':{p.name:sha(p) for p in files},'thresholds':{'ON':10.,'OFF':5.},'grouping':'Inherited exact interval components/counts/memberships. Original representatives retained separately; AZ representatives and top group each selected by maximum source seedESS then lowest global seed row.','selection':'At most one exact3ON and one exact1or2ON component; preserve both if intervals overlap and disclose dependence.','local_window':'Union of six projected midpoint centers and six metadata-mapped fixed-frequency centers, padded1024channels on either side, clipped to storedband; all16rows/sixscans retained. Normalize complete native arrays by exact AC method before slicing.','fixed_frequency_companion':'For each selected representative, source midpoint center defines a fixed frequency using source fch1/df. Round mapped native channel in each destination; zero drift, same width, same16rows, use exact zero-rate grid calibration index and scalar per-row/full math.fsum. Preserve unsupported status where outside native band. Descriptive/background control, no flags/counts/ranking/veto/origin changes. AZ freezes this inherited rule before any AZ visit65133 powers are read. Prior AO/AP HIP76603 power reads concern a different target and do not provide AZ outcomes.', 'plots':'Metadata-driven full saved windows and ±32native-channel zoom centered at each selected source fixed frequency mapped to every scan. Three ON/OFF pairs,all16rows, time-row+seconds axes, cyan original integertrack and orange dashed prospective fixedcenter; shared−2..15 display limits. All centers and retained crop computed without power-dependent choices.', 'checks':'Hash-bound protocol, independent reviewPASS, all6closed scan summaries, catalog/triage publication hashes and native hashes. Recover each selected scalar fsum track from saved calibration with tolerance1e-4+5e-6abs(reference).','limits':['Empirical detector score is not calibrated Gaussian significance. Templatewidth is not intrinsic linewidth.','Frequency components and correlated template rows are not physical emitters or accepted SETI candidates.','Broad OFF evidence remains descriptive; no automatic veto or origin assignment.','Only selected representatives receive bounded local context; all other components remain queued. Local followup of this same cadence adds no extra coverage or epochs.']})
 print(json.dumps({'frozen':True,'plan_sha256':sha(B/'PLAN_FROZEN_AZ.json')}))
def check_plan():
 p=read(B/'PLAN_FROZEN_AZ.json')
 for name,digest in p['source_sha256'].items():assert sha(B/name)==digest
 return p
def smoke():
 check_plan();n=5;centers=np.array([100,300,500,700,100],dtype=np.int32)
 es=np.array([[12,0,12,0,12,0],[11,0,11,0,0,0],[13,0,0,0,0,0],[15,6,15,6,15,6],[14,0,14,0,14,0]],dtype=float)
 flags=np.zeros((n,6),dtype=bool);flags[:,[1,3,5]]=es[:,[1,3,5]]>=5
 t={'seed_ess':np.array([12.,11.,13.,15.,14.]),'forced_status':np.ones((n,6),dtype=np.uint8),'narrow_off_flag':flags,'forced_center_ess':es,'forced_max_ess':es,'seed_source_scan':np.zeros(n,dtype=np.uint8),'seed_width_channels':np.ones(n,dtype=np.int16),'predicted_center':np.repeat(centers[:,None],6,axis=1),'seed_drift_index':np.full(n,419,dtype=np.int32),'seed_channel_at_midpoint':centers,'seed_drift_hz_s':np.zeros(n),'seed_frequency_at_midpoint_mhz':2300-centers*2.7939677238464355e-6,'broad_max_ess':es}
 scopes=[{'tref_midpoint_mjd':100+i/86400,'df_hz':-2.7939677238464355,'fch1_mhz':2300.,'dt_seconds':18.253611008} for i in range(6)]
 g,m=grouping(t,scopes);assert [x['group']['representative_global_seed_row'] for x in g['selected']]==[4,2]
 c=g['intermittent_counts'];assert [c[f'fully_supported_noOFF_exact_ON_count_{k}_rows'] for k in (1,2,3)]==[1,1,2]
 assert np.array_equal(m['all3ON__exact_center_0'],np.array([0,4]))
 # Exact ties select lowest serialized global row.
 tie={**t,'seed_ess':t['seed_ess'].copy()};tie['seed_ess'][4]=12.;gt,_=grouping(tie,scopes);assert gt['selected'][0]['group']['representative_global_seed_row']==0
 unsupported={**t,'forced_status':np.full((n,6),2,dtype=np.uint8)};gu,_=grouping(unsupported,scopes);assert gu['selected']==[]
 # Prospective fixed companion is zero drift and metadata-mapped in a new band.
 nr,nc=16,1024;rates=np.linspace(-4.,4.,839);off=np.rint(rates[:,None]*(np.arange(nr)-7.5)*scopes[0]['dt_seconds']/scopes[0]['df_hz']).astype(np.int32)
 raw=np.full((nr,nc),100.,dtype=np.float32);y=np.zeros_like(raw);width=3;center=400
 raw[:,center-1:center+2]+=2.;y[:,center-1:center+2]=2.
 grid={'drift_hz_s':rates,'offsets':off,'calibration_width_3':np.tile(np.array([0.,2.]),(839,1))}
 rep={'source_scan':0,'channel_at_midpoint':center,'width_channels':width}
 expected=96.;scores=[]
 for j in range(6):
  fc,ch=fixed_companion(raw,y,grid,rep,scopes,j);assert fc['status']=='MEASURED' and fc['mapped_center_channel']==center and fc['zero_drift_index']==419
  assert np.all(ch==center) and fc['normalized_track']['total']==expected and fc['empirical_score']==48.;scores.append(fc['empirical_score'])
 shifted=[dict(s) for s in scopes];shifted[1]['fch1_mhz']-=2*shifted[1]['df_hz']/1e6
 _,mapped=fixed_geometry(rep,shifted,1);assert mapped==center+2
 outside=[dict(s) for s in scopes];outside[1]['fch1_mhz']+=2000*abs(scopes[1]['df_hz'])/1e6
 fc,_=fixed_companion(raw,y,grid,rep,outside,1);assert fc['status']=='UNSUPPORTED_NATIVE_BAND' and 'empirical_score' not in fc
 new(B/'SYNTHETIC_CHECKS_AZ.json',{'status':'PASS','HIP44295_powers_read':False,'power_flag_scope':'AZ archivevisit65133 only; parent powers concern other archive IDs','current_archive_visit_65133_powers_read':False,'current_AZ_detector_or_followup_outcomes_read':False,'historical_HIP76603_AO_AP_powers_previously_read':True,'plan_sha256':sha(B/'PLAN_FROZEN_AZ.json'),'checks':['exact1/2/3partition','OFF exclusion','interval connected components','maxsourceESS ranking','lowestrow tie break','no backfill','unsupported empty selection','newSband metadata frequency mapping','zero-rate calibration index419 derived fromratevector','same-width16row fixed scalar sums and scores','mapped2channel frequency shift','unsupportedfixedcontrol remains explicit without score']})
 print('SYNTHETIC_PASS')
def run(a):
 assert a.parent_go;plan=check_plan();assert read(B/'SYNTHETIC_CHECKS_AZ.json')['status']=='PASS'
 protocol=Path(a.protocol).resolve();results=Path(a.results).resolve();review=Path(a.review).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
 p=read(protocol);rv=read(review);assert rv['status']=='PASS' and rv['protocol_sha256']==sha(protocol)
 reviewed=rv['input_and_source_sha256_before_after']
 reviewed_paths=[protocol]+[results/f'scan{j}_{kind}.npz' for j in range(6) for kind in ('grid','audit','catalog')]+[results/f'scan{j}_summary.json' for j in range(6)]+[results/'all_ON_forced_triage.npz',results/'TRIAGE_SUMMARY.json']
 for path in reviewed_paths:assert str(path) in reviewed and sha(path)==reviewed[str(path)],('Current input differs from independently reviewed file',str(path))
 assert p['target'].upper()=='HIP44295' and p['primary_id']==65133
 assert p['configuration']['threshold_ess']==10. and p['configuration']['off_flag_threshold_ess']==5.
 scopes=p['scans'];assert [s['role'] for s in scopes]==['ON','OFF']*3
 bound={str(protocol):sha(protocol),str(review):sha(review)}
 for s in scopes:
  j=s['scan'];sm=read(results/f'scan{j}_summary.json');assert sm['complete'] and sm['protocol_sha256']==sha(protocol)
  for pub in sm['publications']:assert sha(pub['path'])==pub['sha256'];bound[pub['path']]=pub['sha256']
 triagepath=results/'all_ON_forced_triage.npz';closed=read(results/'TRIAGE_RUN_CLOSED.json');assert closed['status']=='COMPLETE' and closed['protocol_sha256']==sha(protocol)
 assert closed['publications'][0]['sha256']==sha(triagepath);bound[str(triagepath)]=sha(triagepath)
 new(out/'INPUT_BINDING_AZ.json',{'bound_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_NPZ_and_native_loads':True,'files_sha256':bound,'plan_sha256':sha(B/'PLAN_FROZEN_AZ.json')})
 t=arrays(triagepath);g,members=grouping(t,scopes);ts=read(results/'TRIAGE_SUMMARY.json')
 assert g['all3ON_counts']['ON_catalog_rows']==ts['ON_catalog_rows']
 assert g['all3ON_counts']['exact_center_all3ON_noOFF_rows']==ts['no_OFF_flag_all_three_ON_center_above_threshold_rows']
 assert g['all3ON_counts']['inclusive_neighborhood_all3ON_noOFF_rows']==ts['no_OFF_flag_all_three_ON_neighborhood_above_threshold_rows']
 new(out/'GROUPING_AZ.json',g);publications=[publish(out/'ALL_GROUP_MEMBERS_AZ.npz',members)]
 records=[];local=[]
 for number,item in enumerate(g['selected'],1):
  rep=item['group']['representative'];centers=rep['projected_centers_six_scans'];fixedcenters=[fixed_geometry(rep,scopes,j)[1] for j in range(6)];lo=max(0,min(centers+fixedcenters)-1024);hi=min(scopes[0]['nchannels'],max(centers+fixedcenters)+1025)
  records.append({'selection_number':number,'origin':item['origin'],'group':item['group'],'window_lo':lo,'window_hi_exclusive':hi,'fixed_frequency_MHz':fixed_geometry(rep,scopes,rep['source_scan'])[0],'fixed_centers_six_scans':fixedcenters,'scans':[]});local.append({})
 maxerr=0.
 for s in scopes if records else []:
  j=s['scan'];native=Path(p['root'])/s['native_path'];assert sha(native)==s['input_sha256'];bound[str(native)]=s['input_sha256']
  raw=np.load(native,mmap_mode='r',allow_pickle=False);y,anchors=normalize(raw,4096);grid=arrays(results/f'scan{j}_grid.npz')
  for idx,rec in enumerate(records):
   rep=rec['group']['representative'];row=rec['group']['representative_global_seed_row'];width=rep['width_channels'];ri=rep['drift_index'];center=int(t['predicted_center'][row,j]);lo=rec['window_lo'];hi=rec['window_hi_exclusive']
   off=np.rint(rep['drift_hz_s']*(np.arange(16)-7.5)*s['dt_seconds']/s['df_hz']).astype(np.int32);assert np.array_equal(off,grid['offsets'][ri]);assert grid['drift_hz_s'][ri]==rep['drift_hz_s'];ch=center+off
   assert int(ch.min())-width//2>=lo and int(ch.max())+width//2<hi
   vals=np.asarray(raw[:,lo:hi]).copy();norm=np.asarray(y[:,lo:hi]).copy();nr=row_metrics(norm,ch,width,lo);rr=row_metrics(vals,ch,width,lo);cal=grid[f'calibration_width_{width}'][ri]
   score=(nr['total']-float(cal[0]))/float(cal[1]);ref=float(t['forced_center_ess'][row,j]);err=abs(score-ref);assert err<=1e-4+5e-6*abs(ref);maxerr=max(maxerr,err)
   local[idx].update({f'raw_scan{j}':vals,f'normalized_scan{j}':norm,f'original_integer_channels_scan{j}':ch,f'normalized_row_contributions_scan{j}':np.asarray(nr['row_contributions']),f'raw_row_contributions_scan{j}':np.asarray(rr['row_contributions'])})
   companion,fixedchannels=fixed_companion(raw,y,grid,rep,scopes,j)
   local[idx][f'fixed_integer_channels_scan{j}']=fixedchannels
   if companion['status']=='MEASURED':
    local[idx][f'fixed_normalized_row_contributions_scan{j}']=np.asarray(companion['normalized_track']['row_contributions']);local[idx][f'fixed_raw_row_contributions_scan{j}']=np.asarray(companion['raw_track']['row_contributions'])
   rec['scans'].append({'scan':j,'role':s['role'],'fch1_mhz':s['fch1_mhz'],'df_hz':s['df_hz'],'dt_seconds':s['dt_seconds'],'fixed_frequency_companion':companion,'normalized_original_track':nr,'raw_original_track':rr,'calibration_median':float(cal[0]),'calibration_scale':float(cal[1]),'recovered_ESS':score,'forced_center_ESS':ref,'absolute_ESS_error':err})
  del raw,y,grid
 for idx,rec in enumerate(records):
  local[idx]['native_channels']=np.arange(rec['window_lo'],rec['window_hi_exclusive'],dtype=np.int32);publications.append(publish(out/f'SELECTED_{idx+1}_SIX_SCAN_LOCAL_ARRAYS_AZ.npz',local[idx]))
 selectedkeys={(x['origin'],x['group']['class'],x['group']['group_id']) for x in g['selected']};backlog=[]
 for origin,groups in [('all3ON',g['all3ON_groups']),('intermittent1or2ON',g['intermittent_groups'])]:
  for group in groups:backlog.append({'target':'HIP44295','primary_id':65133,'namespace':origin,'class':group['class'],'group_id':group['group_id'],'representative_global_seed_row':group['representative_global_seed_row'],'bounded_local_context_completed':(origin,group['class'],group['group_id']) in selectedkeys})
 for path,digest in bound.items():assert sha(path)==digest
 check_plan();report={'schema':'SETI_AZ_GROUPING_BOUNDED_LOCAL_CONTEXT_V1','status':'COMPLETE','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':'HIP44295','primary_id':65133,'protocol_sha256':sha(protocol),'independent_detector_review_sha256':sha(review),'plan_sha256':sha(B/'PLAN_FROZEN_AZ.json'),'grouping_sha256':sha(out/'GROUPING_AZ.json'),'counts':{'all3ON':g['all3ON_counts'],'exact_ON_classes':g['intermittent_counts']},'selected_representatives':records,'selected_group_count':len(records),'actual_AZ_selection_counts':g['actual_AZ_selection_counts'],'fixed_frequency_companion_checks':sum(x['fixed_frequency_companion']['status']=='MEASURED' for rec in records for x in rec['scans']),'fixed_frequency_companion_scope':'Prospective descriptive background control only; original flags, counts, ranking and selected identities remain unchanged.','local_track_checks':6*len(records),'maximum_selected_track_ESS_error':maxerr,'publications':publications,'local_context_backlog':backlog,'all_input_sha256_after_verified':bound,'physical_origin':'UNRESOLVED','accepted_SETI_candidates':0,'new_examined_MHz_visits':0,'new_independent_epochs':0,'limits':plan['limits']}
 new(out/'FOLLOWUP_RESULT_AZ.json',report);print(json.dumps({'status':'COMPLETE','selected':len(records),'local_track_checks':report['local_track_checks'],'maximum_ESS_error':maxerr,'result_sha256':sha(out/'FOLLOWUP_RESULT_AZ.json')}),flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('action',choices=['freeze','smoke','run']);q.add_argument('--protocol');q.add_argument('--results');q.add_argument('--review');q.add_argument('--output');q.add_argument('--parent-go',action='store_true');a=q.parse_args()
 if a.action=='freeze':freeze()
 elif a.action=='smoke':smoke()
 else:run(a)
