"""Prospective M43AF native translation challenge and joint response study."""
import argparse
import copy
import gzip
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path

import numpy as np

import m43ae_joint_response as ae
from m43e_economical_bank import read_sealed, write_sealed
from m43af_scalar_audit import audit_acquisition
from seti_repeater import detector_m43u as detector, search_v0p6 as core
from seti_repeater.acquisition_m43af import acquire
from seti_repeater.boundary_m43af import coordinates, fit, case_outcome, REFERENCES
from seti_repeater.native_null_m43af import NativeShiftOverlay

ROOT = ae.ROOT
OUT = ROOT/'results_m43af_response'
CONFIG = ROOT/'config/m43af_response_study.json'


def save(path, record):
    payload = dict(record)
    payload.pop('result_sha256', None)
    payload['result_sha256'] = detector.digest(payload)
    if path.exists():
        assert read_sealed(path) == payload, 'preserve closed result: '+str(path)
        return payload
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = core.canonical_json_bytes(payload)
    data = gzip.compress(raw, compresslevel=6, mtime=0) if path.suffix == '.gz' else raw+b'\n'
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(data)
    temp.replace(path)
    return payload


def validate(freeze=None):
    cfg = json.loads(CONFIG.read_text())
    assert platform.python_version() == cfg['python_version']
    assert {n:importlib.metadata.version(n) for n in cfg['dependencies']} == cfg['dependencies']
    for p, h in cfg['pinned_sha256'].items():
        assert ae.sha(ROOT/p) == h, p
    if freeze:
        receipt = read_sealed(OUT/'public_freeze.json')
        assert receipt['remote_verified'] and receipt['commit'] == freeze
        assert receipt['config_sha256'] == ae.sha(CONFIG)
        assert subprocess.check_output(['git', 'show', freeze+':'+str(CONFIG.relative_to(ROOT))], cwd=ROOT) == CONFIG.read_bytes()
    return cfg


def context(runtime):
    # The unchanged M43AE context verifies the original 96 arrays, 48 native
    # gathers and M43Z calibration binding. Only the new null view is derived.
    return ae.context(runtime, json.loads(ae.CONFIG.read_text()))


def native_samples(c, store):
    checks = []
    for kind in ('on', 'off'):
        for e in range(3):
            src = c.receiver.cache(f'epoch{e+1}_{kind}', 1).source
            for w in core.M37_SPECTRAL_WIDTHS:
                for t in (0, len(c.bank)//2, len(c.bank)-1):
                    for pos in (0, c.grid.support_bin_count//2, c.grid.support_bin_count-1):
                        idx = c.overlay.joint_indices[kind, e][t, :, pos]
                        expected = ae.prior.raw_window_score(src, idx, [], w)['score']
                        value = store.get(kind, t, w)[0][e, pos]
                        assert np.float32(expected).view('<u4') == value.view('<u4')
                        checks.append(dict(kind=kind, epoch=e, width=w, template=t,
                                           support_index=pos, score=float(value), exact=True))
    assert len(checks) == 432
    return checks


def preflight(runtime):
    cfg = validate()
    c = context(runtime)
    zero = NativeShiftOverlay(c.receiver, [0, 0, 0], c.bank, c.table, c.basis, c.grid)
    for key in c.baseline.expected_ids:
        assert np.array_equal(zero.baseline.get(*key)[0].view('<u4'),
                              c.baseline.get(*key)[0].view('<u4')), key
    z = copy.copy(c)
    z.receiver, z.overlay = zero.receiver, zero
    samples = native_samples(z, zero.baseline)
    save(OUT/'runtime_preflight.json', dict(passed=True, config_sha256=ae.sha(CONFIG),
        all_96_arrays_exact=True, all_48_native_gathers_exact=True,
        zero_translation_all_score_bits_exact=True, direct_native_checks=samples,
        new_null_rows_evaluated=0, new_response_descriptors_evaluated=0,
        original_calibration_binding=c.binding))
    print('M43AF NATIVE PREFLIGHT PASSED', flush=True)


def collect(c, cfg, freeze, case, phase, source=None):
    name = ('historical__' if phase.startswith('historical') else '')+case['name']
    path = OUT/'records'/(name+'.json.gz')
    if path.exists():
        r = read_sealed(path)
        assert r['case'] == case and r['phase'] == phase
        assert r['freeze_commit'] == freeze and r['config_sha256'] == ae.sha(CONFIG)
        return r
    is_null = phase.startswith('null_')
    historical = None
    if source is not None:
        assert ae.sha(ROOT/source['file']) == source['file_sha256']
        historical = read_sealed(ROOT/source['file'])
        assert historical['result_sha256'] == source['record_sha256']
        store = c.overlay.trial(case['components'])
        assert ae.payload_identity(c) == historical['native_payload_identity']
        geo = copy.deepcopy(historical['geometry_member_audit'])
        original = None
        rows = copy.deepcopy(historical['endpoints'])
        reused = historical['profiles']
    else:
        store, original, audits = ae.upstream(c, case)
        geo = ae.geometry_audit(original)
        rows = ([] if is_null else [ae.endpoint_row(c, case, p, a, path.name,
            original['additional_evidence_complete'] if p == ae.prior.POLICIES[-1] else True)
            for p, a in audits.items()])
        reused = {}
    parts = ae.prior.native_parts(c.overlay, case['components'])
    direct, seen = [], {}

    def check(kind, e, t, w, pos, score):
        key = kind, e, t, w, pos
        if key in seen:
            assert seen[key] == score
            return
        src = c.receiver.cache(f'epoch{e+1}_{kind}', 1).source
        d = ae.prior.raw_window_score(src, c.overlay.joint_indices[kind, e][t, :, pos],
                                      parts.get((kind, e), []), w)
        assert np.float32(d['score']).view('<u4') == np.float32(score).view('<u4')
        direct.append(dict(kind=kind, epoch=e, template=t, width=w,
                           support_index=pos, score=score, exact=True))
        seen[key] = score

    evidence = acquire(geo, store, c.grid, c.on, c.off, reused, check)
    scalar = audit_acquisition(geo, evidence, c.grid, c.on, c.off)
    associated = rows[0]['truth_association']['associated_record_ids'] if rows else []
    summary = dict(name=case['name'], panel=phase, signal_present=case.get('signal_present', False),
        complete=evidence['counts']['incomplete_profiles'] == 0 and evidence['counts']['undefined_member_measurements'] == 0,
        members=[dict(record_id=m['record_id'], coordinate=coordinates(m)) for m in evidence['measurements']],
        associated_record_ids=associated,
        reference_recovered={p:next((r['recovered'] for r in rows if r['policy'] == p), False) for p in REFERENCES})
    r = save(path, dict(case=case, phase=phase, freeze_commit=freeze, config_sha256=ae.sha(CONFIG),
        source=source, upstream_evidence=original, upstream_reused=source is not None,
        geometry_member_audit=geo, native_payload_identity=ae.payload_identity(c),
        original_endpoints=rows, acquisition=evidence, scalar_audit=scalar, direct_checks=direct,
        null_direct_native_checks=native_samples(c, store) if is_null else [],
        upstream_final_counts=(original['final_counts'] if original else historical['final_counts']),
        summary=summary))
    print(json.dumps(dict(name=case['name'], phase=phase, eligible=len(summary['members']),
                         complete=summary['complete'])), flush=True)
    return r


def index_record(r):
    name = ('historical__' if r['phase'].startswith('historical') else '')+r['case']['name']
    path = OUT/'records'/(name+'.json.gz')
    return dict(name=r['case']['name'], phase=r['phase'], file=str(path.relative_to(ROOT)),
                file_sha256=ae.sha(path), record_sha256=r['result_sha256'],
                native_payload_identity=r['native_payload_identity'])


def null_records(c, cfg, freeze, phase):
    rows = cfg['training_native_shifts'] if phase == 'null_training' else cfg['heldout_native_shifts']
    records = []
    for i, shifts in enumerate(rows):
        case = dict(name=f'{phase}{i:03d}', components=[], shifts=shifts, signal_present=False)
        path = OUT/'records'/(case['name']+'.json.gz')
        if path.exists():
            record = read_sealed(path)
            assert record['case'] == case and record['phase'] == phase
            assert record['freeze_commit'] == freeze and record['config_sha256'] == ae.sha(CONFIG)
        else:
            overlay = NativeShiftOverlay(c.receiver, shifts, c.bank, c.table, c.basis, c.grid)
            shifted = copy.copy(c)
            shifted.overlay, shifted.receiver, shifted.baseline = overlay, overlay.receiver, overlay.baseline
            record = collect(shifted, cfg, freeze, case, phase)
            del overlay, shifted
        records.append(record)
    return records


def run(runtime, freeze, phase, model_publication=None):
    cfg = validate(freeze)
    pre = read_sealed(OUT/'runtime_preflight.json')
    assert pre['passed'] and pre['config_sha256'] == ae.sha(CONFIG)
    c = context(runtime)
    if phase == 'training':
        assert not (OUT/'model_decision.json').exists(), 'preserve completed training'
        nulls = null_records(c, cfg, freeze, 'null_training')
        baseline_source = cfg['historical_sources']['baseline']
        baseline_case = read_sealed(ROOT/baseline_source['file'])['case']
        baseline = collect(c, cfg, freeze, baseline_case, 'baseline', baseline_source)
        training = [collect(c, cfg, freeze, case, 'training') for case in cfg['training_cases']]
        native = {r['native_payload_identity'] for r in training}
        overlap = native.intersection(cfg['previous_native_payload_identities'])
        model = fit([r['summary'] for r in training], baseline['summary'], [r['summary'] for r in nulls])
        from m43af_study_audit import audit_fit
        model_audit = audit_fit([r['summary'] for r in training], baseline['summary'],
                               [r['summary'] for r in nulls], model)
        save(OUT/'training_audit.json', model_audit)
        model = save(OUT/'training_grid.json.gz', model)
        decision = save(OUT/'model_decision.json', dict(freeze_commit=freeze, config_sha256=ae.sha(CONFIG),
            feasible=model['feasible'] and not overlap,
            boundary=model['boundary'] if not overlap else None,
            reason=model['reason'] if not overlap else 'training_native_payload_overlap',
            training_grid_sha256=model['result_sha256'],
            inventory=[index_record(r) for r in [baseline]+training+nulls],
            native_payload_overlap=sorted(overlap), training_distinct_payloads=len(native),
            training_native_nulls=len(nulls), null_eligible_members=sum(len(r['summary']['members']) for r in nulls),
            conditional_profile_tail_measured=any(r['summary']['members'] for r in nulls),
            native_validation_opened=False, general_adoption_qualified=False))
        print(json.dumps({k:decision[k] for k in ('feasible', 'boundary', 'reason', 'null_eligible_members')}), flush=True)
        return
    decision = read_sealed(OUT/'model_decision.json')
    assert decision['freeze_commit'] == freeze and decision['config_sha256'] == ae.sha(CONFIG)
    if not model_publication:
        raise ValueError('public model decision commit required before historical/validation work')
    assert subprocess.check_output(['git', 'show', model_publication+':results_m43af_response/model_decision.json'], cwd=ROOT) == (OUT/'model_decision.json').read_bytes()
    publication = read_sealed(OUT/'model_publication.json')
    assert publication['remote_verified'] and publication['commit'] == model_publication
    assert publication['model_decision_sha256'] == decision['result_sha256']
    if phase == 'historical':
        for name, source in cfg['historical_sources'].items():
            if name == 'baseline':
                continue
            old = read_sealed(ROOT/source['file'])
            group = 'historical_original' if old['case']['panel'] == 'historical' else 'historical_additional'
            collect(c, cfg, freeze, old['case'], group, source)
    elif phase == 'validation':
        if not decision['feasible']:
            raise ValueError('no feasible training model; validation must remain unopened')
        null_records(c, cfg, freeze, 'null_validation')
        for case in cfg['validation_cases']:
            collect(c, cfg, freeze, case, 'validation')
    else:
        raise ValueError('unknown phase')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--freeze')
    p.add_argument('--phase', choices=('training', 'historical', 'validation'))
    p.add_argument('--preflight', action='store_true')
    p.add_argument('--model-publication')
    a = p.parse_args()
    if a.preflight:
        preflight(a.runtime_root)
    else:
        if not a.freeze or not a.phase:
            p.error('--freeze and --phase required')
        run(a.runtime_root, a.freeze, a.phase, a.model_publication)
