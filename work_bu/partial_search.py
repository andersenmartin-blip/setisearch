"""Prospective partial HIP44295 local-ESS adapter; no import-time power access.

The three BN numerical functions are compiled without editing their AST. BO's
generic strict NPY reader is transport only; its HIP45688 binding is not used.
The original BB/BC/BE six-scan acquisition and BA coverage remain incomplete.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import signal
import statistics
import sys

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BN = ROOT / 'work_bu/vendor/bounded_search_bn.py'
BN_SHA = '7f2e10f1814c29f60808712321e2a904f4dc6716ed7b85b15853a9b928824062'
WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
BATCHES = [list(range(start, start + 8)) for start in (1, 9, 17, 25)]
IDS = (65133, 65135, 65137, 65139, 65141)
TARGETS = ('HIP44295', 'HIP43151', 'HIP44295', 'HIP43162', 'HIP44295')
TSTARTS = (57660.61375, 57660.6178125, 57660.62186342593,
           57660.62590277778, 57660.62993055556)
NUMERIC_FUNCTIONS = ('drift_rates', 'local_maximum', 'search_scan')
CALIBRATION_DOMAIN = 'Each selected4096channelqcore at its own fixedstride, independently for each scan,width,drift'
SCOPE_NUMERICS = {
    'complete_scans': 5, 'rows_per_scan': 16, 'q_count': 32, 'scan_q_searches': 160,
    'drift_rates': 839, 'track_combinations_per_scan_q': 9020928,
    'track_combinations_per_batch': 360837120, 'track_combinations_total': 1443348480,
    'selected_independent_scalar_checks_per_batch': 1440,
    'shared_kernel_calibration_vector_replays_per_batch': 480,
    'selected_carrier_channels': 131072, 'technical_channel_bin_width_hz': 366210.9375,
    'complete_OFF_support': False, 'original_coverage_credit': 0,
    'calibrated_FAP': False, 'calibrated_astronomical_sensitivity': False,
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def save_npz(path, arrays):
    path = Path(path)
    require(all(not np.asarray(value).dtype.hasobject for value in arrays.values()), 'Object arrays forbidden')
    with path.open('xb') as stream:
        np.savez_compressed(stream, **arrays); stream.flush(); os.fsync(stream.fileno())
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def load_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def required_source_pins():
    """All source dependencies read by this adapter, including BO pin checks."""
    paths = [Path(__file__).resolve(), BN, ROOT/'work_bo/src/methods.py',
             ROOT/'work_bo/src/npy_adapter.py', ROOT/'work_bo/vendor/current/kernel_v.py',
             ROOT/'work_bo/vendor/current/continuous_normalization_ac.py',
             ROOT/'work_bo/vendor/legacy/search_pilot.py', ROOT/'work_bo/vendor/legacy/run_pilot.py']
    return {str(path): sha(path) for path in paths}


def load_numerics():
    require(sha(BN) == BN_SHA, 'Exact frozen BN source differs')
    methods = module_at('bu_bo_methods', ROOT / 'work_bo/src/methods.py')
    kernel, normalizer = methods.load_current()
    tree = ast.parse(BN.read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in NUMERIC_FUNCTIONS]
    require(tuple(node.name for node in nodes) == NUMERIC_FUNCTIONS, 'Exact numerical function set differs')
    pure_tree = ast.Module(body=nodes, type_ignores=[])
    namespace = {'np': np, 'math': math, 'kernel': kernel, 'WIDTHS': WIDTHS,
                 'STRIDES': STRIDES, 'require': require}
    exec(compile(pure_tree, str(BN), 'exec'), namespace)
    # No historical module imports or HDF5 codec activation occur here.
    return kernel, normalizer, namespace


def verify_header_content(scope, index, header):
    """Bind actual HDF5 attributes; archive catalogue MJD is not sample zero."""
    attrs = header['attrs']; archive = header['archive']
    require(header['scan'] == index and header['shape'] == [16,1,359661568], 'Original HDF5 geometry differs')
    require(archive['id'] == IDS[index] and archive['target'] == TARGETS[index]
            and attrs['source_name'] == TARGETS[index], 'Header/archive source identity differs')
    expected = {'tstart': TSTARTS[index], 'tsamp': 18.253611008,
                'fch1': 2802.83203125, 'foff': -2.7939677238464355e-06,
                'nchans': 359661568, 'nbits': 32, 'nifs': 1}
    require(all(attrs[key] == value for key,value in expected.items()), 'Frozen original header attributes differ')
    binding = {'header_tstart_mjd': attrs['tstart'], 'dt_seconds': attrs['tsamp'],
               'df_hz': attrs['foff']*1e6, 'source_header_first_frequency_mhz': attrs['fch1'],
               'source_nchannels': attrs['nchans']}
    require(all(scope[key] == value for key,value in binding.items()), 'Plan geometry is not bound to original attributes')
    chunks = header['chunks']
    require(len(chunks) == 16 and [chunk['time_index'] for chunk in chunks] == list(range(16)), 'Sixteen original row descriptors required')
    require(all(chunk['scan'] == index and chunk['chunk_offset'] == [row,0,179306496]
                and chunk['filter_mask'] == 0 and chunk['size'] > 0
                for row,chunk in enumerate(chunks)), 'Original native row coordinate binding differs')
    return binding


def validate_plan(plan, planpath, check_inputs=True):
    require(plan['schema'] == 'SETI_BU_PARTIAL_HIP44295_LOCAL_Q_ESS_V1', 'Wrong prospective family')
    require(plan['core_q_list'] == list(range(1, 33)) and plan['batch_q_lists'] == BATCHES, 'Fixed four-batch scope differs')
    require(plan['native_channel_start'] == 179306496 and plan['native_channel_count'] == 1048576, 'Native171 geometry differs')
    require(plan['core_width_channels'] == plan['support_halo_channels'] == plan['bandpass_block_channels'] == 4096, 'Core/halo/normalizer differs')
    require(plan['widths_channels'] == list(WIDTHS) and plan['strides'] == list(STRIDES), 'Width/stride family differs')
    require(plan['max_abs_drift_hz_s'] == 4 and plan['threshold_ess'] == 10 and plan['off_flag_threshold_ess'] == 5, 'Frozen thresholds differ')
    require(plan['calibration_domain'] == CALIBRATION_DOMAIN, 'Local-q calibration domain must be explicit')
    require(plan['previously_acquired_data'] is True and plan['new_independent_observation'] is False,
            'Acquired 2016 data are not a new independent observation epoch')
    require(plan['missing_scan'] == 5 and plan['complete_OFF_support'] is False, 'Missing OFF5 must stay explicit')
    require(plan['new_archive_requests_authorized'] == 0 and plan['original_coverage_credit'] == 0, 'No archive requests or original coverage credit')
    require(np.__version__ == '2.3.5', 'Pinned NumPy runtime differs')
    sources = plan['source_sha256']
    require(all(path in sources for path in required_source_pins()), 'Adapter, transport, and exact numerical sources must be pinned')
    for path, digest in sources.items():
        require(sha(path) == digest, 'Source bytes differ: ' + path)
    require(sources[str(BN)] == BN_SHA, 'BN digest differs')
    require(plan['metadata_evidence'], 'Separately authenticated metadata evidence required')
    for evidence in plan['metadata_evidence']:
        require(sha(evidence['path']) == evidence['sha256'], 'Metadata evidence changed')
    scopes = plan['scans']
    require([s['scan'] for s in scopes] == list(range(5)), 'Only complete scans0..4 are admitted; OFF5 forbidden')
    for index, scope in enumerate(scopes):
        require(scope['role'] == ('ON' if index % 2 == 0 else 'OFF') and scope['archive_id'] == IDS[index]
                and scope['target'] == TARGETS[index], 'Scan/source identity differs')
        require(scope['nrows'] == 16 and scope['nchannels'] == 1048576, 'Full sixteen-row native scan required')
        require(scope['dt_seconds'] == 18.253611008 and scope['df_hz'] == -2.7939677238464355, 'Header sampling differs')
        require(scope['header_tstart_mjd'] == TSTARTS[index], 'Source epoch differs')
        expected_midpoint = scope['header_tstart_mjd'] + 7.5 * scope['dt_seconds'] / 86400
        require(scope['tref_midpoint_mjd'] == expected_midpoint, 'Midpoint convention differs')
        first = scope['source_header_first_frequency_mhz'] + 179306496 * scope['df_hz'] / 1e6
        require(scope['fch1_mhz'] == first and math.isfinite(first), 'Native first-channel frequency binding differs')
        require(type(scope['source_nchannels']) is int and scope['source_nchannels'] >= 180355072, 'Original source channel extent differs')
        require(sha(scope['header_path']) == scope['header_sha256'], 'Original header evidence differs')
        verify_header_content(scope,index,read(scope['header_path']))
        if check_inputs:
            require(Path(scope['path']).stat().st_size == scope['input_bytes'] and sha(scope['path']) == scope['input_sha256'], 'Input NPY bytes differ')
    require(len({s['fch1_mhz'] for s in scopes}) == 1, 'Destination native grids differ')
    span = (max(s['tref_midpoint_mjd'] for s in scopes) - min(s['tref_midpoint_mjd'] for s in scopes)) * 86400
    maximum_shift = math.ceil(4 * (span + 7.5 * scopes[0]['dt_seconds']) / abs(scopes[0]['df_hz'])) + 16
    radius = math.ceil(1 + .5 * (8 / 838) * span / abs(scopes[0]['df_hz']))
    require(maximum_shift + radius < 4096, 'Frozen support halo is insufficient')
    require(Path(planpath).is_file(), 'Saved plan required')
    return plan


def prepare_inputs(plan, planpath, out, qs, normalizer):
    adapter = module_at('bu_bo_npy_adapter', ROOT / 'work_bo/src/npy_adapter.py')
    lo, hi = max(0, min(qs)*4096-4096), min(1048576, (max(qs)+1)*4096+4096)
    records = []
    for scope in plan['scans']:
        rows = tuple(scope['row_sha256']) if scope.get('row_sha256') is not None else None
        pin = adapter.NpyPin(scope['input_bytes'], scope['input_sha256'], scope['powers_sha256'], row_sha256=rows)
        with adapter.open_verified_npy(scope['path'], pin, require_nonnegative=True) as opened:
            normalized, anchors = normalizer.normalize(opened.array, 4096)
            crop = normalized[:, lo:hi].copy()
            del normalized
            receipt = dict(opened.receipt)
        path = out / ('scan%d_normalized_support.npy' % scope['scan'])
        with path.open('xb') as stream:
            np.save(stream, crop, allow_pickle=False); stream.flush(); os.fsync(stream.fileno())
        anchor_pub = save_npz(out / ('scan%d_fullnative_anchor_audit.npz' % scope['scan']), anchors)
        records.append({'scan': scope['scan'], 'support_start': lo, 'support_stop': hi,
                        'normalized_support_path': str(path.resolve()), 'normalized_support_sha256': sha(path),
                        'anchor_audit': anchor_pub, 'input_transport_receipt': receipt})
        print(json.dumps({'event': 'FULL_NATIVE_NORMALIZATION_COMPLETE', 'scan': scope['scan'], 'support': [lo, hi]}), flush=True)
    result = {'schema': 'SETI_BU_NORMALIZED_INPUTS_V1', 'plan_sha256': sha(planpath), 'q_list': qs,
              'scans': records, 'full_native_channel_count': 1048576, 'missing_scan': 5,
              'normalization_version': normalizer.VERSION}
    write(out/'NORMALIZED_INPUTS_COMPLETE.json', result)
    return result


def classify_partial(center_scores, max_scores, valid):
    require(center_scores.shape == max_scores.shape == valid.shape and center_scores.ndim == 2
            and center_scores.shape[1] == 6, 'Explicit six-slot association geometry required')
    require(not valid[:,5].any() and np.isnan(center_scores[:,5]).all() and np.isnan(max_scores[:,5]).all(), 'OFF5 must remain missing, never zero-filled')
    supported = valid[:,:5].all(axis=1)
    on3 = valid[:,[0,2,4]].all(axis=1) & (center_scores[:,[0,2,4]] >= 10).all(axis=1)
    off_veto = ((max_scores[:,[1,3]] >= 5) & valid[:,[1,3]]).any(axis=1)
    status = np.full(len(valid), 'UNSUPPORTED', dtype='<U28')
    status[supported & ~on3] = 'THREE_ON_FAIL'
    status[supported & on3 & off_veto] = 'REJECTED_AVAILABLE_OFF'
    status[supported & on3 & ~off_veto] = 'INCOMPLETE_OFF_COVERAGE'
    return {'available_scans_supported': supported, 'three_ON_pass': on3,
            'available_OFF_veto': off_veto, 'complete_OFF_support': np.zeros(len(valid), dtype=np.bool_),
            'candidate_status': status}


def associate_partial(plan, records, grids, catalogs, kernel, supports):
    pieces = []
    for scan in (0,2,4):
        catalog = dict(catalogs[scan])
        catalog['source_scan'] = np.full(len(catalog['ess']), scan, dtype=np.int8)
        pieces.append(catalog)
    seeds = {key: np.concatenate([c[key] for c in pieces]) for key in pieces[0]}
    n = len(seeds['ess']); require(n <= 3000000, 'Finite ON seed cap reached')
    center_scores = np.full((n,6), np.nan)
    maximum_scores = np.full((n,6), np.nan)
    valid = np.zeros((n,6), dtype=np.bool_)
    predicted = np.full((n,6), -1, dtype=np.int32)
    for scope, record, grid, y in zip(plan['scans'], records, grids, supports):
        scan = scope['scan']; rates = grid['drift_hz_s']
        gaps = np.array([(scope['tref_midpoint_mjd']-src['tref_midpoint_mjd'])*86400 for src in plan['scans']])[seeds['source_scan']]
        frequencies = seeds['frequency_at_midpoint_mhz'] + seeds['drift_hz_s'] * gaps / 1e6
        centers = np.rint((frequencies-scope['fch1_mhz'])*1e6/scope['df_hz']).astype(np.int32)-record['support_start']
        predicted[:,scan] = centers + record['support_start']
        radii = np.ceil(1+.5*(rates[1]-rates[0])*np.abs(gaps)/abs(scope['df_hz'])).astype(np.int64)
        for width in WIDTHS:
            prepared = kernel.boxcars(y, width)
            for ri in np.unique(seeds['drift_index'][seeds['width_channels'] == width]):
                rows = np.flatnonzero((seeds['width_channels']==width)&(seeds['drift_index']==ri))
                offsets = grid['offsets'][ri]
                for radius in np.unique(radii[rows]):
                    selected = rows[radii[rows] == radius]; c = centers[selected]
                    supported = (c+int(offsets.min())-width//2-radius >= 0)&(c+int(offsets.max())+width//2+radius < y.shape[1])
                    selected = selected[supported]; c = c[supported]
                    if not len(selected):
                        continue
                    requested = (c[:,None]+np.arange(-int(radius),int(radius)+1)[None,:]).ravel()
                    unique, inverse = np.unique(requested, return_inverse=True)
                    sums = kernel.tracks_selected(y,prepared,offsets,unique,width)[0]
                    median, scale = grid[f'calibration_width_{width}'][ri]
                    scores = ((sums-median)/scale)[inverse].reshape(len(selected),2*int(radius)+1)
                    require(np.isfinite(scores).all(), 'Nonfinite forced score')
                    center_scores[selected,scan] = scores[:,int(radius)]
                    maximum_scores[selected,scan] = scores.max(axis=1)
                    valid[selected,scan] = True
    source_error = np.abs(center_scores[np.arange(n), seeds['source_scan']]-seeds['ess'])
    require(np.isfinite(source_error).all() and (source_error == 0).all(), 'Forced source score differs from exact search')
    classified = classify_partial(center_scores, maximum_scores, valid)
    arrays = {'seed_'+key: value for key,value in seeds.items()}
    arrays.update(forced_center_local_ess=center_scores, forced_neighborhood_max_local_ess=maximum_scores,
                  forced_valid=valid, predicted_native_center=predicted, source_ess_error=source_error, **classified)
    counts = {label: int((classified['candidate_status'] == label).sum()) for label in
              ('REJECTED_AVAILABLE_OFF','INCOMPLETE_OFF_COVERAGE','THREE_ON_FAIL','UNSUPPORTED')}
    summary = {'ON_local_catalog_rows': n, 'available_measurement_slots': n*5,
               'supported_available_slots': int(valid[:,:5].sum()), 'missing_OFF5_slots': n,
               'three_ON_pass_rows': int(classified['three_ON_pass'].sum()),
               'available_OFF_veto_rows': int(classified['available_OFF_veto'].sum()),
               'status_counts': counts, 'complete_OFF_support': False,
               'full_cadence_candidate_assessment': 'NOT_EVALUABLE_MISSING_OFF5',
               'maximum_source_ess_error': float(source_error.max(initial=0))}
    return arrays, summary


def run_batch(planpath, out, batch_number):
    planpath, out = Path(planpath), Path(out)
    plan = validate_plan(read(planpath), planpath)
    require(type(batch_number) is int and 1 <= batch_number <= 4, 'Batch number must be1..4')
    require(not out.exists(), 'No output overwrite or rerun')
    initial_plan_sha = sha(planpath)
    kernel, normalizer, numeric = load_numerics()
    qs = BATCHES[batch_number-1]
    out.mkdir(parents=True)
    write(out/'BATCH_START.json', {'batch': batch_number, 'q_list': qs, 'plan_sha256': initial_plan_sha,
                                  'started_utc': datetime.now(timezone.utc).isoformat()})
    prepared = prepare_inputs(plan, planpath, out, qs, normalizer)
    supports = [np.load(record['normalized_support_path'], mmap_mode='r', allow_pickle=False) for record in prepared['scans']]
    results = []
    for q in qs:
        dest = out / f'q{q:03d}'; dest.mkdir()
        grids, catalogs, summaries = [], [], []
        for scope, record, y in zip(plan['scans'], prepared['scans'], supports):
            grid, audit, catalog, summary = numeric['search_scan'](y, scope, plan, record['support_start'], q)
            summary['publications'] = [save_npz(dest/f'scan{scope["scan"]}_{label}.npz', arrays)
                                       for label,arrays in [('grid',grid),('audit',audit),('catalog',catalog)]]
            write(dest/f'scan{scope["scan"]}_summary.json', summary)
            grids.append(grid); catalogs.append(catalog); summaries.append(summary)
            print(json.dumps({'event': 'SCAN_Q_SEARCH_COMPLETE', 'scan': scope['scan'], 'q': q,
                              'local_hits': summary['local_hits']}), flush=True)
        arrays, association = associate_partial(plan, prepared['scans'], grids, catalogs, kernel, supports)
        association['publication'] = save_npz(dest/'PARTIAL_ASSOCIATION.npz', arrays)
        q_result = {'q': q, 'scans': summaries, 'association': association,
                    'track_trials': sum(item['track_trials'] for item in summaries),
                    'status': 'FIVE_SCAN_PARTIAL_EXPLORATORY_COMPLETE', 'plan_sha256': initial_plan_sha}
        require(q_result['track_trials'] == 45104640, 'Fixed five-scan track count differs')
        write(dest/'PARTIAL_Q_COMPLETE.json', q_result); results.append(q_result)
    validate_plan(plan, planpath)
    require(sha(planpath) == initial_plan_sha, 'Frozen plan changed')
    result = {'schema': 'SETI_BU_PARTIAL_BATCH_V1', 'status': 'PARTIAL_BATCH_COMPLETE_AUDIT_PENDING',
              'batch': batch_number, 'q_list': qs, 'plan_sha256': initial_plan_sha, 'results': results,
              'track_trials': sum(item['track_trials'] for item in results), 'complete_OFF_support': False,
              'full_cadence_candidate_assessment': 'NOT_EVALUABLE_MISSING_OFF5', 'original_coverage_credit': 0,
              'new_archive_requests': 0, 'new_observation_epochs': 0, 'calibrated_FAP': False,
              'completed_utc': datetime.now(timezone.utc).isoformat()}
    write(out/'BATCH_COMPLETE.json', result)
    return result


def bounded_run_batch(planpath, out, batch_number):
    def expired(signum, frame):
        raise TimeoutError('BU fixed 600-second batch budget reached')
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(600)
    try:
        return run_batch(planpath,out,batch_number)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM,previous)


def scalar_sum(y, offsets, center, width):
    half = width//2
    return math.fsum(float(y[row,center+int(offset)+delta]) for row,offset in enumerate(offsets)
                     for delta in range(-half,half+1))


def audit_batch(planpath, out):
    planpath, out = Path(planpath), Path(out)
    plan = validate_plan(read(planpath), planpath)
    result = read(out/'BATCH_COMPLETE.json'); ph = sha(planpath)
    require(result['plan_sha256'] == ph and result['q_list'] == BATCHES[result['batch']-1], 'Batch binding differs')
    prepared = read(out/'NORMALIZED_INPUTS_COMPLETE.json')
    require(prepared['plan_sha256'] == ph and prepared['q_list'] == result['q_list'], 'Normalization binding differs')
    kernel, _, numeric = load_numerics()
    rates = numeric['drift_rates'](plan)
    times = (np.arange(16,dtype=np.float64)-7.5)*plan['scans'][0]['dt_seconds']
    offsets = np.rint(rates[:,None]*times[None,:]/plan['scans'][0]['df_hz']).astype(np.int32)
    supports = []
    for record in prepared['scans']:
        require(sha(record['normalized_support_path']) == record['normalized_support_sha256'], 'Saved support changed')
        require(sha(record['anchor_audit']['path']) == record['anchor_audit']['sha256'], 'Saved anchors changed')
        supports.append(np.load(record['normalized_support_path'],mmap_mode='r',allow_pickle=False))
    checks = vectors = 0; maximum_error = maximum_calibration_error = 0.0
    for inline in result['results']:
        q = inline['q']; dest = out/f'q{q:03d}'; saved = read(dest/'PARTIAL_Q_COMPLETE.json')
        require(saved == inline, 'Batch/q result differs')
        grids, catalogs = [], []
        for scope, record, y, summary in zip(plan['scans'],prepared['scans'],supports,saved['scans']):
            scan = scope['scan']; require(read(dest/f'scan{scan}_summary.json') == summary, 'Saved scan summary differs')
            for pub in summary['publications']:
                require(sha(pub['path']) == pub['sha256'] and Path(pub['path']).stat().st_size == pub['bytes'], 'Saved scan publication changed')
            grid, audit, catalog = [load_npz(dest/f'scan{scan}_{label}.npz') for label in ('grid','audit','catalog')]
            require(np.array_equal(grid['drift_hz_s'],rates) and np.array_equal(grid['offsets'],offsets), 'Grid differs')
            require(len(catalog['ess']) == summary['local_hits'] and (catalog['ess'] >= 10).all(), 'Catalog count/threshold differs')
            grids.append(grid); catalogs.append(catalog)
            for width,stride in zip(WIDTHS,STRIDES):
                centers = np.arange(q*4096,(q+1)*4096,stride,dtype=np.int32)
                require(np.array_equal(grid[f'centers_width_{width}'],centers), 'Search centers differ')
                sample = centers[[0,len(centers)//2,len(centers)-1]]
                require(np.array_equal(audit[f'scalar_centers_width_{width}'],sample)
                        and np.array_equal(audit[f'scalar_ris_width_{width}'],[0,419,838]), 'Audit coordinates differ')
                boxcars = kernel.boxcars(y,width)
                for row,ri in enumerate((0,419,838)):
                    replay = kernel.tracks_grid(y,boxcars,offsets[ri],q*4096-record['support_start'],(q+1)*4096-record['support_start'],stride,width)[0]
                    median = statistics.median(float(value) for value in replay)
                    scale = 1.4826*statistics.median(abs(float(value)-median) for value in replay)
                    error = max(abs(median-grid[f'calibration_width_{width}'][ri,0]),abs(scale-grid[f'calibration_width_{width}'][ri,1]))
                    require(error <= 1e-10*max(abs(median),abs(scale),1), 'Saved calibration differs')
                    vectors += 1; maximum_calibration_error = max(maximum_calibration_error,float(error))
                    for column,center in enumerate(sample):
                        value = scalar_sum(y,offsets[ri],int(center)-record['support_start'],width)
                        error = abs(value-float(audit[f'scalar_sums_width_{width}'][row,column]))
                        require(error < 5e-5, 'Independent selected scalar sum differs')
                        checks += 1; maximum_error = max(maximum_error,error)
        pub = saved['association']['publication']; require(sha(pub['path']) == pub['sha256'], 'Saved association changed')
        association = load_npz(pub['path'])
        replay, summary = associate_partial(plan,prepared['scans'],grids,catalogs,kernel,supports)
        require(set(replay) == set(association), 'Association columns differ')
        for key in replay:
            equal = np.array_equal(replay[key],association[key],equal_nan=True) if replay[key].dtype.kind == 'f' else np.array_equal(replay[key],association[key])
            require(equal, 'Saved association replay differs: '+key)
        require(summary == {key:value for key,value in saved['association'].items() if key != 'publication'}, 'Association summary differs')
    require(checks == len(result['q_list'])*180 and vectors == len(result['q_list'])*60, 'Finite audit counts differ')
    return {'schema':'SETI_BU_PARTIAL_AUDIT_V1','status':'PASS_BOUNDED_SAVED_RESULT_AUDIT','plan_sha256':ph,
            'batch_complete_sha256':sha(out/'BATCH_COMPLETE.json'),'q_list':result['q_list'],
            'independent_selected_scalar_checks':checks,'shared_kernel_calibration_vector_replays':vectors,
            'maximum_scalar_error':maximum_error,'maximum_calibration_error':maximum_calibration_error,
            'association_replay':'SAME_UNCHANGED_KERNEL_AND_PARTIAL_ADAPTER_NOT_INDEPENDENT',
            'complete_OFF_support':False,'full_cadence_candidate_assessment':'NOT_EVALUABLE_MISSING_OFF5'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path); parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--batch',type=int); parser.add_argument('--audit-receipt',type=Path)
    args = parser.parse_args()
    if args.audit_receipt is not None:
        require(args.batch is None,'Audit has no batch mutation argument')
        write(args.audit_receipt,audit_batch(args.plan,args.out))
    else:
        bounded_run_batch(args.plan,args.out,args.batch)
