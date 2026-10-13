#!/usr/bin/env python3
"""Independent cached ON fixed-context QA; no science read before exact GO.

Baseline profiles are imported only through immutable byte/object hashes and
complete core/width/all-six center identities. New physical profiles are checked
against authenticated original H5 rows with independent NumPy median501 tiles.
"""
from __future__ import annotations
import argparse,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
PRODUCER=ROOT/'on_cached/context'
CHUNK,CORE,HALO=1048576,4096,4000
BAND0=170*CHUNK
FCH1,DF,TSAMP=2802832031.25,-2.7939677238464355,18.253611008
SCANS=('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
DC=(178782208,179830784,180879360)
CPU_CAP,WALL_CAP,RAM_CAP=600,900,2147483648
ATOL,RTOL=1e-7,1e-10
OLD_MATRIX=ROOT/'next_dc/crossscan/results/CONTEXT_PROFILES.json'
OLD_CROPS=ROOT/'next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json'
OLD_QA=ROOT/'next_dc/qa/context/QA_RECEIPT.json'
CURRENT_RAW=ROOT/'on_cached/feasibility/RAW_RESTORATION_RECEIPT.json'
PRIOR_SOURCE_SCOPE=ROOT/'carrier_followup/context/SCOPE.json'
MANIFEST=ROOT/'on_cached/restored/metadata/native171/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'


def require(value,message):
 if not value:raise ValueError(message)
def read(path):return json.loads(path.read_bytes(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def pin(path):
 path=path.resolve();return {'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}
def objsha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def save(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
def centers_for(track,scan,headers,np):
 if 'reference_origin_scan_id' in track:
  origin=track['reference_origin_scan_id'];times=np.asarray(track['original_origin_row_times_from_reference_s'],dtype=np.float64)
  require(origin==track['scan_id'] and np.array_equal(times,np.arange(16)*TSAMP),'Confirmed original direct-ON reference vector differs')
  require(track['reference_time_mjd']==headers[origin]['tstart']+TSAMP/(2*86400),'Original ON first midpoint differs')
 else:
  # Legacy baseline metadata is only used to form its immutable query identity.
  origin=track['scan_id'];times=np.arange(16)*TSAMP
 elapsed=(headers[scan]['tstart']-headers[origin]['tstart'])*86400+times
 centers=np.rint((track['frequency_hz_at_own_first_midpoint']-FCH1)/DF+track['drift_hz_s']*elapsed/DF).astype(np.int64)
 return centers,elapsed

def geometry(track,headers,np):
 value={'native_chunk_index':track['native_chunk_index'],'core_q':track['core_q'],'width_channels':track['width_channels'],
        'six_scan_rounded_absolute_centers':[centers_for(track,s,headers,np)[0].tolist() for s in SCANS]}
 raw_geometry={'width_channels':value['width_channels'],'six_scan_rounded_absolute_centers':value['six_scan_rounded_absolute_centers']}
 value['raw_geometry_id']=objsha(raw_geometry)
 return objsha(value),value

def independent_norm(joined,core0,np):
 local0=core0-BAND0;core=joined[:,local0:local0+CORE].astype(np.float64)
 require(core.shape==(16,CORE),'Full16 normalization core unavailable')
 levels=np.median(core,axis=1);require(np.isfinite(levels).all() and (levels>0).all(),'Invalid independent rowpower level')
 residual=np.empty_like(core)
 for row in range(16):
  support=joined[row,local0-250:local0+CORE+250].astype(np.float64)/levels[row]
  require(support.shape==(CORE+500,),'Independent exact501 support unavailable')
  windows=np.lib.stride_tricks.sliding_window_view(support,501)
  for start in range(0,CORE,512):
   stop=min(start+512,CORE);residual[row,start:stop]=core[row,start:stop]/levels[row]-np.median(windows[start:stop],axis=1)
 center=np.median(residual,axis=1);scale=1.4826*np.median(np.abs(residual-center[:,None]),axis=1)
 require(np.isfinite(scale).all() and (scale>0).all(),'Invalid independent residualMAD')
 location=center+np.mean(np.clip(residual-center[:,None],-5*scale[:,None],5*scale[:,None]),axis=1)
 return {'row_power_median':levels.tolist(),'row_residual_median':center.tolist(),'row_residual_MAD_scale':scale.tolist(),
         'row_winsorized_residual_location':location.tolist(),'normalization_unmasked_counts':[CORE]*16,
         'normalization_source_channel_interval_half_open':[core0,core0+CORE]}


def prepare():
 # Metadata and opaque byte hashes only; no scores/norms/raw arrays parsed.
 contract=read(PRODUCER/'PROSPECTIVE_CONTRACT.json')
 require(contract['schema']=='SETI_ON_CACHED_FIXED_CONTEXT_PROSPECTIVE_CONTRACT_V1','Agreed producer contract schema differs')
 require(contract['time_contract_agreed_with_selector_owner'] is True,'Exact original ON time convention must be agreed')
 paths=[Path(__file__),BASE/'PROSPECTIVE_QA_PLAN.json',OLD_QA,ROOT/'next_dc/qa/context/REPRODUCTION_RECEIPT.json',
   PRODUCER/'PROSPECTIVE_CONTRACT.json',ROOT/'on_cached/ROOT_SCOPE.json',CURRENT_RAW,PRIOR_SOURCE_SCOPE,MANIFEST,
   ROOT/'on_cached/feasibility/RUNTIME_INSTALL_RECEIPT.json']
 paths.append(ROOT/'on_cached/feasibility/ON_NORMALIZATION_DOMAIN_CENSUS.json')
 scope={'schema':'SETI_ON_CACHED_INDEPENDENT_CONTEXT_QA_SCOPE_V1','status':'FROZEN_BEFORE_FIRST_ARRAY_QA_AFTER_METADATA_GATE_CORRECTION',
  'qa_sha256':sha(Path(__file__)),'input_pins':[pin(path) for path in paths],
  'admission_required':['scope_sha256','qa_sha256','producer_scope_sha256','producer_receipt_sha256','producer_matrix_sha256','expected_new_physical_templates','expected_new_fixed_queries'],
  'producer_scope_path':'on_cached/context/SCOPE.json','producer_receipt_path':'on_cached/context/results/EXECUTION_RECEIPT.json','producer_matrix_path':'on_cached/context/results/CONTEXT_PROFILES.json',
  'limits':{'CPU_seconds':CPU_CAP,'wall_seconds':WALL_CAP,'RAM_bytes':RAM_CAP},
  'normalization':'Independent full16 static4096core, original rowmedian, exact501 median NumPy512channel tiles, residualMAD and winsorized location.',
  'logical_identity':'ON origin scan_id plus original primary_id and rank; target name is not used as identity.',
  'time_rule':'Explicit selected reference_origin_scan_id and exact original_origin_row_times_from_reference_s; actual scan gap plus exact original16-row vector. Own reference validated as original ON first midpoint.',
  'physical_identity':'Canonical JSON {native_chunk_index,core_q,width_channels,six_scan_rounded_absolute_centers,raw_geometry_id}; raw_geometry_id hashes width+sixscan vectors. Original samecore domain mandatory.',
  'baseline_reuse':'Hash-only import of old54logical/48physical profiles; same native,q,width and all6x16 exact centers. No baseline normalization or score rerun.',
  'new_profiles':'Recompute only absent physical fixed templates. Authenticate original18 file and288 decoded-row identities; preserve unique absent12096 crops.',
  'own_scalar_check':'Compare selected own context score to original ON per-carrier map scalar; no optimization. Original own normalization terms are checked for new query own context only.',
  'detector_imported':False,'detector_grid_rerun':False,'new_mask_or_veto':False,'new_telescope_requests':0,'qualified_SETI_detection':False}
 scope['metadata_interface_correction']={'reason':'Validate final immutable census PASS status and2298/zero-mismatch counts rather than provisional boolean key.',
   'initial_failure_before_any_array_payload_decode':True,'scientific_formulas_changed':False,
   'initial_failure_receipt':pin(BASE/'attempt1/INTERFACE_FAILURE_RECEIPT.json')}
 save(BASE/'scope.json',scope);print(json.dumps({'qa_sha256':scope['qa_sha256'],'scope_sha256':sha(BASE/'scope.json'),'status':scope['status']}))


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');parser.add_argument('--check-only',action='store_true')
 parser.add_argument('--go',type=Path);parser.add_argument('--scope',type=Path,default=BASE/'scope.json');args=parser.parse_args()
 if args.prepare:prepare();return
 if args.check_only:print(json.dumps({'status':'PREPARED_NO_SCIENCE_ARRAYS','qa_sha256':sha(Path(__file__)),'detector_imported':False}));return
 require(args.go is not None,'Separate exact rootGO required')
 scope,go=read(args.scope),read(args.go)
 require(go.get('authorized') and go['scope_sha256']==sha(args.scope) and go['qa_sha256']==sha(Path(__file__)),'QA scope/code GO differs')
 require(go.get('baseline_own_scalar_comparison_authorized',False),'GO must explicitly authorize selected imported baseline own scalar comparison')
 require(not (BASE/'QA_RECEIPT.json').exists(),'QA receipt is not overwriteable')
 def timeout(a,b):raise TimeoutError('Independent contextQA resource limit')
 signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(WALL_CAP)
 resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(RAM_CAP,RAM_CAP))
 started,cpu=time.monotonic(),time.process_time()
 import numpy as np
 pins={};mismatches=[];maxerrors={};checks=0
 def checked(path,declared=None):
  path=path.resolve();actual=pin(path)
  require(declared is None or all(actual[k]==declared[k] for k in ('bytes','sha256')),'Input pin differs: '+str(path))
  require(str(path) not in pins or pins[str(path)]==actual,'Repeated input changed');pins[str(path)]=actual;return path
 def compare(a,b,label,numeric=False,category=None):
  nonlocal checks
  checks+=1;x,y=np.asarray(a),np.asarray(b)
  if numeric:
   ok=x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all() and np.allclose(x,y,atol=ATOL,rtol=RTOL)
   if x.shape==y.shape and x.size:maxerrors[category or label]=max(maxerrors.get(category or label,0),float(np.max(np.abs(x-y))))
  else:ok=x.shape==y.shape and np.array_equal(x,y)
  if not ok:mismatches.append(label)
  return ok
 for d in scope['input_pins']:checked(ROOT/d['path'],d)
 checked(args.scope);checked(args.go)
 for key,name in [('producer_scope_sha256','SCOPE.json'),('producer_receipt_sha256','results/EXECUTION_RECEIPT.json'),('producer_matrix_sha256','results/CONTEXT_PROFILES.json')]:
  p=PRODUCER/name;require(sha(p)==go[key],'RootGO producer hash differs '+name);checked(p)
 ps=read(PRODUCER/'SCOPE.json');receipt=read(PRODUCER/'results/EXECUTION_RECEIPT.json');matrix=read(PRODUCER/'results/CONTEXT_PROFILES.json')
 compare(receipt['scope_sha256'],sha(PRODUCER/'SCOPE.json'),'producer_scope_pin')
 compare(receipt['driver_sha256'],sha(PRODUCER/'driver.py'),'producer_code_pin');checked(PRODUCER/'driver.py')
 for d in ps['input_byte_pins'].values():checked(ROOT/d['path'],d)
 for d in receipt['output_byte_pins']:checked(ROOT/d['path'],d)
 selected=read(checked(ROOT/'on_cached/ranking/SELECTED_TOP9.json'))['records']
 require(len(selected)==9,'Exactly nine original ON logical templates required')
 census=read(checked(ROOT/'on_cached/feasibility/ON_NORMALIZATION_DOMAIN_CENSUS.json'))
 require(census['status']=='PASS_ALL2298_EXACT_ORIGINAL4096_PHYSICAL_CORE_NORMALIZATIONS'
         and census['counts']['ON_map_normalizations']==2298 and census['counts']['mismatching_records']==0,'Original ON normalization-domain census differs')
 original_source_metadata=read(checked(PRIOR_SOURCE_SCOPE));current_raw=read(checked(CURRENT_RAW))
 original_sources={(row['native_chunk_index'],row['scan_id']):row for row in original_source_metadata['source_records']}
 sourcefiles={}
 for row in current_raw['sources']:
  identity=(row['native_chunk_index'],row['scan_id']);original=original_sources[identity]
  for field in ('bytes','sha256','shape','source_channel0','decoded_rows'):compare(row[field],original[field],str(identity)+'/original_source_'+field)
  path=ROOT/row['restored_path'];checked(path,row);sourcefiles[identity]=(row,path)
 require(len(sourcefiles)==18,'Original18 H5 identities required')
 source_manifest={x['label']:x for x in read(checked(MANIFEST))['sources']}
 headers={s:x['current_header']['data_attributes'] for s,x in source_manifest.items()}
 compare(headers,ps['headers'],'original_headers')
 oldmatrix,oldcrops=read(checked(OLD_MATRIX)),read(checked(OLD_CROPS));oldqa=read(checked(OLD_QA))
 require(oldqa['mismatches']==[],'Pinned previous fullrawQA must have zero mismatches')
 baseline={}
 for track in oldmatrix['frozen_selected_records']:
  key,value=geometry(track,headers,np);template=track['primary_target']+'_rank'+str(track['exploratory_selection_rank'])
  baseline.setdefault(key,{'geometry':value,'template_ids':[]})['template_ids'].append(template)
 require(len(oldmatrix['profiles'])==54 and len(baseline)==8 and len(oldcrops['crops'])==48,'Original exposed baseline cardinality differs')
 for p in oldmatrix['profiles']:
  checked(ROOT/p['raw_capsule']['path'],p['raw_capsule']);checked(ROOT/p['normalization']['path'],p['normalization'])
 for p in oldcrops['crops']:checked(ROOT/p['crop']['path'],p['crop'])
 oldcropkeys={(x['scan_id'],x['native_chunk_index'],x['core_q']):x for x in oldcrops['crops']}
 expectednew={};logical={}
 for track in selected:
  require(track['width_channels'] in (1,3) and track['native_chunk_index'] in (170,171,172) and track['original_acquisition_role']=='ON','Selected original ON family differs')
  compare(track['reference_time_mjd'],headers[track['scan_id']]['tstart']+TSAMP/(2*86400),'selected/'+track['scan_id']+'/reference_midpoint')
  template=track['scan_id']+'_rank'+str(track['exploratory_selection_rank']);key,value=geometry(track,headers,np)
  require(template not in logical,'Logical selected template duplicate')
  logical[template]={'track':track,'key':key,'geometry':value,'reuse':key in baseline}
  if key not in baseline:expectednew.setdefault(key,track)
 compare(len(selected)*6,len(matrix['selected_profiles']),'selected_profile_count')
 compare(len(expectednew)*6,len(matrix['new_physical_profiles']),'new_physical_profile_count')
 compare(sorted(expectednew),sorted(x['physical_template_id'] for x in ps['new_physical_templates']),'new_physical_identity_set')
 require(len(expectednew)==go['expected_new_physical_templates'],'RootGO permitted new physical template count differs')
 require(len(matrix['new_physical_profiles'])==go['expected_new_fixed_queries'],'RootGO permitted new fixed query count differs')
 compare(sorted(logical),sorted(x['template_id'] for x in ps['selected_logical_templates']),'logical_identity_set')
 for frozen in ps['selected_logical_templates']:
  independent=logical[frozen['template_id']]
  compare(frozen['selected_original_record'],independent['track'],frozen['template_id']+'/scope_selected_tuple')
  compare(frozen['physical_template_id'],independent['key'],frozen['template_id']+'/scope_physical_identity')
  compare(frozen['physical_geometry'],independent['geometry'],frozen['template_id']+'/scope_all6_geometry')
  compare(frozen['reuse_baseline'],independent['reuse'],frozen['template_id']+'/scope_reuse_class')
 for obj,label in [(ps,'scope'),(receipt,'receipt'),(matrix,'matrix')]:
  for field in ('new_detector_grid','new_mask_or_veto','qualified_SETI_detection'):
   if field in obj:compare(obj[field],False,label+'/'+field)
 baselineimports,newlinks,ownmatches=0,0,0;seen=set();mapcache={};newbyid={}
 for physical in matrix['new_physical_profiles']:
  identity=(physical['physical_template_id'],physical['context_scan_id']);require(identity not in newbyid,'Duplicate new physical profile');newbyid[identity]=physical
 for wrapper in matrix['selected_profiles']:
  template,scan=wrapper['template_id'],wrapper['context_scan_id'];identity=(template,scan);require(identity not in seen,'Duplicate selected context');seen.add(identity)
  item=logical[template];track,key=item['track'],item['key'];source=wrapper['source_fixed_profile'];centers,elapsed=centers_for(track,scan,headers,np)
  compare(wrapper['selected_original_record'],track,str(identity)+'/selected_tuple');compare(wrapper['physical_template_id'],key,str(identity)+'/physical_identity')
  compare(source['rounded_absolute_centers'],centers,str(identity)+'/all16_centers');compare(source['width_channels'],track['width_channels'],str(identity)+'/width');compare(wrapper['raw_geometry_id'],item['geometry']['raw_geometry_id'],str(identity)+'/raw_geometry_id')
  compare(wrapper['times_from_primary_reference_s'],elapsed,str(identity)+'/elapsed')
  compare(source['context_target'],headers[scan]['source_name'],str(identity)+'/context_target')
  compare(source['original_acquisition_role'],'ON' if scan.endswith('_on') else 'OFF',str(identity)+'/original_role')
  compare(source['context_scan_id'],scan,str(identity)+'/scan')
  if item['reuse']:
   oldtemplate=baseline[key]['template_ids'][0];prior=next(x for x in oldmatrix['profiles'] if x['template_id']==oldtemplate and x['context_scan_id']==scan)
   compare(objsha(source),objsha(prior),str(identity)+'/exact_imported_profile_object_SHA')
   compare(wrapper['baseline_matrix_pin'],pin(OLD_MATRIX),str(identity)+'/baseline_matrix_pin');baselineimports+=1
  else:
   compare(objsha(source),objsha(newbyid[key,scan]),str(identity)+'/new_profile_object_SHA');newlinks+=1
  if scan==track['scan_id']:
   mp=track['map_pin'];checked(ROOT/mp['path'],mp)
   if mp['path'] not in mapcache:
    with np.load(ROOT/mp['path'],allow_pickle=False) as data:mapcache[mp['path']]={k:data[k].copy() for k in ('maximum_robust_box_track_score','winning_drift_hz_s','winning_width_channels','source_reference_channels')}
   original=mapcache[mp['path']];index=track['carrier_index_in_core']
   compare(original['maximum_robust_box_track_score'][index],track['score'],str(identity)+'/original_map_scalar')
   compare(original['winning_drift_hz_s'][index],track['drift_hz_s'],str(identity)+'/original_map_drift')
   compare(int(original['winning_width_channels'][index]),track['width_channels'],str(identity)+'/original_map_width')
   compare(int(original['source_reference_channels'][index]),track['reference_source_channel'],str(identity)+'/original_map_carrier')
   compare(source['fixed_robust_box_track_score'],track['score'],str(identity)+'/own_score',True,'own_score');ownmatches+=1
 require(seen=={(t,s) for t in logical for s in SCANS},'Selected sixscan contexts incomplete')
 # Authenticate and reconstruct only genuinely new fixed physical contexts.
 croprecords=[];reusedcroprecords=[];diagnostics=[];decodedrows=0;normalqueries=0;newprofilechecks=0;rawcellchecks=0
 producer_crop_keys={(x['scan_id'],x['native_chunk_index'],x['core_q']):x for x in matrix['new_normalization_crops']}
 if expectednew:
  import h5py,hdf5plugin
  require(hdf5plugin.register(filters='bshuf',force=True) and h5py.h5z.filter_avail(32008),'Original decoder unavailable')
  cropdir=BASE/'RAW_NORMALIZATION_CROPS';cropdir.mkdir(exist_ok=False)
  for scan in SCANS:
   joined=np.empty((16,3*CHUNK),dtype='<f4')
   for native in (170,171,172):
    record,path=sourcefiles[native,scan]
    with h5py.File(path,'r',rdcc_nbytes=8*1024**2) as handle:
     data=handle['data'];require(data.shape==(16,1,CHUNK) and data.dtype.str=='<f4','Original source shape/dtype differs')
     compare(int(data.attrs['original_source_frequency_chunk_origin']),native*CHUNK,scan+'/'+str(native)+'/source_origin')
     compare(data.attrs['original_source_url'],source_manifest[scan]['url'],scan+'/'+str(native)+'/source_url')
     compare(data.attrs['original_source_etag'],source_manifest[scan]['etag'],scan+'/'+str(native)+'/source_etag')
     for row in record['decoded_rows']:
      r=row['time_row'];values=data[r,0,:];require(np.isfinite(values).all() and (values>=0).all(),'Invalid source rawpower')
      compare(hashlib.sha256(values.tobytes()).hexdigest(),row['decoded_sha256'],scan+'/'+str(native)+'/'+str(r)+'/decoded_SHA')
      joined[r,(native-170)*CHUNK:(native-169)*CHUNK]=values;decodedrows+=1
   normcache={}
   for key,track in expectednew.items():
    profile=newbyid[key,scan];native,q,width=track['native_chunk_index'],track['core_q'],track['width_channels'];core0=native*CHUNK+q*CORE;crop0=core0-HALO;cropkey=(scan,native,q)
    compare(profile['canonical_selected_original_record'],track,profile['profile_id']+'/canonical_selected_original_record')
    compare(profile['physical_template_id'],key,profile['profile_id']+'/physical_template_id')
    compare(profile['raw_geometry_id'],geometry(track,headers,np)[1]['raw_geometry_id'],profile['profile_id']+'/raw_geometry_id')
    if cropkey not in normcache:
     normal=independent_norm(joined,core0,np);normcache[cropkey]=normal;normalqueries+=1
     crop=joined[:,crop0-BAND0:crop0-BAND0+12096].copy();require(crop.shape==(16,12096),'Independent12096 crop unavailable')
     declaration={'scan_id':scan,'native_chunk_index':native,'core_q':q,'shape':[16,12096],
       'absolute_source_channel_interval_half_open':[crop0,crop0+12096],'normalization_source_channel_interval_half_open':[core0,core0+CORE],
       'raw_float32_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'raw_float32_source_row_sha256':[hashlib.sha256(crop[r].tobytes()).hexdigest() for r in range(16)],
       'physical_profile_ids':[p['profile_id'] for (pid,s),p in newbyid.items() if s==scan and expectednew[pid]['native_chunk_index']==native and expectednew[pid]['core_q']==q]}
     if cropkey in oldcropkeys:
      prior=oldcropkeys[cropkey];compare(declaration['raw_float32_sha256'],prior['raw_float32_sha256'],str(cropkey)+'/prior_authenticated_crop_SHA')
      compare(declaration['raw_float32_source_row_sha256'],prior['raw_float32_source_row_sha256'],str(cropkey)+'/prior_crop16rowSHA');declaration['crop']=prior['crop'];reusedcroprecords.append(declaration)
     else:
      producer_crop=producer_crop_keys[cropkey]
      compare(declaration['raw_float32_sha256'],producer_crop['raw_float32_sha256'],str(cropkey)+'/producer_crop_SHA')
      compare(declaration['raw_float32_source_row_sha256'],producer_crop['raw_float32_source_row_sha256'],str(cropkey)+'/producer_crop16rowSHA')
      with np.load(checked(ROOT/producer_crop['crop']['path'],producer_crop['crop']),allow_pickle=False) as stored:
       compare(stored['raw_power'].view(np.uint32),crop.view(np.uint32),str(cropkey)+'/producer_fullcrop_bits')
       compare(stored['source_rows'],np.arange(16),str(cropkey)+'/producer_fullcrop_rows')
       compare(stored['absolute_source_channel_interval_half_open'],[crop0,crop0+12096],str(cropkey)+'/producer_fullcrop_interval')
       compare(stored['normalization_source_channel_interval_half_open'],[core0,core0+CORE],str(cropkey)+'/producer_fullcrop_norminterval')
      path=cropdir/('%s_native%d_q%03d_crop12096.npz'%(scan,native,q))
      with path.open('xb') as stream:np.savez(stream,raw_power=crop,absolute_source_channel_interval_half_open=np.asarray([crop0,crop0+12096],dtype=np.int64),normalization_source_channel_interval_half_open=np.asarray([core0,core0+CORE],dtype=np.int64),source_rows=np.arange(16,dtype=np.int64),tstart_mjd=np.asarray(headers[scan]['tstart']),tsamp_s=np.asarray(TSAMP))
      declaration['crop']=pin(path);croprecords.append(declaration)
     del crop
    normal=normcache[cropkey];savednormal=read(checked(ROOT/profile['normalization']['path'],profile['normalization']))
    interval=savednormal.get('normalization_source_channel_interval_half_open')
    if interval is None:interval=[savednormal['normalization_source_channels'][0],savednormal['normalization_source_channels'][-1]+1]
    compare(interval,[core0,core0+CORE],profile['profile_id']+'/normdomain');compare(savednormal['normalization_unmasked_counts'],[CORE]*16,profile['profile_id']+'/normcounts')
    for field in ('row_power_median','row_residual_median','row_residual_MAD_scale','row_winsorized_residual_location'):compare(savednormal[field],normal[field],profile['profile_id']+'/'+field,True,field)
    for item in logical.values():
     original=item['track']
     if item['key']==key and original['scan_id']==scan:
      originalnormal=read(checked(ROOT/original['normalization_pin']['path'],original['normalization_pin']))
      for field in ('row_power_median','row_residual_median','row_residual_MAD_scale','row_winsorized_residual_location'):
       compare(originalnormal[field],normal[field],profile['profile_id']+'/original_own_normalization/'+field,True,'original_own_'+field)
    centers,elapsed=centers_for(track,scan,headers,np);compare(profile['rounded_absolute_centers'],centers,profile['profile_id']+'/centers')
    if 'times_from_primary_reference_s' in profile:compare(profile['times_from_primary_reference_s'],elapsed,profile['profile_id']+'/elapsed')
    if 'row_midpoint_mjd' in profile:compare(profile['row_midpoint_mjd'],[headers[scan]['tstart']+(r+.5)*TSAMP/86400 for r in range(16)],profile['profile_id']+'/midpoint')
    indices=centers[:,None]-BAND0+np.arange(-251,252)[None,:];require((indices>=0).all() and (indices<3*CHUNK).all(),'Frozen raw503 support outside authenticated band')
    raw=joined[np.arange(16)[:,None],indices]
    with np.load(checked(ROOT/profile['raw_capsule']['path'],profile['raw_capsule']),allow_pickle=False) as capsule:
     compare(capsule['raw_power'].view(np.uint32),raw.view(np.uint32),profile['profile_id']+'/raw503bits');rawcellchecks+=16*503
     compare(capsule['rounded_absolute_centers'],centers,profile['profile_id']+'/capsule_centers')
     if 'source_rows' in capsule:compare(capsule['source_rows'],np.arange(16),profile['profile_id']+'/capsule_rows')
     if 'times_from_primary_reference_s' in capsule:compare(capsule['times_from_primary_reference_s'],elapsed,profile['profile_id']+'/capsule_elapsed')
     normalized=raw.astype(np.float64)/np.asarray(normal['row_power_median'])[:,None];columns=251+(np.asarray([-1,0,1]) if width==3 else np.asarray([0]))
     medians=np.column_stack([np.median(normalized[:,c-250:c+251],axis=1) for c in columns]);z=(normalized[:,columns]-medians-np.asarray(normal['row_winsorized_residual_location'])[:,None])/np.asarray(normal['row_residual_MAD_scale'])[:,None]
     sums=z.sum(axis=1);rows=sums/np.sqrt(16*width);score=float(sums.sum()/np.sqrt(16*width))
     compare(capsule['standardized_original_box_cells'],z,profile['profile_id']+'/capsule_cells',True,'original_cell_standardized')
     compare(capsule['standardized_row_box_sums'],sums,profile['profile_id']+'/capsule_rowsums',True,'row_standardized_box_sum')
     compare(capsule['row_score_contribution'],rows,profile['profile_id']+'/capsule_rowcontribution',True,'row_score_contribution')
    compare(profile['row_standardized_box_sum'],sums,profile['profile_id']+'/rowsums',True,'row_standardized_box_sum');compare(profile['row_score_contribution'],rows,profile['profile_id']+'/rowcontribution',True,'row_score_contribution')
    compare(profile['fixed_robust_box_track_score'],score,profile['profile_id']+'/score',True,'new_fixedscore')
    overlap=np.any(np.abs(centers[:,None]-np.asarray(DC)[None,:])<=width//2,axis=1);positive=np.maximum(rows,0);total=float(positive.sum())
    compare(profile['DC_contact_rows_any_frozen_center'],np.flatnonzero(overlap),profile['profile_id']+'/DC_contact');compare(profile['positive_row_count'],int((positive>0).sum()),profile['profile_id']+'/positive_rows')
    if total:compare(profile['positive_row_contribution_max_fraction'],float(positive.max()/total),profile['profile_id']+'/maxfraction',True,'positive_max_fraction')
    else:compare(profile['positive_row_contribution_max_fraction'],None,profile['profile_id']+'/maxfraction_null')
    if scan==track['scan_id']:compare(score,track['score'],profile['profile_id']+'/independent_own_score',True,'independent_own_score')
    newprofilechecks+=1;diagnostics.append({'physical_template_id':key,'context_scan_id':scan,'independent_score':score,'DC_contact_rows':np.flatnonzero(overlap).tolist()})
   del joined,normcache
 for path,prior in pins.items():require(pin(Path(path))==prior,'Input changed during independentQA')
 require(newprofilechecks==len(expectednew)*6 and ownmatches==len(selected),'IndependentQA profile completeness differs')
 cpusecs,wallsecs,rss=time.process_time()-cpu,time.monotonic()-started,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 require(cpusecs<=CPU_CAP and wallsecs<=WALL_CAP and rss<=RAM_CAP,'IndependentQA measured resource cap exceeded')
 cropbytes=sum(x['crop']['bytes'] for x in croprecords)
 require(cropbytes<=64*1024**2,'Preserved new crops exceed64MiB')
 save(BASE/'RAW_NORMALIZATION_CROP_MANIFEST.json',{'schema':'SETI_ON_CACHED_QA_NEW_CROP_MANIFEST_V1','crop_count':len(croprecords),'bytes':cropbytes,'crops':croprecords,
   'reused_prior_authenticated_crops':reusedcroprecords,'original_source_raw_row_authenticated':bool(expectednew),'baseline_raw_authentication_receipt':pin(OLD_QA)})
 save(BASE/'INDEPENDENT_CONTEXT_DIAGNOSTICS.json',{'new_physical_profiles':diagnostics,'baseline_profiles_recomputed':0})
 counts={'selected_logical_templates':len(selected),'selected_logical_profiles_verified':len(seen),'baseline_logical_profiles_hash_imported':baselineimports,
   'new_selected_logical_profile_links':newlinks,'new_distinct_physical_profiles_independently_verified':newprofilechecks,'new_distinct_physical_templates':len(expectednew),
   'source_file_byte_identities_verified':18,'decoded_source_rows_verified_for_new_queries':decodedrows,'baseline_physical_profiles_recomputed':0,
   'distinct_new_profile_core_scan_normalizations_independently_recomputed':normalqueries,'fullcore501_median_positions':normalqueries*16*CORE,
   'fullcore_normalization_terms':normalqueries*16*4,'raw503_cells_bitverified':rawcellchecks,'selected_original_own_map_scalar_matches':ownmatches,
   'preserved_unique_absent12096_crops':len(croprecords),'preserved_crop_bytes':cropbytes,'prior_authenticated_crop_hash_matches':len(reusedcroprecords),'comparisons':checks}
 result={'schema':'SETI_ON_CACHED_INDEPENDENT_CONTEXT_QA_RECEIPT_V1','status':'PASS_INDEPENDENT_ON_NEW_FIXED_CONTEXTS_AND_EXACT_BASELINE_REUSE' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
   'counts':counts,'mismatch_count':len(mismatches),'mismatches':mismatches,'max_absolute_errors':maxerrors,'input_pins_before_and_after':list(pins.values()),
   'CPU_seconds':cpusecs,'wall_seconds':wallsecs,'peak_RSS_bytes':rss,'limits':scope['limits'],'runtime':{'Python':sys.version.split()[0],'NumPy':np.__version__},
   'detector_imported':False,'detector_grid_rerun':False,'new_mask_or_veto':False,'new_telescope_requests':0,'qualified_SETI_detection':False,
   'metadata_interface_correction':scope.get('metadata_interface_correction'),
   'limitations':['Hash-reused baseline normalization and profiles inherit prior rawQA and NumPy reproduction; this run does not recompute baseline scores.',
     'Fixed ON contexts include same-target scans within one observing visit. Numerical integrity does not establish celestial origin, false-alarm significance or independent repeated target visits.']}
 save(BASE/'QA_RECEIPT.json',result);signal.alarm(0);print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins_before_and_after','runtime','limitations')}))

if __name__=='__main__':main()
