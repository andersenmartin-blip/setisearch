#!/usr/bin/env python3
"""One-shot output/index QA and independent raw-row digest authentication.

No detector, profile kernel, normalization, median, nearest matcher or source GET.
Run only after the profile child is CLOSED exit 0 with its actual COMPLETE.
"""
import time
WALL_START = time.monotonic()
import argparse
import importlib.metadata
import zipfile
from profile_contract import *

QA_CPU_CAP, QA_WALL_CAP, QA_MEMORY_CAP = 120.0, 1800.0, 1073741824
QA_STATUS = 'PASS_635_TRIPLES_11430_FIXED_PROFILE_OUTPUTS_AND23465616_RAW_CELL_OCCURRENCE_DIGESTS'
ARRAY_SCHEMA = {
    'logical_geometry_indices': ('<i4', (1905, 6)),
    'logical_times_seconds_from_original_reference': ('<f8', (1905, 6, 16)),
    'geometry_source_channel_centers': ('<i8', (11369, 16)),
    'geometry_scan_indices': ('<i2', (11369,)),
    'geometry_width_channels': ('<i2', (11369,)),
    'source_channel_offsets': ('<i8', (129,)),
    'scans': ('<U10', (6,)),
    'saved_full_native_row_medians': ('<f8', (6, 16)),
    'geometry_center_row_normalized_power': ('<f8', (11369, 16)),
    'geometry_flank_median_row_normalized_power': ('<f8', (11369, 16)),
    'geometry_center_minus_flank_rows': ('<f8', (11369, 16)),
    'geometry_raw_width_mean_power': ('<f4', (11369, 16)),
    'geometry_mean_raw_frequency_profile': ('<f4', (11369, 129)),
    'geometry_mean_row_normalized_frequency_profile': ('<f8', (11369, 129)),
    'geometry_mean_normalized_minus_flank_frequency_profile': ('<f8', (11369, 129)),
    'geometry_raw_row_SHA256': ('|u1', (11369, 16, 32)),
}
MEASUREMENT_FILES = {
    'INPUT_PINS.json', 'PROFILE_CHECKPOINT.json', 'COMPACT_FIXED_PROFILES.npz',
    'PROFILES_epoch1_on.json', 'PROFILES_epoch2_on.json', 'PROFILES_epoch3_on.json',
    'FIXED_ALL_SIX_PROFILES.json', 'EXECUTION_RECEIPT.json',
}


def qa_usage():
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds': time.monotonic() - WALL_START,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def qa_enforce():
    use = qa_usage()
    require(use['process_CPU_seconds_including_imports'] <= QA_CPU_CAP
        and use['wall_seconds'] <= QA_WALL_CAP and use['peak_RSS_bytes'] <= QA_MEMORY_CAP,
        'Measured independent QA resources exceed frozen bounds')
    return use


def finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def publish_qa(path, value, roots, review):
    temporary = path.with_name(path.name + '.prepared')
    save_new(temporary, value)
    require(temporary.stat().st_size <= 1048576, 'QA receipt exceeds 1MiB terminal reservation')
    require(tree_size(roots) + temporary.stat().st_size <= WORKSPACE_CAP
        and tree_size([str(review)]) + temporary.stat().st_size < OUTPUT_CAP,
        'QA terminal publication exceeds shared/output bounds')
    use = qa_enforce()
    require(use['process_CPU_seconds_including_imports'] < QA_CPU_CAP - .1
        and use['wall_seconds'] < QA_WALL_CAP - 2, 'QA terminal publication lacks resource headroom')
    signal.alarm(0)
    signal.signal(signal.SIGXCPU, signal.SIG_IGN)
    os.link(temporary, path)
    fsync_directory(path.parent)
    temporary.unlink()
    fsync_directory(path.parent)


def collect_pin(item, pins):
    path = verify_pin(item)
    require(str(path) not in pins or pins[str(path)] == item, 'Conflicting repeated QA input pin')
    pins[str(path)] = item
    return path


def add_json(path, pins, expected=None):
    item = pin(path, expected)
    collect_pin(item, pins)
    return item, pinned_json(item)


def closed_contract(args, scope, pins):
    out = Path(scope['output_directory'])
    stage = out.parent
    require(scope['schema'] == SCHEMA and scope['family_id'] == FAMILY
        and scope['admission_pin']['sha256'] == args.expected_admission_sha256,
        'Frozen profile scope/admission differs')
    require(out.is_absolute() and out.resolve() == out and stage.resolve() == stage
        and out == Path(__file__).parents[2] / 'results' / FAMILY / 'measurement',
        'Canonical fixed profile measurement directory required')
    expected = {'selected_triples': 635, 'selected_members': 1905,
        'logical_scan_profiles': 11430, 'logical_time_rows': 182880,
        'unique_geometries': 11369, 'new_geometry_aliases': 61, 'old_geometry_aliases': 0,
        'old_saved_profiles': 54, 'old_saved_geometries': 312, 'excluded_match_id': EXCLUDED,
        'source_channel0': C0, 'source_chunk_channel_count': COUNT,
        'profile_offset_interval_inclusive': [-64, 64], 'CPU_cap_s': CPU_CAP,
        'CPU_hard_limit_s': 182, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
        'output_reservation_bytes': OUTPUT_CAP, 'shared_workspace_cap_bytes': WORKSPACE_CAP}
    require(all(scope.get(k) == v for k, v in expected.items()), 'Frozen profile counts/caps differ')
    require({p.name for p in out.iterdir()} == MEASUREMENT_FILES,
        'Exactly eight completed measurement outputs required; failures/extra outputs are not admitted')
    for item in scope['pinned_metadata_files'] + scope['pinned_dependency_files']:
        collect_pin(item, pins)
    # The separately named inputs must refer to the same frozen inventory,
    # rather than silently adopting a fresh identity outside that inventory.
    named = [scope[k] for k in ('source_pin', 'normalization_pin', 'acquisition_pin',
        'matching_TOP_pin', 'matching_execution_pin', 'matching_review_pin')]
    named += scope['old_profile_pins'] + [x['file_pin'] for x in scope['compact_records']]
    for item in named:
        require(pins.get(item['path']) == item, 'Named source/history input missing from exact frozen inventory')
    dep = {x['path']: x for x in scope['pinned_dependency_files']}
    for name in ('profile_saved.py', 'profile_contract.py', 'FIELD_SCHEMA.json', 'run_frozen_once.py'):
        p = Path(__file__).with_name(name)
        require(str(p) in dep, 'Required frozen worker/contract/schema/launcher dependency absent')
    require(dep[str(Path(__file__).with_name('profile_saved.py'))]['sha256'] == scope['script_sha256'],
        'Frozen worker code pin differs')
    ap, admission = add_json(scope['admission_pin']['path'], pins, args.expected_admission_sha256)
    require(ap == scope['admission_pin']
        and admission['schema'] == 'SETI_S2017_CROSS_ON_PROFILES_ROOT_ADMISSION_V1'
        and admission['status'] == 'PASS_CLOSED_DURABLE_MATCHED_SOURCE_NO_DUPLICATE_PROFILE_PHASE'
        and all(admission.get(k) is True for k in ('all_original171_numeric_QA_processes_closed',
            'matching_numeric_and_output_QA_processes_closed', 'durable_source_RAW_and_RESULTS_verified',
            'durable_matching_RESULTS_verified', 'fresh_duplicate_registry_no_profile_phase',
            'profiles_not_previously_measured')),
        'Actual closed/durable/nonduplicate profile admission required')
    require(admission['source_root'] == scope['source_root']
        and admission['shared_workspace_roots'] == scope['shared_workspace_roots']
        and admission['verified_selected_members_sha256'] == scope['selected_members_sha256']
        and admission['verified_ordered_geometry_sha256'] == scope['ordered_geometry_sha256'],
        'Actual admission selection/geometry/disk paths differ')
    for item in admission['proof_pins']:
        collect_pin(item, pins)
    ep, execution = add_json(out / 'EXECUTION_RECEIPT.json', pins)
    op, outer = add_json(stage / 'ROOT_OUTER_EXECUTION_RECEIPT.json', pins, args.expected_outer_sha256)
    require(execution['status'] == PROFILE_STATUS and execution['family_id'] == FAMILY
        and execution['scope_sha256'] == args.expected_scope_sha256
        and execution['script_sha256'] == scope['script_sha256']
        and execution['public_freeze_commit'] == args.freeze_commit
        and execution['admission_pin'] == scope['admission_pin']
        and execution['selected_members_sha256'] == scope['selected_members_sha256']
        and execution['ordered_geometry_sha256'] == scope['ordered_geometry_sha256'],
        'Actual original profile COMPLETE scope/code/freeze pins differ')
    for key in ('selected_triples', 'selected_members', 'logical_scan_profiles', 'logical_time_rows',
                'unique_geometries', 'new_geometry_aliases', 'old_geometry_aliases'):
        require(execution[key] == expected[key], 'Actual COMPLETE count differs: ' + key)
    require(outer['status'] == 'PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS'
        and outer['child_exit_code'] == 0 and outer['child_timed_out'] is False
        and outer['automatic_retry_performed'] is False
        and outer['freeze_commit'] == args.freeze_commit
        and outer['inner_terminal_sha256'] == ep['sha256']
        and outer['inner_terminal_status'] == PROFILE_STATUS
        and outer['launcher_sha256'] == dep[str(Path(__file__).with_name('run_frozen_once.py'))]['sha256']
        and (outer['CPU_cap_s'], outer['wall_cap_s'], outer['memory_cap_bytes']) == (180, 1800, MEMORY_CAP),
        'Profile child must be CLOSED exit 0 with matching original COMPLETE and outer cap PASS')
    for key, cap in (('child_process_CPU_seconds', CPU_CAP), ('child_wall_seconds', WALL_CAP),
                     ('child_peak_RSS_bytes', MEMORY_CAP)):
        require(finite_nonnegative(outer[key]) and outer[key] <= cap, 'Actual outer resource bound differs')
    for key, cap in (('process_CPU_seconds', CPU_CAP), ('wall_seconds', WALL_CAP), ('peak_RSS_bytes', MEMORY_CAP)):
        require(finite_nonnegative(execution[key]) and execution[key] <= cap, 'Actual inner resource bound differs')
    require(execution['H5_source_opened'] is True and execution['profiles_measured'] is True
        and execution['new_profile_normalization_performed'] is True
        and execution['fixed_profile_flank_medians_newly_measured'] is True
        and execution['full_native_row_denominator_medians_recomputed'] is False
        and execution['original_detector_or_map_preprocessing_reexecuted'] is False
        and (execution['new_HTTP_requests'], execution['new_source_BODY_bytes'], execution['cost_DKK']) == (0, 0, 0),
        'Actual profile operation flags differ')
    ip, inputs = add_json(out / 'INPUT_PINS.json', pins)
    require(inputs['family_id'] == FAMILY and inputs['scope_sha256'] == args.expected_scope_sha256
        and inputs['script_sha256'] == scope['script_sha256'] and inputs['public_freeze_commit'] == args.freeze_commit
        and inputs['admission_pin'] == scope['admission_pin']
        and inputs['selected_members_sha256'] == scope['selected_members_sha256']
        and inputs['pinned_files'] == scope['pinned_metadata_files'] + scope['pinned_dependency_files'],
        'Original execution input manifest differs')
    marker_pin, marker = add_json(stage / 'PROFILE_STARTED_ONCE.json', pins)
    require(marker['status'] == 'STARTED_ONCE_NO_RETRY' and marker['family_id'] == FAMILY
        and marker['scope_sha256'] == args.expected_scope_sha256
        and marker['public_freeze_commit'] == args.freeze_commit, 'Original attempt identity differs')
    checkpoint_pin, checkpoint = add_json(out / 'PROFILE_CHECKPOINT.json', pins)
    require(checkpoint['family_id'] == FAMILY and checkpoint['complete'] is True
        and checkpoint['source_scans_loaded'] == list(SCANS)
        and checkpoint['unique_geometries_measured'] == 11369
        and checkpoint['logical_scan_profiles'] == 11430 and checkpoint['logical_time_rows'] == 182880
        and checkpoint['scientific_execution_status'] == 'MEASUREMENT_COMPLETE_FINAL_RESOURCE_ADMISSION_PENDING',
        'Original final measurement checkpoint differs')
    jp, index = add_json(out / 'FIXED_ALL_SIX_PROFILES.json', pins)
    require(jp == execution['profile_JSON_pin'] and index['schema'] == SCHEMA and index['family_id'] == FAMILY
        and index['complete'] is True and index['measurement_complete_resource_admission_pending'] is True
        and index['ordered_geometry_sha256'] == scope['ordered_geometry_sha256']
        and index['compact_arrays_pin'] == execution['compact_arrays_pin'], 'Completed profile index differs')
    for key in ('selected_triples', 'selected_members', 'logical_scan_profiles', 'logical_time_rows',
                'unique_geometries', 'new_geometry_aliases', 'old_geometry_aliases'):
        require(index[key] == expected[key], 'Profile index count differs: ' + key)
    collect_pin(execution['compact_arrays_pin'], pins)
    require(execution['compact_arrays_pin']['path'] == str(out / 'COMPACT_FIXED_PROFILES.npz'), 'NPZ path differs')
    source = pinned_json(scope['source_pin'])
    norm = pinned_json(scope['normalization_pin'])
    require(scope['source_pin']['sha256'] == SOURCE_SHA and scope['normalization_pin']['sha256'] == NORM_SHA
        and scope['matching_TOP_pin']['sha256'] == TOP_SHA,
        'Original source/normalization identity differs')
    require(execution['verified_source_rows'] == [{'scan_id': x['scan_id'],
        'file_sha256': x['file_pin']['sha256'], 'decoded_rows_verified': 16} for x in scope['compact_records']],
        'Original COMPLETE source-row provenance differs')
    members = selected_members(pinned_json(scope['matching_TOP_pin']))
    require(selection_sha(members) == scope['selected_members_sha256'], 'Original selected TOP identities differ')
    oldkeys, oldgeo = old_geometries([pinned_json(p) for p in scope['old_profile_pins']])
    for m in members:
        k = m['original_member']['original_key']
        require((k['scan_id'], k['source_reference_channel'], float_bits(k['reference_seconds_from_anchor']),
            float_bits(k['drift_hz_s']), k['width_channels']) not in oldkeys, 'Original saved hypothesis admitted again')
    return out, stage, execution, index, source, norm, members, oldgeo


def verify_outputs(np, scope, out, index, source, norm, members, oldgeo, pins):
    npz_path = out / 'COMPACT_FIXED_PROFILES.npz'
    schema = read_json(Path(__file__).with_name('FIELD_SCHEMA.json'))
    require(schema['schema'] == 'SETI_S2017_CROSS_ON_COMPACT_PROFILE_FIELD_SCHEMA_V1'
        and schema['family_id'] == FAMILY and set(schema['arrays']) == set(ARRAY_SCHEMA)
        and all((v['dtype'], tuple(v['shape'])) == ARRAY_SCHEMA[k] for k, v in schema['arrays'].items()),
        'Frozen descriptive field schema differs from independent QA array contract')
    with zipfile.ZipFile(npz_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == 16
            and set(names) == {k + '.npy' for k in ARRAY_SCHEMA}
            and sum(x.file_size for x in archive.infolist()) < OUTPUT_CAP,
            'NPZ member names/uniqueness/uncompressed size differ')
    with np.load(npz_path, allow_pickle=False) as stored:
        require(set(stored.files) == set(ARRAY_SCHEMA), 'NPZ exact sixteen-array inventory differs')
        arrays = {name: stored[name] for name in ARRAY_SCHEMA}
    for name, (dtype, shape) in ARRAY_SCHEMA.items():
        a = arrays[name]
        require(a.dtype.str == dtype and a.shape == shape and not a.dtype.hasobject,
            'NPZ dtype/shape differs: ' + name)
        if a.dtype.kind == 'f':
            require(np.isfinite(a).all(), 'Nonfinite saved profile array: ' + name)
    require(arrays['scans'].tolist() == list(SCANS)
        and arrays['source_channel_offsets'].tolist() == list(range(-64, 65)), 'Saved scan/offset ordering differs')
    medians = np.asarray([norm['row_power_medians'][s] for s in SCANS], dtype='<f8')
    require(np.isfinite(medians).all() and (medians > 0).all()
        and arrays['saved_full_native_row_medians'].tobytes(order='C') == medians.tobytes(order='C'),
        'Saved96 denominators differ; no median has been recomputed')
    mapping = arrays['logical_geometry_indices']
    centers = arrays['geometry_source_channel_centers']
    si = arrays['geometry_scan_indices']; widths = arrays['geometry_width_channels']
    require((mapping >= 0).all() and (mapping < 11369).all()
        and (si >= 0).all() and (si < 6).all() and np.isin(widths, [1, 3]).all()
        and (centers >= C0 + 64).all() and (centers < C0 + COUNT - 64).all(),
        'Saved geometry bounds/scans/widths differ')
    geometry = [(SCANS[int(si[g])], int(widths[g]), tuple(int(c) for c in centers[g])) for g in range(11369)]
    require(len(set(geometry)) == 11369 and not (set(geometry) & oldgeo),
        'Duplicate unique geometry or old312 overlap')
    serial = [[s, w, list(cs)] for s, w, cs in geometry]
    require(hashlib.sha256(json.dumps(serial, separators=(',', ':')).encode()).hexdigest()
        == scope['ordered_geometry_sha256'], 'Stored ordered geometry SHA differs')
    headers = {x['label']: x['current_header']['data_attributes'] for x in source['sources']}
    anchor = min(h['tstart'] for h in headers.values())
    require(float_bits(index['MJD_anchor']) == float_bits(anchor), 'Saved original MJD anchor differs')
    seen, records = set(), {}
    origin_files = index['origin_record_files']
    require(len(origin_files) == 3 and [x['originating_ON'] for x in origin_files] == list(ONS),
        'Exactly three chronological origin JSONs required')
    for origin, item in zip(ONS, origin_files):
        p = item['file_pin']
        require(p['path'] == str(out / ('PROFILES_' + origin + '.json'))
            and item['logical_member_count'] == 635 and item['logical_scan_profiles'] == 3810,
            'Origin JSON path/count differs')
        collect_pin(p, pins);v = pinned_json(p)
        require(v['schema'] == SCHEMA and v['family_id'] == FAMILY
            and v['originating_ON'] == origin and len(v['records']) == 635, 'Origin JSON envelope differs')
        require([r['logical_member_index'] for r in v['records']]
            == [j for j, m in enumerate(members) if m['member_scan_id'] == origin], 'Origin JSON exact member order differs')
        for rec in v['records']:
            j = rec['logical_member_index']
            require(type(j) is int and 0 <= j < 1905 and j not in records
                and {k: rec[k] for k in members[j]} == members[j], 'Original member copy differs')
            records[j] = rec
    require(set(records) == set(range(1905)), 'Each1905 member must be represented exactly once')
    times = arrays['logical_times_seconds_from_original_reference']
    residual = arrays['geometry_center_minus_flank_rows']
    medians_not_recomputed = 0
    for j, member in enumerate(members):
        m = member['original_member']; k = m['original_key']; rec = records[j]
        require([x['scan_id'] for x in rec['scan_profiles']] == list(SCANS), 'Each member requires all6 signed scan profiles')
        origin_index = SCANS.index(member['member_scan_id'])
        origin_mean = float(residual[int(mapping[j, origin_index])].mean())
        base = (m['original_reference_frequency_hz'] - FCH1) / DF
        for s, scan in enumerate(SCANS):
            g = int(mapping[j, s]);sp = rec['scan_profiles'][s]
            require(geometry[g][0] == scan and geometry[g][1] == k['width_channels'], 'Logical scan/width mapping differs')
            expected_centers = []
            for row in range(16):
                dt = (headers[scan]['tstart'] - anchor) * 86400 + (row + .5) * TSAMP - k['reference_seconds_from_anchor']
                require(float_bits(times[j, s, row]) == float_bits(dt), 'Original per-member reference/time was changed')
                expected_centers.append(round(base + k['drift_hz_s'] * dt / DF))
            require(tuple(expected_centers) == geometry[g][2], 'Frozen selected member center16 differs')
            if g not in seen:
                require(g == len(seen), 'Unique geometry first-use order differs')
                seen.add(g)
            require(sp['target_scan_id'] == scan and sp['geometry_index'] == g
                and sp['row_array_ref'] == {'file': 'COMPACT_FIXED_PROFILES.npz',
                    'array': 'geometry_center_minus_flank_rows', 'index': g}
                and sp['target_role'] == ('ON' if scan in ONS else 'OFF'), 'Logical row reference/role differs')
            rows = residual[g];metrics = sp['metrics']
            require(set(metrics) == {'mean', 'median', 'positive_rows', 'first_eight_mean',
                'last_eight_mean', 'minimum_half_mean'}, 'Saved scalar metric keys differ')
            require(type(metrics['positive_rows']) is int and 0 <= metrics['positive_rows'] <= 16
                and all(type(v) in (int, float) and math.isfinite(v)
                    for name, v in metrics.items() if name != 'positive_rows'),
                'Saved scalar metric numeric types/finiteness differ')
            first, last = float(rows[:8].mean()), float(rows[8:].mean())
            expected_metrics = {'mean': float(rows.mean()), 'positive_rows': int(np.count_nonzero(rows > 0)),
                'first_eight_mean': first, 'last_eight_mean': last, 'minimum_half_mean': min(first, last)}
            require(all(metrics[name] == value for name, value in expected_metrics.items()),
                'Saved JSON scalar copies inconsistent with saved signed residual rows')
            require(type(metrics['median']) in (int, float) and math.isfinite(metrics['median'])
                and float(rows.min()) <= metrics['median'] <= float(rows.max()), 'Saved median is nonfinite/outside saved row bounds')
            medians_not_recomputed += 1
            require(sp['origin_ON_mean_minus_this_scan_mean'] == origin_mean - float(rows.mean()),
                'Saved origin-ON comparison is not subtraction of the saved signed means')
        if (j + 1) % 128 == 0:
            qa_enforce()
    require(len(seen) == 11369 and mapping.size - len(seen) == 61, 'Unique geometry coverage/alias count differs')
    return arrays, {'member_records_checked': 1905, 'logical_scan_profiles_checked': 11430,
        'logical_rows_checked': 182880, 'unique_geometries_checked': 11369,
        'unique_geometry_rows_checked': 181904, 'aliases_checked': 61, 'old_geometry_overlap': 0,
        'stored_denominators_byte_checked': 96, 'saved_JSON_median_values_not_recomputed': medians_not_recomputed}


def authenticate_raw_rows(np, h5py, scope, source, arrays):
    centers = arrays['geometry_source_channel_centers']
    scans = arrays['geometry_scan_indices']; offsets = arrays['source_channel_offsets']
    stored_sha = arrays['geometry_raw_row_SHA256']
    require([r['scan_id'] for r in scope['compact_records']] == list(SCANS), 'Six original source compacts required')
    authenticated, digest_rows, cells = [], 0, 0
    for s, scan in enumerate(SCANS):
        rec = scope['compact_records'][s]
        identity = next(x for x in source['sources'] if x['label'] == scan)
        group = np.flatnonzero(scans == s)
        require(len(rec['decoded_rows']) == 16 and len(group) > 0, 'Sixteen declared rows per source scan required')
        with h5py.File(rec['file_pin']['path'], 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                and data.attrs['original_source_url'] == identity['url']
                and data.attrs['original_source_etag'] == identity['etag'], 'Authenticated compact header/source identity differs')
            for row, rp in enumerate(rec['decoded_rows']):
                values = data[row, 0, :]
                require(values.shape == (COUNT,) and values.dtype.str == '<f4'
                    and rp['time_row'] == row and rp['decoded_bytes'] == COUNT * 4
                    and hashlib.sha256(values.tobytes(order='C')).hexdigest() == rp['decoded_sha256'],
                    'Independent full decoded source row SHA differs from original acquisition')
                # Byte selection only: no float promotion/division/profile arithmetic.
                indices = centers[group, row, None] - C0 + offsets[None, :]
                selected = values[indices]
                require(selected.dtype.str == '<f4' and selected.shape == (len(group), 129), 'Selected raw row shape/endian differs')
                for n, g in enumerate(group):
                    actual = hashlib.sha256(selected[n].tobytes(order='C')).digest()
                    require(actual == stored_sha[int(g), row].tobytes(order='C'),
                        'Independent129-cell raw-row digest differs from stored output digest')
                    digest_rows += 1;cells += 129
                del values, indices, selected
                qa_enforce()
        authenticated.append({'scan_id': scan, 'file_pin': rec['file_pin'], 'decoded_rows_authenticated_once': 16,
            'geometry_count': int(len(group)), 'geometry_row_digests_checked': int(len(group)) * 16})
    require(len(authenticated) == 6 and digest_rows == 181904 and cells == 23465616,
        'All unique geometry source digest counts differ')
    return authenticated, {'compact_files_opened_once': 6, 'full_source_rows_decoded_authenticated_once': 96,
        'full_source_float32_cells_SHA_authenticated': 100663296,
        'selected_geometry_row_digests_checked': digest_rows,
        'unique_geometry_raw_cell_occurrences_digest_checked': cells,
        'logical_raw_cell_occurrences': 23591520}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('scope', 'expected-scope-sha256', 'expected-admission-sha256', 'expected-outer-sha256',
                 'expected-qa-sha256', 'freeze-commit', 'qa-freeze-commit'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--root-go-after-profile-complete', action='store_true');args = p.parse_args()
    require(args.root_go_after_profile_complete
        and all(re.fullmatch(r'[0-9a-f]{64}', getattr(args, n)) for n in ('expected_scope_sha256',
            'expected_admission_sha256', 'expected_outer_sha256', 'expected_qa_sha256'))
        and all(re.fullmatch(r'[0-9a-f]{40}', getattr(args, n)) for n in ('freeze_commit', 'qa_freeze_commit')),
        'Actual SHA pins, separate public QA freeze and explicit root post-COMPLETE GO required')
    require(digest(__file__) == args.expected_qa_sha256, 'Frozen independent QA source differs')
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    def limit(signum, frame):
        raise ResourceLimitExceeded('OS independent QA resource limit ' + str(signum))
    signal.signal(signal.SIGALRM, limit);signal.signal(signal.SIGXCPU, limit);signal.alarm(1800)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 122))
    resource.setrlimit(resource.RLIMIT_AS, (QA_MEMORY_CAP, QA_MEMORY_CAP))
    pins = {}
    collect_pin(pin(Path(__file__), args.expected_qa_sha256), pins)
    scope_pin, scope = add_json(checked_file(args.scope), pins, args.expected_scope_sha256)
    stage = Path(scope['output_directory']).parent
    require(stage.is_absolute() and stage.resolve() == stage
        and stage == Path(__file__).parents[2] / 'results' / FAMILY, 'Canonical QA stage required')
    review = stage / 'review'
    require(not review.is_symlink(), 'QA review directory may not be a symlink')
    review.mkdir(exist_ok=True)
    require(not any((review / name).exists() for name in ('QA_STARTED_ONCE.json', 'QA_RECEIPT.json',
        'QA_FAILURE_RECEIPT.json', 'QA_RECEIPT.json.prepared')), 'Independent QA is one-shot without retry/resume')
    save_new(review / 'QA_STARTED_ONCE.json', {'status': 'STARTED_ONCE_INDEPENDENT_OUTPUT_AND_RAW_ROW_DIGEST_QA',
        'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256,
        'qa_script_sha256': args.expected_qa_sha256, 'public_profile_freeze_commit': args.freeze_commit,
        'public_QA_freeze_commit': args.qa_freeze_commit, 'expected_outer_sha256': args.expected_outer_sha256})
    owner_handles, profile_gate, committed = [], None, False
    try:
        # Hold original guards and the completed profile's own inode before
        # even opaque H5 byte checks; all later source access remains readonly.
        require(len(scope['owner_kernel_guard_paths']) == 7, 'Exactly seven original171 guards required')
        owner_handles = acquire_owner_guards(scope)
        verify_no_live_owner_processes(scope)
        gp = checked_file(scope['serial_gate_path'])
        require(gp == stage / 'SERIAL_ACTIVE.flock', 'Canonical original profile process gate required')
        profile_gate = os.fdopen(os.open(gp, os.O_RDONLY | os.O_NOFOLLOW), 'rb', buffering=0)
        fcntl.flock(profile_gate.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        gate_stat = os.fstat(profile_gate.fileno())
        require(gp.stat().st_ino == gate_stat.st_ino and gp.stat().st_dev == gate_stat.st_dev,
            'Original profile gate was replaced')
        out, stage, execution, index, source, norm, members, oldgeo = closed_contract(args, scope, pins)
        roots = [Path(x) for x in scope['shared_workspace_roots']]
        for path in (Path(scope['source_root']), stage, Path(__file__), scope_pin['path']):
            path = Path(path)
            require(path.is_absolute() and path.resolve() == path
                and any(path == r or r in path.parents for r in roots), 'Shared disk roots omit QA/source/code')
        require(tree_size(scope['shared_workspace_roots']) + OUTPUT_CAP <= WORKSPACE_CAP,
            'Fresh QA shared12GiB gate plus128MiB reservation fails')
        free = os.statvfs(review)
        require(free.f_bavail * free.f_frsize >= OUTPUT_CAP, 'Physical free space below QA128MiB reservation')
        qa_enforce()
        for pkg, version in {'numpy': '2.3.5', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}.items():
            require(importlib.metadata.version(pkg) == version, 'Frozen QA codec runtime differs: ' + pkg)
        import numpy as np
        import h5py
        import hdf5plugin
        require(h5py.version.hdf5_version == '1.14.6' and np.dtype('<f4').isnative,
            'Frozen independent QA HDF5/endian differs')
        arrays, output_counts = verify_outputs(np, scope, out, index, source, norm, members, oldgeo, pins)
        verified_source, source_counts = authenticate_raw_rows(np, h5py, scope, source, arrays)
        for item in pins.values():
            verify_pin(item)
        verify_no_live_owner_processes(scope)
        for handle, name in zip(owner_handles, scope['owner_kernel_guard_paths']):
            held = os.fstat(handle.fileno());now = Path(name).stat()
            require((held.st_ino, held.st_dev) == (now.st_ino, now.st_dev), 'An original171 guard was replaced')
        require((gp.stat().st_ino, gp.stat().st_dev) == (gate_stat.st_ino, gate_stat.st_dev), 'Original profile gate was replaced')
        require(tree_size(scope['shared_workspace_roots']) + 1048576 <= WORKSPACE_CAP
            and tree_size([str(review)]) < OUTPUT_CAP - 1048576, 'Final QA disk lacks1MiB publication headroom')
        terminal = {'schema': 'SETI_S2017_CROSS_ON_FIXED_PROFILE_OUTPUT_SOURCE_DIGEST_QA_V1',
            'status': QA_STATUS, 'family_id': FAMILY, 'public_profile_freeze_commit': args.freeze_commit,
            'public_QA_freeze_commit': args.qa_freeze_commit, 'scope_sha256': args.expected_scope_sha256,
            'qa_script_sha256': args.expected_qa_sha256, 'profile_script_sha256': execution['script_sha256'],
            'execution_receipt_sha256': pins[str(out / 'EXECUTION_RECEIPT.json')]['sha256'],
            'outer_execution_receipt_sha256': args.expected_outer_sha256,
            'selected_members_sha256': scope['selected_members_sha256'],
            'ordered_geometry_sha256': scope['ordered_geometry_sha256'],
            'counts': {**output_counts, **source_counts}, 'verified_source_inputs': verified_source,
            'all_input_byte_pins': list(pins.values()), 'all_input_end_readbacks_exact': True,
            'original_source_raw_rows_authenticated': True, 'selected_raw_row_SHA256_digests_independently_matched': True,
            'profiles_remeasured': False, 'profile_kernel_reexecuted': False,
            'normalization_reexecuted': False, 'flank_or_full_native_medians_recomputed': False,
            'detector_or_preprocessing_reexecuted': False, 'nearest_matching_reexecuted': False,
            'source_HDF5_files_opened_readonly': True, 'new_scientific_hypothesis_combinations': 0,
            'new_HTTP_requests': 0, 'new_source_BODY_bytes': 0, 'cost_DKK': 0,
            'CPU_cap_s': QA_CPU_CAP, 'CPU_hard_limit_s': 122, 'wall_cap_s': QA_WALL_CAP,
            'memory_cap_bytes': QA_MEMORY_CAP, 'output_reservation_bytes': OUTPUT_CAP,
            'shared_workspace_cap_bytes': WORKSPACE_CAP,
            'limits': ['Raw SHA equality authenticates selected cell bytes; no independent normalized/flank/profile-kernel arithmetic reproduction.',
                'Stored JSON median values are checked for finiteness and saved-row bounds, not recomputed.',
                'Saved signed residual scalar copies and means are checked internally; no new ranking or candidate threshold.',
                'These remain posthoc same-visit selected descriptive profiles, not calibrated SNR/FAP, OFF veto or origin classification.'],
            **qa_enforce()}
        publish_qa(review / 'QA_RECEIPT.json', terminal, scope['shared_workspace_roots'], review)
        committed = True
        try:
            print(json.dumps({'status': QA_STATUS, 'counts': terminal['counts'],
                **{k: terminal[k] for k in ('process_CPU_seconds_including_imports', 'wall_seconds', 'peak_RSS_bytes')}}), flush=True)
        except BrokenPipeError:
            pass
    except BaseException as exc:
        if not committed and not (review / 'QA_RECEIPT.json').exists():
            save_new(review / 'QA_FAILURE_RECEIPT.json', {'status': 'FAILED_ONE_SHOT_INDEPENDENT_QA_NO_RETRY',
                'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256,
                'qa_script_sha256': args.expected_qa_sha256, 'error_type': type(exc).__name__,
                'error': str(exc), 'partial_evidence_preserved': True, **qa_usage()})
        raise
    finally:
        signal.alarm(0)
        if profile_gate is not None:
            profile_gate.close()
        for handle in owner_handles:
            handle.close()


if __name__ == '__main__':
    main()
