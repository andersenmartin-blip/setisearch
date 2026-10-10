#!/usr/bin/env python3
"""One new, bounded fixed-profile family. No detector/search/preprocessing calls."""
import argparse
import importlib.metadata
import sys
from profile_contract import *


def profile_kernel(np, raw, row_medians, width):
    """Pure ndarray kernel: the original fixed_profiles measurement arithmetic."""
    offsets = np.arange(-64,65)
    flank = np.abs(offsets)>3
    normalized = raw.astype(np.float64)/row_medians[:,None]
    baseline = np.median(normalized[:,flank],axis=1)
    radius = width//2
    center = normalized[:,64-radius:65+radius].mean(axis=1)
    residual = center-baseline
    mean_profile = np.mean(normalized-baseline[:,None],axis=0)
    return {'center':center,'flank':baseline,'residual':residual,
        'raw_width_mean':raw[:,64-radius:65+radius].mean(axis=1),
        'mean_raw':raw.mean(axis=0),'mean_normalized':normalized.mean(axis=0),
        'mean_residual':mean_profile}


def derive_geometry(np, members, headers, oldgeo):
    anchor=min(h['tstart'] for h in headers.values())
    offsets=np.arange(-64,65)
    grid=np.linspace(-4.0,4.0,785)
    times=np.empty((1905,6,16),dtype='<f8')
    mapping=np.empty((1905,6),dtype='<i4')
    unique=[]; cache={}
    for j,member in enumerate(members):
        m=member['original_member']; k=m['original_key']
        ref=(headers[k['scan_id']]['tstart']-anchor)*86400+.5*TSAMP
        require(float_bits(ref)==float_bits(k['reference_seconds_from_anchor']), 'Original ON reference differs')
        require(1<=m['core_q']<=254 and k['source_reference_channel']//CORE==C0//CORE+m['core_q']
            and k['width_channels'] in (1,3) and 0<=k['drift_grid_index']<785
            and float_bits(grid[k['drift_grid_index']])==float_bits(k['drift_hz_s'])
            and float_bits(FCH1+k['source_reference_channel']*DF)==float_bits(m['original_reference_frequency_hz']),
            'Original selected hypothesis/channel/grid differs')
        dt=np.asarray([(headers[s]['tstart']-anchor)*86400+(np.arange(16)+.5)*TSAMP
            - k['reference_seconds_from_anchor'] for s in SCANS])
        base=(m['original_reference_frequency_hz']-FCH1)/DF
        centers=np.rint(base+k['drift_hz_s']*dt/DF).astype(np.int64)
        require(centers.min()-64>=C0 and centers.max()+64<C0+COUNT, 'Frozen profile exceeds retained chunk')
        times[j]=dt
        for i,scan in enumerate(SCANS):
            key=(scan,k['width_channels'],tuple(int(c) for c in centers[i]))
            require(key not in oldgeo, 'An old saved scan profile geometry would be remeasured')
            if key not in cache:
                cache[key]=len(unique);unique.append(key)
            mapping[j,i]=cache[key]
    require(len(unique)==11369 and mapping.size-len(unique)==61, '11369 geometries/61 aliases differ')
    serial=[[scan,width,list(cs)] for scan,width,cs in unique]
    geometry_sha=hashlib.sha256(json.dumps(serial,separators=(',',':')).encode()).hexdigest()
    return unique,mapping,times,float(anchor),geometry_sha


def summary_metrics(np, residual):
    first=float(residual[:8].mean());last=float(residual[8:].mean())
    return {'mean':float(residual.mean()),'median':float(np.median(residual)),
        'positive_rows':int(np.count_nonzero(residual>0)), 'first_eight_mean':first,
        'last_eight_mean':last,'minimum_half_mean':min(first,last)}


def load_contract(args):
    scope=read_json(args.scope,args.expected_scope_sha256)
    require(scope['schema']==SCHEMA and scope['family_id']==FAMILY
        and scope['script_sha256']==digest(__file__), 'Profile source/scope differs')
    expected={'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,
        'output_reservation_bytes':OUTPUT_CAP,'shared_workspace_cap_bytes':WORKSPACE_CAP,
        'selected_triples':635,'selected_members':1905,'logical_scan_profiles':11430,
        'logical_time_rows':182880,'unique_geometries':11369,'new_geometry_aliases':61,
        'old_geometry_aliases':0,'old_saved_profiles':54,'old_saved_geometries':312,'excluded_match_id':EXCLUDED,'source_channel0':C0,
        'source_chunk_channel_count':COUNT,'profile_offset_interval_inclusive':[-64,64],
        'flank_rule':'abs(offset)>3;122channels','retry_resume_or_rerun_authorized':False}
    require(all(scope.get(k)==v for k,v in expected.items()),'Scope measurement/budget differs')
    require(args.root_go_after_profile_freeze and re.fullmatch(r'[0-9a-f]{40}',args.freeze_commit), 'Actual root freeze/GO required')
    require(scope['admission_pin']['sha256']==args.expected_admission_sha256,'Admission CLI differs')
    pins=scope['pinned_metadata_files']+scope['pinned_dependency_files']
    for p in pins:verify_pin(p)
    admission=pinned_json(scope['admission_pin'])
    require(admission['schema']=='SETI_S2017_CROSS_ON_PROFILES_ROOT_ADMISSION_V1'
        and admission['status']=='PASS_CLOSED_DURABLE_MATCHED_SOURCE_NO_DUPLICATE_PROFILE_PHASE'
        and all(admission.get(k) is True for k in ('all_original171_numeric_QA_processes_closed',
            'matching_numeric_and_output_QA_processes_closed','durable_source_RAW_and_RESULTS_verified',
            'durable_matching_RESULTS_verified','fresh_duplicate_registry_no_profile_phase','profiles_not_previously_measured')),
        'Closed/durable/nonduplicate profile admission required')
    require(admission['source_root']==scope['source_root'] and admission['shared_workspace_roots']==scope['shared_workspace_roots'],
        'Admission paths differ')
    for p in admission['proof_pins']:verify_pin(p)
    roots=[Path(x) for x in scope['shared_workspace_roots']]
    for p in (Path(scope['source_root']),Path(scope['output_directory']).parent,Path(__file__),Path(args.scope)):
        require(p.is_absolute() and p.resolve()==p and any(p==r or r in p.parents for r in roots), 'Disk roots omit source/output/code')
    require(tree_size(scope['shared_workspace_roots'])+OUTPUT_CAP<=WORKSPACE_CAP, 'Fresh shared12GiB gate with128MiB reservation fails')
    free=os.statvfs(Path(scope['output_directory']).parent)
    require(free.f_bavail*free.f_frsize>=OUTPUT_CAP,'Physical free space below128MiB reservation')
    verify_no_live_owner_processes(scope)
    source=pinned_json(scope['source_pin']);norm=pinned_json(scope['normalization_pin'])
    require(scope['source_pin']['sha256']==SOURCE_SHA and scope['normalization_pin']['sha256']==NORM_SHA
        and norm['source_channel0']==C0 and norm['count']==COUNT and norm['raw_dtype']=='<f4', 'Canonical source/denominator differs')
    require(set(norm['row_power_medians'])==set(SCANS)
        and all(len(v)==16 and all(math.isfinite(x) and x>0 for x in v) for v in norm['row_power_medians'].values()),
        'All96 finite positive stored denominators required')
    members=selected_members(pinned_json(scope['matching_TOP_pin']))
    require(selection_sha(members)==scope['selected_members_sha256'], 'Frozen member metadata changed')
    oldkeys,oldgeo=old_geometries([pinned_json(p) for p in scope['old_profile_pins']])
    for m in members:
        k=m['original_member']['original_key']
        require((k['scan_id'],k['source_reference_channel'],float_bits(k['reference_seconds_from_anchor']),
            float_bits(k['drift_hz_s']),k['width_channels']) not in oldkeys,'Old member hypothesis admitted')
    return scope,pins,admission,source,norm,members,oldgeo


def compute(np,h5py,scope,source,norm,members,oldgeo,out,start_cpu,start_wall):
    headers={x['label']:x['current_header']['data_attributes'] for x in source['sources']}
    unique,mapping,times,anchor,gsha=derive_geometry(np,members,headers,oldgeo)
    require(gsha==scope['ordered_geometry_sha256'], 'Frozen ordered geometry digest differs')
    ng=len(unique);offsets=np.arange(-64,65)
    centers=np.asarray([x[2] for x in unique],dtype='<i8')
    scans=np.asarray([SCANS.index(x[0]) for x in unique],dtype='<i2')
    widths=np.asarray([x[1] for x in unique],dtype='<i2')
    raw=np.empty((ng,16,129),dtype='<f4')
    verified=[]
    for si,scan in enumerate(SCANS):
        rec=next(x for x in scope['compact_records'] if x['scan_id']==scan)
        identity=next(x for x in source['sources'] if x['label']==scan)
        group=np.flatnonzero(scans==si)
        with h5py.File(rec['file_pin']['path'],'r',rdcc_nbytes=8*1024**2) as handle:
            data=handle['data']
            require(data.shape==(16,1,COUNT) and data.dtype.str=='<f4'
                and int(data.attrs['original_source_frequency_chunk_origin'])==C0
                and data.attrs['original_source_url']==identity['url'] and data.attrs['original_source_etag']==identity['etag'],
                'Compact source dataset/attributes differ')
            for row,rp in enumerate(rec['decoded_rows']):
                values=data[row,0,:]
                require(values.dtype.str=='<f4' and values.shape==(COUNT,)
                    and rp['time_row']==row and rp['decoded_bytes']==COUNT*4
                    and hashlib.sha256(values.tobytes(order='C')).hexdigest()==rp['decoded_sha256']
                    and np.isfinite(values).all() and (values>=0).all(),'Authenticated native source row differs')
                indices=centers[group,row,None]-C0+offsets[None,:]
                raw[group,row,:]=values[indices]
                del values,indices
        verified.append({'scan_id':scan,'file_sha256':rec['file_pin']['sha256'],'decoded_rows_verified':16})
        save_atomic(out/'PROFILE_CHECKPOINT.json',{'family_id':FAMILY,'complete':False,
            'source_scans_loaded':list(SCANS[:si+1]),'unique_geometries':ng,'profiles_measured':0})
        enforce_usage(start_cpu,start_wall)
    arrays={'logical_geometry_indices':mapping,'logical_times_seconds_from_original_reference':times,
        'geometry_source_channel_centers':centers,'geometry_scan_indices':scans,'geometry_width_channels':widths,
        'source_channel_offsets':offsets.astype('<i8'),'scans':np.asarray(SCANS),
        'saved_full_native_row_medians':np.asarray([norm['row_power_medians'][s] for s in SCANS],dtype='<f8'),
        'geometry_center_row_normalized_power':np.empty((ng,16),dtype='<f8'),
        'geometry_flank_median_row_normalized_power':np.empty((ng,16),dtype='<f8'),
        'geometry_center_minus_flank_rows':np.empty((ng,16),dtype='<f8'),
        'geometry_raw_width_mean_power':np.empty((ng,16),dtype='<f4'),
        'geometry_mean_raw_frequency_profile':np.empty((ng,129),dtype='<f4'),
        'geometry_mean_row_normalized_frequency_profile':np.empty((ng,129),dtype='<f8'),
        'geometry_mean_normalized_minus_flank_frequency_profile':np.empty((ng,129),dtype='<f8'),
        'geometry_raw_row_SHA256':np.empty((ng,16,32),dtype='u1')}
    fields={'center':'geometry_center_row_normalized_power','flank':'geometry_flank_median_row_normalized_power',
        'residual':'geometry_center_minus_flank_rows','raw_width_mean':'geometry_raw_width_mean_power',
        'mean_raw':'geometry_mean_raw_frequency_profile','mean_normalized':'geometry_mean_row_normalized_frequency_profile',
        'mean_residual':'geometry_mean_normalized_minus_flank_frequency_profile'}
    for g in range(ng):
        medians=arrays['saved_full_native_row_medians'][scans[g]]
        result=profile_kernel(np,raw[g],medians,int(widths[g]))
        for key,name in fields.items():
            require(np.isfinite(result[key]).all(),'Nonfinite new profile')
            arrays[name][g]=result[key]
        for row in range(16):
            arrays['geometry_raw_row_SHA256'][g,row]=np.frombuffer(hashlib.sha256(raw[g,row].tobytes(order='C')).digest(),dtype='u1')
        if (g+1)%512==0:enforce_usage(start_cpu,start_wall)
    del raw
    records=[]
    for j,member in enumerate(members):
        origin=SCANS.index(member['member_scan_id']);origin_res=arrays['geometry_center_minus_flank_rows'][mapping[j,origin]]
        profiles=[]
        for si,scan in enumerate(SCANS):
            g=int(mapping[j,si]);res=arrays['geometry_center_minus_flank_rows'][g]
            profiles.append({'scan_id':scan,'target_scan_id':scan,'geometry_index':g,'metrics':summary_metrics(np,res),
                'row_array_ref':{'file':'COMPACT_FIXED_PROFILES.npz','array':'geometry_center_minus_flank_rows','index':g},
                'origin_ON_mean_minus_this_scan_mean':float(origin_res.mean()-res.mean()),
                'target_role':'ON' if scan in ONS else 'OFF'})
        records.append({'logical_member_index':j,**member,'scan_profiles':profiles})
    npz=out/'COMPACT_FIXED_PROFILES.npz'
    with npz.open('xb') as f:np.savez(f,**arrays);f.flush();os.fsync(f.fileno())
    fsync_directory(out)
    origin_pins=[]
    for origin in ONS:
        subset=[x for x in records if x['member_scan_id']==origin]
        require(len(subset)==635,'Each origin must retain635 logical members')
        path=out/('PROFILES_'+origin+'.json')
        save_new(path,{'schema':SCHEMA,'family_id':FAMILY,'originating_ON':origin,'records':subset})
        origin_pins.append({'originating_ON':origin,'logical_member_count':635,'logical_scan_profiles':3810,'file_pin':pin(path)})
    save_new(out/'FIXED_ALL_SIX_PROFILES.json',{'schema':SCHEMA,'family_id':FAMILY,'complete':True,
        'measurement_complete_resource_admission_pending':True,'selected_triples':635,'selected_members':1905,
        'logical_scan_profiles':11430,'logical_time_rows':182880,'unique_geometries':ng,'new_geometry_aliases':61,
        'old_geometry_aliases':0,'ordered_geometry_sha256':gsha,'MJD_anchor':anchor,
        'compact_arrays_pin':pin(npz),'origin_record_files':origin_pins,'limitations':LIMITATIONS})
    save_atomic(out/'PROFILE_CHECKPOINT.json',{'family_id':FAMILY,'complete':True,'source_scans_loaded':list(SCANS),
        'unique_geometries_measured':ng,'logical_scan_profiles':11430,'logical_time_rows':182880,
        'scientific_execution_status':'MEASUREMENT_COMPLETE_FINAL_RESOURCE_ADMISSION_PENDING'})
    return verified,pin(npz),pin(out/'FIXED_ALL_SIX_PROFILES.json'),gsha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',required=True);parser.add_argument('--expected-scope-sha256',required=True)
    parser.add_argument('--expected-admission-sha256',required=True);parser.add_argument('--freeze-commit',required=True)
    parser.add_argument('--root-go-after-profile-freeze',action='store_true');args=parser.parse_args()
    start_cpu,start_wall=0.0,time.monotonic()
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    def limit(signum,frame):raise ResourceLimitExceeded('OS profile resource limit '+str(signum))
    signal.signal(signal.SIGALRM,limit);signal.signal(signal.SIGXCPU,limit);signal.alarm(int(WALL_CAP))
    resource.setrlimit(resource.RLIMIT_CPU,(180,182));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    scope=read_json(checked_file(args.scope),args.expected_scope_sha256)
    require(scope['schema']==SCHEMA and scope['family_id']==FAMILY and scope['script_sha256']==digest(__file__),'Early source identity differs')
    out=Path(scope['output_directory']);stage=out.parent
    require(stage.resolve()==stage and Path(scope['attempt_marker_path'])==stage/'PROFILE_STARTED_ONCE.json','Canonical stage/marker required')
    save_new(Path(scope['attempt_marker_path']),{'family_id':FAMILY,'scope_sha256':args.expected_scope_sha256,
        'public_freeze_commit':args.freeze_commit,'status':'STARTED_ONCE_NO_RETRY','PID':os.getpid()})
    owner_handles=[];gate=None;created=False;committed=False
    try:
        owner_handles=acquire_owner_guards(scope)
        scope,pins,admission,source,norm,members,oldgeo=load_contract(args)
        gp=Path(scope['serial_gate_path']);fd=os.open(gp,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        gate=os.fdopen(fd,'r+b',buffering=0);fcntl.flock(gate.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        inode=os.fstat(gate.fileno());require(stat.S_ISREG(inode.st_mode) and gp.stat().st_ino==inode.st_ino,'Stable profile gate differs')
        out.mkdir(exist_ok=False);created=True
        save_new(out/'INPUT_PINS.json',{'family_id':FAMILY,'scope_sha256':args.expected_scope_sha256,
            'script_sha256':scope['script_sha256'],'public_freeze_commit':args.freeze_commit,
            'admission_pin':scope['admission_pin'],'pinned_files':pins,'selected_members_sha256':scope['selected_members_sha256']})
        for pkg,version in {'numpy':'2.3.5','h5py':'3.15.1','hdf5plugin':'7.1.0'}.items():
            require(importlib.metadata.version(pkg)==version,'Frozen codec runtime differs:'+pkg)
        import numpy as np
        import h5py
        import hdf5plugin
        require(h5py.version.hdf5_version=='1.14.6' and np.dtype('<f4').isnative,'Frozen HDF5/endian differs')
        verified,npzpin,jsonpin,gsha=compute(np,h5py,scope,source,norm,members,oldgeo,out,start_cpu,start_wall)
        require(digest(args.scope)==args.expected_scope_sha256 and digest(__file__)==scope['script_sha256'],'End scope/script changed')
        for p in pins:verify_pin(p)
        for p in admission['proof_pins']:verify_pin(p)
        verify_no_live_owner_processes(scope)
        for handle,name in zip(owner_handles,scope['owner_kernel_guard_paths']):
            held=os.fstat(handle.fileno());now=Path(name).stat();require((held.st_ino,held.st_dev)==(now.st_ino,now.st_dev),'Owner guard replaced')
        require(gp.stat().st_ino==inode.st_ino and gp.stat().st_dev==inode.st_dev,'Profile serial gate replaced')
        require(tree_size([str(out)])<OUTPUT_CAP-65536
            and tree_size(scope['shared_workspace_roots'])+1048576<=WORKSPACE_CAP,
            'Final output/shared disk lacks1MiB terminal-publication headroom')
        use=enforce_usage(start_cpu,start_wall)
        terminal={'status':PROFILE_STATUS,'family_id':FAMILY,'scope_sha256':args.expected_scope_sha256,
            'script_sha256':scope['script_sha256'],'public_freeze_commit':args.freeze_commit,
            'admission_pin':scope['admission_pin'],'selected_members_sha256':scope['selected_members_sha256'],
            'ordered_geometry_sha256':gsha,'selected_triples':635,'selected_members':1905,
            'logical_scan_profiles':11430,'logical_time_rows':182880,'unique_geometries':11369,
            'new_geometry_aliases':61,'old_geometry_aliases':0,'verified_source_rows':verified,
            'compact_arrays_pin':npzpin,'profile_JSON_pin':jsonpin,'H5_source_opened':True,'profiles_measured':True,
            'new_profile_normalization_performed':True,'fixed_profile_flank_medians_newly_measured':True,
            'full_native_row_denominator_medians_recomputed':False,'original_detector_or_map_preprocessing_reexecuted':False,
            'new_HTTP_requests':0,'new_source_BODY_bytes':0,'cost_DKK':0,'limitations':LIMITATIONS,**use}
        publish_terminal(out/'EXECUTION_RECEIPT.json',terminal,start_cpu,start_wall,scope['shared_workspace_roots'],out);committed=True
        try:print(json.dumps({'status':PROFILE_STATUS,**use}),flush=True)
        except BrokenPipeError:pass
    except BaseException as exc:
        if not committed and (not created or not (out/'EXECUTION_RECEIPT.json').exists()):
            path=(out/'FAILURE_RECEIPT.json') if created else stage/'PREFLIGHT_FAILURE_RECEIPT.json'
            save_new(path,{'status':'INCOMPLETE_ONE_SHOT_PROFILE_FAMILY_NO_RETRY','family_id':FAMILY,
                'scope_sha256':args.expected_scope_sha256,'error_type':type(exc).__name__,'error':str(exc),
                'partial_outputs_preserved':created,**usage(start_cpu,start_wall)})
        raise
    finally:
        signal.alarm(0)
        if gate is not None:gate.close()
        for h in owner_handles:h.close()


if __name__=='__main__':main()
