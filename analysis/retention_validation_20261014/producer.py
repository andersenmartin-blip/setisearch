#!/usr/bin/env python3
"""Frozen local top-five retention control on new exact-rational placements.

Uses previously exposed saved residual scores; this is a conditional algorithm
control, not a fresh telescope observation or a calibrated false-alarm test.
`prepare` reads JSON and hashes bytes only. `run` opens saved numerical arrays.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import resource
import signal
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

DF = -2.7939677238464355
HALF_DRIFT = 4 / 158
HOSTS = (-768, 768)
AMPLITUDES = (0, 2, 8)
KS = (1, 5)
DC = (178782208, 179830784, 180879360)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def pin(path, root):
    path = Path(path)
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': sha256(path)}


def exact_nearest_even(value):
    q, r = divmod(value.numerator, value.denominator)
    twice = 2 * r
    return q + int(twice > value.denominator or (twice == value.denominator and q % 2 != 0))


def exact_truth(profile, drift_fraction, phase_fraction, host):
    """Rationalize each stored binary64 constant separately, never a sum/product."""
    d = Fraction.from_float(profile['original_drift_hz_s'])
    d += Fraction(*map(int, drift_fraction)) * Fraction.from_float(HALF_DRIFT)
    p = Fraction(*map(int, phase_fraction))
    base = profile['source_reference_channel'] + host
    df = Fraction.from_float(DF)
    return [exact_nearest_even(Fraction(base) + p + d * Fraction.from_float(t) / df)
            for t in profile['times_from_primary_reference_s']]


def source_scores_from_terms(terms):
    """Reusable NumPy-only four-row score; normalization is frozen upstream."""
    import numpy as np
    terms = np.asarray(terms, dtype=np.float64)
    require(terms.shape[-1] == 4 and np.isfinite(terms).all(), 'Invalid four-row standardized terms')
    return terms.sum(axis=-1, dtype=np.float64) / 2.0


def source_path_scores(raw, normal, source_rows, absolute_channels, channel0):
    """Reusable NumPy-only raw501 score calculation; default control does not call it.

    Raw power and original per-row normalization values are arguments supplied
    by the caller. Original normalization and four-row sum/sqrt(4) are retained.
    This optional raw-source function is unexecuted and untested in this control;
    only source_scores_from_terms is used and checked against saved scores.
    """
    import numpy as np
    rows = np.asarray(source_rows, dtype=np.int64)
    channels = np.asarray(absolute_channels, dtype=np.int64)
    local = channels - channel0
    require(rows.shape == channels.shape and rows.shape[-1] == 4, 'Path shape differs')
    require(local.min() >= 250 and local.max() + 250 < raw.shape[1], 'Raw501 support missing')
    terms = np.empty_like(channels, dtype=np.float64)
    for row in range(raw.shape[0]):
        where = rows == row
        if not where.any():
            continue
        unique, inverse = np.unique(local[where], return_inverse=True)
        ratio = raw[row].astype(np.float64) / normal['row_power_median'][row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, 501)
        medians = np.median(windows[unique - 250], axis=1)
        residual = (ratio[unique] - medians - normal['row_winsorized_residual_location'][row])
        terms[where] = (residual / normal['row_residual_MAD_scale'][row])[inverse]
    return source_scores_from_terms(terms), terms


def flatten_family(profile, host):
    bins, rows, windows = [], [], []
    seen = set()
    original_indices = []
    index = 0
    for w in profile['windows']:
        for p in w['paths']:
            channels = tuple(c + host for c in p['channels'])
            key = (w['window_index'], channels)
            if key not in seen:
                seen.add(key)
                bins.append(channels); rows.append(w['window_source_rows'])
                windows.append(w['window_index']); original_indices.append(index)
            index += 1
    return bins, rows, windows, original_indices, index


def prepare(args):
    """Pin proposed scope after independently written geometry-only manifest exists."""
    root = args.input_root.resolve()
    here = Path(__file__).resolve().parent
    manifest_path = here / 'GEOMETRY_MANIFEST.json'
    manifest = read(manifest_path)
    novelty_path = here / 'PHYSICAL_NOVELTY_CENSUS.json'
    novelty = read(novelty_path)
    require(novelty['counts']['physical_new_overlap_prior'] == 0 and
            novelty['counts']['physical_profile_aliases'] == 0 and
            novelty['counts']['physical_unique_geometries'] == len(manifest['geometries']),
            'Cross-profile physical novelty differs')
    geometry_path = root / 'rounding_followup/exact_geometry_results/GEOMETRY.json'
    geometry = read(geometry_path)
    families = {p['profile_id']: p for p in geometry['profiles']}
    require(len(families) == 54, 'Expected 54 frozen profiles')
    geometries = manifest['geometries']
    require(0 < len(geometries) <= 3024, 'Unexpected geometry count')
    for t in geometries:
        family = families[t['profile_id']]
        require(t['host_offset_channels'] in HOSTS, 'Undeclared injection host')
        require(exact_truth(family, t['drift_fraction'], t['phase_fraction'],
                            t['host_offset_channels']) == t['truth16'], 'Exact representative truth differs')
        require([t['truth16'][r] for r in t['true_active_source_rows']] == t['truth_active4'],
                'Active-four truth differs')
        require(all(t[k] for k in ('exact_search_lookup_complete', 'raw501_crop_complete'))
                and not t['selected_active4_dc_contact'] and not t['canonical_placement_seen_in_prior'],
                'Metadata placement unavailable or old absolute placement reused')
        require(t['alias_draw_count'] == len(t['draws']), 'Alias census differs')
        for draw in t['draws']:
            truth = exact_truth(family, draw['drift_fraction'], draw['phase_fraction'], t['host_offset_channels'])
            require(truth == draw['canonical_truth16'] and
                    [truth[r] for r in t['true_active_source_rows']] == t['truth_active4'],
                    'Exact alias placement differs')
    all_pins = [pin(root / p, root) for p in (
        'rounding_followup/exact_geometry_results/GEOMETRY.json',
        'rounding_followup/results/INJECTIONS.json',
        'rounding_followup/results/PROFILES.json',
        'rounding_followup/results/EXECUTION_RECEIPT.json',
        'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json')]
    receipt = read(root / 'rounding_followup/results/EXECUTION_RECEIPT.json')
    expected = {x['path']: x['sha256'] for x in receipt['outputs'] if x['path'].startswith('profiles/')}
    for pid in sorted(families):
        path = root / 'rounding_followup/results/profiles' / (pid + '_paths.npz')
        declaration = pin(path, root)
        require(declaration['sha256'] == expected['profiles/' + path.name], 'Archived path array hash differs')
        all_pins.append(declaration)
    scope = {
        'schema': 'SETI_FROZEN_LOCAL_RETENTION_SCOPE_V1',
        'date': '2026-10-14',
        'status': 'PROPOSED_METADATA_COMPLETE_AWAITING_ROOT_GO',
        'input_root': str(root),
        'input_pins': all_pins,
        'geometry_manifest_pin': pin(manifest_path, here),
        'physical_novelty_pin': pin(novelty_path, here),
        'producer_pin': pin(Path(__file__).resolve(), here),
        'metadata_code_pin': {'path': str(here.parent / 'validation_design/build_geometry_manifest.py'),
                              'sha256': sha256(here.parent / 'validation_design/build_geometry_manifest.py')},
        'physical_novelty_code_pin': {'path': str(here.parent / 'validation_design/physical_novelty.py'),
                                     'sha256': sha256(here.parent / 'validation_design/physical_novelty.py')},
        'profile_count': 54,
        'geometry_count': len(geometries),
        'nominal_geometry_draws': 3024,
        'actual_numeric_trial_count': len(geometries) * 3,
        'fixed_panel': {'host_offsets': list(HOSTS), 'amplitudes': list(AMPLITUDES),
                        'drift_fractions': [['-83','100'], ['47','100']],
                        'phase_fractions': [['-41','100'], ['13','100']],
                        'window_indices': list(range(7))},
        'fixed_policy': {
            'k': 5, 'comparison_k': 1,
            'domain': 'local exact-native refinement around previously selected nine tracks; 54 context profiles',
            'hypothesis_identity': ['window_source_rows', 'native_four_bins'],
            'trial_dedup': ['profile_id', 'host_offset_channels', 'true_active_source_rows', 'truth_native4'],
            'tie_order': 'descending saved/injected score, ascending window start, ascending native four-bin tuple',
            'score': 'frozen standardized four-row sum divided by 2; additive single-bin residual injection amplitude/2 per matching active cell',
            'rank_min': '1 + strictly greater scores',
            'rank_max': 'greater-or-equal scores',
            'capture': 'complete active-four truth identity retained by deterministic top k',
            'amplitude0': 'sham-target ranks only; unique profile-host retention lists count null workload once',
            'observed_offset0': '54 descriptive top-five lists and shared-cell overlap only'},
        'resource_envelope': {'reserved_CPU_s': 180, 'metadata_CPU_s_cap': 60,
                              'producer_CPU_s_cap': 60, 'QA_CPU_s_cap': 60,
                              'wall_s_cap_each': 300, 'memory_bytes_cap_each': 1073741824,
                              'output_bytes_cap': 30000000, 'cost_DKK': 0},
        'interpretation': ['New exact-rational physical injection placements on exposed background.',
                           'Paired conditional retention control, no independent trials assumption.',
                           'No p-value, FAP, instrumental line response or physical sensitivity established.',
                           'Original full-six-scan-chain pilot gates cannot pass on this local bank.'],
        'preserved': {'qualified_SETI_detection': False, 'pilot_gate_pass': False,
                      'original_A_B': 'FAIL_CLOSED', 'protected_2016': True, 'closed_2019': True,
                      'new_observation': False, 'new_telescope_requests': 0, 'new_telescope_bytes': 0}
    }
    write_json(here / 'SCOPE.json', scope)
    print(json.dumps({'status': scope['status'], 'geometry_count': len(geometries),
                      'numeric_trials': scope['actual_numeric_trial_count'],
                      'scope_sha256': sha256(here / 'SCOPE.json')}))


def json_cell(value):
    return json.dumps(value, separators=(',', ':'))


def write_csv(path, rows):
    require(bool(rows), 'Cannot save empty table')
    with Path(path).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def run(args):
    started_wall, started_cpu = time.monotonic(), time.process_time()
    here = Path(__file__).resolve().parent
    scope_path = here / 'SCOPE.json'
    require(sha256(scope_path) == args.go_scope_sha256, 'Root-GO scope digest differs')
    scope = read(scope_path)
    require(sha256(Path(__file__).resolve()) == scope['producer_pin']['sha256'], 'Frozen producer differs')
    go_path = here / 'GO.json'
    require(go_path.is_file(), 'Root-authored GO.json is required before saved-array execution')
    go = read(go_path)
    require(go['scope_sha256'] == sha256(scope_path) and
            go['producer_sha256'] == sha256(Path(__file__).resolve()) and
            go['metadata_manifest_sha256'] == scope['geometry_manifest_pin']['sha256'], 'Root GO pins differ')
    budget = scope['resource_envelope']
    resource.setrlimit(resource.RLIMIT_CPU, (budget['producer_CPU_s_cap'], budget['producer_CPU_s_cap']))
    resource.setrlimit(resource.RLIMIT_AS, (budget['memory_bytes_cap_each'], budget['memory_bytes_cap_each']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Producer wall cap exceeded')))
    signal.alarm(budget['wall_s_cap_each'])
    root = args.input_root.resolve() if args.input_root else Path(scope['input_root'])
    for p in scope['input_pins']:
        path = root / p['path']
        require(path.stat().st_size == p['bytes'] and sha256(path) == p['sha256'], 'Frozen input differs: ' + p['path'])
    declaration = scope['geometry_manifest_pin']
    manifest_path = here / declaration['path']
    require(sha256(manifest_path) == declaration['sha256'], 'Frozen manifest differs')
    manifest = read(manifest_path)
    declaration = scope['physical_novelty_pin']
    novelty_path = here / declaration['path']
    require(sha256(novelty_path) == declaration['sha256'], 'Frozen physical novelty annex differs')
    novelty = read(novelty_path)
    families = {p['profile_id']: p for p in read(root / 'rounding_followup/exact_geometry_results/GEOMETRY.json')['profiles']}
    grouped = defaultdict(list)
    for t in manifest['geometries']:
        grouped[t['profile_id']].append(t)
    require(len(grouped) == 54, 'Geometry profile census differs')
    import numpy as np
    out = args.output_root.resolve()
    require(not out.exists() and not out.is_relative_to(root), 'Fresh output outside input archive required')
    out.mkdir(parents=True)
    trial_rows, candidate_rows, observed_rows, pair_rows, null_rows = [], [], [], [], []
    checked_scores, max_score_error = 0, 0.0
    for pid in sorted(grouped):
        family = families[pid]
        path = root / 'rounding_followup/results/profiles' / (pid + '_paths.npz')
        with np.load(path, allow_pickle=False) as a:
            raw_windows = a['path_window_index']
            raw_rows = a['path_source_rows']
            for host in (0,) + HOSTS:
                oi = int(np.flatnonzero(a['offset_channels'] == host)[0])
                bins_list, rows_list, window_list, unique_indices, original_count = flatten_family(family, host)
                require(original_count == len(raw_windows), 'Full family length differs')
                take = np.asarray(unique_indices, dtype=np.int64)
                channels = np.asarray(bins_list, dtype=np.int64)
                rows = np.asarray(rows_list, dtype=np.int64)
                windows = np.asarray(window_list, dtype=np.int64)
                require(np.array_equal(a['absolute_channels'][oi, take], channels) and
                        np.array_equal(raw_rows[take], rows) and
                        np.array_equal(raw_windows[take], windows), 'Saved path identities differ from exact metadata')
                base = a['scores'][oi, take].astype(np.float64)
                recomputed = source_scores_from_terms(a['residual_row_terms'][oi, take])
                error = float(np.max(np.abs(recomputed - base)))
                max_score_error = max(max_score_error, error); checked_scores += len(base)
                require(error <= 1e-12 and np.isfinite(base).all(), 'Saved source scores differ')
                eligible = ~a['path_dc_mask'][oi, take]
                require(np.array_equal(~eligible, np.isin(channels, np.asarray(DC)).any(axis=1)), 'DC mask differs')
                eligible_idx = np.flatnonzero(eligible)
                require(len(eligible_idx) >= 5, 'Fewer than five eligible local hypotheses')
                # Lexsort primary key is the last supplied key. Four bins are
                # tie keys after window start; metadata family is deduplicated.
                def ordered(scores):
                    i = eligible_idx
                    order = np.lexsort((channels[i,3], channels[i,2], channels[i,1], channels[i,0],
                                        rows[i,0], -scores[i]))
                    return i[order]
                null_order = ordered(base)
                if host == 0:
                    for position, i in enumerate(null_order[:5], 1):
                        observed_rows.append({'profile_id': pid, 'rank': position, 'host_offset_channels': 0,
                            'path_index': int(take[i]), 'window_index': int(windows[i]),
                            'source_rows': json_cell(rows[i].tolist()), 'native4': json_cell(channels[i].tolist()),
                            'score': float(base[i]), 'eligible_unique_hypotheses': int(len(eligible_idx)),
                            'new_detection': False, 'domain': 'local_refinement_of_preselected_top9'})
                    for left in range(5):
                        for right in range(left + 1, 5):
                            i, j = null_order[left], null_order[right]
                            cells_i = set(zip(rows[i].tolist(), channels[i].tolist()))
                            cells_j = set(zip(rows[j].tolist(), channels[j].tolist()))
                            pair_rows.append({'profile_id': pid, 'rank_a': left+1, 'rank_b': right+1,
                                'shared_active_cells': len(cells_i & cells_j),
                                'shared_source_rows': len(set(rows[i]) & set(rows[j])),
                                'same_window': bool(windows[i] == windows[j]),
                                'score_gap': float(base[i] - base[j])})
                    continue
                null_rows.append({'profile_id': pid, 'host_offset_channels': host,
                    'eligible_unique_hypotheses': int(len(eligible_idx)),
                    'retained_k1_count': 1, 'retained_k5_count': 5, 'additional_candidates': 4,
                    'top1_score': float(base[null_order[0]]), 'top5_cut_score': float(base[null_order[4]]),
                    'top5_indices': json_cell(take[null_order[:5]].tolist()),
                    'top5_scores': json_cell(base[null_order[:5]].tolist()),
                    'independent_null_trials': False, 'p_value': 'NOT_CALIBRATED'})
                for t in grouped[pid]:
                    if t['host_offset_channels'] != host:
                        continue
                    truth = np.asarray(t['truth16'], dtype=np.int64)
                    active = np.zeros(16, dtype=bool)
                    active[np.asarray(t['true_active_source_rows'], dtype=np.int64)] = True
                    matches = (channels == truth[rows]) & active[rows]
                    counts = matches.sum(axis=1, dtype=np.int64)
                    truth_mask = eligible & (counts == 4)
                    truth_indices = np.flatnonzero(truth_mask)
                    require(len(truth_indices) == 1, 'Unique complete truth identity missing after dedup')
                    ti = int(truth_indices[0])
                    require(int(windows[ti]) == t['true_window_index'], 'Truth window differs')
                    for amp in AMPLITUDES:
                        scores = base + amp * counts / 2.0
                        rank_order = ordered(scores)
                        top5 = rank_order[:5]
                        truth_score = float(scores[ti])
                        greater = int(np.count_nonzero(scores[eligible] > truth_score))
                        equal = int(np.count_nonzero(scores[eligible] == truth_score))
                        deterministic_rank = int(np.flatnonzero(rank_order == ti)[0]) + 1
                        winner = int(rank_order[0])
                        partial = rank_order[counts[rank_order] < 4]
                        pi = int(partial[0])
                        row = {
                            'geometry_id': t['geometry_id'], 'profile_id': pid,
                            'origin_scan_id': t['origin_scan_id'], 'context_scan_id': t['context_scan_id'],
                            'origin_rank': t['origin_rank'],
                            'host_offset_channels': host, 'amplitude': amp,
                            'true_window_index': t['true_window_index'],
                            'true_active_source_rows': json_cell(t['true_active_source_rows']),
                            'truth_absolute_centers': json_cell(t['truth16']),
                            'truth_native4': json_cell(t['truth_active4']),
                            'relative_native4': json_cell(t['native4']),
                            'native4_seen_in_prior_same_profile_window': t['native4_seen_in_prior_same_profile_window'],
                            'alias_draw_count': t['alias_draw_count'],
                            'truth_best_path_index': int(take[ti]), 'truth_path_count': 1,
                            'truth_score': truth_score,
                            'truth_rank_min': 1 + greater, 'truth_rank_max': greater + equal,
                            'truth_rank_tie_count': equal, 'truth_deterministic_rank': deterministic_rank,
                            'winner_path_index': int(take[winner]), 'winner_window_index': int(windows[winner]),
                            'winner_score': float(scores[winner]), 'winner_overlap_count': int(counts[winner]),
                            'winner_minus_truth_score': float(scores[winner] - truth_score),
                            'best_partial_path_index': int(take[pi]), 'best_partial_window_index': int(windows[pi]),
                            'best_partial_score': float(scores[pi]), 'best_partial_overlap_count': int(counts[pi]),
                            'truth_minus_best_partial_score': float(truth_score - scores[pi]),
                            'truth_retained_top1': bool(ti in rank_order[:1]),
                            'truth_retained_top5': bool(ti in top5),
                            'full_truth_retained_count_top1': int(np.count_nonzero(counts[rank_order[:1]] == 4)),
                            'full_truth_retained_count_top5': int(np.count_nonzero(counts[top5] == 4)),
                            'retained_count_top1': 1, 'retained_count_top5': 5,
                            'retained_top5_indices': json_cell(take[top5].tolist()),
                            'retained_top5_overlaps': json_cell(counts[top5].tolist()),
                            'eligible_unique_hypotheses': int(len(eligible_idx)),
                            'sham_target_only': amp == 0}
                        trial_rows.append(row)
                        for position, i in enumerate(top5, 1):
                            candidate_rows.append({'geometry_id': t['geometry_id'], 'profile_id': pid,
                                'host_offset_channels': host, 'amplitude': amp, 'rank': position,
                                'path_index': int(take[i]), 'window_index': int(windows[i]),
                                'source_rows': json_cell(rows[i].tolist()), 'native4': json_cell(channels[i].tolist()),
                                'score': float(scores[i]), 'matched_active_cells': int(counts[i]),
                                'complete_truth': bool(counts[i] == 4)})
        if len(observed_rows) % 30 == 0:
            print(json.dumps({'profiles_completed': len(observed_rows)//5, 'trial_rows': len(trial_rows)}), flush=True)
    require(len(trial_rows) == scope['actual_numeric_trial_count'], 'Frozen actual trial census differs')
    require(len(observed_rows) == 270 and len(null_rows) == 108 and len(pair_rows) == 540, 'Output census differs')
    for filename, records in [('TRIAL_RANKS.csv',trial_rows), ('RETAINED_HYPOTHESES.csv',candidate_rows),
                              ('OBSERVED_TOP5.csv',observed_rows), ('CANDIDATE_OVERLAP.csv',pair_rows),
                              ('NULL_BURDEN.csv',null_rows)]:
        write_csv(out / filename, records)
    def panel(amp):
        rows = [r for r in trial_rows if r['amplitude'] == amp]
        def capture(subset):
            return {'trials':len(subset),
                    'top1_count':sum(r['truth_retained_top1'] for r in subset),
                    'top5_count':sum(r['truth_retained_top5'] for r in subset),
                    'top1_fraction':sum(r['truth_retained_top1'] for r in subset)/len(subset),
                    'top5_fraction':sum(r['truth_retained_top5'] for r in subset)/len(subset)}
        return {'trials': len(rows), 'label': 'SHAM_TARGET_RANK_DIAGNOSTIC' if amp == 0 else 'CONDITIONAL_COMPLETE_TRUTH_CAPTURE',
                'top1_complete_truth_count': sum(r['truth_retained_top1'] for r in rows),
                'top5_complete_truth_count': sum(r['truth_retained_top5'] for r in rows),
                'additional_top5_complete_truth_count': sum(r['truth_retained_top5'] and not r['truth_retained_top1'] for r in rows),
                'top5_missing_truth_count': sum(not r['truth_retained_top5'] for r in rows),
                'top1_complete_truth_fraction':sum(r['truth_retained_top1'] for r in rows)/len(rows),
                'top5_complete_truth_fraction':sum(r['truth_retained_top5'] for r in rows)/len(rows),
                'truth_deterministic_rank_counts': dict(sorted(Counter(r['truth_deterministic_rank'] for r in rows).items())),
                'winner_overlap_counts': dict(sorted(Counter(r['winner_overlap_count'] for r in rows).items())),
                'by_host':{str(h):capture([r for r in rows if r['host_offset_channels']==h]) for h in HOSTS},
                'by_relative_native4_novelty':{
                    'unseen_relative_path':capture([r for r in rows if not r['native4_seen_in_prior_same_profile_window']]),
                    'seen_relative_path_new_absolute_placement':capture([r for r in rows if r['native4_seen_in_prior_same_profile_window']])},
                'hypothesis_slots_top1': len(rows), 'hypothesis_slots_top5': len(rows) * 5}
    summary = {
        'schema': 'SETI_FROZEN_LOCAL_RETENTION_RESULT_V1',
        'status': 'COMPLETE_CONDITIONAL_CONTROL_ON_NEW_PLACEMENTS_EXPOSED_BACKGROUND',
        'date': '2026-10-14', 'geometry_count': scope['geometry_count'],
        'nominal_geometry_draws': 3024, 'numeric_trial_count': len(trial_rows),
        'geometry_manifest_sha256': sha256(manifest_path),
        'physical_novelty_counts':novelty['counts'],
        'retention_policy_frozen_k': 5, 'comparison_k': 1,
        'amplitude_panels': {str(a): panel(a) for a in AMPLITUDES},
        'null_burden_unique_profile_host_lists': {'lists':108, 'top1_candidates':108,
            'top5_candidates':540, 'additional_candidates':432,
            'workload_ratio':5, 'independent_null_trials':False, 'false_alarm_calibrated':False,
            'top1_score_min_median_max':[float(x) for x in np.quantile([r['top1_score'] for r in null_rows],(0,.5,1))],
            'top5_cut_score_min_median_max':[float(x) for x in np.quantile([r['top5_cut_score'] for r in null_rows],(0,.5,1))]},
        'observed_offset0_lists': {'profiles':54, 'top1_candidates':54, 'top5_candidates':270,
            'pairwise_comparisons':540, 'shared_cell_count_distribution':dict(sorted(Counter(r['shared_active_cells'] for r in pair_rows).items())),
            'new_detection':False, 'scope':'local exact-native refinement around preselected top9'},
        'source_score_recomputed_count': checked_scores, 'source_score_max_absolute_error': max_score_error,
        'optional_raw_source_function_status': 'UNEXECUTED_UNTESTED_NOT_USED_FOR_RESULTS',
        'qualified_SETI_detection':False, 'pilot_gate_pass':False,
        'original_A_B':'FAIL_CLOSED', 'full6scan_chain_gates_tested':False,
        'calibrated_FAP':False, 'new_observation':False, 'new_telescope_requests':0,
        'interpretation':scope['interpretation']}
    write_json(out / 'SUMMARY.json', summary)
    outputs = [pin(p, out) for p in sorted(out.iterdir()) if p.is_file()]
    require(sum(p['bytes'] for p in outputs) <= budget['output_bytes_cap'], 'Output bytes cap exceeded')
    elapsed_cpu, elapsed_wall = time.process_time()-started_cpu, time.monotonic()-started_wall
    require(elapsed_cpu <= budget['producer_CPU_s_cap'], 'Producer CPU cap exceeded')
    write_json(out / 'EXECUTION_RECEIPT.json', {
        'schema':'SETI_FROZEN_LOCAL_RETENTION_EXECUTION_RECEIPT_V1', 'status':'COMPLETE',
        'scope_sha256':sha256(scope_path), 'producer_sha256':sha256(Path(__file__)),
        'geometry_manifest_sha256':sha256(manifest_path), 'opened_saved_profile_arrays':54,
        'effective_input_root':str(root),
        'raw_spectral_arrays_opened':False, 'new_telescope_requests':0, 'new_telescope_bytes':0,
        'outputs':outputs, 'resource_usage':{'CPU_s':elapsed_cpu,'wall_s':elapsed_wall,
             'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}})
    signal.alarm(0)
    print(json.dumps(summary, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('input_root', type=Path)
    execute = sub.add_parser('run')
    execute.add_argument('output_root', type=Path)
    execute.add_argument('--input-root', type=Path,
                         help='Portable input root; all relative frozen pins remain required')
    execute.add_argument('--go-scope-sha256', required=True)
    args = parser.parse_args()
    (prepare if args.command == 'prepare' else run)(args)


if __name__ == '__main__':
    main()
