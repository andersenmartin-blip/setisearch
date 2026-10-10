#!/usr/bin/env python3
"""Shared stdlib-only contract and bounded lifecycle. No science imports here."""
import fcntl, hashlib, json, math, os, re, resource, signal, stat, struct, time
from pathlib import Path
FAMILY = 'radio_s2017_cross_on_profiles_20261010'
SCHEMA = 'SETI_S2017_CROSS_ON_ALL_SIX_FIXED_PROFILES_V1'
SCANS = ('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
ONS = ('epoch1_on','epoch2_on','epoch3_on')
C0, COUNT, CORE = 179306496, 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, MEMORY_CAP = 180.0, 1800.0, 1073741824
OUTPUT_CAP, WORKSPACE_CAP = 134217728, 12884901888
EXCLUDED = 'radio_s2017_cross_on_storage_recovery_20261010_rank_0001'
TOP_SHA = 'f225f42ef99f71e8c6b51f268d1c9e8dd7cb8ec0903f0b5853cea73b1eb02439'
SOURCE_SHA = '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107'
NORM_SHA = '6dced4644d01db8a6a2dc8d4b740c63ca2d582691bdef810d1a9138c8d97b7cf'
GAP_SHA = 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58'
MATCH_FAMILY = 'radio_s2017_cross_on_storage_recovery_20261010'
MATCH_STATUS = 'COMPLETE_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_EXPLORATORY_ONLY'
PROFILE_STATUS = 'COMPLETE_635_S2017_MATCHED_TRIPLES_ALL_SIX_FIXED_PROFILES_EXPLORATORY_ONLY'
LIMITATIONS = [
 'Posthoc same-visit ON-selected association and fixed profiles; not independent validation.',
 'Each of the three member tracks is unchanged; profiles do not fit a consensus.',
 'Logical profiles and shared controls are correlated; geometric aliases share one extraction.',
 'A weak transported OFF path does not exclude nearby stationary or differently drifting OFF structure.',
 'No detector, preprocessing, global-median recomputation, new ranking, threshold, OFF veto or source GET.',
 'No calibrated SNR/FAP, probability, candidate qualification, flux/sensitivity or origin classification.',
 'Old A/B FAIL_CLOSED, protected holdouts and original whole-source MD5 limitations remain unchanged.',
 'Full raw/normalized patches are not retained; their exact row SHA and durable original source pins support reproduction.'
]


class ResourceLimitExceeded(RuntimeError):
    pass

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def checked_file(path):
    path = Path(path)
    require(path.is_absolute(), 'Input/output paths must be absolute')
    require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Expected regular non-symlink file')
    require(path.resolve() == path, 'File path must be canonical')
    return path

def verify_pin(pin):
    require(set(pin) == {'path', 'sha256', 'bytes'}, 'Unexpected file pin schema')
    path = checked_file(pin['path'])
    require(type(pin['bytes']) is int and pin['bytes'] >= 0
        and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']) is not None, 'Invalid file pin')
    require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input file byte pin differs: ' + str(path))
    return path

def read_json(path, expected_sha=None, expected_bytes=None):
    raw = Path(path).read_bytes()
    require(expected_sha is None or hashlib.sha256(raw).hexdigest() == expected_sha, 'Metadata snapshot SHA differs')
    require(expected_bytes is None or len(raw) == expected_bytes, 'Metadata snapshot byte size differs')
    return json.loads(raw)

def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(Path(path).parent)

def save_atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    save_new(temporary, value)
    os.replace(temporary, path)
    fsync_directory(path.parent)

def publish_terminal(path, value, start_cpu, start_wall, workspace_roots, output_root):
    # Materialize, flush and account serialization before terminal publication.
    # Hard-link publication is exclusive; no existing terminal is replaced.
    path = Path(path)
    temporary = path.with_name(path.name + '.prepared')
    save_new(temporary, value)
    require(temporary.stat().st_size <= 65536, 'Terminal receipt exceeds reserved small-control budget')
    # Account the transient second directory entry created by the hard link.
    require(tree_size(workspace_roots) + temporary.stat().st_size <= WORKSPACE_CAP,
        'Prepared terminal plus publication exceeds shared workspace cap')
    require(tree_size([str(output_root)]) + temporary.stat().st_size < OUTPUT_CAP,
        'Prepared terminal plus publication exceeds output reservation')
    use = enforce_usage(start_cpu, start_wall)
    require(use['process_CPU_seconds'] < CPU_CAP - .1 and use['wall_seconds'] < WALL_CAP - 2,
        'Insufficient bounded headroom to publish final receipt')
    signal.alarm(0)
    signal.signal(signal.SIGXCPU, signal.SIG_IGN)
    os.link(temporary, path)
    fsync_directory(path.parent)
    temporary.unlink()
    fsync_directory(path.parent)

def usage(start_cpu, start_wall):
    return {'process_CPU_seconds': time.process_time() - start_cpu,
        'wall_seconds': time.monotonic() - start_wall,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}

def enforce_usage(start_cpu, start_wall):
    use = usage(start_cpu, start_wall)
    if use['process_CPU_seconds'] > CPU_CAP or use['wall_seconds'] > WALL_CAP or use['peak_RSS_bytes'] > MEMORY_CAP:
        raise ResourceLimitExceeded('Measured profile use exceeds frozen caps')
    return use

def tree_size(roots):
    paths = [Path(item) for item in roots]
    require(paths and all(path.is_absolute() and path.is_dir() and path.resolve() == path for path in paths), 'Workspace roots must exist and be canonical')
    require(len(set(paths)) == len(paths), 'Repeated workspace root')
    require(not any(a != b and a in b.parents for a in paths for b in paths), 'Overlapping workspace roots')
    total = 0
    for root in paths:
        for base, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories if not (Path(base) / name).is_symlink()]
            for name in files:
                info = (Path(base) / name).lstat()
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
                elif stat.S_ISLNK(info.st_mode):
                    total += info.st_size
    return total

def verify_no_live_owner_processes(scope):
    # Check actual scientific command arguments, without exposing command text.
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            arguments = (process / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        for relative in scope['owner_scientific_command_paths']:
            suffix = relative.encode()
            require(not any(argument == suffix or argument.endswith(b'/' + suffix) for argument in arguments),
                'An original scientific numeric/QA process remains active')

def acquire_owner_guards(scope):
    handles = []
    try:
        for name in scope['owner_kernel_guard_paths']:
            path = checked_file(name)
            # Existing inode only: never create, truncate or rewrite owner locks.
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            handle = os.fdopen(fd, 'rb', buffering=0)
            handles.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            original = os.fstat(handle.fileno())
            require(path.stat().st_ino == original.st_ino and path.stat().st_dev == original.st_dev,
                'Original kernel guard was replaced')
        return handles
    except BaseException:
        for handle in handles:
            handle.close()
        raise


def pin(path, expected=None):
    path = checked_file(path)
    item = {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}
    require(expected is None or item['sha256'] == expected, 'Expected historical SHA differs')
    return item


def pinned_json(item):
    return read_json(item['path'], item['sha256'], item['bytes'])


def float_bits(value):
    return struct.pack('<d', float(value)).hex()


def member_key(key):
    return (key['visit'], key['scan_id'], int(key['source_reference_channel']),
        float_bits(key['reference_seconds_from_anchor']), float_bits(key['drift_hz_s']), int(key['width_channels']))


def selected_members(top):
    require(top['family_id'] == MATCH_FAMILY and top['matched_triples'] == top['displayed_records'] == 636
        and top['display_truncated'] is False and len(top['records']) == 636, 'All636 matches required')
    require([x['display_rank'] for x in top['records']] == list(range(1,637)), 'Original match order differs')
    require(sum(x['match_id'] == EXCLUDED for x in top['records']) == 1, 'Exact excluded identity absent/repeated')
    members = []
    for triple in top['records']:
        require([m['scan_id'] for m in triple['members']] == list(ONS), 'Three original ON members required')
        if triple['match_id'] == EXCLUDED:
            for m in triple['members']:
                k = m['original_key']
                require(k['source_reference_channel'] == 179830784 and k['drift_grid_index'] == 392
                    and float_bits(k['drift_hz_s']) == float_bits(-4.440892098500626e-16)
                    and k['width_channels'] == 1, 'Known excluded triple identity changed')
            continue
        for m in triple['members']:
            require(m['scan_id'] == m['original_key']['scan_id'], 'Member origin differs')
            members.append({'match_id': triple['match_id'], 'original_display_rank': triple['display_rank'],
                'member_scan_id': m['scan_id'], 'original_member': m})
    require(len(members) == 1905 and len({member_key(m['original_member']['original_key']) for m in members}) == 1905,
        'Fixed1905 unique member hypotheses required')
    return members


def selection_sha(members):
    return hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def old_geometries(old_profiles):
    keys, geometry = set(), set()
    for records in old_profiles:
        require(len(records) == 9, 'Each old file must retain nine profiles')
        for rec in records:
            t = rec['selected_track']
            keys.add((t['originating_scan'], t['source_reference_channel'], float_bits(t['reference_seconds_from_anchor']),
                float_bits(t['drift_hz_s']), t['width_channels']))
            require(rec['fixed_frequency_shift_channels'] == 0
                and [x['scan_id'] for x in rec['scan_profiles']] == list(SCANS), 'Old fixed geometry differs')
            for sp in rec['scan_profiles']:
                require(len(sp['frozen_source_channel_centers']) == 16, 'Old sixteen centers required')
                geometry.add((sp['scan_id'], t['width_channels'], tuple(sp['frozen_source_channel_centers'])))
    require(len(keys) == 54 and len(geometry) == 312, 'Historical54/312 identity inventory differs')
    return keys, geometry


def metadata_inventory(project, owner):
    """No NPZ/HDF5 decoding. Authenticate only historical JSON/code/opaque files."""
    project, owner = Path(project), Path(owner)
    pins = {}
    def record(path, expected=None):
        p = pin(path, expected)
        require(p['path'] not in pins or pins[p['path']] == p, 'Conflicting repeated input pin')
        pins[p['path']] = p
        return p
    def qa_attests(qa, item):
        p = Path(item['path'])
        matches = [qa['all_input_byte_pins'][k] for k in (str(p), str(p.relative_to(owner))) if k in qa['all_input_byte_pins']]
        require(len(matches) == 1 and matches[0] == {'sha256':item['sha256'],'bytes':item['bytes']},
            'Historical metadata not attested by its original QA')
    source_pin = record(owner/'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json', SOURCE_SHA)
    source = pinned_json(source_pin)
    require(source['native_chunk_index'] == 171 and source['physical_channel_interval_half_open'] == [C0,C0+COUNT]
        and [x['label'] for x in source['sources']] == list(SCANS), 'Wrong retained source geometry')
    for item in source['sources']:
        h = item['current_header']; a = h['data_attributes']
        require(h['dataset_shape'] == [16,1,359661568] and h['dataset_chunks'] == [1,1,COUNT]
            and h['dtype_exact'] == '<f4' and a['fch1']*1e6 == FCH1 and a['foff']*1e6 == DF
            and a['tsamp'] == TSAMP, 'Frozen actual source/header/grid differs')
    q = owner/'analysis/new_visit_recovery/results'
    bulk = owner/'analysis/s2017_full_band/results'
    qqa_pin, bqa_pin = record(q/'review/QA_RECEIPT.json'), record(bulk/'review/QA_RECEIPT.json')
    qqa, bqa = pinned_json(qqa_pin), pinned_json(bqa_pin)
    require(qqa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and bqa['status'] == 'PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS', 'Original source QA incomplete')
    qa_attests(qqa,source_pin)
    old_profile_pins, norm_pins, terminals = [], [], []
    for name, directory, qa in [('q128',q/'search',qqa), *[(f'batch{i:02d}',bulk/f'batch{i:02d}',bqa) for i in range(1,4)]]:
        ep = record(directory/'EXECUTION_RECEIPT.json'); e = pinned_json(ep)
        status = ('COMPLETE_NEW_S2017_THREE_CORE_MAPS_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY' if name=='q128'
            else 'COMPLETE_S2017_PREVIOUSLY_UNSEARCHED_INTERIOR_BATCH_EXPLORATORY_ONLY')
        require(e['status']==status and e['source_manifest_sha256']==SOURCE_SHA, 'Original execution incomplete/wrong source')
        require(e['scope_sha256'] == (qqa['scope_sha256'] if name=='q128' else bqa['scope_SHA256s'][name])
            and e['driver_sha256']==qa['driver_sha256'] and e['public_freeze_commit']==qa['public_freeze_commit']
            and ep['sha256']==(qqa['search_receipt_sha256'] if name=='q128' else bqa['search_receipt_SHA256s'][name]),
            'Original execution/QA scope, code, freeze, terminal joins differ')
        driver_path=(owner/'analysis/new_visit_recovery/driver.py') if name=='q128' else (owner/'analysis/s2017_full_band/driver.py')
        scope_path=(owner/'analysis/new_visit_recovery/scope.json') if name=='q128' else (owner/'analysis/s2017_full_band/scopes'/(name+'.json'))
        dp=record(driver_path,e['driver_sha256']);sp=record(scope_path,e['scope_sha256'])
        qa_attests(qa,dp);qa_attests(qa,sp)
        terminals.append(ep)
        npin=record(directory/'NORMALIZATION.json',NORM_SHA);qa_attests(qa,npin);norm_pins.append(npin)
        pp=record(directory/'FIXED_TOP3_PROFILES.json');qa_attests(qa,pp);old_profile_pins.append(pp)
    joined=owner/'analysis/s2017_next_native/boundaries'
    jqa_pin=record(joined/'results/review/QA_RECEIPT.json','48153e180358319feb3906fc719eabc9f224200933aa69eccbe0e20cdb8f1b36')
    jqa=pinned_json(jqa_pin)
    require(jqa['status']=='PASS12_S2017_JOINED_MAPS18_FIXED_PROFILES192_JOINED_MEDIANS_AND222912_BITWISE_SOURCE_CELLS',
        'Existing joined18 profile QA required')
    jd=record(joined/'driver.py',jqa['driver_sha256']);qa_attests(jqa,jd)
    record(joined/'qa_saved_outputs.py',jqa['qa_script_sha256'])
    for pair,chunks in [('pair170_171',[170,171]),('pair171_172',[171,172])]:
        sp=record(joined/'scopes'/(pair+'.json'),jqa['scope_SHA256s'][pair]);qa_attests(jqa,sp)
        ep=record(joined/'results'/pair/'measurement/EXECUTION_RECEIPT.json',jqa['pair_execution_receipt_SHA256s'][pair])
        e=pinned_json(ep)
        require(e['status']=='COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'
            and e['pair_id']==pair and e['source_chunk_ids']==chunks and e['source_channel0']==chunks[0]*COUNT
            and e['source_channel_count']==2*COUNT and e['scope_sha256']==sp['sha256']
            and e['driver_sha256']==jqa['driver_sha256'] and e['public_freeze_commit']==jqa['search_public_freeze_commit'],
            'Existing joined profile execution/source/scope/code/freeze joins differ')
        pp=record(joined/'results'/pair/'measurement/FIXED_TOP3_PROFILES.json');qa_attests(jqa,pp);old_profile_pins.append(pp)
    norm=pinned_json(norm_pins[0])
    require(norm['source_channel0']==C0 and norm['count']==COUNT and norm['raw_dtype']=='<f4'
        and set(norm['row_power_medians'])==set(SCANS)
        and all(len(v)==16 and all(math.isfinite(x) and x>0 for x in v) for v in norm['row_power_medians'].values()),
        'Saved full-native denominators differ/nonpositive')
    record(owner/'analysis/new_visit_search/dependencies/gap_search.py',GAP_SHA)
    record(owner/'analysis/new_visit_search/qa_saved_outputs.py',qqa['qa_script_sha256'])
    record(owner/'analysis/s2017_full_band/qa_saved_outputs.py',bqa['qa_script_sha256'])
    acq_pin=record(q/'acquire/ACQUISITION_RESULT.json');acq=pinned_json(acq_pin)
    qa_attests(qqa,acq_pin)
    require(acq['status']=='COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
        and acq['source_manifest_sha256']==SOURCE_SHA and acq['complete_compact_files']==6
        and len(acq['decoded_files'])==6 and len({x['scan_id'] for x in acq['decoded_files']})==6,
        'All six original compacts required')
    compact_records=[]
    for label in SCANS:
        item=next(x for x in acq['decoded_files'] if x['scan_id']==label)
        require(item['array_file']==label+'.compact.h5' and item['shape']==[16,1,COUNT]
            and item['source_channel0']==C0 and [x['time_row'] for x in item['decoded_rows']]==list(range(16))
            and all(x['decoded_bytes']==COUNT*4 for x in item['decoded_rows']), 'Compact16-row identity differs')
        cp=record(q/'acquire'/item['array_file'],item['file_sha256'])
        require(cp['bytes']==item['bytes'], 'Compact size differs')
        qa_attests(qqa,cp)
        compact_records.append({'scan_id':label,'file_pin':cp,'decoded_rows':item['decoded_rows']})
    mr=project/'results'/MATCH_FAMILY;mt=project/'tools'/MATCH_FAMILY
    match_scope_pin=record(mt/'scope.json');ms=pinned_json(match_scope_pin)
    original_matching_pins={x['path']:x for x in ms['pinned_metadata_files']}
    for path,item in pins.items():
        if path in original_matching_pins:require(item==original_matching_pins[path], 'Original metadata changed since completed matching freeze')
    match_script_pin=record(mt/'match_saved.py',ms['script_sha256'])
    match_top_pin=record(mr/'measurement/TOP1000.json',TOP_SHA);top=pinned_json(match_top_pin)
    match_exec_pin=record(mr/'measurement/EXECUTION_RECEIPT.json');me=pinned_json(match_exec_pin)
    match_outer_pin=record(mr/'ROOT_OUTER_EXECUTION_RECEIPT.json');outer=pinned_json(match_outer_pin)
    match_review_pin=record(mr/'proofs/S2017_CROSS_ON_STORAGE_ACTUAL_OUTPUT_ONLY_REVIEW.json');review=pinned_json(match_review_pin)
    require(me['status']==MATCH_STATUS and me['scope_sha256']==match_scope_pin['sha256']
        and me['script_sha256']==match_script_pin['sha256'] and me['matched_triples']==636,
        'Actual matching execution wrong/incomplete')
    require(outer['child_exit_code']==0 and outer['inner_terminal_sha256']==match_exec_pin['sha256']
        and outer['inner_terminal_status']==MATCH_STATUS and outer['freeze_commit']==me['public_freeze_commit'],
        'Matching outer process not closed COMPLETE')
    require(review['status']=='PASS_BOUNDED_OUTPUT_ONLY_636_RELATION_TOP_AND_ACTUAL_EXECUTION_METADATA_CONTRACTS'
        and review['all_contract_checks_passed'] is True and review['scope_sha256']==match_scope_pin['sha256']
        and review['source_script_sha256']==match_script_pin['sha256']
        and review['public_freeze_commit']==me['public_freeze_commit'], 'Actual matching output QA required')
    for p in (match_top_pin,match_exec_pin,match_scope_pin,match_outer_pin):
        require(review['input_pins'].get(p['path'])==p, 'Matching review does not attest exact admitted file')
    members=selected_members(top)
    old_keys, oldgeo=old_geometries([pinned_json(p) for p in old_profile_pins])
    interval_pin=record(project/'tools'/FAMILY/'NATIVE170172_PROFILE_INTERVAL_DISJOINTNESS.json',
        '2c05744df764f03a0b5cc8765115d1c803fa9103742f6feb7c0e08a59a103452')
    interval=pinned_json(interval_pin)
    require(interval['status']=='PASS_54_NATIVE170172_FIXED_CASE_WINDOWS_DISJOINT_FROM_NATIVE171'
        and interval['completed_cases']==54 and interval['scan_profiles']==324
        and interval['native171_interval_half_open']==[C0,C0+COUNT]
        and interval['individual_context_support_intersection_with_native171_count']==0
        and len(interval['files'])==len(interval['profile_file_pins'])==6,
        'Outside-band54/324 interval proof differs')
    for p in interval['input_file_pins']+interval['profile_file_pins']:record(p['path'],p['sha256']);verify_pin(p)
    require({x['profile_file_pin']['path'] for x in interval['files']}=={x['path'] for x in interval['profile_file_pins']},
        'Outside-band proof file inventory differs')
    for f in interval['files']:
        chunk=f['source_chunk_id'];records=pinned_json(f['profile_file_pin']);bounds=[]
        require(chunk in (170,172) and len(records)==9,'Only six outside-band nine-case files admitted')
        for r in records:
            require([s['scan_id'] for s in r['scan_profiles']]==list(SCANS),'Outside-band six scan inventory differs')
            for s in r['scan_profiles']:
                cs=s['frozen_source_channel_centers']
                require(len(cs)==16 and all(type(c) is int for c in cs),'Outside-band integer geometry differs')
                lo,hi=min(cs)-64,max(cs)+65;bounds.append((lo,hi))
                require(chunk*COUNT<=lo<hi<=(chunk+1)*COUNT and (hi<=C0 or lo>=C0+COUNT),
                    'An existing outside-band profile window reaches native171')
        require([min(x[0] for x in bounds),max(x[1] for x in bounds)]==f['support_interval_half_open'],
            'Outside-band proof support bounds differ')
    for m in members:
        k=m['original_member']['original_key']
        require((k['scan_id'],k['source_reference_channel'],float_bits(k['reference_seconds_from_anchor']),
            float_bits(k['drift_hz_s']),k['width_channels']) not in old_keys, 'Existing profile hypothesis would be repeated')
    return {'pins':list(pins.values()),'source_pin':source_pin,'normalization_pin':norm_pins[0],
        'acquisition_pin':acq_pin,'compact_records':compact_records,'old_profile_pins':old_profile_pins,
        'matching_TOP_pin':match_top_pin,'matching_execution_pin':match_exec_pin,'matching_review_pin':match_review_pin,
        'members':members,'selection_sha256':selection_sha(members),'source':source,'old_geometries':oldgeo,
        'outside_native_profile_interval_proof_pin':interval_pin,
        'owner_kernel_guard_paths':ms['owner_kernel_guard_paths'],'owner_scientific_command_paths':ms['owner_scientific_command_paths']+[
            'analysis/s2017_next_native/boundaries/driver.py','analysis/s2017_next_native/boundaries/qa_saved_outputs.py']}
