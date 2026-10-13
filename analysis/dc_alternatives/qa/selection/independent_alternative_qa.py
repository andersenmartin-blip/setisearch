#!/usr/bin/env python3
"""Independent exhaustive original-family audit, admitted only after root GO.

No producer/detector imports. Complete original frames and immutable original
terms feed exact prefix scores; independently reestimated terms are audit-only.
The broad prior cached-map QA is authenticated and reused without rescoring.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,importlib.util,json,os,resource,signal,sys,time
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
CPU_CAP=600;WALL_CAP=900;RAM_CAP=2147483648
TARGETS=['epoch1_on','epoch2_on','epoch3_on'];CHUNK=1048576;CORE=4096
FCH1=2802832031.25;DF=-2.7939677238464355;TSAMP=18.253611008
DC=[178782208,179830784,180879360]

def require(condition,message):
 if not condition:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def read(path):return json.loads(path.read_bytes(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def save(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def rankkey(r):return (-r['score'],r['frequency_hz_at_own_first_midpoint'],r['drift_hz_s'],r['width_channels'],r['native_chunk_index'],r['core_q'],r['carrier_index_in_core'])
def clean_point(group,original,score,drift,width,index,centers):
 m=group['source_map_metadata'];scan=group['primary_scan_id']
 return {'primary_scan_id':scan,'primary_target':'HIP98505','scan_id':scan,'original_acquisition_role':'ON','reference_origin_scan_id':scan,
 'native_chunk_index':group['native_chunk_index'],'core_q':group['core_q'],'carrier_index_in_core':original['carrier_index_in_core'],
 'reference_source_channel':original['reference_source_channel'],'frequency_hz_at_own_first_midpoint':original['frequency_hz_at_own_first_midpoint'],
 'reference_time_mjd':group['reference_time_mjd'],'origin_tstart_mjd':group['origin_tstart_mjd'],'reference_seconds_from_anchor':group['reference_seconds_from_anchor'],
 'MJD_anchor':group['MJD_anchor'],'original_origin_row_times_from_reference_s':group['original_origin_row_times_from_reference_s'],
 'score':float(score),'drift_hz_s':float(drift),'width_channels':int(width),'drift_grid_index':int(index),'rounded_absolute_centers':[int(c) for c in centers],
 'map_pin':m['map_pin'],'normalization_pin':m['normalization_pin'],'original_checkpoint_pin':m['checkpoint_pin'],
 'score_provenance':'EXACT_ORIGINAL_PREFIX_DC_UNTOUCHED_ALTERNATIVE','source_kind':'recovered_original_DC_free_hypothesis'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-only',action='store_true');p.add_argument('--scope',type=Path,default=BASE/'scope.json');p.add_argument('--go',type=Path);args=p.parse_args()
 if args.check_only:
  print(json.dumps({'status':'PROSPECTIVE_QA_CODE_ONLY','code_sha256':digest(Path(__file__)),'source_float_values_read':0,'hypothesis_scores_computed':0}));return
 require(args.go is not None,'Root GO required');go=read(args.go);qascope=read(args.scope)
 require(go['authorized'] and go['qa_code_sha256']==digest(Path(__file__)) and go['qa_scope_sha256']==digest(args.scope),'Frozen QA admission mismatch')
 require(not (BASE/'QA_RECEIPT.json').exists(),'QA receipt must not be overwritten')
 def deadline(*a):raise TimeoutError('Independent alternative QA resource cap')
 signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.alarm(WALL_CAP)
 resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(RAM_CAP,RAM_CAP))
 started=time.monotonic();cpu=time.process_time();pins={};checks=0;mismatches=[];errors={};audits=[]
 import numpy as np
 require(np.__version__=='2.3.5','Original NumPy2.3.5 required')
 sys.path.insert(0,str(ROOT/'on_cached/deps'));import h5py,hdf5plugin
 require(h5py.__version__=='3.15.1' and h5py.version.hdf5_version=='1.14.6','Frozen HDF5 runtime mismatch')
 require(hdf5plugin.register(filters='bshuf',force=True) and h5py.h5z.filter_avail(32008),'Bitshuffle unavailable')
 def checked(path,declared=None):
  path=path.resolve();actual={'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
  require(declared is None or all(actual[k]==declared[k] for k in ('bytes','sha256')),'Input hash mismatch '+actual['path'])
  require(str(path) not in pins or pins[str(path)]==actual,'Input changed');pins[str(path)]=actual;return path
 def equal(actual,expected,label):
  nonlocal checks
  checks+=1
  if isinstance(actual,np.ndarray) or isinstance(expected,np.ndarray):ok=np.array_equal(actual,expected)
  else:ok=actual==expected
  if not ok:mismatches.append(label)
  return ok
 def close(actual,expected,label,tolerance):
  nonlocal checks
  checks+=1;difference=float(np.max(np.abs(np.asarray(actual,dtype=float)-np.asarray(expected,dtype=float))))
  errors[label.split('/')[0]]=max(errors.get(label.split('/')[0],0),difference)
  if difference>tolerance:mismatches.append(label)
  return difference
 for pin in qascope['input_pins']:checked(ROOT/pin['path'],pin)
 checked(Path(__file__));checked(args.scope);checked(args.go)
 kernel_path=checked(ROOT/qascope['independent_kernel_pin']['path'],qascope['independent_kernel_pin'])
 spec=importlib.util.spec_from_file_location('independent_frozen_core',kernel_path);kernel=importlib.util.module_from_spec(spec);spec.loader.exec_module(kernel)
 search=ROOT/'dc_alternatives/search';scope=read(checked(ROOT/qascope['producer_scope_path']))
 equal(digest(search/'scope.json'),go['producer_scope_sha256'],'root_admission/scope');equal(digest(search/'recover_alternatives.py'),go['producer_code_sha256'],'root_admission/producer')
 require(scope['primary_scan_ids']==TARGETS and len(scope['groups'])==18,'Original group domain differs')
 equal(scope['constants'],{'fch1_hz':FCH1,'df_hz':DF,'tsamp_s':TSAMP,'rows':16,'core_channels':CORE,'fine_channels_per_native':CHUNK,'DC_channels':DC},'original_constants')
 prior=read(checked(ROOT/qascope['prior_all_map_QA_receipt_pin']['path'],qascope['prior_all_map_QA_receipt_pin']))
 equal(prior['status'],'PASS_INDEPENDENT_ALL9412608_ON_CARRIER_SELECTION','prior_all_map_QA/status')
 equal(prior['counts']['maps'],2298,'prior_all_map_QA/maps');equal(prior['counts']['excluded'],7083,'prior_all_map_QA/excluded');equal(prior['mismatches'],[],'prior_all_map_QA/mismatches')
 inventory=read(checked(ROOT/scope['excluded_inventory_pin']['path'],scope['excluded_inventory_pin']))
 require(len(inventory['records'])==7083 and len(inventory['groups'])==18,'Inventory dimensions differ')
 producer={};summaries={};actual_records={}
 for scan in TARGETS:
  folder=search/scan;receipt=read(checked(folder/'EXECUTION_RECEIPT.json'))
  equal(receipt['scope_sha256'],digest(search/'scope.json'),scan+'/receipt_scope');equal(receipt['producer_sha256'],digest(search/'recover_alternatives.py'),scan+'/receipt_code')
  equal(receipt['status'],'PASS_EXACT_ORIGINAL_UNRESTRICTED_REPLAY_AND_DC_ALTERNATIVES',scan+'/receipt_status')
  for pin in receipt['outputs']:checked(ROOT/pin['path'],pin)
  result=read(checked(folder/'RESULT.json'));producer[scan]=result
  require(len(result['group_summaries'])==6 and len(result['alternative_records'])==2361,'Producer result dimensions differ')
  for summary in result['group_summaries']:
   gid=summary['group_id'];require(gid not in summaries,'Duplicate group summary');summaries[gid]=summary
  for r in result['alternative_records']:
   o=r['original_cached_tuple_and_DC_geometry'];identity=(o['group_id'],o['carrier_index_in_core']);require(identity not in actual_records,'Duplicate recovered record');actual_records[identity]=r
 expected_records={};clean_candidates={s:[] for s in TARGETS};counts={s:{'inventory_carriers':0,'recovered_nonempty_carriers':0,'EMPTY_carriers':0,'original_unrestricted_tuples_reconciled_exactly':0,'original_hypothesis_score_occurrences':0,'admissible_hypothesis_occurrences':0,'raw_frames_saved':0,'native_sources_decoded_once':0,'new_normalization_fits':0,'new_telescope_HTTP':0} for s in TARGETS}
 norm_errors={};tie_carriers=0;tie_max=0;row_hashes=0;fullframe_positions=0;direct_audits=0
 for scan in TARGETS:
  groups=[g for g in scope['groups'] if g['primary_scan_id']==scan]
  require({(g['native_chunk_index'],g['core_q']) for g in groups}=={(n,q) for n in (170,171,172) for q in (127,128)},'Affected group coverage differs')
  for native in (170,171,172):
   same=[g for g in groups if g['native_chunk_index']==native];declaration=same[0]['raw_source_metadata']
   equal(same[0]['raw_source_pin'],same[1]['raw_source_pin'],scan+'/same_native_source')
   source=checked(ROOT/same[0]['raw_source_pin']['path'],same[0]['raw_source_pin'])
   with h5py.File(source,'r',rdcc_nbytes=8*1024**2) as f:
    data=f['data'];require(data.shape==(16,1,CHUNK) and data.dtype.str=='<f4','Raw source header differs')
    equal(int(data.attrs['original_source_frequency_chunk_origin']),native*CHUNK,scan+'/raw_source_origin');parent=data[:,0,:]
   require(len(declaration['decoded_rows'])==16,'Raw source row pins incomplete')
   for row in declaration['decoded_rows']:
    payload=parent[row['time_row']].astype('<f4',copy=False).tobytes();equal(len(payload),row['decoded_bytes'],'source_row/bytes');equal(hashlib.sha256(payload).hexdigest(),row['decoded_sha256'],'source_row/hash');row_hashes+=1
   counts[scan]['native_sources_decoded_once']+=1
   for group in same:
    gid=group['group_id'];summary=summaries[gid];frame=group['exact_original_frame'];q=group['core_q'];source0=native*CHUNK+q*CORE-4000
    equal(frame['original_s_power_source_channel0'],source0,gid+'/frame_origin');equal(frame['original_s_power_shape'],[16,12096],gid+'/frame_shape')
    equal(group['original_origin_row_times_from_reference_s'],[r*TSAMP for r in range(16)],gid+'/own_row_times')
    rawpath=checked(ROOT/summary['raw_frame_pin']['path'],summary['raw_frame_pin'])
    with np.load(rawpath,allow_pickle=False) as a:
     require(set(a.files)=={'raw_power','source_channel0','normalization_source_channel_interval_half_open'},'Saved frame schema differs')
     raw=a['raw_power'];equal(raw.shape,(16,12096),gid+'/raw_frame_shape');equal(raw.dtype.str,'<f4',gid+'/raw_frame_dtype')
     equal(int(a['source_channel0']),source0,gid+'/saved_origin');equal(a['normalization_source_channel_interval_half_open'],frame['normalization_source_channel_interval_half_open'],gid+'/saved_core_interval')
    lo,hi=frame['native_parent_slice_local_half_open'];equal(raw.view(np.uint32),parent[:,lo:hi].view(np.uint32),gid+'/original_H5_frame_bits')
    m=group['source_map_metadata'];checked(ROOT/m['checkpoint_pin']['path'],m['checkpoint_pin']);norm=read(checked(ROOT/m['normalization_pin']['path'],m['normalization_pin']))
    equal(norm['normalization_source_channels'],list(range(*frame['normalization_source_channel_interval_half_open'])),gid+'/original_norm_core');equal(norm['normalization_unmasked_counts'],[4096]*16,gid+'/unmasked')
    independent=kernel.independent_core_normalization_audit(raw,source0,frame['normalization_source_channel_interval_half_open'],np)
    for name,value in independent.items():norm_errors[name]=max(norm_errors.get(name,0),close(value,norm[name],'norm_'+name+'/'+gid,qascope['normalization_absolute_tolerance']))
    z=kernel.original_z_from_raw_frame(raw,norm,np);fullframe_positions+=z.size
    equal(hashlib.sha256(z.astype('<f8',copy=False).tobytes()).hexdigest(),summary['original_normalized_z_rowmajor_float64_sha256'],gid+'/fullframe_z_bits')
    with np.load(checked(ROOT/m['map_pin']['path'],m['map_pin']),allow_pickle=False) as a:maps={k:a[k] for k in a.files}
    grid=maps['drift_grid_hz_s'];equal(grid,np.linspace(-4,4,785),gid+'/original_grid_bits');equal(maps['valid_hypothesis_count'],np.full(4096,1570,dtype=np.int64),gid+'/old_valid_counts')
    equal(maps['source_reference_channels'],np.arange(native*CHUNK+q*CORE,native*CHUNK+(q+1)*CORE,dtype=np.int64),gid+'/reference_channels');equal(maps['frequency_hz_at_tref'],FCH1+DF*maps['source_reference_channels'],gid+'/reference_frequencies')
    touched=np.zeros(CORE,dtype=bool);old_centers=[]
    for row in range(16):
     center=np.rint((maps['frequency_hz_at_tref']-FCH1)/DF+maps['winning_drift_hz_s']*(row*TSAMP)/DF).astype(np.int64);old_centers.append(center)
     for dc in DC:touched|=np.abs(center-dc)<=maps['winning_width_channels']//2
    indices=np.flatnonzero(touched);originals=[inventory['records'][i] for i in group['excluded_inventory_indices']]
    equal(indices,np.asarray([o['carrier_index_in_core'] for o in originals]),gid+'/complete_excluded_inventory')
    require(len(indices)==group['excluded_count'],'Group excluded count differs');original_centers=np.stack(old_centers,axis=1)
    for o in originals:
     i=o['carrier_index_in_core'];label=gid+'/'+str(i)
     equal(o['original_cached_score'],float(maps['maximum_robust_box_track_score'][i]),label+'/oldscore');equal(o['original_cached_drift_hz_s'],float(maps['winning_drift_hz_s'][i]),label+'/olddrift');equal(o['original_cached_width_channels'],int(maps['winning_width_channels'][i]),label+'/oldwidth')
     equal(o['original_cached_rounded_centers'],original_centers[i],label+'/oldcenters');equal(o['reference_source_channel'],int(maps['source_reference_channels'][i]),label+'/sourcechannel');equal(o['frequency_hz_at_own_first_midpoint'],float(maps['frequency_hz_at_tref'][i]),label+'/frequency')
     equal(o['original_cached_drift_grid_index'],int(np.searchsorted(grid,maps['winning_drift_hz_s'][i])),label+'/old_grid_index')
     contact=np.abs(original_centers[i][:,None]-np.asarray(DC)[None,:])<=int(maps['winning_width_channels'][i])//2
     equal(o['original_DC_contact_row_indices'],np.flatnonzero(contact.any(axis=1)).tolist(),label+'/old_contact_rows');equal(o['original_DC_contact_counts_by_bin'],{str(dc):int(contact[:,k].sum()) for k,dc in enumerate(DC)},label+'/old_contact_counts')
    family=kernel.exhaustive_original_scores(z,source0,maps['frequency_hz_at_tref'][indices],grid,(1,3),[r*TSAMP for r in range(16)],FCH1,DF,DC,np)
    oldidx=family['unconstrained_best_index'];equal(family['unconstrained_best_score'],maps['maximum_robust_box_track_score'][indices],gid+'/unrestricted_scores_exact');equal(grid[oldidx%785],maps['winning_drift_hz_s'][indices],gid+'/unrestricted_drifts_exact');equal(np.where(oldidx<785,1,3),maps['winning_width_channels'][indices],gid+'/unrestricted_widths_exact')
    admissible_counts=family['admissible'].sum(axis=0);n=len(indices);nonempty=int(family['has_clean_hypothesis'].sum());admissible_total=int(admissible_counts.sum())
    winnerpin=summary['recovered_winner_arrays_pin'];winnerpath=checked(ROOT/winnerpin['path'],winnerpin)
    with np.load(winnerpath,allow_pickle=False) as a:winning={k:a[k] for k in a.files}
    has=family['has_clean_hypothesis'];choice=family['best_clean_index'];expectedarrays={'reference_source_channel':maps['source_reference_channels'][indices],'carrier_index_in_core':indices,'admissible_hypothesis_count':admissible_counts,'no_admissible_hypothesis':~has,'clean_maximum_score':family['best_clean_score'],'clean_winning_width_channels':np.where(has,np.where(choice<785,1,3),0),'clean_winning_drift_grid_index':np.where(has,choice%785,-1),'original_cached_maximum_score':family['unconstrained_best_score'],'original_cached_winning_drift_hz_s':grid[oldidx%785],'original_cached_winning_width_channels':np.where(oldidx<785,1,3)}
    require(set(winning)==set(expectedarrays)|{'clean_winning_drift_hz_s'},'Corrected winner NPZ schema differs')
    for name,value in expectedarrays.items():equal(winning[name],value,gid+'/winner_NPZ/'+name)
    equal(winning['clean_winning_drift_hz_s'][has],grid[choice[has]%785],gid+'/winner_NPZ/clean_drift');equal(np.isnan(winning['clean_winning_drift_hz_s'][~has]).all(),True,gid+'/winner_NPZ/empty_drift_NaN')
    counts[scan]['inventory_carriers']+=n;counts[scan]['recovered_nonempty_carriers']+=nonempty;counts[scan]['EMPTY_carriers']+=n-nonempty;counts[scan]['original_unrestricted_tuples_reconciled_exactly']+=n;counts[scan]['original_hypothesis_score_occurrences']+=1570*n;counts[scan]['admissible_hypothesis_occurrences']+=admissible_total;counts[scan]['raw_frames_saved']+=1
    equal(summary['inventory_carriers'],n,gid+'/summary_count');equal(summary['original_hypothesis_score_occurrences'],1570*n,gid+'/summary_hypotheses');equal(summary['admissible_hypothesis_occurrences'],admissible_total,gid+'/summary_admissible');equal(summary['EMPTY_carriers'],n-nonempty,gid+'/summary_empty');equal(summary['original_unrestricted_tuples_reconciled_exactly'],n,gid+'/summary_unrestricted')
    ties=family['exact_maximum_tie_count'];tie_carriers+=int((ties>1).sum());tie_max=max(tie_max,int(ties.max()))
    groupaudit={'group_id':gid,'raw_frame_pin':summary['raw_frame_pin'],'unrestricted_maximum_absolute_score_difference':float(np.max(np.abs(family['unconstrained_best_score']-maps['maximum_robust_box_track_score'][indices]))),'admissible_hypothesis_occurrences':admissible_total,'EMPTY_carriers':n-nonempty,'winner_audits':[]}
    for j,o in enumerate(originals):
     identity=(gid,o['carrier_index_in_core']);actual=actual_records[identity];label=gid+'/'+str(identity[1]);empty=not bool(family['has_clean_hypothesis'][j]);new=None
     equal(actual['original_cached_tuple_and_DC_geometry'],o,label+'/preserved_original');equal(actual['original_unrestricted_score_drift_width_reconciled_exactly'],True,label+'/original_reconciliation');equal(actual['admissible_hypothesis_count'],int(admissible_counts[j]),label+'/admissible_count');equal(actual['no_admissible_hypothesis'],empty,label+'/empty');equal(actual['status'],'EMPTY' if empty else 'RECOVERED_CLEAN_MAXIMUM',label+'/status')
     if not empty:
      index=int(family['best_clean_index'][j]);width=1 if index<785 else 3;di=index%785;drift=float(grid[di]);score=float(family['best_clean_score'][j]);frequency=o['frequency_hz_at_own_first_midpoint'];centers=np.rint((frequency-FCH1)/DF+drift*np.asarray([r*TSAMP for r in range(16)])/DF).astype(np.int64)
      new=clean_point(group,o,score,drift,width,di,centers);clean_candidates[scan].append(new)
      new['authoritative_score_source']={'kind':'recovered_original_DC_free_hypothesis','pin':winnerpin,'record_index':j,'score_field':'clean_maximum_score','drift_field':'clean_winning_drift_hz_s','width_field':'clean_winning_width_channels','channel_field':'reference_source_channel','group_id':gid}
      for name,value in new.items():equal(actual['clean_maximum'][name],value,label+'/clean/'+name)
      equal(bool(np.any(np.abs(centers[:,None]-np.asarray(DC)[None,:])<=width//2)),False,label+'/clean_geometry');require(score<=o['original_cached_score'],'Conditional maximum exceeded original maximum')
      direct=kernel.direct_cell_score(z,source0,frequency,drift,width,[r*TSAMP for r in range(16)],FCH1,DF,np);close(direct,score,'direct_vs_prefix/'+label,qascope['direct_score_absolute_tolerance']);direct_audits+=1
     else:equal(actual['clean_maximum'],None,label+'/empty_null')
     expected_records[identity]={'original':o,'clean':new,'admissible_count':int(admissible_counts[j]),'status':'EMPTY' if empty else 'RECOVERED_CLEAN_MAXIMUM'}
     groupaudit['winner_audits'].append({'carrier':identity[1],'chosen_original_order_index':None if empty else int(family['best_clean_index'][j]),'exact_maximum_tie_count':int(ties[j]),'admissible_count':int(admissible_counts[j])})
    audits.append(groupaudit);del raw,z,maps,family
   del parent
 require(set(actual_records)==set(expected_records),'Recovered record identity coverage differs')
 reconstructed={};global9=[]
 def compare_point(actual,expected,label):
  for name,value in expected.items():equal(actual.get(name),value,label+'/'+name)
 for scan in TARGETS:
  oldpin=next(p['result_pin'] for p in scope['cached_clean_prefixes'] if p['primary_scan_id']==scan);old=read(checked(ROOT/oldpin['path'],oldpin));base=[dict(r,score_provenance='ORIGINAL_CACHED_DC_UNTOUCHED_WINNER') for r in old['raw_TOP700']]
  for r in base:
   r['source_kind']='original_clean_cached_carrier_maximum';r['authoritative_score_source']={'kind':r['source_kind'],'pin':r['map_pin'],'record_index':r['carrier_index_in_core'],'score_field':'maximum_robust_box_track_score','drift_field':'winning_drift_hz_s','width_field':'winning_width_channels','channel_field':'source_reference_channels'}
  require(len(base)==700 and len({r['reference_source_channel'] for r in base})==700,'Old exact prefix invalid');require(not ({r['reference_source_channel'] for r in base}&{r['reference_source_channel'] for r in clean_candidates[scan]}),'Old/new carrier sets overlap')
  merged=sorted(base+clean_candidates[scan],key=rankkey)[:700];require(len({r['reference_source_channel'] for r in merged})==700,'Merged sourcechannel uniqueness failed')
  for rank,r in enumerate(merged,1):r['raw_rank']=rank
  separated=[]
  for r in merged:
   if all(abs(r['reference_source_channel']-s['reference_source_channel'])>3 for s in separated):separated.append(dict(r,frequency_separated_rank=len(separated)+1))
   if len(separated)==100:break
  require(len(separated)==100 and separated[-1]['raw_rank']<=694,'Exact prefix separation bound failed')
  top3=[dict(r,rank=i,exploratory_selection_rank=i) for i,r in enumerate(separated[:3],1)];global9.extend(top3)
  own={'raw_TOP700':merged,'raw_TOP100':merged[:100],'frequency_separated_TOP100':separated,'TOP3':top3};reconstructed[scan]=own
  result=producer[scan];counts[scan]['complete_clean_family_nonempty_carriers']=old['counts']['eligible_DC_untouched_carriers']+len(clean_candidates[scan]);equal(result['counts'],counts[scan],scan+'/all_counts');equal(result['cached_clean_prefix_pin'],oldpin,scan+'/clean_prefix_pin');equal(result['previous_ON_TOP3'],old['TOP3'],scan+'/previous_TOP3')
  for field,expected in own.items():
   equal(len(result[field]),len(expected),scan+'/'+field+'/length')
   for i,(a,b) in enumerate(zip(result[field],expected),1):compare_point(a,b,scan+'/'+field+'/'+str(i))
  equal(result['prefix_completeness']['last_separated_choice_raw_rank'],separated[-1]['raw_rank'],scan+'/separation_bound')
  rows=list(csv.DictReader(checked(search/scan/'RECOVERED_CARRIERS.csv').open()));require(len(rows)==2361,'RecoveredCSVcount differs')
  for row in rows:
   identity=(row['group_id'],int(row['carrier_index_in_core']));e=expected_records[identity];o=e['original'];c=e['clean'];label='CSV/'+str(identity)
   for field,value in [('reference_source_channel',o['reference_source_channel']),('admissible_hypothesis_count',e['admissible_count']),('original_score',o['original_cached_score']),('original_drift',o['original_cached_drift_hz_s']),('original_width',o['original_cached_width_channels']),('clean_score',c['score'] if c else None),('clean_drift',c['drift_hz_s'] if c else None),('clean_width',c['width_channels'] if c else None)]:equal(None if row[field]=='' else (int(row[field]) if isinstance(value,int) else float(row[field])),value,label+'/'+field)
   equal(row['status'],e['status'],label+'/status')
 aggregate=read(checked(search/'AGGREGATION_RECEIPT.json'))
 for pin in aggregate['inputs']+aggregate['outputs']:checked(ROOT/pin['path'],pin)
 selected=read(checked(search/'SELECTED_TOP9.json'));equal(len(selected['records']),9,'global9_count')
 for i,(a,b) in enumerate(zip(selected['records'],global9)):compare_point(a,b,'global9/'+str(i))
 totals={k:sum(c[k] for c in counts.values()) for k in counts[TARGETS[0]]};equal(selected['counts'],totals,'global_counts');equal(aggregate['counts'],totals,'aggregate_counts')
 for path,oldpin in pins.items():require({'path':Path(path).relative_to(ROOT).as_posix(),'bytes':Path(path).stat().st_size,'sha256':digest(Path(path))}==oldpin,'Input changed at QA close')
 cpusecs=time.process_time()-cpu;wallsecs=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 require(cpusecs<=CPU_CAP and wallsecs<=WALL_CAP and rss<=RAM_CAP,'Measured QA resource cap exceeded')
 auditpath=BASE/'DETAILED_AUDIT.json.gz';auditbytes=(json.dumps({'input_pins_before_and_after':list(pins.values()),'groups':audits},sort_keys=True,separators=(',',':'))+'\n').encode()
 with auditpath.open('xb') as f:f.write(gzip.compress(auditbytes,compresslevel=9,mtime=0))
 result={'status':'PASS_INDEPENDENT_EXHAUSTIVE_DC_ALTERNATIVES' if not mismatches else 'FAIL_MISMATCHES_PRESERVED','counts':dict(totals,checks=checks,source_files=9,decoded_row_hashes=row_hashes,fullframe_running_median_positions=fullframe_positions,independent_full16_core_normalizations=18,direct_cell_score_audits=direct_audits,clean_maxima_with_multiple_exact_ties=tie_carriers,maximum_exact_tie_count=tie_max),
 'per_ON_counts':counts,'mismatch_count':len(mismatches),'mismatches':mismatches[:100],'maximum_absolute_errors':errors,'normalization_audit_errors':norm_errors,'exact_original_score_and_winner_comparison_no_epsilon':True,'winner_normalization_terms':'immutable original saved row terms; independent estimates only audited',
 'separated100_last_raw_ranks':{s:r['frequency_separated_TOP100'][-1]['raw_rank'] for s,r in reconstructed.items()},'TOP3_recovered_alternative_count':sum(r['score_provenance']=='EXACT_ORIGINAL_PREFIX_DC_UNTOUCHED_ALTERNATIVE' for r in global9),
 'compact_detailed_audit_pin':{'path':auditpath.relative_to(ROOT).as_posix(),'bytes':auditpath.stat().st_size,'sha256':digest(auditpath)},'CPU_seconds':cpusecs,'wall_seconds':wallsecs,'peak_RSS_bytes':rss,'limits':{'CPU_seconds':CPU_CAP,'wall_seconds':WALL_CAP,'RAM_bytes':RAM_CAP},
 'producer_or_detector_imported':False,'new_telescope_requests':0,'new_hypothesis_grid':False,'qualified_SETI_detection':False,
 'limitations':['Exhaustive original1570 hypotheses only at7083 previously DC-contacting cached winners; remaining clean winners and fullmap coverage authenticated from prior all2298map QA.', 'Original prefix arithmetic and first exact ties reproduced; direct cell sums and independently reestimated normalization terms are tolerance audits only.', 'Saved crops reproduce the numerical results, while H5 decoded-row authentication and archived original driver/checkpoint provenance remain prerequisites.', 'Exact rawTOP700 merge and referencechannel separation do not establish independent physical sources, calibrated SNR/FAP, new observing visits or extraterrestrial origin.']}
 save(BASE/'QA_RECEIPT.json',result);signal.alarm(0);print(json.dumps(result))

if __name__=='__main__':main()
