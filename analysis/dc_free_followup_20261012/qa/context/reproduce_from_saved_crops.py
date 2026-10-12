#!/usr/bin/env python3
"""Portable NumPy-only numerical replay of54 fixed historical profiles.

Run from an unpacked result package that preserves root-relative file paths.
Requires Python3 and NumPy only. It authenticates48 queried raw12096 crops,
reconstructs their full16 normalization with exact501 medians, then extracts
all54 raw503 profiles and compares frozen canonical scores/geometry. Original
HDF5 authentication is prior provenance; this replay opens no HDF5 files.
"""
from __future__ import annotations
import argparse,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
BASE=Path(__file__).resolve().parent
DEFAULT_ROOT=BASE.parents[2]
CORE=4096;HALO=4000;CHUNK=1048576;FCH1=2802832031.25;DF=-2.7939677238464355;TSAMP=18.253611008
DC=[n*CHUNK+CHUNK//2 for n in (170,171,172)];CPU_CAP=600;WALL_CAP=900;RAM_CAP=2*1024**3;ATOL=1e-7;RTOL=1e-10

def require(test,message):
 if not test:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def read(path):return json.loads(path.read_bytes(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
def save_new(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def confined(root,name):
 relative=Path(name);require(not relative.is_absolute() and '..' not in relative.parts,'Root-relative confined path required')
 path=(root/relative).resolve();require(path.is_relative_to(root) and not path.is_symlink(),'Input escapes package root');return path

def normalize_crop(raw,np):
 """Reuse independentQA formulas; no canonical normalization conditions score."""
 core=raw[:,HALO:HALO+CORE].astype(np.float64)
 level=np.median(core,axis=1);require((level>0).all(),'Invalid independent rowpower median')
 residual=np.empty_like(core)
 for row in range(16):
  support=raw[row,HALO-250:HALO+CORE+250].astype(np.float64)/level[row]
  windows=np.lib.stride_tricks.sliding_window_view(support,501)
  for start in range(0,CORE,512):
   stop=min(start+512,CORE)
   residual[row,start:stop]=core[row,start:stop]/level[row]-np.median(windows[start:stop],axis=1)
 center=np.median(residual,axis=1);mad=1.4826*np.median(np.abs(residual-center[:,None]),axis=1)
 require((mad>0).all() and np.isfinite(mad).all(),'Invalid independentMAD')
 location=center+np.mean(np.clip(residual-center[:,None],-5*mad[:,None],5*mad[:,None]),axis=1)
 return {'row_power_median':level.tolist(),'row_residual_median':center.tolist(),
         'row_residual_MAD_scale':mad.tolist(),'row_winsorized_residual_location':location.tolist(),
         'normalization_unmasked_counts':[CORE]*16}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--root',type=Path,default=DEFAULT_ROOT,help='Unpacked package root containing next_dc/')
 parser.add_argument('--scope',type=Path,default=BASE/'REPRODUCTION_SCOPE.json')
 parser.add_argument('--go',type=Path,default=BASE/'REPRODUCTION_GO.json')
 parser.add_argument('--out',type=Path,default=BASE/'REPRODUCTION_RECEIPT.json')
 parser.add_argument('--check-only',action='store_true')
 args=parser.parse_args()
 if args.check_only:
  print(json.dumps({'status':'NUMPY_ONLY_REPLAY_INTERFACE_PREPARED','code_sha256':digest(Path(__file__)),'opens_HDF5':False}));return
 root=args.root.resolve();scopepath=args.scope.resolve();gopath=args.go.resolve();out=args.out.resolve()
 require(not out.exists(),'Do not overwrite replay receipt; use a new --out path')
 scope=read(scopepath);go=read(gopath)
 require(go['authorized'] and go['scope_sha256']==digest(scopepath) and go['code_sha256']==digest(Path(__file__)),'Exact local replay freeze differs')
 require(scope['limits']=={'CPU_seconds':CPU_CAP,'wall_seconds':WALL_CAP,'RAM_bytes':RAM_CAP},'Replay resource limits differ')
 def timeout(signum,frame):raise TimeoutError('NumPy-only replay resourcecap')
 signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(WALL_CAP)
 resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(RAM_CAP,RAM_CAP))
 started=time.monotonic();cpu=time.process_time()
 import numpy as np
 pins={};mismatches=[];maxerrors={};checks=0
 def pin(path):return {'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
 def checked(declared):
  path=confined(root,declared['path']);actual=pin(path)
  require(all(actual[k]==declared[k] for k in ('bytes','sha256')),'Replay input pin mismatch '+declared['path'])
  require(str(path) not in pins or pins[str(path)]==actual,'Replay input changed');pins[str(path)]=actual;return path
 def compare(actual,expected,label,numeric=False,category=None):
  nonlocal checks
  checks+=1;a=np.asarray(actual);b=np.asarray(expected)
  if numeric:
   ok=a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a,b,atol=ATOL,rtol=RTOL)
   delta=float(np.max(np.abs(a-b))) if a.shape==b.shape and a.size else None
   if delta is not None:maxerrors[category or label]=max(maxerrors.get(category or label,0),delta)
  else:ok=a.shape==b.shape and np.array_equal(a,b)
  if not ok:mismatches.append(label)
 for declared in scope['input_pins']:checked(declared)
 inputpaths={d['path']:confined(root,d['path']) for d in scope['input_pins']}
 manifest=read(inputpaths['next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json'])
 matrix=read(inputpaths['next_dc/crossscan/results/CONTEXT_PROFILES.json'])
 producer_scope=read(inputpaths['next_dc/crossscan/SCOPE.json']);headers=producer_scope['headers']
 profiles=matrix['profiles'];require(len(profiles)==54 and len(manifest['crops'])==48,'Replay54profiles/48crops required')
 compare(matrix['frozen_selected_records'],producer_scope['frozen_selected_records'],'frozen_original_tuples')
 profile_index={p['profile_id']:p for p in profiles};require(len(profile_index)==54,'Duplicate profile IDs')
 replayed={};rows_hashed=0;fullmedian_positions=0;ownscore_matches=0
 for declaration in manifest['crops']:
  croppath=checked(declaration['crop'])
  with np.load(croppath,allow_pickle=False) as values:crop={k:values[k].copy() for k in values.files}
  raw=crop['raw_power'];require(raw.shape==(16,12096) and raw.dtype.str=='<f4','Savedcrop float32 geometry differs')
  require(np.isfinite(raw).all() and (raw>=0).all(),'Invalid savedcrop power')
  scan=declaration['scan_id'];native=declaration['native_chunk_index'];q=declaration['core_q']
  core0=native*CHUNK+q*CORE;crop0=core0-HALO;cropstop=core0+CORE+HALO
  compare(crop['absolute_source_channel_interval_half_open'],[crop0,cropstop],'crop/absolute_source_interval')
  compare(crop['normalization_source_channel_interval_half_open'],[core0,core0+CORE],'crop/core_source_interval')
  compare(crop['source_rows'],np.arange(16),'crop/source_row_ids')
  compare(crop['tstart_mjd'],headers[scan]['tstart'],'crop/header_tstart')
  compare(crop['tsamp_s'],TSAMP,'crop/header_tsamp')
  compare(hashlib.sha256(raw.tobytes()).hexdigest(),declaration['raw_float32_sha256'],'crop/full_float32_hash')
  for row in range(16):
   compare(hashlib.sha256(raw[row].tobytes()).hexdigest(),declaration['raw_float32_source_row_sha256'][row],'crop/'+str((scan,native,q,row))+'/rowhash');rows_hashed+=1
  norm=normalize_crop(raw,np);fullmedian_positions+=16*CORE
  expected_profiles=[p['profile_id'] for p in profiles if p['context_scan_id']==scan and p['selected_original_record']['native_chunk_index']==native and p['selected_original_record']['core_q']==q]
  compare(declaration['profile_ids'],expected_profiles,'crop/profile_mapping')
  for profile_id in declaration['profile_ids']:
   require(profile_id not in replayed,'A profile mapped to multiple crops');p=profile_index[profile_id];track=p['selected_original_record'];width=track['width_channels'];origin=track['scan_id']
   require(width in (1,3),'Changed original width')
   savednorm=read(checked(p['normalization']))
   compare(savednorm['normalization_source_channel_interval_half_open'],[core0,core0+CORE],profile_id+'/norm_interval')
   compare(savednorm['normalization_unmasked_counts'],[CORE]*16,profile_id+'/norm_counts')
   for term in ('row_power_median','row_residual_median','row_residual_MAD_scale','row_winsorized_residual_location'):
    compare(savednorm[term],norm[term],profile_id+'/'+term,True,term)
   elapsed=(headers[scan]['tstart']-headers[origin]['tstart'])*86400+np.arange(16)*TSAMP
   centers=np.rint((track['frequency_hz_at_own_first_midpoint']-FCH1)/DF+track['drift_hz_s']*elapsed/DF).astype(np.int64)
   compare(centers,p['rounded_absolute_centers'],profile_id+'/canonical_centers')
   compare(elapsed,p['times_from_primary_reference_s'],profile_id+'/canonical_elapsed')
   indices=centers[:,None]-crop0+np.arange(-251,252)[None,:]
   require((indices>=0).all() and (indices<12096).all(),'Replay profile lacks savedcrop raw503 support')
   profile_raw=raw[np.arange(16)[:,None],indices]
   with np.load(checked(p['raw_capsule']),allow_pickle=False) as values:capsule={k:values[k].copy() for k in values.files}
   compare(profile_raw.view(np.uint32),capsule['raw_power'].view(np.uint32),profile_id+'/replayed_raw503_bits')
   compare(centers,capsule['rounded_absolute_centers'],profile_id+'/capsule_centers')
   compare(elapsed,capsule['times_from_primary_reference_s'],profile_id+'/capsule_elapsed')
   ratio=profile_raw.astype(np.float64)/np.asarray(norm['row_power_median'])[:,None]
   columns=np.array([250,251,252]) if width==3 else np.array([251])
   med=np.column_stack([np.median(ratio[:,c-250:c+251],axis=1) for c in columns])
   z=(ratio[:,columns]-med-np.asarray(norm['row_winsorized_residual_location'])[:,None])/np.asarray(norm['row_residual_MAD_scale'])[:,None]
   terms=z.sum(axis=1);contribution=terms/np.sqrt(16*width);score=float(terms.sum()/np.sqrt(16*width))
   compare(z,capsule['standardized_original_box_cells'],profile_id+'/box_cells',True,'original_box_cells')
   compare(terms,capsule['standardized_row_box_sums'],profile_id+'/capsule_box_rows',True,'standardized_row_box_sums')
   compare(terms,p['row_standardized_box_sum'],profile_id+'/canonical_box_rows',True,'standardized_row_box_sums')
   compare(contribution,capsule['row_score_contribution'],profile_id+'/capsule_row_contribution',True,'row_score_contribution')
   compare(contribution,p['row_score_contribution'],profile_id+'/canonical_row_contribution',True,'row_score_contribution')
   compare(score,p['fixed_robust_box_track_score'],profile_id+'/canonical_score',True,'fixed_robust_box_track_score')
   if origin==scan:
    compare(score,track['score'],profile_id+'/original_selected_score',True,'original_selected_score');ownscore_matches+=1
   contact=np.any(np.abs(centers[:,None]-np.asarray(DC)[None,:])<=width//2,axis=1)
   compare(np.flatnonzero(contact),p['DC_contact_rows_any_frozen_center'],profile_id+'/DC_contact_rows')
   replayed[profile_id]={'scan':scan,'width':width,'centers':centers,'score':score}
 require(len(replayed)==54 and ownscore_matches==9,'Replay profile/origin count differs')
 geometries={(v['scan'],v['width'],tuple(int(x) for x in v['centers'])) for v in replayed.values()}
 compare(len(geometries),matrix['distinct_physical_original_box_profile_geometries'],'physical_geometry_count')
 compare(54-len(geometries),matrix['duplicate_logical_profiles_with_same_physical_geometry'],'logical_duplicate_count')
 for path,oldpin in pins.items():require(pin(Path(path))==oldpin,'Replay input changed atclose')
 cpusecs=time.process_time()-cpu;wallsecs=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 require(cpusecs<=CPU_CAP and wallsecs<=WALL_CAP and rss<=RAM_CAP,'Measured replay resourcecap exceeded')
 result={'schema':'SETI_PORTABLE_NUMPY_ONLY_CROP_REPRODUCTION_V1',
         'status':'PASS_NUMPY_ONLY54_FIXED_PROFILES48_FULLCORE_NORMALIZATIONS' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
         'scope_sha256':digest(scopepath),'code_sha256':digest(Path(__file__)),
         'counts':{'authenticated_raw_crops':48,'authenticated_rawcrop_row_SHA':rows_hashed,'fullcore501_median_positions':fullmedian_positions,
                   'fullcore_normalization_terms':48*16*4,'fixed_profiles':54,'raw503_profile_cells_verified':54*16*503,
                   'own_original_score_matches':ownscore_matches,'distinct_physical_profile_geometries':len(geometries),
                   'duplicate_logical_geometries':54-len(geometries),'comparisons':checks},
         'mismatches':mismatches,'max_absolute_errors':maxerrors,'input_pins_before_and_after':list(pins.values()),
         'CPU_seconds':cpusecs,'wall_seconds':wallsecs,'peak_RSS_bytes':rss,'runtime':{'Python':sys.version.split()[0],'numpy':np.__version__},
         'limits':scope['limits'],'HDF5_files_opened':0,'HDF5_or_hdf5plugin_imported':False,'detector_imported':False,
         'new_search_or_mask':False,'telescope_requests':0,'qualified_SETI_detection':False,
         'limitations':['This is a numerical replay using previously queried authenticated cropped spectra. Original whole-source HDF5 byte and decoded-row authentication is established by separate fullrawQA and acquisition provenance.',
                        'The saved48 normalization crops provide every raw input used by the unchanged fullcore normalization and54 fixed-score queries, without copying full telescope source files.',
                        'Original search maximization, selection completeness and significance are not reproduced. No independent repeated sky observation or false-alarm calibration follows.']}
 save_new(out,result);signal.alarm(0)
 print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins_before_and_after','runtime','limitations')}))
if __name__=='__main__':main()
