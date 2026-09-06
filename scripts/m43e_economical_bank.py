#!/usr/bin/env python3
"""M43E: frozen cause diagnosis, checkerboard bank and fresh confirmation."""
import argparse
import gzip
import hashlib
import json
import math
import time
from pathlib import Path
import numpy as np
from m43b_active_support import ROOT, ACTIVITY, seal
from m43c_coverage_cause import template_diagnostic, truth_cause
from m43d_bank_coverage import LABELS, nested_banks, candidate_pairs, bank_summary
from seti_repeater import search_v0p6 as core

FRESH_LABEL = 'm43e-fresh-confirmation-disk-v1-2026-09-06'
OUT = ROOT/'results_m43e_economical_bank'
CAUSES = ('track-shape-incompatible', 'outside-carrier-range', 'carrier-grid-gap', 'numerical-boundary-unresolved')


def read_sealed(path):
    raw = path.read_bytes()
    if path.suffix == '.gz':
        raw = gzip.decompress(raw)
    result = json.loads(raw)
    if result['result_sha256'] != seal({k:v for k,v in result.items() if k != 'result_sha256'}):
        raise RuntimeError('changed identity: '+str(path))
    return result


def write_sealed(path, record):
    record = dict(record)
    record['result_sha256'] = seal(record)
    raw = core.canonical_json_bytes(record)
    if path.suffix == '.gz':
        raw = gzip.compress(raw, compresslevel=9, mtime=0)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(raw); temp.replace(path)
    return record


def checkerboard_bank(full_bank, prefix_count=889):
    """Keep disk16 unchanged; add only even-parity nodes from disk32."""
    if prefix_count != 889 or len(full_bank) != 3301:
        raise ValueError('unexpected M43D inventory')
    source_indices = list(range(prefix_count))
    for index, record in enumerate(full_bank[prefix_count:], start=prefix_count):
        i, j = record['coefficient_x']*32, record['coefficient_y']*32
        if i != round(i) or j != round(j):
            raise ValueError('non-lattice M43D point')
        if (int(i)+int(j)) % 2 == 0:
            source_indices.append(index)
    records = []
    for new_index, source_index in enumerate(source_indices):
        record = dict(full_bank[source_index])
        if source_index >= prefix_count:
            record['m43d_template_index'] = source_index
        record['template_index'] = new_index
        records.append(record)
    return records, np.asarray(source_indices, dtype='<i8')


def fresh_truths(grid):
    def uniform(ordinal, axis):
        digest = hashlib.sha256(core.canonical_json_bytes([FRESH_LABEL, ordinal, axis])).digest()
        return (int.from_bytes(digest[:8], 'big') >> 11)/2**53
    left, right = float(grid.score_hz[256]), float(grid.score_hz[-257])
    result = []
    for ordinal in range(1024):
        r = math.sqrt((ordinal//32 + uniform(ordinal, 'r2'))/32)
        phase = (ordinal%32 + uniform(ordinal, 'phase'))/32
        row = {'truth_ordinal':ordinal, 'radial_stratum':ordinal//32, 'phase_stratum':ordinal%32,
               'coefficient_x':r*math.cos(2*math.pi*phase), 'coefficient_y':r*math.sin(2*math.pi*phase),
               'proxy_carrier_hz':left+(right-left)*uniform(ordinal, 'carrier')}
        row['truth_id'] = seal(row)
        result.append(row)
    return result


def subset_summary(pairs, distances, source_indices, full_count, grid):
    inverse = np.full(full_count, -1, dtype='<i8')
    inverse[source_indices] = np.arange(len(source_indices))
    mapped = inverse[pairs[:, 0]]
    use = mapped >= 0
    remapped = np.column_stack((mapped[use], pairs[use, 1])).astype('<i8')
    return bank_summary(remapped, distances[use], len(source_indices), grid)


def diagnose(matrix, truth_track, score_hz):
    details = [template_diagnostic(a, truth_track, score_hz, 0) for a in matrix]
    cause, counts = truth_cause(details)
    if cause == 'supported':
        raise RuntimeError('unexpected exact support in failed association')
    best = min(range(len(details)), key=lambda i:details[i]['minimum_continuous_residual_hz'])
    return {'cause':cause, 'template_cause_counts':counts, 'best_template_index':best,
            'best_continuous_fit':details[best], 'details_sha256':seal(details)}


def choose_bank(groups, ordered=('checker32', 'disk32')):
    """Use every preregistered development group; never tune on fresh data."""
    if not groups or any(g['truth_count'] <= 0 for g in groups):
        raise ValueError('empty development group')
    return next((name for name in ordered
                 if all(g['supported'][name]*100 >= g['truth_count']*95 for g in groups)), None)


def context():
    cfgpath = ROOT/'config/m43e_economical_bank.json'
    cfg = json.loads(cfgpath.read_text())
    for path, digest in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise RuntimeError('frozen file changed: '+path)
    old = read_sealed(ROOT/'results_m43d_bank_coverage/geometry.json.gz')
    metadata = json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text())
    basis = core.make_factor_basis_from_metadata(metadata)
    original = json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())['template_bank']['records']
    old_banks = nested_banks(original)
    full = old_banks['disk32']
    checker, selected = checkerboard_bank(full)
    banks = {'baseline':old_banks['baseline'], 'disk16':old_banks['disk16'], 'checker32':checker, 'disk32':full}
    indices = {name:np.arange(len(bank), dtype='<i8') for name,bank in banks.items()}
    indices['checker32'] = selected
    table = core.make_template_factor_table(basis, full, expected_template_bank_sha256=core.template_bank_sha256(full))
    if table.factor_table_sha256 != old['largest_factor_table_sha256'] or basis.basis_sha256 != old['factor_basis_sha256']:
        raise RuntimeError('M43D basis/table differ')
    epoch_matrices = tuple(core.factor_table_for_scan(table,basis,label) for label in LABELS)
    matrices = {act:np.ascontiguousarray(np.concatenate([epoch_matrices[i] for i in act],axis=1)) for act in ACTIVITY}
    grid = core.make_m37_proxy_carrier_grid('m37_1412p5')
    inventory = {}
    for name, bank in banks.items():
        inventory[name] = {'template_count':len(bank), 'bank_sha256':core.template_bank_sha256(bank),
            'm43d_source_indices_sha256':hashlib.sha256(indices[name].tobytes()).hexdigest(),
            'score_cells_per_window':len(bank)*grid.score_bin_count*32,
            'relative_score_cells_to_93':len(bank)/93,
            'factor_table_bytes_six_scans':len(bank)*table.factors.shape[1]*8}
    OUT.mkdir(exist_ok=True); (OUT/'checkpoints').mkdir(exist_ok=True)
    return {'cfg_sha':hashlib.sha256(cfgpath.read_bytes()).hexdigest(), 'old':old, 'basis':basis,
            'banks':banks,'indices':indices,'matrices':matrices,'grid':grid,'inventory':inventory}


def evaluate(c, truth, act, stage, ordinal, old_row=None, selection_sha=None):
    path = OUT/'checkpoints'/f'{stage}-{ordinal:04d}.json'
    if path.exists():
        row = read_sealed(path)
        if (row['config_sha256'] != c['cfg_sha'] or row['truth'] != truth or row['active_epochs'] != list(act)
                or row['selection_sha256'] != selection_sha
                or row['parent_row_sha256'] != (old_row['result_sha256'] if old_row else None)):
            raise RuntimeError('checkpoint ancestry differs')
        return row
    factors = tuple(core.template_factors_from_basis(c['basis'],truth,scan_label=l) for l in LABELS)
    y = np.float64(truth['proxy_carrier_hz'])*np.concatenate([factors[i] for i in act])
    tick = time.perf_counter()
    pairs, distances, work = candidate_pairs(c['grid'].score_hz, c['matrices'][act], y)
    summaries = {name:subset_summary(pairs, distances, c['indices'][name],3301,c['grid']) for name in c['banks']}
    geometry_seconds = time.perf_counter()-tick
    diagnoses = {}
    if old_row:
        # Reproduce all four original pair inventories and witnesses, including disk8.
        for name, count in (('baseline',93),('disk8',289),('disk16',889),('disk32',3301)):
            if bank_summary(pairs,distances,count,c['grid']) != old_row['banks'][name]:
                raise RuntimeError('M43D replay differs: '+name)
        for name in ('disk16','disk32'):
            if not old_row['banks'][name]['supported']:
                diagnoses[name] = diagnose(c['matrices'][act][c['indices'][name]],y,c['grid'].score_hz)
    row = {'config_sha256':c['cfg_sha'],'stage':stage,'ordinal':ordinal,'truth':truth,'active_epochs':list(act),
           'parent_row_sha256':old_row['result_sha256'] if old_row else None,
           'selection_sha256':selection_sha,'banks':summaries,'diagnoses':diagnoses,
           'm43d_four_bank_replay_exact':old_row is not None,
           'geometry_seconds':geometry_seconds,'distance_cells_evaluated':work}
    return write_sealed(path,row)


def summarize(rows, names):
    return {'truth_count':len(rows),'supported':{name:sum(r['banks'][name]['supported'] for r in rows) for name in names}}


def common_record(c):
    return {'config_sha256':c['cfg_sha'],'m43d_result_sha256':c['old']['result_sha256'],
            'bank_inventory':c['inventory'],'factor_basis_sha256':c['basis'].basis_sha256,
            'new_spectral_reads':0,'new_injections':0,'new_scores':0,
            'production_detector_changed':False,'sensitivity_claimed':False}


def development(c):
    rows=[]
    for ordinal,old_row in enumerate(c['old']['rows']):
        rows.append(evaluate(c,old_row['truth'],tuple(old_row['active_epochs']),'development',ordinal,old_row))
        if (ordinal+1)%256==0:print('M43D associations replayed',ordinal+1,'/2560',flush=True)
    if len(rows)!=2560:raise RuntimeError('M43D denominator differs')
    names=list(c['banks'])
    groups=[{'group':'historical',**summarize(rows[:512],names)}]
    for act in ACTIVITY:
        chosen=[r for r in rows[512:] if r['active_epochs']==list(act)]
        if len(chosen)!=512:raise RuntimeError('M43D development group differs')
        groups.append({'group':'m43d-known-'+''.join(map(str,act)),**summarize(chosen,names)})
    causes={}
    for name in ('disk16','disk32'):
        cases=[r for r in rows if name in r['diagnoses']]
        causes[name]={'failed_associations':len(cases),'unique_truth_ids':len({r['truth']['truth_id'] for r in cases}),
                      'causes':{cause:sum(r['diagnoses'][name]['cause']==cause for r in cases) for cause in CAUSES}}
    result={**common_record(c),'artifact_type':'m43e-development-and-cause-diagnosis-v1',
            'status':'development-complete-fresh-confirmation-pending','groups':groups,'cause_summary':causes,
            'm43d_associations_replayed':len(rows),'selected_bank':choose_bank(groups),'rows':rows}
    result=write_sealed(OUT/'development.json.gz',result)
    selection={**common_record(c),'artifact_type':'m43e-public-nomination-v1',
               'development_result_sha256':result['result_sha256'],'selected_bank':result['selected_bank'],
               'rule':'first of checker32,disk32 with >=95 percent in all five M43D development groups',
               'fresh_confirmation_evaluated':False}
    selection=write_sealed(OUT/'selection.json',selection)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True)
    print('PUBLISH selection.json before confirmation:',selection['result_sha256'],flush=True)


def confirmation(c):
    selection=read_sealed(OUT/'selection.json');dev=read_sealed(OUT/'development.json.gz')
    if (selection['config_sha256']!=c['cfg_sha'] or selection['development_result_sha256']!=dev['result_sha256']
            or selection['selected_bank']!=choose_bank(dev['groups']) or selection['bank_inventory']!=c['inventory']):
        raise RuntimeError('nomination ancestry differs')
    if selection['selected_bank'] is None:
        raise RuntimeError('no nominated bank; stop before fresh confirmation')
    fresh=fresh_truths(c['grid'])
    occupied={(r['truth']['coefficient_x'],r['truth']['coefficient_y']) for r in c['old']['rows']}
    occupied.update((r['coefficient_x'],r['coefficient_y']) for r in c['banks']['disk32'])
    new_points={(r['coefficient_x'],r['coefficient_y']) for r in fresh}
    if len(new_points)!=1024 or new_points & occupied:raise RuntimeError('fresh overlap or duplicate')
    rows=[]
    for i,t in enumerate(fresh):
        for j,act in enumerate(ACTIVITY):
            rows.append(evaluate(c,t,act,'confirmation',4*i+j,selection_sha=selection['result_sha256']))
        if (i+1)%128==0:print('fresh tracks',i+1,'/1024 (four activities each)',flush=True)
    groups=[]
    for act in ACTIVITY:
        chosen=[r for r in rows if r['active_epochs']==list(act)]
        if len(chosen)!=1024:raise RuntimeError('fresh denominator differs')
        groups.append({'active_epochs':list(act),**summarize(chosen,list(c['banks']))})
    nominee=selection['selected_bank']
    passed=all(g['supported'][nominee]*100>=g['truth_count']*95 for g in groups)
    result={**common_record(c),'artifact_type':'m43e-fresh-geometric-confirmation-v1',
            'status':'geometric-gate-passed-operational-validation-pending' if passed else 'geometric-gate-failed',
            'selection_sha256':selection['result_sha256'],'development_result_sha256':dev['result_sha256'],
            'fresh_truth_inventory_sha256':seal(fresh),'fresh_unique_tracks':1024,'fresh_associations':4096,
            'groups':groups,'selected_bank':nominee,'selected_bank_gate_passed':passed,
            'geometry_seconds_sum':sum(r['geometry_seconds'] for r in rows),
            'distance_cells_evaluated':sum(r['distance_cells_evaluated'] for r in rows),'rows':rows}
    result=write_sealed(OUT/'confirmation.json.gz',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['development','confirmation'],required=True)
    args=parser.parse_args();c=context()
    (development if args.stage=='development' else confirmation)(c)


if __name__=='__main__':main()
