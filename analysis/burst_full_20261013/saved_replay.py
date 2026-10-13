"""Portable replay of saved NEW2010 burst audits; no HDF5 input or import.

scalar mode verifies all10050 saved fourrow scores conditional on authenticated
saved normalization/tuples. full_dc adds independent direct501 normalization and
unrestricted/DC-clean exhaustive maxima on18 retained DC-affected frames only.
It is a narrow arithmetic replay, not a new full-cadence source authentication,
all2010 independent remax, pilot replay, global-ranking or sky-detection test.
Numerical arrays are opened only after exact own public freeze and root GO.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'seti_burst_full'
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CHUNK, CORE, HALO = 1048576, 4096, 4000
STARTS, WIDTHS, DRIFT_COUNT = (0, 2, 4, 6, 8, 10, 12), (1, 3), 159
DC_CHANNELS = (178782208, 179830784, 180879360)
NATIVES, ON_SCANS = (170, 171, 172), ('epoch1_on', 'epoch2_on', 'epoch3_on')
PILOT_DOMAINS = tuple((n, 4 + 8*k) for n in NATIVES for k in range(32))
DOMAINS = tuple((n,q) for n in NATIVES for q in range(256)
                if (n,q) not in ((170,0),(172,255)) and (n,q) not in PILOT_DOMAINS)
JOBS = {f'full20170428_epoch{epoch}_HIP98505_shard{shard:02d}':
        (f'epoch{epoch}_on', DOMAINS[96*shard:96*(shard+1)])
        for epoch in (1,2,3) for shard in range(7)}
CPU_CAP, WALL_CAP, MEMORY_CAP, OUTPUT_CAP = 600, 900, 2*1024**3, 8*1024**2
ATOL, RTOL = 1e-7, 1e-10
QA_SOURCE_SHA256 = 'ccc7f96d079653d04df5a679af2192173a8e1281c80a3d21b995d5a3dd847cd5'
QA_HELPERS_SHA256 = '1ecf7341951a768dbd0ad5d541eaa121dd1a349aac8c7ddfc9a88049284ae53d'
HELPER_PROVENANCE = 'Exact narrow independent helpers copied from frozen qa_v2.py; no runtime import of producer, detector, QA, HDF5 or SciPy.'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()


def unique_pairs(items):
    result={}
    for key,value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key]=value
    return result


def decode(raw):
    return json.loads(raw,object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def metadata(path):
    return decode(Path(path).read_bytes())


def confined(root,name):
    part=Path(name)
    require(not part.is_absolute() and '..' not in part.parts, 'Relative safe path required')
    path=root/part
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined or symlink input')
    return path


def pin(root,path):
    return {'path':Path(path).relative_to(root).as_posix(),'bytes':Path(path).stat().st_size,'sha256':digest(path)}


def verify_pin(root,p):
    path=confined(root,p['path'])
    require(pin(root,path)==p, 'File bytepin differs: '+p['path'])
    return path


def save(path,value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        stream.flush();os.fsync(stream.fileno())


def equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b, equal_nan=True), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def independent_dual_max(z, frequencies, crop0, drift_grid, times, dc_channels,
                         fch1=FCH1, df=DF, starts=STARTS, widths=WIDTHS):
    """Own prefix/frame enumeration; only sixteen-row standardized terms input.

    No producer cache or producer numerical function is called. Both maxima
    use window/width/drift ascending and strict-greater updates. EMPTY retains
    score -inf, index/start/width -1 and valid count0.
    """
    z = np.asarray(z, dtype=np.float64)
    frequencies, drift_grid, times = [np.asarray(value, dtype=np.float64)
                                     for value in (frequencies, drift_grid, times)]
    require(z.ndim == 2 and z.shape[0] == 16 and np.isfinite(z).all(), 'Finite sixteen-row standardized terms required')
    require(frequencies.ndim == drift_grid.ndim == times.ndim == 1 and len(times) == 4
            and times[0] == 0 and np.isfinite(frequencies).all() and np.isfinite(drift_grid).all()
            and np.isfinite(times).all() and df != 0, 'Independent family input differs')
    carriers = len(frequencies)
    prefix = np.concatenate((np.zeros((16, 1), dtype=np.float64), np.cumsum(z, axis=1)), axis=1)
    def blank():
        return {'score': np.full(carriers, -np.inf, dtype=np.float64),
                'drift_grid_index': np.full(carriers, -1, dtype=np.int16),
                'window_start_row': np.full(carriers, -1, dtype=np.int16),
                'width_channels': np.full(carriers, -1, dtype=np.int16),
                'valid_hypothesis_count': np.zeros(carriers, dtype=np.int64)}
    result = {'raw': blank(), 'clean': blank()}
    base = (frequencies - fch1) / df
    dc = np.asarray(dc_channels, dtype=np.int64)
    for start in starts:
        require(0 <= start <= 12, 'Window outside sixteen rows')
        for width in widths:
            require(width in (1, 3), 'Unknown box width')
            radius = width // 2
            for di, drift in enumerate(drift_grid):
                centers = np.rint(base[:, None] + drift * times[None, :] / df).astype(np.int64)
                lower, upper = centers - crop0 - radius, centers - crop0 + radius + 1
                valid = ((lower >= 0) & (upper <= z.shape[1])).all(axis=1)
                touching = np.zeros(carriers, dtype=bool)
                for channel in dc:
                    touching |= ((centers - radius <= channel) & (centers + radius >= channel)).any(axis=1)
                terms = np.zeros(carriers, dtype=np.float64)
                for row in range(4):
                    left = np.clip(lower[:, row], 0, z.shape[1])
                    right = np.clip(upper[:, row], 0, z.shape[1])
                    terms += prefix[start + row, right] - prefix[start + row, left]
                score = terms / np.sqrt(4 * width)
                for kind, admitted in (('raw', valid), ('clean', valid & ~touching)):
                    value = result[kind]
                    value['valid_hypothesis_count'] += admitted
                    improve = admitted & (score > value['score'])
                    value['score'][improve] = score[improve]
                    value['drift_grid_index'][improve] = di
                    value['window_start_row'][improve] = start
                    value['width_channels'][improve] = width
    return result


def independent_clean_counts(frequencies, drift_grid, times):
    """Geometry-only census, independent of scores and saved winning tuples."""
    base = (frequencies - FCH1) / DF
    count = np.zeros(len(frequencies), dtype=np.int64)
    for width in WIDTHS:
        radius = width // 2
        for drift in drift_grid:
            centers = np.rint(base[:, None] + drift * times[None, :] / DF).astype(np.int64)
            touched = np.zeros(len(frequencies), dtype=bool)
            for dc in DC_CHANNELS:
                touched |= ((centers - radius <= dc) & (centers + radius >= dc)).any(axis=1)
            count += ~touched
    return count * len(STARTS)


def independent_normal(raw):
    """All4096/full16 core normalization by direct501 batched medians."""
    require(raw.shape == (16, CORE + 2 * HALO) and raw.dtype == np.dtype('<f4'), 'Raw16x12096 crop differs')
    level = np.median(raw[:, HALO:HALO + CORE].astype(np.float64), axis=1)
    residual = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        power = raw[row, HALO - 250:HALO + CORE + 250].astype(np.float64) / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(power, 501)
        for begin in range(0, CORE, 256):
            stop = min(begin + 256, CORE)
            residual[row, begin:stop] = power[250 + begin:250 + stop] - np.median(windows[begin:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    require(np.all(level > 0) and np.all(scale > 0), 'Independent normalization scales invalid')
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def independent_standardized_region(raw, normal, margin=81):
    """Standardized terms on core±81 channels, direct501 median arithmetic."""
    length = CORE + 2 * margin
    result = np.empty((16, length), dtype=np.float64)
    for row in range(16):
        power = raw[row, HALO - margin - 250:HALO + CORE + margin + 250].astype(np.float64) / normal['row_power_median'][row]
        windows = np.lib.stride_tricks.sliding_window_view(power, 501)
        for begin in range(0, length, 256):
            stop = min(begin + 256, length)
            medians = np.median(windows[begin:stop], axis=1)
            result[row, begin:stop] = (power[250 + begin:250 + stop] - medians -
                                       normal['row_winsorized_residual_location'][row]) / normal['row_residual_MAD_scale'][row]
    return result


def scalar_rows(raw, normal, width, absolute_rows):
    require(raw.shape == (4, 503) and raw.dtype == np.dtype('<f4') and width in WIDTHS, 'Raw503 query differs')
    ratio = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[absolute_rows, None]
    columns = list(range(251 - width // 2, 252 + width // 2))
    median = np.column_stack([np.median(ratio[:, c - 250:c + 251], axis=1) for c in columns])
    standardized = (ratio[:, columns] - median - np.asarray(normal['row_winsorized_residual_location'])[absolute_rows, None]) / np.asarray(normal['row_residual_MAD_scale'])[absolute_rows, None]
    rows = standardized.sum(axis=1)
    return rows, float(rows.sum() / np.sqrt(4 * width))


def prepare(root,args):
    # All inputs in preparation are code or JSON. NPZ bytes are declared by
    # original complete receipts and the independently completed source QA.
    code_freeze_path=confined(root,BASE+'/REPLAY_CODE_FREEZE.json')
    require(args.code_freeze_sha256 and digest(code_freeze_path)==args.code_freeze_sha256,
            'Exact source-only replay code freeze required before reading result metadata')
    code_freeze=metadata(code_freeze_path)
    require(code_freeze['status']=='PASS_PUBLIC_FREEZE_SAVED_REPLAY_CODE_READBACK'
            and code_freeze['replay_sha256']==digest(Path(__file__).resolve())
            and code_freeze['package_sha256']==digest(root/BASE/'package_replay.py')
            and re.fullmatch('[0-9a-f]{40}',code_freeze['public_commit']), 'Replay code freeze differs')
    go_path=confined(root,BASE+'/REPLAY_PREPARE_GO.json')
    require(args.prepare_go_sha256 and digest(go_path)==args.prepare_go_sha256, 'Exact root metadata-preparation GO required')
    go=metadata(go_path)
    require(go['status']=='GO_PREPARE_FULL_SAVED_DATA_REPLAY_METADATA_ONLY'
            and go['replay_sha256']==code_freeze['replay_sha256']
            and go['code_freeze_sha256']==args.code_freeze_sha256, 'Replay preparation GO differs')
    scope_path=confined(root,BASE+'/SCOPE.json')
    source_scope=metadata(scope_path)
    require(source_scope['new_maps']==2010 and set(source_scope['jobs'])==set(JOBS), 'Original full scope differs')
    qa_path=confined(root,args.main_qa_receipt)
    require(args.main_qa_receipt_sha256 and digest(qa_path)==args.main_qa_receipt_sha256
            and go['main_qa_receipt_sha256']==args.main_qa_receipt_sha256, 'Exact independent main-QA receipt required')
    qa=metadata(qa_path)
    require(qa['status']=='PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY'
            and qa['qa_sha256']==QA_SOURCE_SHA256
            and qa['counts']['scalar_queries']==10050 and qa['counts']['independent_dual_remax_cores']==18
            and qa['counts']['clean_EMPTY_carriers']==9, 'Original independent full-source QA not PASS')
    files={};roles={};jobs=[];scalar=set();full=set()
    def add(p,role,required_scalar=False,required_full=False):
        name=p['path']
        require(Path(name).suffix in ('.py','.json','.md','.txt','.npz') and not name.endswith('.h5'),
                'Replay closure permits no telescope HDF5 files')
        require(name not in files or files[name]==p, 'Conflicting closure pin')
        files[name]=p;roles.setdefault(name,set()).add(role)
        if required_scalar:scalar.add(name)
        if required_scalar or required_full:full.add(name)
    def add_text(path,role,required=True):
        p=pin(root,path);add(p,role,required,required);return p
    for p in source_scope['text_code_pins']:
        require(Path(p['path']).suffix!='.npz', 'Scope text closure unexpectedly numerical')
        verify_pin(root,p);add(p,'original_source_or_pilot_text',True)
    source_scope_pin=add_text(scope_path,'original_primary_scope')
    main_qa_pin=add_text(qa_path,'original_independent_source_QA')
    for name in ('driver.py','prepare_scope.py','ROOT_GO.json','freeze.json','qa_v2.py',
                 'test_qa_synthetic_v2.py','SYNTHETIC_V2_RECEIPT.json','QA_V2_FREEZE.json',
                 'QA_V2_SCIENCE_STATIC_REVIEW.json','SCIENCE_SCOPE_REVIEW.json','QA_ROOT_GO.json'):
        add_text(confined(root,BASE+'/'+name),'original_primary_QA_admission')
    for name in ('saved_replay.py','package_replay.py','REPLAY_REQUIREMENTS.txt','REPLAY_README.md',
                 'REPLAY_CODE_FREEZE.json','REPLAY_PREPARE_GO.json'):
        add_text(confined(root,BASE+'/'+name),'portable_replay_source_admission')
    for job,(scan,domains) in JOBS.items():
        parent=BASE+'/results/'+job
        rp=confined(root,parent+'/EXECUTION_RECEIPT.json')
        r=metadata(rp)
        require(r['status']=='COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY'
                and r['primary_id']==job and r['scan_id']==scan
                and r['scope_sha256']==source_scope_pin['sha256']
                and r['counts']==source_scope['jobs'][job]['expected_counts']
                and qa['primary_receipt_sha256s'][job]==digest(rp), 'Complete shard/QA receipt binding differs')
        inventory={p['path']:p for p in r['output_byte_pins']}
        require(len(inventory)==len(r['output_byte_pins'])==r['counts']['expected_output_files_including_receipt']-1,
                'Original output closure census differs')
        audit_pin=inventory[parent+'/SCORE_AUDITS.json'];map_pin=inventory[parent+'/MAPS.json']
        verify_pin(root,audit_pin);verify_pin(root,map_pin)
        audit=metadata(root/audit_pin['path']);maps=metadata(root/map_pin['path'])
        require(len(maps['records'])==len(domains) and len(audit['records'])==len(domains)*5
                and [(m['native_chunk_index'],m['core_q']) for m in maps['records']]==list(domains),
                'Shard metadata ordered maps/audits differs')
        for p in inventory.values():
            require(p['path'].startswith(parent+'/') and Path(p['path']).suffix in ('.json','.npz'), 'Output outside shard namespace')
            original=qa['input_byte_pins'].get(p['path'])
            require(original=={k:p[k] for k in ('bytes','sha256')}, 'Main-QA did not bind this original output')
            add(p,'new2010_producer_output')
        add_text(rp,'completed_primary_receipt')
        add(map_pin,'map_manifest',True);add(audit_pin,'scalar_audit_manifest',True)
        for m in maps['records']:
            add(m['normalization'],'saved_full16_normalization',True)
            if m['DC_affected_core']:
                require(m['core_q'] in (127,128), 'DC crop outside q127/128')
                add({k:m[k] for k in ('path','bytes','sha256')},'DC_dual_winner_map',False,True)
                add(m['DC_full_raw_core_crop'],'retained_DC_raw16_frame',False,True)
        for a in audit['records']:
            add(a['capsule'],'retained_raw4_scalar_capsule',True)
        jobs.append({'job':job,'scan_id':scan,'domains':[list(x) for x in domains],
                     'receipt':pin(root,rp),'map_manifest':map_pin,'audit_manifest':audit_pin})
    require(len([n for n in roles if 'retained_raw4_scalar_capsule' in roles[n]])==10050
            and len([n for n in roles if 'retained_DC_raw16_frame' in roles[n]])==18, 'Replay payload census differs')
    replay_scope={'schema':'SETI_NEW2010_PORTABLE_SAVED_REPLAY_SCOPE_V1','status':'READY_SAVED_DATA_REPLAY',
        'jobs':jobs,'file_pins':[files[n] for n in sorted(files)],'file_roles':{n:sorted(roles[n]) for n in sorted(roles)},
        'required_members':{'scalar':sorted(scalar),'full_dc':sorted(full)},
        'required_bytes':{'scalar':sum(files[n]['bytes'] for n in scalar),'full_dc':sum(files[n]['bytes'] for n in full)},
        'complete_new2010_closure_bytes':sum(p['bytes'] for p in files.values()),
        'primary_scope_pin':source_scope_pin,'independent_main_QA_receipt_pin':main_qa_pin,
        'replay_sha256':digest(Path(__file__).resolve()),'package_sha256':digest(root/BASE/'package_replay.py'),
        'qa_helper_source_sha256':QA_SOURCE_SHA256,'qa_helper_block_sha256':QA_HELPERS_SHA256,
        'arithmetic_provenance':HELPER_PROVENANCE,
        'authenticated_source_compacts_not_in_bundle':source_scope['source_compacts'],
        'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,'output_cap_bytes':OUTPUT_CAP,
        'expected_scalar_queries':10050,'expected_scalar_power_cells':10050*4*503,
        'expected_full_DC_cores':18,'expected_full_DC_EMPTY':9,
        'source_HDF5_files_read':False,'all2010_grids_independently_remaximized':False,
        'new_telescope_HTTP_requests':0,'qualified_SETI_detection':False,'calibrated_SNR_FAP':False,
        'limitations':['Offline scalar replay is conditional on saved normalization and previously authenticated selected tuples.',
                       'Only18 DC frames independently reproduce normalization and full original dual family.',
                       'Original telescope rows/HDF5 bits are attested by pinned main QA; this replay does not read or reauthenticate them.',
                       'New2010 only. Pilot288/global-ranking/context payloads require the extended full delivery package.']}
    path=confined(root,BASE+'/REPLAY_SCOPE.json');save(path,replay_scope)
    print(json.dumps({'status':'PASS_METADATA_ONLY_REPLAY_SCOPE','scope':pin(root,path),
                      'required_bytes':replay_scope['required_bytes'],'closure_bytes':replay_scope['complete_new2010_closure_bytes']}))


def execute(root,args):
    started,cpu0=time.monotonic(),time.process_time()
    scope_path=confined(root,BASE+'/REPLAY_SCOPE.json')
    require(args.scope_sha256 and digest(scope_path)==args.scope_sha256, 'Exact replay scope SHA required')
    scope=metadata(scope_path)
    require(scope['schema']=='SETI_NEW2010_PORTABLE_SAVED_REPLAY_SCOPE_V1'
            and scope['replay_sha256']==digest(Path(__file__).resolve()), 'Replay source/scope differs')
    freeze_path=confined(root,BASE+'/REPLAY_FREEZE.json')
    require(args.freeze_sha256 and digest(freeze_path)==args.freeze_sha256, 'Exact public saved-replay scope freeze required')
    freeze=metadata(freeze_path)
    require(freeze['status']=='PASS_PUBLIC_FREEZE_SAVED_REPLAY_SCOPE_READBACK'
            and freeze['scope_sha256']==args.scope_sha256 and freeze['replay_sha256']==scope['replay_sha256']
            and re.fullmatch('[0-9a-f]{40}',freeze['public_commit']), 'Replay public freeze identity differs')
    go_path=confined(root,args.root_go)
    require(args.root_go_sha256 and digest(go_path)==args.root_go_sha256,'Exact separate replay root GO required')
    go=metadata(go_path)
    require(go['status']=='GO_SAVED_REPLAY_'+args.mode.upper() and go['mode']==args.mode
            and go['scope_sha256']==args.scope_sha256 and go['replay_sha256']==scope['replay_sha256']
            and go['freeze_sha256']==args.freeze_sha256
            and (go['CPU_cap_s'],go['wall_cap_s'],go['memory_cap_bytes'],go['output_cap_bytes'])
                ==(CPU_CAP,WALL_CAP,MEMORY_CAP,OUTPUT_CAP), 'Replay scientific/resource GO differs')
    expected={p['path']:p for p in scope['file_pins']}
    require(len(expected)==len(scope['file_pins']), 'Duplicate closure names')
    names=scope['required_members'][args.mode]
    require(all(n in expected for n in names) and len(names)==len(set(names)), 'Required subset differs')
    for name in names:verify_pin(root,expected[name])
    locks=[];out=confined(root,args.output)
    require(out.resolve().is_relative_to(root/BASE) and not out.exists(), 'New namespace/output required; no overwrite')
    def alarm(signum,frame):raise TimeoutError('Saved replay resource cap')
    signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGXCPU,alarm)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        lock=(root/BASE/'SAVED_REPLAY.lock').open('a+b');locks.append(lock);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        out.mkdir(exist_ok=False)
        global np
        import numpy as np
        require(np.__version__=='2.3.5','Exact portable NumPy2.3.5 dependency required')
        def archive(p):
            require(p['path'] in names, 'NPZ outside declared replay subset')
            raw=verify_pin(root,p).read_bytes()
            with np.load(io.BytesIO(raw),allow_pickle=False) as values:
                require(len(values.files)==len(set(values.files)), 'Duplicate NPZ member')
                return {k:values[k] for k in values.files}
        count=0;cells=0;dc_count=0;empty_count=0;max_row=max_score=max_norm=max_dual=0.
        drifts,times=np.linspace(-4.,4.,159),np.arange(4)*TSAMP
        normal_fields={'row_power_median','row_residual_median','row_winsorized_residual_location',
                       'row_residual_MAD_scale','normalization_unmasked_counts','normalization_source_channel_interval_half_open'}
        dc_reports=[]
        for jd in scope['jobs']:
            job,scan=jd['job'],jd['scan_id']
            m=metadata(verify_pin(root,jd['map_manifest']));a=metadata(verify_pin(root,jd['audit_manifest']))
            maps={(r['native_chunk_index'],r['core_q']):r for r in m['records']}
            normal={};dc_frames={}
            for key,record in maps.items():
                n,q=key;core0=n*CHUNK+q*CORE
                norm=metadata(verify_pin(root,record['normalization']))
                require(set(norm)==normal_fields,'Normalization schema differs')
                equal(norm['normalization_source_channel_interval_half_open'],[core0,core0+CORE],'Static normalization coordinates differ')
                equal(norm['normalization_unmasked_counts'],np.full(16,CORE),'Normalization counts differ')
                for field in normal_fields-{'normalization_unmasked_counts','normalization_source_channel_interval_half_open'}:
                    require(np.asarray(norm[field]).shape==(16,) and np.isfinite(norm[field]).all(),'Normalization finite shape differs')
                require(np.min(norm['row_power_median'])>0 and np.min(norm['row_residual_MAD_scale'])>0,'Normalization scales invalid')
                normal[key]=norm
                if args.mode=='full_dc' and record['DC_affected_core']:
                    rawframe=archive(record['DC_full_raw_core_crop'])
                    require(set(rawframe)=={'raw_power_full16x12096','absolute_time_rows','source_channel_interval_half_open'},'DC crop members differ')
                    equal(rawframe['absolute_time_rows'],np.arange(16,dtype=np.int64),'DC full rows differ')
                    equal(rawframe['source_channel_interval_half_open'],[core0-HALO,core0+CORE+HALO],'DC full support differs')
                    raw=rawframe['raw_power_full16x12096']
                    require(raw.shape==(16,12096) and raw.dtype==np.dtype('<f4') and np.isfinite(raw).all() and (raw>=0).all(),'DC frame finite raw schema differs')
                    dc_frames[key]=raw
                    independent=independent_normal(raw)
                    for field,v in independent.items():
                        near(norm[field],v,'Independent saved-frame full501 normalization differs')
                        max_norm=max(max_norm,float(np.max(np.abs(np.asarray(norm[field])-v))))
                    value=archive({k:record[k] for k in ('path','bytes','sha256')})
                    equal(value['source_reference_channels'],np.arange(core0,core0+CORE,dtype=np.int64),'DC map carrier coordinates differ')
                    equal(value['frequency_hz_at_window_reference'],FCH1+DF*value['source_reference_channels'],'DC frequency coordinates differ')
                    equal(value['drift_grid_hz_s'],drifts,'DC drift grid differs')
                    z=independent_standardized_region(raw,independent)
                    winners=independent_dual_max(z,value['frequency_hz_at_window_reference'],core0-81,drifts,times,DC_CHANNELS)
                    for kind,prefix in (('raw',''),('clean','DC_clean_')):
                        w=winners[kind];valid=w['valid_hypothesis_count']>0
                        near(value[prefix+'maximum_robust_box_track_score'][valid],w['score'][valid],'Saved DC exhaustive maximum score differs')
                        max_dual=max(max_dual,float(np.max(np.abs(value[prefix+'maximum_robust_box_track_score'][valid]-w['score'][valid]))))
                        for sf,wf in (('winning_drift_grid_index','drift_grid_index'),('winning_window_start_row','window_start_row'),
                                      ('winning_width_channels','width_channels'),('valid_hypothesis_count','valid_hypothesis_count')):
                            equal(value[prefix+sf],w[wf],'Saved DC exhaustive winning tuple/count differs')
                        require(np.isneginf(value[prefix+'maximum_robust_box_track_score'][~valid]).all()
                                and np.isnan(value[prefix+'winning_drift_hz_s'][~valid]).all(),'Saved DC EMPTY score/drift differs')
                        equal(value[prefix+'winning_drift_hz_s'][valid],drifts[w['drift_grid_index'][valid]],'Saved DC winning drift differs')
                    dc_count+=1;empty_count+=int((winners['clean']['valid_hypothesis_count']==0).sum())
                    dc_reports.append({'scan_id':scan,'native_chunk_index':n,'core_q':q,'dual_carrier_winners_verified':CORE,
                                       'clean_EMPTY':int((winners['clean']['valid_hypothesis_count']==0).sum())})
            expected_queries={(n,q,k) for n,q in maps for k in ('first','midpoint','last','core_max','clean_core_max')}
            seen=set()
            for query in a['records']:
                key=(query['native_chunk_index'],query['core_q']);kind=query['query_kind'];identity=key+(kind,)
                require(identity in expected_queries and identity not in seen,'Scalar query census/duplicate differs');seen.add(identity)
                t=query['selected_tuple'];width=t['width_channels'];start=t['window_start_row']
                require(t['primary_id']==job and t['scan_id']==scan and t['winner_kind']==query['winner_kind']
                        and query['winner_kind']==('DC_clean' if kind=='clean_core_max' else 'unrestricted')
                        and width in WIDTHS and start in STARTS and 0<=t['carrier_index_in_core']<CORE
                        and t['window_source_rows']==list(range(start,start+4))
                        and query['normalization']==maps[key]['normalization'],'Scalar saved tuple identity differs')
                channel=key[0]*CHUNK+key[1]*CORE+t['carrier_index_in_core']
                require(t['source_reference_channel']==channel and t['frequency_hz_at_window_reference']==FCH1+DF*channel
                        and t['drift_hz_s']==float(drifts[t['drift_grid_index']]),'Scalar saved source/grid identity differs')
                centers=np.rint((t['frequency_hz_at_window_reference']-FCH1)/DF+t['drift_hz_s']*times/DF).astype(np.int64)
                equal(t['rounded_absolute_centers'],centers,'Tuple rounded trajectory differs')
                equal(t['width_box_source_channels_inclusive'],np.column_stack((centers-width//2,centers+width//2)),'Tuple inclusive support differs')
                touched=np.column_stack([np.abs(centers-dc)<=width//2 for dc in DC_CHANNELS])
                require(t['eligible_DC_untouched']==bool(not touched.any())
                        and (query['winner_kind']!='DC_clean' or not touched.any()),'Scalar saved clean eligibility differs')
                capsule=archive(query['capsule'])
                require(set(capsule)=={'raw_power','absolute_time_rows','rounded_absolute_centers','standardized_row_box_sums'},'Scalar capsule schema differs')
                raw=capsule['raw_power'];rows=np.arange(start,start+4,dtype=np.int64)
                require(raw.dtype==np.dtype('<f4') and raw.shape==(4,503) and np.isfinite(raw).all() and (raw>=0).all(),'Finite raw503 payload differs')
                equal(capsule['absolute_time_rows'],rows,'Scalar absolute rows differ')
                equal(capsule['rounded_absolute_centers'],centers,'Scalar rounded centers differ')
                if key in dc_frames:
                    crop0=key[0]*CHUNK+key[1]*CORE-HALO
                    indexes=centers[:,None]-crop0+np.arange(-251,252)[None,:]
                    require(indexes.min()>=0 and indexes.max()<12096,'DC scalar support leaves retained frame')
                    equal(raw.view(np.uint32),dc_frames[key][rows[:,None],indexes].view(np.uint32),
                          'DC scalar capsule float32 bits differ from independent retained full frame')
                terms,score=scalar_rows(raw,normal[key],width,rows)
                near(capsule['standardized_row_box_sums'],terms,'Direct501 scalar row sums differ')
                near(t['score'],score,'Direct501 scalar queried score differs')
                max_row=max(max_row,float(np.max(np.abs(capsule['standardized_row_box_sums']-terms))))
                max_score=max(max_score,abs(t['score']-score));count+=1;cells+=4*503
            require(seen==expected_queries,'Every five/core scalar position required')
            print(json.dumps({'job':job,'completed_scalar_queries':count,'DC_cores':dc_count}),flush=True)
        require(count==10050 and cells==10050*4*503,'Exact10050 scalar query/cell count differs')
        require((dc_count,empty_count)==((18,9) if args.mode=='full_dc' else (0,0)),'Full/scalar DC census differs')
        for name in names:verify_pin(root,expected[name])
        require(digest(scope_path)==args.scope_sha256 and digest(freeze_path)==args.freeze_sha256
                and digest(go_path)==args.root_go_sha256
                and digest(Path(__file__).resolve())==scope['replay_sha256'],
                'Saved replay code/scope/freeze/root GO changed during execution')
        usage={'process_CPU_seconds':time.process_time()-cpu0,'wall_seconds':time.monotonic()-started,
               'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        require(usage['process_CPU_seconds']<=CPU_CAP and usage['wall_seconds']<=WALL_CAP and usage['peak_RSS_bytes']<=MEMORY_CAP,'Saved replay measured cap exceeded')
        receipt={'schema':'SETI_NEW2010_PORTABLE_SAVED_REPLAY_RECEIPT_V1',
            'status':'PASS10050_SAVED_SCALAR_SCORES'+('_18_DC_FRAME_DUAL_REMAX9_EMPTY' if args.mode=='full_dc' else ''),
            'mode':args.mode,'scope_sha256':args.scope_sha256,'replay_sha256':scope['replay_sha256'],
            'public_freeze_sha256':args.freeze_sha256,'root_go_sha256':args.root_go_sha256,
            'scalar_queries':count,'scalar_power_cells':cells,'independent_saved_DC_frames':dc_count,
            'DC_clean_EMPTY_carriers':empty_count,'DC_reports':dc_reports,
            'max_row_absolute_difference':max_row,'max_scalar_score_absolute_difference':max_score,
            'max_full501_normalization_absolute_difference':max_norm,'max_dual_maximum_score_absolute_difference':max_dual,
            'verified_required_file_pins':[expected[n] for n in names],**usage,
            'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,'output_cap_bytes':OUTPUT_CAP,
            'numpy_version':np.__version__,'source_HDF5_files_read':False,'HDF5_runtime_imported':False,
            'all2010_grids_independently_remaximized':False,'pilot288_replayed':False,
            'new_telescope_HTTP_requests':0,'qualified_SETI_detection':False,'calibrated_SNR_FAP':False,
            'limitations':scope['limitations']}
        require(len((json.dumps(receipt)+'\n').encode())<OUTPUT_CAP,'Saved replay receipt budget exceeded')
        save(out/'REPLAY_RECEIPT.json',receipt);print(receipt['status'],flush=True)
    except BaseException as exc:
        if out.exists() and not (out/'REPLAY_RECEIPT.json').exists():
            save(out/'REPLAY_FAILURE.json',{'status':'FAIL_SAVED_REPLAY_PRESERVED_NO_RETRY','failure_type':type(exc).__name__,'failure':str(exc)})
        raise
    finally:
        signal.alarm(0)
        for lock in reversed(locks):lock.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--check-only',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--mode',choices=('scalar','full_dc'),default='scalar')
    p.add_argument('--output',default=BASE+'/saved_replay_results')
    p.add_argument('--root-go',default=BASE+'/REPLAY_ROOT_GO.json')
    p.add_argument('--main-qa-receipt',default=BASE+'/qa_results/QA_RECEIPT.json')
    for name in ('code-freeze-sha256','prepare-go-sha256','main-qa-receipt-sha256','scope-sha256','freeze-sha256','root-go-sha256'):
        p.add_argument('--'+name)
    args=p.parse_args();root=args.root.resolve()
    if args.check_only:
        require(len(JOBS)==21 and len(DOMAINS)==670,'Saved replay declared census differs')
        print(json.dumps({'status':'PASS_SOURCE_ONLY_NUMPY_SAVED_REPLAY_INTERFACE','scalar_queries':10050,'full_DC_frames':18,
                          'numerical_modules_imported':False,'source_HDF5_files_read':False,
                          'runtime_dependencies':['Python3.12','numpy==2.3.5'],
                          'qa_source_sha256':QA_SOURCE_SHA256,'qa_helper_block_sha256':QA_HELPERS_SHA256}));return
    require(args.prepare!=args.run,'Exactly prepare or run required')
    if args.prepare:prepare(root,args)
    else:execute(root,args)


if __name__=='__main__':main()
