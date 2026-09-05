#!/usr/bin/env python3
"""Frozen metadata-only nested coefficient-disk coverage experiment."""
import hashlib
import json
import math
import time
from pathlib import Path
import numpy as np
from m43b_active_support import ROOT, ACTIVITY, active_plans, seal
from seti_repeater import search_v0p6 as core

LABELS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
LEVELS = (8, 16, 32)
GENERATOR_LABEL = 'm43d-heldout-disk-v1-2026-09-05'
INTERVAL_OUTWARD_HZ = 1e-5


def nested_banks(baseline):
    """Preserve historical prefix; append nested Cartesian disk lattices."""
    records = json.loads(core.canonical_json_bytes(baseline))
    seen = {(r['coefficient_x'], r['coefficient_y']) for r in records}
    banks = {'baseline': list(records)}
    for n in LEVELS:
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                if i*i + j*j > n*n:
                    continue
                x, y = i/n, j/n
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                records.append({'template_index': len(records),
                                'coefficient_x': x, 'coefficient_y': y,
                                'family': 'cartesian-unit-disk',
                                'first_level': n})
        banks[f'disk{n}'] = list(records)
    return banks


def jitter(ordinal, coordinate):
    raw = hashlib.sha256(core.canonical_json_bytes(
        [GENERATOR_LABEL, ordinal, coordinate])).digest()
    return (int.from_bytes(raw[:8], 'big') >> 11) / 2**53


def heldout_truths(grid):
    """512 area-stratified disk points; same carrier domain, off-lattice."""
    left, right = float(grid.score_hz[256]), float(grid.score_hz[-257])
    rows = []
    for ordinal in range(512):
        radius = math.sqrt((ordinal//32 + jitter(ordinal, 'r2'))/16)
        phase = (ordinal%32 + jitter(ordinal, 'phase'))/32
        row = {'truth_ordinal': ordinal, 'coefficient_x': radius*math.cos(2*math.pi*phase),
               'coefficient_y': radius*math.sin(2*math.pi*phase),
               'proxy_carrier_hz': left + (right-left)*jitter(ordinal, 'carrier'),
               'radial_stratum': ordinal//32, 'phase_stratum': ordinal%32}
        row['truth_id'] = seal(row)
        rows.append(row)
    return rows


def candidate_pairs(score_hz, matrix, truth_track):
    """Vectorized interval bounds, then literal binary64 <=20 Hz verification.

    Returns every accepted (template, carrier-index) pair, template-major.
    The outward interval guard is only a prefilter; it cannot admit a match.
    """
    q = np.asarray(score_hz)
    a = np.asarray(matrix)
    y = np.asarray(truth_track)
    if (q.dtype != np.dtype('<f8') or a.dtype != q.dtype or y.dtype != q.dtype
            or q.ndim != 1 or q.size < 2 or a.ndim != 2 or y.ndim != 1
            or a.shape[1] != y.size or not y.size or not a.shape[0]
            or not np.isfinite(q).all() or not np.isfinite(a).all()
            or not np.isfinite(y).all() or np.any(a <= 0)
            or np.any(np.diff(q) <= 0) or np.max(np.abs(q)) > 2e9
            or np.max(np.abs(y)) > 3e9 or np.min(a) < .5 or np.max(a) > 1.5):
        raise ValueError('unsupported geometry or numeric domain')
    lower = np.max((y - (20 + INTERVAL_OUTWARD_HZ))/a, axis=1)
    upper = np.min((y + (20 + INTERVAL_OUTWARD_HZ))/a, axis=1)
    left = np.maximum(0, np.searchsorted(q, lower, side='left') - 4)
    right = np.minimum(q.size, np.searchsorted(q, upper, side='right') + 4)
    lengths = np.where(lower <= upper, np.maximum(0, right-left), 0)
    total = int(lengths.sum())
    if total * y.size > 8_000_000:
        raise RuntimeError('distance-cell capacity exceeded; no truncation')
    if not total:
        return np.empty((0, 2), dtype='<i8'), np.empty(0, dtype='<f8'), 0
    templates = np.repeat(np.arange(a.shape[0], dtype='<i8'), lengths)
    starts = np.repeat(np.cumsum(lengths)-lengths, lengths)
    indices = np.repeat(left, lengths) + np.arange(total) - starts
    distances = np.max(np.abs(q[indices, None]*a[templates] - y), axis=1)
    accepted = distances <= 20.
    pairs = np.column_stack((templates[accepted], indices[accepted])).astype('<i8')
    return pairs, np.asarray(distances[accepted], dtype='<f8'), total*y.size


def bank_summary(pairs, distances, bank_count, grid):
    selected = pairs[pairs[:, 0] < bank_count]
    d = distances[pairs[:, 0] < bank_count]
    witness = None
    if len(selected):
        ti, qi = map(int, selected[0])
        witness = {'template_index': ti, 'carrier_index': qi,
                   'carrier_hz': float(grid.score_hz[qi]),
                   'max_distance_hz': float(d[0])}
    return {'supported': bool(len(selected)), 'candidate_cells': len(selected),
            'candidate_pairs_sha256': hashlib.sha256(selected.tobytes()).hexdigest(),
            'witness': witness}


def verified_json(path):
    row = json.loads(path.read_text())
    if row['result_sha256'] != seal({k:v for k,v in row.items() if k != 'result_sha256'}):
        raise RuntimeError('result identity differs: '+str(path))
    return row


def run():
    started = time.perf_counter()
    cfgpath = ROOT/'config/m43d_bank_coverage.json'
    cfg = json.loads(cfgpath.read_text())
    cfg_hash = hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    for name, digest in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('changed frozen file: '+name)
    prior = verified_json(ROOT/'results_m43b_active_support/geometry.json')
    basis = core.make_factor_basis_from_metadata(json.loads(
        (ROOT/'config/hd156668b_m37_preflight.json').read_text()))
    baseline = json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())['template_bank']['records']
    banks = nested_banks(baseline)
    largest = banks['disk32']
    table = core.make_template_factor_table(basis, largest,
            expected_template_bank_sha256=core.template_bank_sha256(largest))
    if basis.basis_sha256 != prior['factor_basis_sha256'] or core.factor_table_sha256(table.factors[:93]) != prior['factor_table_sha256']:
        raise RuntimeError('historical basis/table differ')
    grid = core.make_m37_proxy_carrier_grid('m37_1412p5')
    matrices = tuple(core.factor_table_for_scan(table, basis, label) for label in LABELS)
    active_matrices = {act: np.ascontiguousarray(np.concatenate([matrices[i] for i in act],axis=1)) for act in ACTIVITY}
    bank_meta = {name: {'template_count': len(bank), 'bank_sha256': core.template_bank_sha256(bank),
                       'template_factor_bytes_all_six_scans': len(bank)*table.factors.shape[1]*8,
                       'score_cells_one_window': len(bank)*grid.score_bin_count*32,
                       'score_cells_five_windows': len(bank)*grid.score_bin_count*32*5,
                       'relative_score_cells': len(bank)/93} for name,bank in banks.items()}
    out = ROOT/'results_m43d_bank_coverage'
    out.mkdir(exist_ok=True)
    local = out/'checkpoints'
    local.mkdir(exist_ok=True)
    rows = []
    # Only expose new held-out tracks to evaluation after old-inventory selection.
    def evaluate(t, act, split, old=None):
        path = local/f"{split}-{t['truth_ordinal']:03d}-{''.join(map(str, act))}.json"
        if path.exists():
            row = verified_json(path)
            if row['config_sha256'] != cfg_hash or row['truth'] != t or row['active_epochs'] != list(act):
                raise RuntimeError('checkpoint ancestry differs')
            return row
        factors = tuple(np.ascontiguousarray(core.template_factors_from_basis(basis,t,scan_label=l)) for l in LABELS)
        y = np.float64(t['proxy_carrier_hz'])*np.concatenate([factors[i] for i in act])
        tick = time.perf_counter()
        pairs, distances, distance_cells = candidate_pairs(grid.score_hz, active_matrices[act], y)
        elapsed = time.perf_counter()-tick
        if old is not None:
            plans = active_plans(grid, tuple(np.ascontiguousarray(m[:93]) for m in matrices), factors, t['proxy_carrier_hz'], act)
            if seal([p.as_record() for p in plans]) != old['active_plan_inventory_sha256']:
                raise RuntimeError('M43B exact plan replay differs')
            reference = np.array([(i,int(qi)) for i,p in enumerate(plans) for qi in p.candidate_indices.indices],dtype='<i8').reshape(-1,2)
            if not np.array_equal(reference,pairs[pairs[:,0]<93]):
                raise RuntimeError('fast geometry differs from original planner')
        summaries = {name:bank_summary(pairs,distances,len(bank),grid) for name,bank in banks.items()}
        row = {'config_sha256': cfg_hash, 'split': split, 'truth': t, 'active_epochs': list(act),
               'banks': summaries, 'm43b_exact_replay': old is not None,
               'distance_cells_evaluated': distance_cells, 'geometry_seconds': elapsed}
        row['result_sha256'] = seal(row)
        temp = path.with_suffix('.tmp')
        temp.write_bytes(core.canonical_json_bytes(row)); temp.replace(path)
        return row
    for ordinal, old in enumerate(prior['rows']):
        t=old['truth']
        rows.append(evaluate(t,tuple(t['active_epochs_zero_based']),'historical',old))
        if (ordinal+1)%64==0: print('historical',ordinal+1,'/512',flush=True)
    historical = {name:sum(r['banks'][name]['supported'] for r in rows) for name in banks}
    if historical['baseline'] != 167 or len(rows)!=512:
        raise RuntimeError('historical denominator or support differs')
    selected = next((name for name in banks if historical[name]/512 >= .95),None)
    selection = {'config_sha256':cfg_hash,'historical_counts':historical,
                 'selected_bank':selected,'rule':'first bank with historical coverage >= 95%'}
    selection['result_sha256'] = seal(selection)
    (out/'historical_selection.json').write_bytes(core.canonical_json_bytes(selection))
    print('FROZEN HISTORICAL SELECTION', json.dumps(selection),flush=True)
    new_truths = heldout_truths(grid)
    historical_points={(r['truth']['coefficient_x'],r['truth']['coefficient_y']) for r in prior['rows']}
    bank_points={(r['coefficient_x'],r['coefficient_y']) for r in largest}
    if any((t['coefficient_x'],t['coefficient_y']) in historical_points|bank_points for t in new_truths):
        raise RuntimeError('held-out point overlaps historical truth or template')
    for ordinal,t in enumerate(new_truths):
        for act in ACTIVITY:rows.append(evaluate(t,act,'heldout'))
        if (ordinal+1)%64==0: print('heldout tracks',ordinal+1,'/512 (four activities each)',flush=True)
    groups=[]
    for act in ACTIVITY:
        chosen=[r for r in rows if r['split']=='heldout' and r['active_epochs']==list(act)]
        if len(chosen)!=512:raise RuntimeError('heldout denominator differs')
        groups.append({'active_epochs':list(act),'truth_count':len(chosen),
                       'supported':{name:sum(r['banks'][name]['supported'] for r in chosen) for name in banks}})
    for row in rows:
        counts=[row['banks'][name]['candidate_cells'] for name in banks]
        if counts != sorted(counts):raise RuntimeError('nested support lost')
    confirmed=selected is not None and all(g['supported'][selected]/512 >= .95 for g in groups)
    result={'artifact_type':'m43d-nested-disk-geometric-coverage-v1',
            'status':'geometry-complete-operational-validation-pending',
            'config_sha256':cfg_hash,'parent_result_sha256':prior['result_sha256'],
            'factor_basis_sha256':basis.basis_sha256,'largest_factor_table_sha256':table.factor_table_sha256,
            'bank_inventory':bank_meta,'historical_supported':historical,
            'historical_truth_count':512,'heldout_unique_track_count':512,'heldout_associations':2048,
            'heldout_truth_inventory_sha256':seal(new_truths),'heldout_groups':groups,
            'historical_selected_bank':selected,'heldout_95_percent_gate_passed':confirmed,
            'selection_sha256':selection['result_sha256'],
            'geometry_seconds_sum':sum(r['geometry_seconds'] for r in rows),
            'distance_cells_evaluated':sum(r['distance_cells_evaluated'] for r in rows),
            'factor_table_bytes':table.factors.nbytes,
            'new_spectral_reads':0,'new_injections':0,'new_scores':0,
            'sensitivity_claimed':False,'production_detector_changed':False,'rows':rows}
    result['result_sha256']=seal(result)
    (out/'geometry.json').write_bytes(core.canonical_json_bytes(result))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True)
    print('wall seconds including reconstruction and baseline replay',time.perf_counter()-started,flush=True)


if __name__=='__main__':run()
