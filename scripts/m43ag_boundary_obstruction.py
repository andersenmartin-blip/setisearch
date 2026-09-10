"""Retrospective exact obstruction audit of sealed M43AF training coordinates.

This script never selects a detector, acquires profiles, or opens validation.
It exhausts the acceptance-equivalent continuous ON cuts and proves the two
extreme training costs for the unchanged family x >= a, y < b.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

SOURCE_COMMIT = 'bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833'
DECISION_SEAL = 'e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3'
REFERENCES = ('neighbor9', 'centered_receiver_off_match_aggregate')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sealed_read(path):
    data = path.read_bytes()
    value = json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)
    payload = dict(value)
    seal = payload.pop('result_sha256')
    if sha(canonical(payload)) != seal:
        raise ValueError('Invalid result seal: '+str(path))
    return value


def validate_cases(cases, required):
    if not cases or len({c['name'] for c in cases}) != len(cases):
        raise ValueError('Nonempty unique case inventory required')
    if not required or len(set(required)) != len(required):
        raise ValueError('Nonempty unique required signal set required')
    signals = {c['name'] for c in cases if c['signal_present']}
    if not set(required) <= signals:
        raise ValueError('Required case is absent or is not a signal')
    for c in cases:
        if c['panel'] not in ('training', 'baseline', 'null_training'):
            raise ValueError('Only closed training/baseline/null summaries allowed')
        if type(c['signal_present']) is not bool or not c['complete']:
            raise ValueError('Complete evidence and explicit signal label required')
        ids = [m['record_id'] for m in c['members']]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate within-case member identity')
        for m in c['members']:
            v = m['coordinate']
            if v is None or any(type(v[k]) not in (float, int) or not math.isfinite(v[k])
                                for k in ('on', 'off')):
                raise ValueError('Complete finite coordinates required')


def points(cases, required):
    """Case OR reduction: associated members for recovery, any control member."""
    required = set(required)
    rows = []
    for c in cases:
        associated = set(c['associated_record_ids'])
        for m in c['members']:
            if not c['signal_present'] or (c['name'] in required and m['record_id'] in associated):
                rows.append((m['coordinate']['on'], m['coordinate']['off'], c['name'],
                             m['record_id'], c['signal_present']))
    return rows


def exact_sweep(cases, required):
    validate_cases(cases, required)
    required = sorted(required)
    controls = sorted(c['name'] for c in cases if not c['signal_present'])
    # Include EVERY eligible member's x, including unassociated signal members,
    # to enumerate all original-rule ON-cut equivalence classes without pruning.
    all_x = sorted({m['coordinate']['on'] for c in cases for m in c['members']}, reverse=True)
    by_x = collections.defaultdict(list)
    for row in points(cases, required):
        by_x[row[0]].append(row)
    signal_min = {name: math.inf for name in required}
    control_min = {name: math.inf for name in controls}
    sweep = []

    def record(a, kind):
        control_floor = min(control_min.values(), default=math.inf)
        lost = sorted(n for n, y in signal_min.items() if not y < control_floor)
        needed = max(signal_min.values())
        leaking = (None if math.isinf(needed) else
                   sorted(n for n, y in control_min.items() if y <= needed))
        sweep.append(dict(on_lower=a, lower_kind=kind,
                          control_free_required_losses=lost,
                          control_free_off_upper=None if math.isinf(control_floor) else control_floor,
                          all_required_off_strict_lower=None if math.isinf(needed) else needed,
                          all_required_min_leaking_cases=leaking))

    record(None, 'above_maximum')
    for a in all_x:
        for _, y, name, _, signal in by_x[a]:
            minima = signal_min if signal else control_min
            minima[name] = min(minima[name], y)
        record(a, 'finite')
    best_loss = min(len(r['control_free_required_losses']) for r in sweep)
    zero_loss_rows = [r for r in sweep if r['all_required_min_leaking_cases'] is not None]
    best_leaks = min((len(r['all_required_min_leaking_cases']) for r in zero_loss_rows), default=None)
    return dict(required_signal_cases=required, non_signal_cases=controls,
                on_cut_equivalence_classes=len(sweep),
                minimum_required_losses_with_zero_leaks=best_loss,
                minimum_leaking_cases_with_all_required=best_leaks,
                control_free_optimal_state_indices=[i for i, r in enumerate(sweep)
                    if len(r['control_free_required_losses']) == best_loss],
                all_required_optimal_state_indices=[i for i, r in enumerate(sweep)
                    if r['all_required_min_leaking_cases'] is not None
                    and len(r['all_required_min_leaking_cases']) == best_leaks], sweep=sweep)


def dominance_certificates(cases, required):
    """A control with xc>=xs and yc<=ys must pass any rule accepting this member."""
    rows = points(cases, required)
    controls = sorted((r for r in rows if not r[4]), key=lambda r:(r[2], r[3]))
    certificates = []
    for name in sorted(required):
        signals = sorted((r for r in rows if r[4] and r[2] == name), key=lambda r:r[3])
        blocked, unblocked = [], []
        for x, y, _, rid, _ in signals:
            witness = next((c for c in controls if c[0] >= x and c[1] <= y), None)
            if witness is None:
                unblocked.append(rid)
            else:
                blocked.append(dict(signal_record_id=rid, signal_coordinate=dict(on=x, off=y),
                    control_case=witness[2], control_record_id=witness[3],
                    control_coordinate=dict(on=witness[0], off=witness[1])))
        certificates.append(dict(case=name, eligible_associated_members=len(signals),
            individually_impossible_without_leaks=not unblocked,
            reason=('no_eligible_associated_members' if not signals else
                    'every_associated_member_dominated' if not unblocked else None),
            blocked_members=blocked, undominated_member_ids=unblocked))
    return certificates


def direct_audit(cases, result, certificates, expected_required):
    """Independent per-cut scalar scan; no incremental minima or sweep helper."""
    required = sorted(expected_required)
    validate_cases(cases, required)
    if result['required_signal_cases'] != required:
        raise ValueError('Required-case inventory differs from sealed inputs')
    case_map = {c['name']:c for c in cases}
    controls = sorted(c['name'] for c in cases if not c['signal_present'])
    if result['non_signal_cases'] != controls:
        raise ValueError('Incorrect non-signal inventory')
    expected_x = sorted({m['coordinate']['on'] for c in cases for m in c['members']}, reverse=True)
    expected_cuts = [('above_maximum', None)]+[('finite', x) for x in expected_x]
    if [(r['lower_kind'], r['on_lower']) for r in result['sweep']] != expected_cuts:
        raise ValueError('Incomplete ON-cut partition')
    if result['on_cut_equivalence_classes'] != len(expected_cuts):
        raise ValueError('Incorrect ON-cut count')
    if sorted(c['case'] for c in certificates) != sorted(required):
        raise ValueError('Incomplete required-case certificate inventory')
    checked_members = 0
    audited_losses, audited_leaks = [], []
    for row in result['sweep']:
        minima = {}
        for c in cases:
            ys = []
            for m in c['members']:
                checked_members += 1
                v = m['coordinate']
                accepted_x = row['lower_kind'] == 'finite' and v['on'] >= row['on_lower']
                associated = m['record_id'] in c['associated_record_ids']
                if accepted_x and (not c['signal_present'] or associated):
                    ys.append(v['off'])
            minima[c['name']] = min(ys, default=math.inf)
        control_floor = min((v for n,v in minima.items() if not case_map[n]['signal_present']),
                            default=math.inf)
        losses = sorted(n for n in required if minima[n] >= control_floor)
        needed = max(minima[n] for n in required)
        leaks = None if math.isinf(needed) else sorted(n for n,v in minima.items()
            if not case_map[n]['signal_present'] and v <= needed)
        if losses != row['control_free_required_losses'] or leaks != row['all_required_min_leaking_cases']:
            raise ValueError('Independent ON-cut audit failed')
        if row['control_free_off_upper'] != (None if math.isinf(control_floor) else control_floor):
            raise ValueError('Independent control ceiling differs')
        if row['all_required_off_strict_lower'] != (None if math.isinf(needed) else needed):
            raise ValueError('Independent signal requirement differs')
        audited_losses.append(len(losses))
        audited_leaks.append(None if leaks is None else len(leaks))
    best_loss = min(audited_losses)
    best_leak = min((n for n in audited_leaks if n is not None), default=None)
    if (result['minimum_required_losses_with_zero_leaks'] != best_loss
        or result['minimum_leaking_cases_with_all_required'] != best_leak
        or result['control_free_optimal_state_indices'] !=
            [i for i, n in enumerate(audited_losses) if n == best_loss]
        or result['all_required_optimal_state_indices'] !=
            [i for i, n in enumerate(audited_leaks) if n is not None and n == best_leak]):
        raise ValueError('Independent headline optimum differs')
    witness_count = 0
    for cert in certificates:
        c = case_map[cert['case']]
        members = {m['record_id']:m['coordinate'] for m in c['members']
                   if m['record_id'] in c['associated_record_ids']}
        listed = [w['signal_record_id'] for w in cert['blocked_members']] + cert['undominated_member_ids']
        if (len(listed) != len(set(listed)) or set(listed) != set(members)
            or cert['eligible_associated_members'] != len(members)):
            raise ValueError('Incomplete member certificate')
        for w in cert['blocked_members']:
            signal = members[w['signal_record_id']]
            cc = case_map[w['control_case']]
            control = next(m['coordinate'] for m in cc['members'] if m['record_id'] == w['control_record_id'])
            if cc['signal_present'] or signal != w['signal_coordinate'] or control != w['control_coordinate']:
                raise ValueError('Incorrect certificate source')
            if not (control['on'] >= signal['on'] and control['off'] <= signal['off']):
                raise ValueError('Invalid dominance inequality')
            first_witness = next((
                (name, m['record_id']) for name in controls
                for m in sorted(case_map[name]['members'], key=lambda m:m['record_id'])
                if m['coordinate']['on'] >= signal['on']
                and m['coordinate']['off'] <= signal['off']), None)
            if first_witness != (w['control_case'], w['control_record_id']):
                raise ValueError('Noncanonical dominance witness')
            witness_count += 1
        for rid in cert['undominated_member_ids']:
            v = members[rid]
            for other in cases:
                if other['signal_present']:
                    continue
                if any(m['coordinate']['on'] >= v['on'] and m['coordinate']['off'] <= v['off']
                       for m in other['members']):
                    raise ValueError('Undominated label is false')
        if cert['individually_impossible_without_leaks'] != (not cert['undominated_member_ids']):
            raise ValueError('Incorrect impossibility label')
        expected_reason = ('no_eligible_associated_members' if not members else
            'every_associated_member_dominated' if not cert['undominated_member_ids'] else None)
        if cert['reason'] != expected_reason:
            raise ValueError('Incorrect impossibility reason')
    return dict(passed=True, independently_scanned_on_classes=len(result['sweep']),
                scalar_member_visits=checked_members, verified_dominance_witnesses=witness_count,
                headline_optima_verified=True, optimal_state_indices_verified=True,
                certificate_reasons_verified=True, deterministic_witnesses_verified=True)


def audit_old_grid(cases, grid, required):
    """Reproduce stored aggregate costs without calling either fitting code."""
    if grid['required_signal_cases'] != sorted(required):
        raise ValueError('Required signal set changed')
    for row in grid['grid']:
        a, b = row['boundary']['on_lower'], row['boundary']['off_upper']
        recovered, leaks = set(), []
        for c in cases:
            surviving = {m['record_id'] for m in c['members']
                if (a is None or m['coordinate']['on'] >= a)
                and (b is None or m['coordinate']['off'] < b)}
            if c['signal_present'] and surviving.intersection(c['associated_record_ids']):
                recovered.add(c['name'])
            if not c['signal_present'] and surviving:
                leaks.append(c['name'])
        losses = sorted(set(required)-recovered)
        if (row['required_signal_losses'] != losses
            or sorted(row['leaking_control_or_baseline_cases']) != sorted(leaks)
            or row['recovered_signal_cases'] != len(recovered)
            or row['feasible'] != (not losses and not leaks)):
            raise ValueError('Historical grid differs')
    return dict(passed=True, checked_grid_points=len(grid['grid']),
        minimum_required_losses_with_zero_leaks=min((len(r['required_signal_losses'])
            for r in grid['grid'] if not r['leaking_control_or_baseline_cases']), default=None),
        minimum_leaking_cases_with_all_required=min((len(r['leaking_control_or_baseline_cases'])
            for r in grid['grid'] if not r['required_signal_losses']), default=None))


def run(root, output):
    source = root/'results_m43af_response'
    decision = sealed_read(source/'model_decision.json')
    if decision['result_sha256'] != DECISION_SEAL or decision['feasible'] or decision['native_validation_opened']:
        raise ValueError('Expected immutable failed training decision')
    cases, input_files, phases = [], [], collections.Counter()
    for item in decision['inventory']:
        path = (root/item['file']).resolve()
        if not path.is_relative_to((source/'records').resolve()) or item['phase'] not in ('training', 'baseline', 'null_training'):
            raise ValueError('Input outside closed training inventory')
        if sha(path.read_bytes()) != item['file_sha256']:
            raise ValueError('Input file changed')
        record = sealed_read(path)
        if (record['result_sha256'] != item['record_sha256'] or record['phase'] != item['phase']
            or record['freeze_commit'] != decision['freeze_commit'] or record['config_sha256'] != decision['config_sha256']
            or record['summary']['name'] != item['name'] or record['summary']['panel'] != item['phase']
            or record['native_payload_identity'] != item['native_payload_identity']):
            raise ValueError('Input provenance changed')
        cases.append(record['summary'])
        input_files.append(dict(path=item['file'], sha256=item['file_sha256'], record_sha256=item['record_sha256']))
        phases[item['phase']] += 1
    if dict(phases) != {'baseline':1, 'training':112, 'null_training':128}:
        raise ValueError('Unexpected phase inventory')
    required = sorted(c['name'] for c in cases if c['signal_present']
        and any(c['reference_recovered'][p] for p in REFERENCES))
    if len(required) != 57:
        raise ValueError('Required recovery denominator changed')
    result = exact_sweep(cases, required)
    certs = dominance_certificates(cases, required)
    audit = direct_audit(cases, result, certs, required)
    grid = sealed_read(source/'training_grid.json.gz')
    if grid['result_sha256'] != decision['training_grid_sha256']:
        raise ValueError('Historical grid seal changed')
    grid_audit = audit_old_grid(cases, grid, required)
    summary = {k:v for k,v in result.items() if k not in ('sweep', 'non_signal_cases')}
    summary.update(milestone='M43AG', scope='retrospective_closed_training_boundary_obstruction',
        source_publication=SOURCE_COMMIT, model_decision_sha256=DECISION_SEAL,
        input_records=len(cases), input_phase_counts=dict(phases),
        training_distinct_native_payloads=decision['training_distinct_payloads'],
        eligible_members=sum(len(c['members']) for c in cases),
        required_associated_members=sum(c['eligible_associated_members'] for c in certs),
        individually_impossible_cases=[c['case'] for c in certs if c['individually_impossible_without_leaks']],
        empty_non_signal_cases=sum(not c['members'] for c in cases if not c['signal_present']),
        baseline_eligible_members=sum(len(c['members']) for c in cases if c['panel']=='baseline'),
        native_null_eligible_members=sum(len(c['members']) for c in cases if c['panel']=='null_training'),
        original_grid_audit=grid_audit, independent_audit=audit,
        selected_boundary=None, detector_adopted=False, new_detector_executions=0,
        validation_opened=False, new_observing_sequences=0,
        physical_false_alarm_probability_measured=False, astronomical_candidate_claimed=False)
    payloads = {'summary.json':summary, 'on_cut_sweep.json':result['sweep'],
                'dominance_certificates.json':certs, 'input_manifest.json':input_files}
    output.mkdir(parents=True, exist_ok=True)
    manifests = []
    for name, value in payloads.items():
        data = canonical(value)
        path = output/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Preserve differing completed diagnostic: '+name)
        path.write_bytes(data)
        manifests.append(dict(path=name, bytes=len(data), sha256=sha(data)))
    manifest = canonical(dict(format='m43ag-derived-diagnostic-v1', files=manifests))
    mp = output/'manifest.json'
    if mp.exists() and mp.read_bytes() != manifest:
        raise ValueError('Preserve differing diagnostic manifest')
    mp.write_bytes(manifest)
    print(json.dumps({k:summary[k] for k in ('milestone', 'input_records', 'eligible_members',
        'on_cut_equivalence_classes', 'minimum_required_losses_with_zero_leaks',
        'minimum_leaking_cases_with_all_required', 'individually_impossible_cases', 'independent_audit')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    run(args.root.resolve(), args.output or args.root/'results_m43ag_obstruction')
