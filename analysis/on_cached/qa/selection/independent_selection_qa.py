#!/usr/bin/env python3
"""Independent streamed QA for all cached per-carrier maxima after rootGO.

Uses repeated sorted-list merges instead of producer heaps. No detector grid,
raw spectral power or new telescope requests. Import/check-only reads no maps.
"""
from __future__ import annotations
import argparse,hashlib,json,os,resource,signal,time,sys
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
CHUNK=1048576;CORE=4096;FCH1=2802832031.25;DF=-2.7939677238464355;TSAMP=18.253611008
DCS=[n*CHUNK+CHUNK//2 for n in (170,171,172)];TARGETS=['epoch1_on','epoch2_on','epoch3_on']
CPU_CAP=600;WALL_CAP=900;RAM_CAP=2*1024**3
EXPECTED_DOMAINS={(170,q) for q in range(1,256)}|{(171,q) for q in range(256)}|{(172,q) for q in range(255)}
FIELDS=['frequency_hz_at_own_first_midpoint','drift_hz_s','width_channels','score','reference_source_channel','native_chunk_index','core_q','carrier_index_in_core','map_id','scan_id','primary_target','primary_scan_id','reference_time_mjd','drift_grid_index','original_acquisition_role','is_cached_coremax_winner','reference_origin_scan_id','reference_seconds_from_anchor','MJD_anchor','origin_tstart_mjd','original_origin_row_times_from_reference_s']

def require(test,message):
 if not test:raise ValueError(message)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(p.read_bytes(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def rankkey(r):return (-r['score'],r['frequency_hz_at_own_first_midpoint'],r['drift_hz_s'],r['width_channels'],r['native_chunk_index'],r['core_q'],r['carrier_index_in_core'])
def extract(a,carrier,group,m):
 return {'primary_scan_id':group['primary_scan_id'],'primary_target':group['primary_target'],'scan_id':group['scan_id'],'map_id':m['canonical_map_id'],
         'native_chunk_index':m['native_chunk_index'],'core_q':m['core_q'],'carrier_index_in_core':int(carrier),
         'reference_source_channel':int(a['source_reference_channels'][carrier]),
         'frequency_hz_at_own_first_midpoint':float(a['frequency_hz_at_tref'][carrier]),
         'drift_hz_s':float(a['winning_drift_hz_s'][carrier]),'width_channels':int(a['winning_width_channels'][carrier]),
         'score':float(a['maximum_robust_box_track_score'][carrier]),
         'reference_time_mjd':group['reference_time_mjd'],'drift_grid_index':int(a['_drift_indices'][carrier]),
         'original_acquisition_role':'ON','is_cached_coremax_winner':int(carrier)==m['_historic_max'],
         'cached_coremax_score':float(a['maximum_robust_box_track_score'][m['_historic_max']]),
         'reference_origin_scan_id':group['scan_id'],'reference_seconds_from_anchor':group['reference_seconds_from_anchor'],
         'MJD_anchor':group['MJD_anchor'],'origin_tstart_mjd':group['origin_tstart_mjd'],
         'original_origin_row_times_from_reference_s':group['original_origin_row_times_from_reference_s'],
         'map_pin':m['map_pin'],'normalization_pin':m['normalization_pin'],'original_checkpoint_pin':m['checkpoint_pin']}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');parser.add_argument('--scope',type=Path,default=BASE/'scope.json');parser.add_argument('--go',type=Path);args=parser.parse_args()
 if args.check_only:
  print(json.dumps({'status':'METADATA_ONLY_QA_PREPARED','code_sha256':digest(Path(__file__)),'expected_domains_per_target':len(EXPECTED_DOMAINS),'score_payloads_read':0}));return
 require(args.go is not None,'Separate rootGO after prospective publicfreeze required')
 go=read(args.go);qascope=read(args.scope)
 require(go['authorized'] and go['qa_code_sha256']==digest(Path(__file__)) and go['qa_scope_sha256']==digest(args.scope),'Frozen QA admission differs')
 require(not (BASE/'QA_RECEIPT.json').exists(),'QA receipt notoverwriteable')
 def deadline(s,f):raise TimeoutError('IndependentallcarrierQA resourcecap')
 signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.alarm(WALL_CAP)
 resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(RAM_CAP,RAM_CAP))
 started=time.monotonic();cpu=time.process_time()
 import numpy as np
 pins={};mismatches=[];checks=0
 def checked(p,declared=None):
  p=p.resolve();actual={'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
  require(declared is None or all(actual[k]==declared[k] for k in ('bytes','sha256')),'Inputpin mismatch '+str(p))
  require(str(p) not in pins or pins[str(p)]==actual,'Inputchanged');pins[str(p)]=actual;return p
 def equal(a,b,label):
  nonlocal checks
  checks+=1;ok=np.array_equal(np.asarray(a),np.asarray(b))
  if not ok:mismatches.append(label)
  return ok
 for d in qascope['input_pins']:checked(ROOT/d['path'],d)
 checked(Path(__file__));checked(args.scope);checked(args.go)
 selector_scope=read(checked(ROOT/qascope['selector_scope_path']))
 protocol=qascope['authenticated_original_protocol']
 require(protocol['metadata_authenticated'] is True,'OriginalONprotocol must be bound before payload use')
 for declaration in protocol['original_driver_pins']:checked(ROOT/declaration['path'],declaration)
 require(protocol['own_elapsed_times_s']==[r*TSAMP for r in range(16)] and protocol['widths_channels']==[1,3] and protocol['drift_grid']=={'first_hz_s':-4,'last_hz_s':4,'count':785},'Unexpected originalON protocol; root scope change required')
 oldindex=load_original_coremax_metadata(selector_scope,checked,read)
 expectedheaders={name[:-4]:(tuple(v['shape']),v['dtype']) for name,v in selector_scope['NPZ_headers'].items()}
 retained={t:[] for t in TARGETS};percore=[];domains={t:set() for t in TARGETS};counts={t:{'maps':0,'carriers':0,'eligible':0,'excluded':0} for t in TARGETS}
 raw_errors=[];coremax_comparisons=0
 for group in selector_scope['groups']:
  target=group['scan_id'];require(target in TARGETS,'Unexpectedtarget')
  for m in group['maps']:
   native,q=m['native_chunk_index'],m['core_q'];domain=(native,q)
   equal(group['primary_scan_id'],group['scan_id'],'ON_primary_scan_identity')
   equal(group['primary_target'],'HIP98505','original_ON_target_identity')
   equal(group['original_acquisition_role'],'ON','original_ON_role')
   equal(group['original_origin_row_times_from_reference_s'],[r*TSAMP for r in range(16)],'own_first_midpoint_row_times')
   require(domain not in domains[target] and domain in EXPECTED_DOMAINS,'Duplicate/unexpecteddomain')
   domains[target].add(domain);path=checked(ROOT/m['map_pin']['path'],m['map_pin']);checked(ROOT/m['normalization_pin']['path'],m['normalization_pin']);checked(ROOT/m['checkpoint_pin']['path'],m['checkpoint_pin'])
   with np.load(path,allow_pickle=False) as archive:
    require(set(archive.files)==set(expectedheaders),'Maparrayfieldnamesdiffer')
    a={k:archive[k].copy() for k in archive.files}
   for k,(shape,dtype) in expectedheaders.items():require(a[k].shape==shape and a[k].dtype.str==dtype,'Maparrayheaderdiffers '+k)
   core0=native*CHUNK+q*CORE
   equal(a['source_reference_channels'],np.arange(core0,core0+CORE,dtype=np.int64),str((target,native,q))+'/allcarrierchannels')
   equal(a['frequency_hz_at_tref'],FCH1+DF*np.arange(core0,core0+CORE,dtype=np.int64),str((target,native,q))+'/allcarrierfrequencies')
   equal(a['drift_grid_hz_s'],np.linspace(-4,4,785),str((target,native,q))+'/originaldriftgrid')
   equal(a['valid_hypothesis_count'],np.full(CORE,1570,dtype=np.int64),str((target,native,q))+'/allhypothesiscounts')
   score=a['maximum_robust_box_track_score'];drift=a['winning_drift_hz_s'];width=a['winning_width_channels'];freq=a['frequency_hz_at_tref']
   require(np.isfinite(score).all() and np.isfinite(drift).all(),'Nonfinitecachedwinner')
   require(np.isin(drift,a['drift_grid_hz_s']).all() and np.isin(width,[1,3]).all(),'Cachedwinningdrift/widthinvalid')
   a['_drift_indices']=np.searchsorted(a['drift_grid_hz_s'],drift);m['_historic_max']=int(np.argmax(score))
   # Independent row loop: exact full absolute channel rounding, then3DCmemberships.
   touched=np.zeros(CORE,dtype=bool)
   for row in range(16):
    centers=np.rint((freq-FCH1)/DF+drift*(row*TSAMP)/DF).astype(np.int64)
    if row==0:equal(centers,a['source_reference_channels'],str((target,native,q))+'/firstrowcenters')
    for dc in DCS:touched|=np.abs(centers-dc)<=width//2
   eligible=np.flatnonzero(~touched);n=int(len(eligible));counts[target]['maps']+=1;counts[target]['carriers']+=CORE;counts[target]['eligible']+=n;counts[target]['excluded']+=CORE-n
   # Per-map candidate sort is independent of producer's streamed scalarheap.
   ordered=eligible[np.lexsort((eligible,width[eligible],drift[eligible],freq[eligible],-score[eligible]))]
   candidates=[extract(a,int(i),group,m) for i in ordered[:700]]
   retained[target]=sorted(retained[target]+candidates,key=rankkey)[:700]
   imax=m['_historic_max'];old=oldindex.get((target,m['canonical_map_id']));maximum=extract(a,imax,group,m)
   if old is not None:
    for field in ['native_chunk_index','core_q','carrier_index_in_core','reference_source_channel','frequency_hz_at_own_first_midpoint','drift_hz_s','width_channels','score','drift_grid_index']:
     equal(maximum[field],old[field],str((target,native,q))+'/originalcoremax/'+field);coremax_comparisons+=1
    original_centers=[int(round((float(freq[imax])-FCH1)/DF+float(drift[imax])*(r*TSAMP)/DF)) for r in range(16)]
    if 'rounded_absolute_centers' in old:equal(original_centers,old['rounded_absolute_centers'],str((target,native,q))+'/originalcoremax_scalar_centers')
    if 'eligible_DC_untouched' in old:equal(not bool(touched[imax]),old['eligible_DC_untouched'],str((target,native,q))+'/originalcoremax_eligibility')
   percore.append({'primary_target':group['primary_target'],'scan_id':target,'primary_scan_id':group['primary_scan_id'],'map_id':m['canonical_map_id'],'native_chunk_index':native,'core_q':q,'cached_carriers':CORE,
                   'eligible_DC_untouched':n,'excluded_by_DC_contact':CORE-n,'eligible_maximum':candidates[0] if candidates else None,'cached_coremax_DC_contact':bool(touched[imax]),'cached_coremax_score':float(score[imax]),'cached_coremax_carrier_index':imax,'cached_coremax':maximum})
 for target in TARGETS:
  require(domains[target]==EXPECTED_DOMAINS and counts[target]['maps']==766 and counts[target]['carriers']==3137536,'Completenessdomain/corecoverage differs')
 reconstructed={}
 for target in TARGETS:
  raw=retained[target];chosen=[];raw_ranks=[]
  for rank,r in enumerate(raw,1):
   if all(abs(r['reference_source_channel']-other['reference_source_channel'])>3 for other in chosen):chosen.append(r);raw_ranks.append(rank)
   if len(chosen)==100:break
  require(len(raw)==min(700,counts[target]['eligible']),'Retainedraw700completenessdiffers')
  if counts[target]['eligible']>=694:require(len(chosen)==100 and raw_ranks[-1]<=694,'Uniquechannelprefixbound failed')
  # Sourcechannel uniqueness follows exact disjointnormalizationcores andpermapchannels.
  require(len({r['reference_source_channel'] for r in raw})==len(raw),'Rawranklistduplicatechannel')
  reconstructed[target]={'raw700':raw,'raw100':raw[:100],'separated100':chosen,'selected3':chosen[:3],'separated_raw_ranks':raw_ranks}
 compare_outputs(ROOT,qascope,selector_scope,reconstructed,percore,counts,equal,checked,read)
 for path,oldpin in pins.items():require({'path':Path(path).relative_to(ROOT).as_posix(),'bytes':Path(path).stat().st_size,'sha256':digest(Path(path))}==oldpin,'InputchangedatQAclose')
 cpusecs=time.process_time()-cpu;wallsecs=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 require(cpusecs<=CPU_CAP and wallsecs<=WALL_CAP and rss<=RAM_CAP,'MeasuredQAresourcecap exceeded')
 save(BASE/'INDEPENDENT_RANK_LISTS.json',{'ON_primary_scans':reconstructed})
 import gzip
 auditraw=(json.dumps({'input_pins_before_and_after':list(pins.values()),'per_core_counts':percore},sort_keys=True,separators=(',',':'))+'\n').encode()
 auditpath=BASE/'INPUT_AND_CORE_AUDIT.json.gz'
 with auditpath.open('xb') as f:f.write(gzip.compress(auditraw,compresslevel=9,mtime=0))
 result={'status':'PASS_INDEPENDENT_ALL9412608_ON_CARRIER_SELECTION' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
         'counts':{'maps':sum(c['maps'] for c in counts.values()),'carrier_maxima':sum(c['carriers'] for c in counts.values()),
                   'eligible':sum(c['eligible'] for c in counts.values()),'excluded':sum(c['excluded'] for c in counts.values()),
                   'geometry_row_occurrences':9412608*16,'DC_row_box_memberships':9412608*16*3,
                   'cached_coremax_maps_independently_recomputed':2298,'original_coremax_records_available':len(oldindex),'old_coremax_field_comparisons':coremax_comparisons,'checks':checks},
         'per_ON_primary_counts':counts,'separated100_last_raw_ranks':{t:r['separated_raw_ranks'][-1] if r['separated_raw_ranks'] else None for t,r in reconstructed.items()},
         'mismatches':mismatches,'exact_comparison_no_epsilon':True,'source_map_pin_count':2298,
         'compact_input_core_audit':{'path':auditpath.relative_to(ROOT).as_posix(),'bytes':auditpath.stat().st_size,'sha256':digest(auditpath)},
         'CPU_seconds':cpusecs,'wall_seconds':wallsecs,'peak_RSS_bytes':rss,'limits':{'CPU_seconds':CPU_CAP,'wall_seconds':WALL_CAP,'RAM_bytes':RAM_CAP},
         'detector_imported':False,'new_scoregrid':False,'raw_spectral_power_arrays_read':0,'telescope_requests':0,'qualified_SETI_detection':False,
         'limitations':['Cachedwinning paths only: excludingDCcontact does not recover alternative nonwinning hypotheses or create a masked search.',
                        'The2298ONmapdomain is complete for the frozeninventory, with original omittedcores respected; this is not complete wholebandcoverage.',
                        'Referencechannel uniqueness andsevenchannelblocking prove exact separatedTOP100 within rawTOP700; geometric separation does not prove different physicalsources.',
                        'NoSNR,FAP,independentvisit or extraterrestrialsourceclassification follows.']}
 save(BASE/'QA_RECEIPT.json',result);signal.alarm(0)
 print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins_before_and_after','limitations')}))



def load_original_coremax_metadata(selector_scope,checked,read):
 """Bind original tuple metadata only when explicitly declared by actual scope."""
 records={}
 for d in selector_scope.get('original_coremax_metadata_pins',[]):
  data=read(checked(ROOT/d['path'],d))
  for record in data['records']:
   identity=(record['scan_id'],record['map_id']);require(identity not in records,'Original coremax identity duplicate')
   records[identity]=record
 return records

def compare_outputs(root,qascope,selector_scope,reconstructed,percore,counts,equal,checked,read):
 import csv,numpy as np
 ranking=root/'on_cached/ranking'
 def match(actual,expected,label):
  for field in FIELDS:equal(actual[field],expected[field],label+'/'+field)
  for field in ('map_pin','normalization_pin','original_checkpoint_pin'):equal(actual[field],expected[field],label+'/'+field)
  equal(actual['cached_coremax_score'],expected['cached_coremax_score'],label+'/cached_coremax_score')
  elapsed=np.array([r*TSAMP for r in range(16)])
  centers=np.rint((expected['frequency_hz_at_own_first_midpoint']-FCH1)/DF+expected['drift_hz_s']*elapsed/DF).astype(np.int64)
  equal(actual['rounded_absolute_centers'],centers,label+'/all16centers');equal(actual['eligible_DC_untouched'],True,label+'/eligible')
  equal(np.any(np.abs(centers[:,None]-np.array(DCS)[None,:])<=expected['width_channels']//2),False,label+'/exact_contact_check')
 def check_csv(path,actual,label):
  rows=list(csv.DictReader(checked(path).open()));require(len(rows)==len(actual),'CSVcount differs '+label)
  for i,(row,r) in enumerate(zip(rows,actual)):
   for field,value in row.items():
    expected=r.get(field)
    if expected is None:equal(value,'',label+'/'+str(i)+'/'+field)
    elif isinstance(expected,bool):equal(value,str(expected),label+'/'+str(i)+'/'+field)
    elif isinstance(expected,int):equal(int(value),expected,label+'/'+str(i)+'/'+field)
    elif isinstance(expected,float):equal(float(value),expected,label+'/'+str(i)+'/'+field)
    else:equal(value,expected,label+'/'+str(i)+'/'+field)
 global_expected=[]
 for scan in TARGETS:
  folder=ranking/scan;receipt=read(checked(folder/'EXECUTION_RECEIPT.json'))
  equal(receipt['scope_sha256'],digest(ranking/'scope.json'),scan+'/receiptscope');equal(receipt['producer_sha256'],digest(ranking/'select_streaming.py'),scan+'/receiptproducer')
  equal(receipt['status'],'PASS_ONCE_ON_CACHED_STREAMING_SELECTION',scan+'/receiptstatus')
  for d in receipt['outputs']:checked(root/d['path'],d)
  result=read(checked(folder/'RESULT.json'));own=reconstructed[scan];actual_counts=result['counts']
  equal(result['primary_scan_id'],scan,scan+'/identity');equal(result['primary_target'],'HIP98505',scan+'/target')
  for field,key in [('maps','maps'),('cached_carriers','carriers'),('eligible_DC_untouched_carriers','eligible'),('DC_contacting_cached_winner_carriers','excluded')]:equal(actual_counts[field],counts[scan][key],scan+'/count/'+field)
  for field in ['source_map_hashes_verified','source_normalization_hashes_verified','cached_coremax_indices_computed']:equal(actual_counts[field],766,scan+'/count/'+field)
  index={(p['native_chunk_index'],p['core_q']):p for p in percore if p['scan_id']==scan};require(len(result['core_summaries'])==len(index)==766,'Percoresummarycountdiffers')
  seen=set()
  for actual in result['core_summaries']:
   identity=(actual['native_chunk_index'],actual['core_q']);require(identity not in seen,'Duplicatecoresummary');seen.add(identity);p=index[identity];label=scan+'/core/'+p['map_id']
   for field in ['native_chunk_index','core_q','cached_carriers','cached_coremax_DC_contact','cached_coremax_score','cached_coremax_carrier_index']:equal(actual[field],p[field],label+'/'+field)
   equal(actual['primary_scan_id'],scan,label+'/primaryscan');equal(actual['eligible_DC_untouched_carriers'],p['eligible_DC_untouched'],label+'/eligible');equal(actual['DC_contacting_cached_winner_carriers'],p['excluded_by_DC_contact'],label+'/excluded')
   if p['eligible_maximum'] is None:equal(actual['eligible_maximum'],None,label+'/eligiblemax')
   else:match(actual['eligible_maximum'],p['eligible_maximum'],label+'/eligiblemax')
  equal(seen,EXPECTED_DOMAINS,scan+'/all_core_summary_domains')
  for key,field,csvfile in [('raw700','raw_TOP700','RAW_TOP700.csv'),('raw100','raw_TOP100','RAW_TOP100.csv'),('separated100','frequency_separated_TOP100','SEPARATED_TOP100.csv'),('selected3','TOP3','TOP3.csv')]:
   values=result[field];require(len(values)==len(own[key]),'Ranklistcountdiffers '+field)
   for i,(a,b) in enumerate(zip(values,own[key]),1):
    label=scan+'/'+field+'/'+str(i);match(a,b,label);rawrank=next(j for j,r in enumerate(own['raw700'],1) if r['reference_source_channel']==b['reference_source_channel']);equal(a['raw_rank'],rawrank,label+'/rawrank')
    if key in ('separated100','selected3'):equal(a['frequency_separated_rank'],i,label+'/separatedrank')
    if key=='selected3':equal(a['rank'],i,label+'/rank');equal(a['exploratory_selection_rank'],i,label+'/exploratoryrank')
   check_csv(folder/csvfile,values,scan+'/'+csvfile)
  equal(result['prefix_completeness']['actual_raw_rank_of_last_separated_choice'],own['separated_raw_ranks'][-1],scan+'/actual_prefixbound');equal(result['prefix_completeness']['bound_for_100th_separated_choice'],694,scan+'/declared_prefixbound')
  global_expected+=own['selected3']
 aggregate=read(checked(ranking/'AGGREGATION_RECEIPT.json'))
 for d in aggregate['inputs']+aggregate['outputs']:checked(root/d['path'],d)
 global_actual=read(checked(ranking/'SELECTED_TOP9.json'))['records'];require(len(global_actual)==len(global_expected)==9,'GlobalTOP9differs')
 for i,(a,b) in enumerate(zip(global_actual,global_expected)):match(a,b,'global9/'+str(i))
 check_csv(ranking/'SELECTED_TOP9.csv',global_actual,'global9CSV')

if __name__=='__main__':main()
