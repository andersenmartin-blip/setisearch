"""Finite independent scalar and serialization audit of closed BI results.

Reads only saved normalized arrays/results after the complete marker exists.
No wrapper import, original telescope decode, network, or new search. Vector
calibration replays use the pinned shared kernel and are labeled accordingly.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'work_be/runtime'))
import numpy as np

WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def scalar_sum(y, offsets, center, width):
    half = width // 2
    return math.fsum(float(y[t, center + int(offsets[t]) + j])
                     for t in range(16) for j in range(-half, half + 1))


def audit(planpath, out, actualpath):
    planpath, out = Path(planpath).resolve(), Path(out).resolve()
    marker = out / 'ALL_FROZEN_Q_COMPLETE.json'
    require(marker.is_file(), 'All-eight-q completion marker required; partial runs are not final results')
    complete, plan = read(marker), read(planpath)
    ph = sha(planpath)
    require(complete['status'] == 'ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE'
            and complete['plan_sha256'] == ph, 'Whole-run completion/plan binding differs')
    require(complete['q_list'] == plan['core_q_list'] == list(range(17, 25)), 'Expected exactly frozen q17..24')
    require(plan['previously_exposed_data'] is True and plan['new_independent_observation'] is False
            and plan['new_archive_requests_authorized'] == 0, 'Exposure/access scope differs')
    require(plan['calibration_domain'] == 'Each selected4096channelqcore at its own fixedstride, independently for each scan,width,drift',
            'Local calibration scope differs')
    require(plan['widths_channels'] == list(WIDTHS) and plan['strides'] == list(STRIDES), 'Width/stride scope differs')
    pins = {str(planpath): ph}

    def pin(path, expected=None):
        path = Path(path).resolve()
        value = sha(path)
        require(expected is None or expected == value, 'Artifact hash differs: ' + str(path))
        require(str(path) not in pins or pins[str(path)] == value, 'Conflicting artifact pin')
        pins[str(path)] = value
        return path

    pin(marker)
    actualpath = pin(actualpath)
    actual = read(actualpath)
    require(actual['actual_exit_code'] == 0 and actual['stdout_eof'] is True
            and actual['child_wait_completed'] is True, 'Closed actual0 process receipt required')
    require(actual['plan_sha256'] == ph and Path(actual['result_path']).resolve() == marker
            and actual['result_sha256'] == sha(marker), 'Actual process is not bound to complete result')
    log = pin(actual['log_path'], actual['log_sha256'])
    require(log.stat().st_size == actual['log_bytes'] == actual['observed_stdout_bytes']
            and actual['log_sha256'] == actual['observed_stdout_sha256'], 'Observed stdout/log identity differs')
    for path, expected in plan['source_sha256'].items():
        pin(path, expected)
    require(actual['source_sha256'] in plan['source_sha256'].values(), 'Actual source is not plan-pinned')
    kernel_paths = [Path(path) for path in plan['source_sha256'] if Path(path).name == 'kernel_v.py']
    require(len(kernel_paths) == 1, 'One unchanged replay kernel required')
    spec = importlib.util.spec_from_file_location('bi_saved_result_replay_kernel', kernel_paths[0])
    replay_kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay_kernel)
    pin(plan['dataset_manifest_path'], plan['dataset_manifest_sha256'])
    scopes = plan['scans']
    require(len(scopes) == 6 and [s['scan'] for s in scopes] == list(range(6))
            and [s['role'] for s in scopes] == ['ON', 'OFF'] * 3, 'Ordered six-scan cadence differs')
    for scope in scopes:
        pin(scope['path'], scope['input_sha256'])
    normalized_path = pin(out / 'NORMALIZED_INPUTS_COMPLETE.json')
    normalized = read(normalized_path)
    require(normalized['status'] == 'PASS' and normalized['plan_sha256'] == ph
            and normalized['full_native_channel_count'] == 1048576 and len(normalized['scans']) == 6,
            'Full-native normalization marker differs')
    support = []
    for scope, record in zip(scopes, normalized['scans']):
        require(record['scan'] == scope['scan'] and record['input_sha256'] == scope['input_sha256'],
                'Normalized/source scan binding differs')
        path = pin(record['normalized_support_path'], record['normalized_support_sha256'])
        pin(record['anchor_audit']['path'], record['anchor_audit']['sha256'])
        matrix = np.load(path, mmap_mode='r', allow_pickle=False)
        require(matrix.shape == (16, record['support_stop'] - record['support_start'])
                and matrix.dtype == np.dtype('<f4') and np.isfinite(matrix).all(), 'Normalized support geometry/values differ')
        support.append(matrix)

    dt, df = scopes[0]['dt_seconds'], scopes[0]['df_hz']
    nside = math.ceil(4 * 16 * dt / abs(df))
    expected_rates = np.linspace(-4, 4, 2 * nside + 1, dtype=np.float64)
    require(len(expected_rates) == 839, 'Expected839 drift rates')
    times = (np.arange(16, dtype=np.float64) - 7.5) * dt
    expected_offsets = np.rint(expected_rates[:, None] * times[None, :] / df).astype(np.int32)
    sum_checks = forced_checks = tested_seeds = total_trials = replay_vectors = 0
    maximum_sum_error = maximum_forced_ess_error = 0.0
    maximum_calibration_error = 0.0
    q_reports = []
    for q, combined_triage in zip(plan['core_q_list'], complete['q_results']):
        dest = out / f'q{q:03d}'
        search_path, triage_path = pin(dest / 'SIX_SCAN_SEARCH_COMPLETE.json'), pin(dest / 'TRIAGE_RESULT.json')
        search, triage = read(search_path), read(triage_path)
        require(search['status'] == 'SIX_SCAN_DETECTOR_COMPLETE_TRIAGE_PENDING'
                and search['plan_sha256'] == triage['plan_sha256'] == ph
                and search['q'] == triage['q'] == q, 'q result/plan binding differs')
        require(triage == combined_triage and triage['status'] == 'BOUNDED_DESCRIPTIVE_SEARCH_COMPLETE',
                'Whole-run triage value differs from saved q result')
        require(len(search['scans']) == 6, 'Six saved scan summaries required')
        grids, catalogs = [], []
        q_trials = 0
        for scope, record, inline_summary in zip(scopes, normalized['scans'], search['scans']):
            scan = scope['scan']
            summary = read(pin(dest / f'scan{scan}_summary.json'))
            require(summary == inline_summary and summary['complete'] is True and summary['scan'] == scan
                    and summary['role'] == scope['role'] and summary['q'] == q, 'Saved scan summary differs')
            for publication in summary['publications']:
                path = pin(publication['path'], publication['sha256'])
                require(path.stat().st_size == publication['bytes'], 'Publication byte length differs')
            require({Path(p['path']).resolve() for p in summary['publications']}
                    == {(dest / f'scan{scan}_{kind}.npz').resolve() for kind in ('grid', 'audit', 'catalog')},
                    'Expected exact grid/audit/catalog publication identities')
            grid, saved, catalog = (arrays(dest / f'scan{scan}_{kind}.npz') for kind in ('grid', 'audit', 'catalog'))
            grids.append(grid); catalogs.append(catalog)
            hits = len(catalog['ess'])
            require(all(len(value) == hits and np.isfinite(value).all() for value in catalog.values())
                    and hits == summary['local_hits'] == sum(v['catalog_local_hits'] for v in summary['width_searches'])
                    and (catalog['ess'] >= 10).all(), 'Saved catalog count/threshold/finite values differ')
            require(np.isin(catalog['width_channels'], WIDTHS).all()
                    and ((catalog['drift_index'] >= 0) & (catalog['drift_index'] < 839)).all()
                    and ((catalog['channel_at_midpoint'] >= q * 4096)
                         & (catalog['channel_at_midpoint'] < (q + 1) * 4096)).all(), 'Catalog track geometry differs')
            require(np.array_equal(grid['drift_hz_s'], expected_rates)
                    and np.array_equal(grid['offsets'], expected_offsets), 'Saved drift grid differs')
            y, origin = support[scan], record['support_start']
            scan_trials = 0
            for wi, (width, stride) in enumerate(zip(WIDTHS, STRIDES)):
                centers = np.arange(q * 4096, (q + 1) * 4096, stride, dtype=np.int32)
                require(np.array_equal(grid[f'centers_width_{width}'], centers), 'Saved frequency centers differ')
                cal = grid[f'calibration_width_{width}']
                require(cal.shape == (839, 2) and np.isfinite(cal).all() and (cal[:, 1] > 0).all(),
                        'Saved calibration shape/values differ')
                indices = np.array([0, len(centers) // 2, len(centers) - 1])
                sample_centers = centers[indices]
                ris = np.array([0, 419, 838], dtype=np.int32)
                require(np.array_equal(saved[f'scalar_ris_width_{width}'], ris)
                        and np.array_equal(saved[f'scalar_centers_width_{width}'], sample_centers),
                        'Deterministic scalar audit coordinates differ')
                values = saved[f'scalar_sums_width_{width}']
                require(values.shape == (3, 3) and np.isfinite(values).all(), 'Saved scalar audit geometry differs')
                prepared = replay_kernel.boxcars(y, width)
                for rirow, ri in enumerate(ris):
                    replay = replay_kernel.tracks_grid(y, prepared, expected_offsets[ri],
                                                       q * 4096 - origin, (q + 1) * 4096 - origin,
                                                       stride, width)[0]
                    center = statistics.median(float(x) for x in replay)
                    scale = 1.4826 * statistics.median(abs(float(x) - center) for x in replay)
                    calibration_error = max(abs(center - float(cal[ri, 0])), abs(scale - float(cal[ri, 1])))
                    require(calibration_error <= 1e-10 * max(abs(center), abs(scale), 1),
                            'Replayed vector with scalar median/MAD differs from saved local calibration')
                    maximum_calibration_error = max(maximum_calibration_error, calibration_error)
                    replay_vectors += 1
                    for column, center in enumerate(sample_centers):
                        got = scalar_sum(y, expected_offsets[ri], int(center) - origin, width)
                        error = abs(got - float(values[rirow, column]))
                        require(error < 5e-5, 'Independent real track sum mismatch')
                        maximum_sum_error = max(maximum_sum_error, error); sum_checks += 1
                del prepared
                expected_trials = len(centers) * 839
                width_summary = summary['width_searches'][wi]
                require(width_summary['width_channels'] == width and width_summary['stride'] == stride
                        and width_summary['track_trials'] == expected_trials, 'Width hypothesis count differs')
                scan_trials += expected_trials
            require(scan_trials == summary['track_trials'] == 9020928, 'Per-scan hypothesis count differs')
            q_trials += scan_trials
        require(q_trials == search['track_trials'] == triage['search_track_trials'] == 54125568,
                'Six-scan q hypothesis count differs')
        total_trials += q_trials
        publication = triage['triage_publication']; pin(publication['path'], publication['sha256'])
        measured = arrays(publication['path'])
        seeds = {}
        for key in catalogs[0]:
            seeds[key] = np.concatenate([catalogs[j][key] for j in (0, 2, 4)])
        seeds['source_scan'] = np.concatenate([np.full(len(catalogs[j]['ess']), j, dtype=np.int8) for j in (0, 2, 4)])
        for key, value in seeds.items():
            require(np.array_equal(measured['seed_' + key], value), 'Saved ON seed inventory differs')
        n = len(seeds['ess']); scores = measured['forced_center_local_ess']; neighborhood = measured['forced_neighborhood_max_local_ess']
        valid = measured['forced_valid']; predictions = measured['predicted_native_center']
        require(scores.shape == neighborhood.shape == valid.shape == predictions.shape == (n, 6)
                and valid.dtype == np.bool_, 'Forced measurement geometry differs')
        require(np.isfinite(scores[valid]).all() and np.isfinite(neighborhood[valid]).all()
                and np.isnan(scores[~valid]).all() and np.isnan(neighborhood[~valid]).all(), 'Forced support/NaN status differs')
        full = valid.all(axis=1); flags = (neighborhood[:, [1, 3, 5]] >= 5).any(axis=1)
        passing = full & (scores[:, [0, 2, 4]] >= 10).all(axis=1) & ~flags
        require(np.array_equal(measured['any_OFF_ge5'], flags)
                and np.array_equal(measured['all3ON_ge10_noOFF'], passing), 'Saved ON/OFF flag identity differs')
        require(triage['ON_local_catalog_rows'] == n and triage['forced_measurement_slots'] == n * 6
                and triage['supported_slots'] == int(valid.sum())
                and triage['unsupported_slots'] == int((~valid).sum())
                and triage['any_OFF_ge5_rows'] == int(flags.sum())
                and triage['all3ON_ge10_noOFF_rows'] == int(passing.sum()), 'Forced count summary differs')
        if n:
            source_errors = np.abs(scores[np.arange(n), seeds['source_scan']] - seeds['ess'])
            require(np.array_equal(source_errors, measured['source_ess_error'])
                    and (source_errors == 0).all(), 'Original source-catalog score identity differs')
        sampled_seeds = set()
        for width in WIDTHS:
            width_rows = np.flatnonzero(seeds['width_channels'] == width)
            if len(width_rows):
                sampled_seeds.update((int(width_rows[0]), int(width_rows[-1])))
        for seed in sorted(sampled_seeds):
            tested_seeds += 1
            source_scope = scopes[int(seeds['source_scan'][seed])]
            ri, width = int(seeds['drift_index'][seed]), int(seeds['width_channels'][seed])
            require(0 <= ri < 839 and width in WIDTHS and float(seeds['drift_hz_s'][seed]) == float(expected_rates[ri]),
                    'Seed drift/width identity differs')
            for scan, (scope, record, y) in enumerate(zip(scopes, normalized['scans'], support)):
                gap = (scope['tref_midpoint_mjd'] - source_scope['tref_midpoint_mjd']) * 86400
                freq = float(seeds['frequency_at_midpoint_mhz'][seed]) + float(expected_rates[ri]) * gap / 1e6
                native_center = round((freq - scope['fch1_mhz']) * 1e6 / scope['df_hz'])
                require(native_center == int(predictions[seed, scan]), 'Independent propagated frequency center differs')
                center = native_center - record['support_start']
                radius = math.ceil(1 + .5 * float(expected_rates[1] - expected_rates[0]) * abs(gap) / abs(scope['df_hz']))
                off = expected_offsets[ri]
                supported = center + int(off.min()) - width // 2 - radius >= 0 and center + int(off.max()) + width // 2 + radius < y.shape[1]
                require(bool(valid[seed, scan]) == supported, 'Independent support validity differs')
                if not supported:
                    continue
                med, scale = grids[scan][f'calibration_width_{width}'][ri]
                reference_scores = [(scalar_sum(y, off, center + delta, width) - float(med)) / float(scale)
                                    for delta in range(-radius, radius + 1)]
                error = max(abs(reference_scores[radius] - float(scores[seed, scan])),
                            abs(max(reference_scores) - float(neighborhood[seed, scan])))
                require(error < 5e-5 / float(scale) + 1e-10, 'Independent forced center/neighborhood ESS differs')
                maximum_forced_ess_error = max(maximum_forced_ess_error, error); forced_checks += 1
        q_reports.append({'q': q, 'track_trials': q_trials, 'ON_catalog_rows': n,
                          'any_OFF_flag_rows': int(flags.sum()), 'all3ON_noOFF_rows': int(passing.sum())})
    require(sum_checks == 1728, 'Expected1728 fixed real scalar comparisons')
    require(replay_vectors == 576, 'Expected576 fixed calibration-vector replays')
    require(total_trials == complete['total_track_trials'] == 433004544, 'Whole frozen-family hypothesis count differs')
    for path, expected in pins.items():
        require(sha(path) == expected, 'Pinned evidence changed during audit')
    return {'schema': 'S2017_BI_INDEPENDENT_REAL_RESULT_SCALAR_AUDIT_V1', 'status': 'PASS_CLOSED_BOUNDED_REAL_RESULTS',
            'completed_utc': datetime.now(timezone.utc).isoformat(), 'plan_sha256': ph,
            'complete_result_sha256': sha(marker), 'audit_source_sha256': sha(__file__),
            'fixed_scalar_sum_comparisons': sum_checks, 'maximum_scalar_sum_error': maximum_sum_error,
            'shared_kernel_calibration_vector_replays': replay_vectors,
            'maximum_replayed_calibration_error': maximum_calibration_error,
            'deterministic_sampled_ON_seeds': tested_seeds, 'forced_center_and_neighborhood_pairs_compared': forced_checks,
            'maximum_forced_local_ess_error': maximum_forced_ess_error, 'track_trials': total_trials,
            'q_results': q_reports, 'input_and_artifact_sha256': pins, 'archive_requests': 0,
            'original_telescope_powers_redecoded_by_this_audit': 0,
            'qualification': 'Finite independent selected-track scalar audit plus shared-kernel vector replay with scalar median/MAD; saved supports, physical trajectories and serialization only.',
            'limitations': ['Does not independently re-decode telescope HDF5/bitshuffle or re-fit full-native normalization coefficients.',
                            'The576fullvector sums replay the same unchanged candidate kernel; only1728fixed selected sums and sampled forced measurements use independentmath.fsum.',
                            'Most forced rows are checked by full serialization/flag/count identities; first/last seeds of each populated width perq additionally checked by independent scalar sums.',
                            'No globalFAP, astronomical sensitivity, discovery, origin or new observation qualification.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--actual', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.plan, args.out, args.actual)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'fixed_scalar_sum_comparisons': result['fixed_scalar_sum_comparisons'],
                      'sampled_seed_count': result['deterministic_sampled_ON_seeds'], 'track_trials': result['track_trials']}))


if __name__ == '__main__':
    main()
