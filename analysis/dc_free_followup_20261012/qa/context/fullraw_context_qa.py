#!/usr/bin/env python3
"""Independent complete normalization and fixed-track QA from restored sources.

No detector imported or grid evaluated. NumPy local501 medians use512channel
core tiles and one source row at a time. All saved full16 core normalization
terms are recomputed from authenticated full raw arrays after root GO only.
"""
from __future__ import annotations
import argparse,hashlib,json,os,resource,signal,time,sys
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
BASE=Path(__file__).resolve().parent;WORKSPACE=BASE.parents[2];RESTORED=WORKSPACE/'next_dc/restored';OLD=WORKSPACE/'seti_previous'
CHUNK=1048576;CORE=4096;HALO=4000;BAND0=170*CHUNK
FCH1=2802832031.25;DF=-2.7939677238464355;TSAMP=18.253611008
SCANS=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
DC=[n*CHUNK+CHUNK//2 for n in (170,171,172)]
CPU_CAP=600;WALL_CAP=900;RAM_CAP=2*1024**3;ATOL=1e-7;RTOL=1e-10

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(p):
 p=p.resolve();return {'path':p.relative_to(WORKSPACE).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
def read(p):return json.loads(p.read_bytes(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def require(v,s):
 if not v:raise ValueError(s)
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def reconstruct_normalization(rawjoined,core0,np):
 """Independent exact501 running medians only on unchanged4096-channel core."""
 local0=core0-BAND0
 core=rawjoined[:,local0:local0+CORE].astype(np.float64)
 require(core.shape==(16,CORE),'Full normalization core unavailable')
 levels=np.median(core,axis=1);require((levels>0).all(),'Invalid rawcore rowlevel')
 residual=np.empty_like(core)
 for r in range(16):
  support=rawjoined[r,local0-250:local0+CORE+250].astype(np.float64)/levels[r]
  require(support.shape==(CORE+500,),'Fullcore501 median support unavailable')
  windows=np.lib.stride_tricks.sliding_window_view(support,501)
  for start in range(0,CORE,512):
   stop=min(start+512,CORE)
   med=np.median(windows[start:stop],axis=1)
   residual[r,start:stop]=core[r,start:stop]/levels[r]-med
 center=np.median(residual,axis=1)
 scale=1.4826*np.median(np.abs(residual-center[:,None]),axis=1)
 require((scale>0).all() and np.isfinite(scale).all(),'Invalid independentMAD')
 clipped=np.clip(residual-center[:,None],-5*scale[:,None],5*scale[:,None])
 location=center+np.mean(clipped,axis=1)
 return {'row_power_median':levels.tolist(),'row_residual_median':center.tolist(),
         'row_residual_MAD_scale':scale.tolist(),'row_winsorized_residual_location':location.tolist(),
         'normalization_unmasked_counts':[CORE]*16,'normalization_source_channel_interval_half_open':[core0,core0+CORE]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-only',action='store_true');p.add_argument('--go',type=Path);p.add_argument('--scope',type=Path,default=BASE/'scope.json');args=p.parse_args()
 if args.check_only:
  print(json.dumps({'status':'PREPARED_SOURCE_NO_SCIENCE_ARRAYS','qa_source_sha256':digest(Path(__file__)),'tile_channels':512,'detector_imported':False}));return
 require(args.go is not None,'Separate rootGO required')
 scope=read(args.scope);go=read(args.go)
 require(go['authorized'] and go['scope_sha256']==digest(args.scope) and go['qa_sha256']==digest(Path(__file__)),'Exact root admission differs')
 require(not (BASE/'QA_RECEIPT.json').exists(),'QA not overwriteable')
 def timeout(a,b):raise TimeoutError('Fullraw independentQA resourcecap')
 signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(WALL_CAP)
 resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(RAM_CAP,RAM_CAP))
 started=time.monotonic();cpu=time.process_time()
 import numpy as np,h5py,hdf5plugin
 require(hdf5plugin.register(filters='bshuf',force=True) and h5py.h5z.filter_avail(32008),'Official bitshuffle decoder unavailable')
 pins={};mismatches=[];maxerrors={};counts={};checks=0
 def checked(path,declared=None):
  path=path.resolve();actual=pin(path)
  require(declared is None or all(actual[k]==declared[k] for k in ('bytes','sha256')),'Filepin differs: '+str(path))
  require(str(path) not in pins or pins[str(path)]==actual,'Repeated input changed');pins[str(path)]=actual;return path
 def compare(a,b,label,numeric=False,category=None):
  nonlocal checks
  checks+=1;x=np.asarray(a);y=np.asarray(b)
  if numeric:
   ok=x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all() and np.allclose(x,y,atol=ATOL,rtol=RTOL)
   delta=float(np.max(np.abs(x-y))) if x.shape==y.shape and x.size else None
   if delta is not None:maxerrors[category or label]=max(maxerrors.get(category or label,0),delta)
  else:ok=x.shape==y.shape and np.array_equal(x,y)
  if not ok:mismatches.append(label)
  return ok
 for d in scope['input_pins']:checked(WORKSPACE/d['path'],d)
 checked(Path(__file__));checked(args.go);checked(args.scope)
 selected=read(checked(WORKSPACE/'next_dc/ranking/SELECTED_TOP9.json'))['records'];require(len(selected)==9,'Nine selected unchanged tracks required')
 # Source original acquisitions supply byte and decoded-row hashes independently of context producer.
 metadata171=read(checked(OLD/'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'))
 metadata_adj=read(checked(OLD/'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'))
 sourcefiles={}
 for native,metadata,folder in [(171,metadata171,'analysis/new_visit_recovery/results/acquire'),(170,metadata_adj,'analysis/s2017_next_native/results/acquire'),(172,metadata_adj,'analysis/s2017_next_native/results/acquire')]:
  for record in metadata['decoded_files']:
   if native!=171 and record['native_chunk_index']!=native:continue
   path=RESTORED/folder/record['array_file'];checked(path,{'bytes':record['bytes'],'sha256':record['file_sha256']})
   sourcefiles[native,record['scan_id']]=(record,path)
 require(len(sourcefiles)==18,'18 original compactsources required')
 manifest=read(checked(OLD/'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'))
 headers={i['label']:i['current_header']['data_attributes'] for i in manifest['sources']}
 contexts=load_context_results(scope,checked,read,np,compare)
 require(len(contexts)==54,'54fixedqueries required')
 rawcropdir=BASE/'RAW_NORMALIZATION_CROPS';rawcropdir.mkdir(exist_ok=False);crop_records=[]
 seen=set();physical_geometry={};decoded_rows=0;normalization_queries=0;fullcore_median_cells=0;score_matches=0;own_matches=0;diagnostics=[]
 for scan in SCANS:
  joined=np.empty((16,3*CHUNK),dtype='<f4')
  for native in (170,171,172):
   record,path=sourcefiles[native,scan]
   with h5py.File(path,'r',rdcc_nbytes=8*1024**2) as h:
    d=h['data'];require(d.shape==(16,1,CHUNK) and d.dtype.str=='<f4','Rawcompact shape/dtype differs')
    compare(int(d.attrs['original_source_frequency_chunk_origin']),native*CHUNK,'source/'+scan+'/'+str(native)+'/channel_origin')
    for row in record['decoded_rows']:
     r=row['time_row'];values=d[r,0,:]
     require(np.isfinite(values).all() and (values>=0).all(),'Invalid rawsourcepower')
     compare(hashlib.sha256(values.tobytes()).hexdigest(),row['decoded_sha256'],'source/'+scan+'/'+str(native)+'/'+str(r)+'/decoded_SHA')
     joined[r,(native-170)*CHUNK:(native-169)*CHUNK]=values;decoded_rows+=1
  normalcache={}
  for context in [c for c in contexts if c['context_scan_id']==scan]:
   track=context['selected_track'];native=track['native_chunk_index'];q=track['core_q'];width=track['width_channels'];rank=track['exploratory_selection_rank']
   identity=(track['primary_target'],rank,scan);require(identity not in seen,'Duplicate newfixedquery');seen.add(identity)
   require(track in selected,'Context selected tuplechanged')
   core0=native*CHUNK+q*CORE;key=(native,q)
   if key not in normalcache:
    normalcache[key]=reconstruct_normalization(joined,core0,np);normalization_queries+=1;fullcore_median_cells+=16*CORE
    crop0=core0-HALO;cropstop=core0+CORE+HALO
    crop=joined[:,crop0-BAND0:cropstop-BAND0].copy();require(crop.shape==(16,12096),'Full normalization12096crop unavailable')
    croppath=rawcropdir/(scan+'_native%d_q%03d_crop12096.npz'%(native,q))
    with croppath.open('xb') as f:np.savez(f,raw_power=crop,absolute_source_channel_interval_half_open=np.asarray([crop0,cropstop]),normalization_source_channel_interval_half_open=np.asarray([core0,core0+CORE]),source_rows=np.arange(16),tstart_mjd=np.asarray(headers[scan]['tstart']),tsamp_s=np.asarray(TSAMP))
    crop_records.append({'scan_id':scan,'native_chunk_index':native,'core_q':q,'crop':pin(croppath),
                         'shape':[16,12096],'absolute_source_channel_interval_half_open':[crop0,cropstop],
                         'normalization_source_channel_interval_half_open':[core0,core0+CORE],
                         'raw_float32_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),
                         'raw_float32_source_row_sha256':[hashlib.sha256(crop[r].tobytes()).hexdigest() for r in range(16)],
                         'profile_ids':[c['profile_id'] for c in contexts if c['context_scan_id']==scan and c['selected_track']['native_chunk_index']==native and c['selected_track']['core_q']==q]})
    del crop
   normal=normalcache[key];savednormal=context['_normalization']
   interval=savednormal.get('normalization_source_channel_interval_half_open')
   if interval is None:interval=[savednormal['normalization_source_channels'][0],savednormal['normalization_source_channels'][-1]+1]
   compare(interval,[core0,core0+CORE],str(identity)+'/normalizationdomain')
   for k in ('row_power_median','row_residual_median','row_residual_MAD_scale','row_winsorized_residual_location'):
    compare(savednormal[k],normal[k],str(identity)+'/'+k,True,k)
   compare(savednormal['normalization_unmasked_counts'],[CORE]*16,str(identity)+'/normalizationcounts')
   elapsed=(headers[scan]['tstart']-headers[track['scan_id']]['tstart'])*86400+np.arange(16)*TSAMP
   centers=np.rint((track['frequency_hz_at_own_first_midpoint']-FCH1)/DF+track['drift_hz_s']*elapsed/DF).astype(np.int64)
   compare(centers,context['rounded_absolute_centers'],str(identity)+'/matrixcenters')
   compare(elapsed,context['times_from_primary_reference_s'],str(identity)+'/elapsedtimes')
   compare(context['row_midpoint_mjd'],[headers[scan]['tstart']+(r+.5)*TSAMP/86400 for r in range(16)],str(identity)+'/rowmidpoints')
   compare(context['context_target'],headers[scan]['source_name'],str(identity)+'/contexttarget')
   compare(context['original_acquisition_role'],'ON' if scan.endswith('_on') else 'OFF',str(identity)+'/originalrole')
   capsule=context['_capsule'];compare(centers,capsule['rounded_absolute_centers'],str(identity)+'/capsulecenters')
   indices=centers[:,None]-BAND0+np.arange(-251,252)[None,:]
   require((indices>=0).all() and (indices<3*CHUNK).all(),'Fixedraw503 supportoutsideband')
   raw=joined[np.arange(16)[:,None],indices]
   compare(raw.view(np.uint32),capsule['raw_power'].view(np.uint32),str(identity)+'/raw503bits')
   normalized=raw.astype(np.float64)/np.asarray(normal['row_power_median'])[:,None]
   offsets=np.array([-1,0,1]) if width==3 else np.array([0]);columns=251+offsets
   median=np.column_stack([np.median(normalized[:,c-250:c+251],axis=1) for c in columns])
   z=(normalized[:,columns]-median-np.asarray(normal['row_winsorized_residual_location'])[:,None])/np.asarray(normal['row_residual_MAD_scale'])[:,None]
   sums=z.sum(axis=1);rows=sums/np.sqrt(16*width);score=float(sums.sum()/np.sqrt(16*width))
   compare(sums,context['row_standardized_box_sum'],str(identity)+'/matrixrows',True,'row_standardized_box_sum')
   compare(sums,capsule['standardized_row_box_sums'],str(identity)+'/capsulerows',True,'row_standardized_box_sum')
   compare(z,capsule['standardized_original_box_cells'],str(identity)+'/originalcellz',True,'original_cell_standardized')
   if 'row_score_contribution' in capsule:compare(rows,capsule['row_score_contribution'],str(identity)+'/rowcontributions',True,'row_score_contribution')
   savedscore=context.get('fixed_robust_box_track_score',context.get('direct_fixed_robust_box_track_score'))
   compare(score,savedscore,str(identity)+'/fixedscore',True,'fixedscore');score_matches+=1
   if scan==track['scan_id']:
    compare(score,track['score'],str(identity)+'/unchangedoriginscore',True,'origin_score');own_matches+=1
    originalcapsule=checked(WORKSPACE/track['capsule_path'],{'bytes':(WORKSPACE/track['capsule_path']).stat().st_size,'sha256':track['capsule_sha256']})
    with np.load(originalcapsule,allow_pickle=False) as oldcap:compare(raw.view(np.uint32),oldcap['raw_power'].view(np.uint32),str(identity)+'/originalselectioncapsulebits')
   # Descriptive DC contact diagnostic uses elapsed context trajectory, no veto applied.
   overlap=np.any(np.abs(centers[:,None]-np.asarray(DC)[None,:])<=width//2,axis=1)
   positive=np.maximum(rows,0);total=float(positive.sum());dominant=int(np.argmax(positive)) if total else None
   compare(context['DC_contact_rows_any_frozen_center'],np.flatnonzero(overlap),str(identity)+'/DCcontacts')
   compare(context['positive_row_count'],int((positive>0).sum()),str(identity)+'/positive_rowcount')
   for n in (1,2,4):
    fraction=float(np.sort(positive)[-n:].sum()/total) if total else None
    compare(context['positive_row_topN_fractions'][str(n)],fraction,str(identity)+'/positive_top'+str(n),total>0,'positive_row_fraction')
   effective=total**2/float((positive**2).sum()) if total else None
   compare(context['positive_contribution_effective_rows'],effective,str(identity)+'/effective_rows',total>0,'positive_effective_rows')
   patch=raw[:,187:316].astype(np.float64);flank=np.median(patch[:,np.r_[0:49,80:129]],axis=1)
   for r,rowmetrics in enumerate(context['raw129_centered_patch_metrics']):
    compare(rowmetrics['source_row'],r,str(identity)+'/morphologyrowid')
    for k,val in [('raw_center_power',float(patch[r,64])),('symmetric98_flank_median',float(flank[r])),('center_over_symmetric98_flank_median',float(patch[r,64]/flank[r]))]:
     compare(rowmetrics[k],val,str(identity)+'/morphology'+k,True,'morphology_'+k)
    compare(rowmetrics['maximum_raw_patch_offset_from_track_center'],int(np.argmax(patch[r]))-64,str(identity)+'/rawpeakoffset')
   geom=(scan,width,tuple(int(x) for x in centers));canonical=physical_geometry.setdefault(geom,context['profile_id'])
   compare(context['canonical_profile_for_same_physical_original_box_geometry'],canonical,str(identity)+'/canonicalgeometry')
   compare(context['duplicates_another_logical_profile_physical_geometry'],canonical!=context['profile_id'],str(identity)+'/duplicate_geometry')
   diagnostics.append({'primary_target':track['primary_target'],'rank':rank,'context_scan_id':scan,'score':score,
                       'DC_box_overlap_rows':np.flatnonzero(overlap).tolist(),'dominant_positive_row':dominant,
                       'dominant_positive_row_fraction':float(positive[dominant]/total) if total else None})
  del joined,normalcache
 for path,oldpin in pins.items():require(pin(Path(path))==oldpin,'InputchangedduringQA')
 counts.update({'source_files_hashed':18,'decoded_source_rows_verified':decoded_rows,'profiles_verified':score_matches,
                'own_primary_score_matches':own_matches,'distinct_fullcore_normalization_queries':normalization_queries,
                'fullcore501_median_positions':fullcore_median_cells,'fullcore_normalization_row_terms':normalization_queries*16*4,
                'raw503_profile_bits_verified':54*16*503,'comparisons':checks,
                'distinct_physical_original_box_geometries':len(physical_geometry),
                'duplicate_logical_profile_geometries':54-len(physical_geometry)})
 require(decoded_rows==288 and score_matches==54 and own_matches==9 and len(seen)==54,'FullrawQA completeness differs')
 cpusecs=time.process_time()-cpu;wallsecs=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 require(cpusecs<=CPU_CAP and wallsecs<=WALL_CAP and rss<=RAM_CAP,'MeasuredfullrawQA resourcecap exceeded')
 rawcropbytes=sum(c['crop']['bytes'] for c in crop_records);require(rawcropbytes<=40*1024**2,'Regenerable normalization crops exceed40MiB')
 save(BASE/'RAW_NORMALIZATION_CROP_MANIFEST.json',{'crop_count':len(crop_records),'bytes':rawcropbytes,'cropped_float32_power_cells':len(crop_records)*16*12096,'original_source_raw_row_authenticated':True,'crops':crop_records})
 counts['preserved_normalization_crops']=len(crop_records);counts['preserved_normalization_crop_bytes']=rawcropbytes
 save(BASE/'INDEPENDENT_CONTEXT_DIAGNOSTICS.json',{'profiles':diagnostics})
 result={'status':'PASS_INDEPENDENT_FULLRAW_NORMALIZATION_AND54_FIXED_CONTEXTS' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
         'counts':counts,'mismatches':mismatches,'max_absolute_errors':maxerrors,'input_pins_before_and_after':list(pins.values()),
         'CPU_seconds':cpusecs,'wall_seconds':wallsecs,'peak_RSS_bytes':rss,
         'limits':{'CPU_seconds':CPU_CAP,'wall_seconds':WALL_CAP,'RAM_bytes':RAM_CAP},
         'runtime':{'Python':sys.version.split()[0],'numpy':np.__version__,'h5py':h5py.__version__,'HDF5':h5py.version.hdf5_version,'hdf5plugin':__import__('importlib.metadata',fromlist=['version']).version('hdf5plugin')},
         'fullcore_normalization_independently_recomputed':True,'detector_imported':False,'detector_grid_rerun':False,
         'mask_or_veto_applied':False,'new_telescope_requests':0,'new_sky_observations':0,'qualified_SETI_detection':False,
         'limitations':['Selection is an exposed DC-aware subset of cached per-core maxima, not exhaustive DC-free reoptimization.',
                        'Original search maximization, multi-trial selection and false-alarm calibration are not independently rerun.',
                        'Full normalization and rawscores are independently recomputed from original restored float32 arrays; this verifies numerical integrity, not astrophysical origin.',
                        'Different historical primary targets and contexts are descriptive; no independent repeated visit of one target is established. AB failclosed and protected2016 holdouts remain unchanged.']}
 save(BASE/'QA_RECEIPT.json',result);signal.alarm(0);print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins_before_and_after','runtime','limitations')}))

def load_context_results(scope,checked,read,np,compare):
 root=WORKSPACE/'next_dc/crossscan';receipt=read(checked(root/'results/EXECUTION_RECEIPT.json'));producer_scope=read(checked(root/'SCOPE.json'))
 compare(receipt['scope_sha256'],digest(root/'SCOPE.json'),'producer_receipt_scope')
 compare(receipt['driver_sha256'],digest(root/'driver.py'),'producer_receipt_code')
 for d in receipt['input_byte_pins'].values():checked(WORKSPACE/d['path'],d)
 for d in receipt['output_byte_pins']:checked(WORKSPACE/d['path'],d)
 matrix=read(checked(root/'results/CONTEXT_PROFILES.json'));compare(matrix['frozen_selected_records'],producer_scope['frozen_selected_records'],'context_frozen_selection')
 contexts=[]
 for original in matrix['profiles']:
  c=dict(original);c['selected_track']=c['selected_original_record']
  d=c['raw_capsule']
  with np.load(checked(WORKSPACE/d['path'],d),allow_pickle=False) as capsule:c['_capsule']={k:capsule[k].copy() for k in capsule.files}
  d=c['normalization'];c['_normalization']=read(checked(WORKSPACE/d['path'],d));contexts.append(c)
 return contexts
if __name__=='__main__':main()
