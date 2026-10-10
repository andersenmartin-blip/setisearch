#!/usr/bin/env python3
"""Prospective single-shot acquisition of fixed adjacent S2017 native170/172.

Check-only verifies metadata/code and opens no HDF5, codec or telescope values.
Execution requires exact public freeze and root GO after independent review.
"""
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import stat
import sys
import time

for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
SCANS=('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
NATIVES=(170,172)
COUNT=1048576
SOURCE_WORKERS=4
VERSIONS={'numpy':'2.3.5','scipy':'1.17.0','h5py':'3.15.1','hdf5plugin':'7.1.0'}
MEMORY_CAP=2*1024**3
BODY_CAP=640*1024**2
CPU_CAP,WALL_CAP=180,1800
WORKSPACE_CAP=8*1024**3
STAGE='analysis/s2017_next_native/results/acquire'
LOCK='analysis/s2017_next_native/ACTIVE_FAMILY_FLOCK.lock'


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for raw in iter(lambda:handle.read(1024**2),b''):h.update(raw)
    return h.hexdigest()


def save(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as handle:
        json.dump(value,handle,indent=2,allow_nan=False);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    tmp.replace(path)


def confined(root,name):
    path=root/name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and path.resolve().is_relative_to(root),'Path outside frozen workspace')
    return path


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def check_pins(root,scope):
    for name,pin in scope['pinned_metadata_and_code'].items():
        path=confined(root,name)
        require(path.stat().st_size==pin['bytes'] and digest(path)==pin['sha256'],'Frozen code/metadata changed: '+name)


def workspace_allocated(root):
    seen=set();total=0
    for base,dirs,files in os.walk(root,followlinks=False):
        for name in files:
            info=os.lstat(Path(base)/name)
            key=(info.st_dev,info.st_ino)
            if stat.S_ISREG(info.st_mode) and key not in seen:
                seen.add(key);total+=info.st_blocks*512
    return total


def directory_bytes(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def contract(root,scope):
    expected={'schema':'SETI_S2017_ADJACENT170_172_ACQUISITION_SCOPE_V1','native_chunk_indices':list(NATIVES),
        'scan_order':list(SCANS),'rows_per_scan':16,'native_chunk_count':343,'native_chunk_channels':COUNT,
        'fch1_hz':2802832031.25,'df_hz':-2.7939677238464355,'tsamp_s':18.253611008,
        'source_workers_max':SOURCE_WORKERS,'rows_serial_per_source':32,'payload_HTTP_request_cap':192,
        'payload_BODY_cap_bytes':BODY_CAP,'exact_expected_payload_BODY_bytes':597792529,
        'reserved_payload_BODY_upper_bound_bytes':597792721,'acquisition_CPU_cap_s':CPU_CAP,
        'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,'workspace_cap_bytes':WORKSPACE_CAP,
        'acquisition_artifact_cap_bytes':2*597792529+64*1024**2,'output_stage':STAGE,'family_lock_path':LOCK,
        'runtime_package_versions':VERSIONS,'hdf5_version':'1.14.6','HDF5_assembly_threads':1,
        'write_decode_interleaving':False,'expected_compact_files':12,'expected_raw_sidecars':192,
        'retry_resume_or_rerun_authorized':False,'repeated_source_GETs_authorized':0,
        'new_metadata_HTTP_requests':0,'new_spectrum_selection':False,'scientific_search_run':False,
        'original_A_B_status':'FAIL_CLOSED_UNCHANGED','qualified_sky_detection':False,'OFF_veto_applied':False,
        'calibrated_SNR_FAP':False,'cost_DKK':0}
    require(all(scope.get(k)==v for k,v in expected.items()),'Scope differs from implemented exact adjacent acquisition')
    require(digest(__file__)==scope['driver_sha256'],'Driver differs from prospective freeze')
    check_pins(root,scope)
    activation=json.loads(confined(root,scope['root_activation_path']).read_bytes())
    require(activation['acquisition_threads_max']==SOURCE_WORKERS and activation['acquisition_memory_cap_bytes']==MEMORY_CAP
        and activation['workspace_cap_bytes']==WORKSPACE_CAP and activation['new_power_GETs_max']==192
        and activation['power_BODY_bytes_exact']==597792529 and activation['power_attempts_per_exact_range']==1
        and activation['selection']['native_chunks']==list(NATIVES) and activation['source_manifest_path']==scope['source_manifest_path']
        and activation['source_manifest_sha256']==scope['pinned_metadata_and_code'][scope['source_manifest_path']]['sha256'],
        'Root activation source/resource selection differs')
    source=json.loads(confined(root,scope['source_manifest_path']).read_bytes())
    prior=json.loads(confined(root,'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json').read_bytes())
    require(source['schema']=='SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1'
        and source['status']=='PASS_EXACT192_FROZEN_SOURCE_DESCRIPTORS_METADATA_ONLY'
        and source['native_chunk_indices']==list(NATIVES) and source['scan_order']==list(SCANS)
        and source['spectral_values_read'] is False and source['spectral_payload_fetched'] is False,
        'Exact pre-adjacent-value metadata-only source manifest required')
    ranges={label:[] for label in SCANS};total=0
    for native in NATIVES:
        band=source['by_native_chunk'][str(native)];c0=native*COUNT;items=band['sources']
        require(band['native_chunk_index']==native and band['physical_channel_interval_half_open']==[c0,c0+COUNT],
            'Wrong adjacent native channel frame')
        require([x['label'] for x in items]==list(SCANS) and [x['role'].upper() for x in items]==['ON','OFF']*3,
            'Exactly six chronological source scans per native required')
        anchor=min(x['current_header']['data_attributes']['tstart'] for x in items);previous=-math.inf;subtotal=0
        for item in items:
            header=item['current_header'];attrs=header['data_attributes'];rows=item['chunks']
            require(header['dataset_shape']==[16,1,359661568] and header['dataset_chunks']==[1,1,COUNT]
                and header['dataset_dtype']=='float32' and header['dtype_exact']=='<f4'
                and len(header['hdf5_filters'])==1 and header['hdf5_filters'][0][:3]==[32008,1,[0,3,4,0,2]],
                'Source shape/dtype/filter pipeline differs')
            require(attrs['fch1']*1e6==scope['fch1_hz'] and attrs['foff']*1e6==scope['df_hz']
                and attrs['tsamp']==scope['tsamp_s'] and attrs['nchans']==359661568,'Actual source grid differs')
            require(item['url'].startswith('https://bldata.berkeley.edu/pipeline/AGBT17A_999_55/holding/')
                and re.fullmatch(r'"[^"\r\n]+"',item['etag']) and item['source_file_bytes']>0,'Exact URL/ETag/source size required')
            start=(attrs['tstart']-anchor)*86400
            require(math.isfinite(start) and start>=previous,'Actual scan times unordered or overlapping')
            previous=start+16*scope['tsamp_s']
            require(len(rows)==16 and [r['time_row'] for r in rows]==list(range(16)),'All16 source row descriptors required')
            for row in rows:
                offset,size=row['byte_offset'],row['stored_size']
                require(row['chunk_origin']==[row['time_row'],0,c0] and row['filter_mask']==0
                    and row['decoded_size']==4*COUNT and 0<size<=4*COUNT and 0<=offset<=item['source_file_bytes']-size
                    and row['byte_range']==f'bytes={offset}-{offset+size-1}','Exact payload descriptor bounds/filter/origin differ')
                ranges[item['label']].append((offset,offset+size));subtotal+=size
            require(item['future_spectral_payload_bytes']==sum(r['stored_size'] for r in rows),'Per-source payload sum stale or wrong')
        require(subtotal==band['total_future_spectral_payload_bytes'],'Per-native source BODY total differs');total+=subtotal
    for label,payloads in ranges.items():
        ordered=sorted(payloads)
        require(len(ordered)==32 and len(set(ordered))==32 and all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:])),
            '192 source ranges must be unique and disjoint')
        prioritem=next(x for x in prior['sources'] if x['label']==label)
        require(all(not (low<r['byte_offset']+r['stored_size'] and r['byte_offset']<high)
            for low,high in ordered for r in prioritem['chunks']),'Any previously opened171 source range is forbidden')
        a=source['by_native_chunk']['170']['sources'][SCANS.index(label)]
        b=source['by_native_chunk']['172']['sources'][SCANS.index(label)]
        require(all(a[k]==b[k] for k in ('url','etag','source_file_bytes','current_header')),'Native sources have different scan identity')
    require(total==source['total_future_spectral_payload_bytes']==scope['exact_expected_payload_BODY_bytes']
        and total+192==scope['reserved_payload_BODY_upper_bound_bytes']<=BODY_CAP,'Exact192-range BODY bound differs')
    for package,version in VERSIONS.items():require(importlib.metadata.version(package)==version,'Runtime package differs: '+package)
    return source


def measured(started):
    return {'process_CPU_seconds_including_imports':time.process_time(),'wall_seconds_including_imports':time.monotonic()-started,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}


def main():
    started=time.monotonic();p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','scope','expected-scope-sha256','freeze-commit'):p.add_argument('--'+name,required=True)
    p.add_argument('--check-only',action='store_true');p.add_argument('--root-go-after-review',action='store_true')
    args=p.parse_args();root=Path(args.root).resolve()
    require(re.fullmatch('[0-9a-f]{40}',args.freeze_commit),'Actual public40-hex prospective freeze required')
    require(Path(args.scope).resolve()==root/'analysis/s2017_next_native/acquire_scope.json','Scope path differs')
    require(digest(args.scope)==args.expected_scope_sha256,'Scope differs from actual public freeze')
    scope=json.loads(Path(args.scope).read_bytes());source=contract(root,scope)
    if args.check_only:
        print(json.dumps({'status':'PASS_METADATA_CODE_ONLY_NO_VALUES_NO_HTTP','scope_sha256':args.expected_scope_sha256,
            'exact192_range_BODY_bytes':scope['exact_expected_payload_BODY_bytes']}));return
    require(args.root_go_after_review,'Root GO after exact public freeze/readback and independent review required')
    allocated=workspace_allocated(root)
    require(allocated+scope['acquisition_artifact_cap_bytes']<=WORKSPACE_CAP,'Insufficient remaining8GiB unique allocated workspace cap')
    out=root/STAGE;out.mkdir(parents=True,exist_ok=False)
    receipt={'schema':'SETI_S2017_ADJACENT170_172_ACQUISITION_RECEIPT_V1','status':'IN_PROGRESS','phase':'acquire',
        'scope_sha256':args.expected_scope_sha256,'driver_sha256':digest(__file__),'public_freeze_commit':args.freeze_commit,
        'source_manifest_sha256':digest(root/scope['source_manifest_path']),'native_chunk_indices':list(NATIVES),
        'source_values_already_opened_in_prior_native171':True,'adjacent_values_previously_opened':False,
        'source_selection':'fixed+/-1 adjacent coverage around native171; prior171 results known',
        'scientific_search_run':False,'qualified_sky_detection':False,'OFF_veto_applied':False,'calibrated_SNR_FAP':False,
        'original_A_B_status':'FAIL_CLOSED_UNCHANGED','retry_resume_or_rerun_authorized':False,
        'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,'workspace_cap_bytes':WORKSPACE_CAP,
        'workspace_allocated_bytes_before':allocated,'cost_DKK':0,'limitations':scope['limitations']}
    lock_handle=None
    def deadline(signum,frame):raise TimeoutError('Frozen acquisition CPU/wall limit reached')
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    signal.alarm(max(1,int(WALL_CAP-(time.monotonic()-started))))
    try:
        lock_handle=(root/LOCK).open('a+');fcntl.flock(lock_handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(out/'INPUT_PINS.json',{'scope_sha256':args.expected_scope_sha256,'public_freeze_commit':args.freeze_commit,
            'pinned_metadata_and_code':scope['pinned_metadata_and_code']})
        save(out/'ACQUISITION_RESULT.json',receipt)
        module=load_module('s2017_adjacent_raw_acquisition',root/scope['code_paths']['acquire'])
        summary=module.acquire(sys.modules[__name__],root,scope,source,out,started,receipt)
        check_pins(root,scope);require(digest(args.scope)==args.expected_scope_sha256,'Scope changed during acquisition')
        use=measured(started);artifacts=directory_bytes(out);allocated=workspace_allocated(root)
        require(use['process_CPU_seconds_including_imports']<=CPU_CAP and use['wall_seconds_including_imports']<=WALL_CAP
            and use['peak_RSS_bytes']<=MEMORY_CAP and artifacts<=scope['acquisition_artifact_cap_bytes']
            and allocated<=WORKSPACE_CAP,'Measured resource/storage cap exceeded')
        receipt.update(summary,**use,acquisition_artifact_bytes=artifacts,workspace_allocated_bytes_after=allocated,
            status='COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY')
        ledger=json.loads((out/'SOURCE_BODY_LEDGER.json').read_bytes())
        ledger.update(complete=True,completion_resource_guard={'status':'PASS_BEFORE_COMPLETE',**use,
            'acquisition_artifact_bytes':artifacts,'workspace_allocated_bytes':allocated})
        save(out/'SOURCE_BODY_LEDGER.json',ledger);save(out/'ACQUISITION_RESULT.json',receipt)
        print(json.dumps({k:receipt[k] for k in ('status','new_telescope_HTTP_requests','new_telescope_BODY_bytes',*use)}),flush=True)
    except BaseException as error:
        receipt.update(status='INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',error_type=type(error).__name__,error=str(error),**measured(started))
        save(out/'ACQUISITION_RESULT.json',receipt);save(out/'FAILURE_RECEIPT.json',receipt);raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:lock_handle.close()

if __name__=='__main__':main()
