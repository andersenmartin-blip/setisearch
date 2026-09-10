"""M43AI: select one fixed OR rule from closed M43AH development evidence.

Member acceptance sees observable features only. Case labels and associations
are confined to training selection and endpoint accounting. This module does
not run native acquisition or open old held-out panels.
"""
import argparse
import copy
import json
import math
from pathlib import Path

import m43ag_boundary_obstruction as ag
import m43ah_epoch_support as ah

ROOT = Path(__file__).resolve().parents[1]
METHODS = ah.METHODS
SOURCE_COMMIT = 'cc52f3b2f5a0cc3dfbf3dd84f65c14f272e71098'
SOURCE_HASHES = {
    'features.json': '5e68f47fb49375db9dcd082b41155d3ef58472f05a798168c7d0a067a463cd8a',
    'second_epoch_on.json': '943e800b92479f0cfe4c73afbac79d0a18b69cd5957cd9e94c3b1539dd7e19a7',
    'second_epoch_excess.json': '9cfffc4bc4842a1609477c500e4655911130b778196561d2f2f67d8bafe62e09',
    'input_manifest.json': 'fcbfe5c54940e3ba48d2a399b3817be44cb48e314c6e165d16f444a89e94cb70',
    'summary.json': '8dd8941832350ab7469e7b6aaad6986d708e8aa2e95696ef4199d6363a9a65d6',
}


def save(path, value):
    data = ag.canonical(value)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve completed M43AI evidence: '+str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def sealed(value):
    value = copy.deepcopy(value)
    value.pop('result_sha256', None)
    value['result_sha256'] = ag.sha(ag.canonical(value))
    return value


def verify_seal(value):
    if sealed(value) != value:
        raise ValueError('Changed M43AI sealed evidence')
    return value


def validate_model(model):
    if model.get('schema') != 'm43ai-two-rectangle-or-v1':
        raise ValueError('Wrong model schema')
    if model.get('operator') != 'member_or':
        raise ValueError('Wrong member operator')
    branches = model['branches']
    if [b['feature'] for b in branches] != list(METHODS):
        raise ValueError('Exactly the two frozen feature families are required')
    for b in branches:
        ah.finite(b['on_lower'])
        if b['off_upper'] is not None:
            ah.finite(b['off_upper'])
    return branches


def accepted_branches(model, features, off_coordinate):
    """Return branch names for one observable member; no truth fields needed."""
    branches = validate_model(model)
    off = ah.finite(off_coordinate)
    # Validate both features even when the first branch already passes.
    values = {name: ah.finite(features[name]) for name in METHODS}
    return [b['feature'] for b in branches
            if values[b['feature']] >= b['on_lower']
            and (b['off_upper'] is None or off < b['off_upper'])]


def select_model(families):
    """First optimum in the frozen descending-ON ledger, independently per family.

    This maximizes the ON lower cut among a family's published zero-leak
    minimum-loss states. Keep its exact strict OFF ceiling. No pair search,
    threshold midpoint, margin objective or post-evaluation adjustment is used.
    """
    branches = []
    for method in METHODS:
        result = families[method]['result']
        rows = result['sweep']
        minimum = min(len(r['control_free_required_losses']) for r in rows)
        indices = [i for i, r in enumerate(rows)
                   if len(r['control_free_required_losses']) == minimum]
        if (indices != result['control_free_optimal_state_indices']
                or minimum != result['minimum_required_losses_with_zero_leaks']):
            raise ValueError('Published optimum inventory differs')
        i = indices[0]
        row = rows[i]
        if row['lower_kind'] != 'finite':
            raise ValueError('No nonempty finite rule selected')
        branches.append(dict(feature=method, on_lower=row['on_lower'],
            off_upper=row['control_free_off_upper'], source_state_index=i,
            standalone_required_losses=row['control_free_required_losses']))
    model = dict(schema='m43ai-two-rectangle-or-v1', operator='member_or',
        branches=branches, selection='first zero-leak minimum-loss state in each descending-ON M43AH ledger',
        source_publication=SOURCE_COMMIT, detector_adopted=False)
    validate_model(model)
    return model


def case_endpoint(case, features, model):
    ids = [m['record_id'] for m in case['members']]
    if (len(ids) != len(set(ids)) or len(features) != len(ids)
            or {m['record_id'] for m in features} != set(ids)):
        raise ValueError('Incomplete or duplicate feature/member inventory')
    if case['complete'] is not True or type(case['signal_present']) is not bool:
        raise ValueError('Complete case evidence and explicit signal label required')
    by_id = {m['record_id']: m for m in features}
    decisions = []
    for member in case['members']:
        f = by_id[member['record_id']]
        if f['original_m43af_coordinate'] != member['coordinate']:
            raise ValueError('Original OFF coordinate binding differs')
        branches = accepted_branches(model, f, member['coordinate']['off'])
        decisions.append(dict(record_id=member['record_id'], branches=branches,
                              accepted=bool(branches)))
    accepted = {d['record_id'] for d in decisions if d['accepted']}
    associated = set(case['associated_record_ids'])
    recovered = bool(accepted & associated)
    return dict(name=case['name'], panel=case['panel'], signal_present=case['signal_present'],
        complete=True, eligible_members=len(ids), decisions=decisions,
        accepted_record_ids=sorted(accepted), associated_accepted_ids=sorted(accepted & associated),
        unassociated_accepted_ids=sorted(accepted-associated), recovered=recovered,
        control_leak=not case['signal_present'] and bool(accepted),
        false_control_association=not case['signal_present'] and recovered,
        reference_recovered={p: case['reference_recovered'][p] for p in ag.REFERENCES})


def summarize(rows):
    if len(rows) != len({r['name'] for r in rows}):
        raise ValueError('Duplicate endpoint case identity')
    signals = {r['name'] for r in rows if r['signal_present']}
    recovered = {r['name'] for r in rows if r['signal_present'] and r['recovered']}
    refs = {p: {r['name'] for r in rows if r['signal_present'] and r['reference_recovered'][p]}
            for p in ag.REFERENCES}
    required = set().union(*refs.values())
    leaks = sorted(r['name'] for r in rows if r['control_leak'])
    return dict(case_count=len(rows), signal_case_count=len(signals),
        non_signal_case_count=len(rows)-len(signals), required_signal_cases=sorted(required),
        recovered_signal_cases=sorted(recovered), lost_signal_cases=sorted(signals-recovered),
        required_signal_losses=sorted(required-recovered), leaking_non_signal_cases=leaks,
        false_control_associations=sorted(r['name'] for r in rows if r['false_control_association']),
        reference_counts={p: len(v) for p, v in refs.items()},
        reference_losses={p: sorted(v-recovered) for p, v in refs.items()},
        reference_gains={p: sorted(recovered-v) for p, v in refs.items()},
        signal_cases_with_unassociated_survivors=sorted(r['name'] for r in rows
            if r['signal_present'] and r['unassociated_accepted_ids']),
        joint_case_requirements_passed=not (required-recovered or leaks),
        eligible_members=sum(r['eligible_members'] for r in rows),
        surviving_members=sum(len(r['accepted_record_ids']) for r in rows))


def scalar_endpoint_audit(cases, ledger, model, outcomes):
    """Direct independent member reduction; does not call acceptance/accounting."""
    raw, excess = model['branches']
    checked = 0
    for case, feature_case, outcome in zip(cases, ledger, outcomes, strict=True):
        if case['name'] != feature_case['name'] or case['name'] != outcome['name']:
            raise ValueError('Audit case order differs')
        fm = {f['record_id']: f for f in feature_case['members']}
        expected = []
        for m in case['members']:
            f = fm[m['record_id']]
            y = m['coordinate']['off']
            a = f['second_epoch_on'] >= raw['on_lower']
            b = raw['off_upper'] is None or y < raw['off_upper']
            c = f['second_epoch_excess'] >= excess['on_lower']
            d = excess['off_upper'] is None or y < excess['off_upper']
            if (a and b) or (c and d):
                expected.append(m['record_id'])
            checked += 1
        expected.sort()
        matches = sorted(set(expected).intersection(case['associated_record_ids']))
        if (outcome['accepted_record_ids'] != expected or outcome['associated_accepted_ids'] != matches
                or outcome['recovered'] != bool(matches)
                or outcome['control_leak'] != (not case['signal_present'] and bool(expected))):
            raise ValueError('Independent scalar member/case audit differs')
    return dict(passed=True, cases_checked=len(cases), members_checked=checked)


def training_sources(training_root):
    source = ROOT/'results_m43ah_epoch_support'
    values = {}
    for name, sha in SOURCE_HASHES.items():
        data = (source/name).read_bytes()
        if ag.sha(data) != sha:
            raise ValueError('Published M43AH input changed: '+name)
        values[name] = json.loads(data)
    cases = []
    decision = ag.sealed_read(training_root/'results_m43af_response/model_decision.json')
    if decision['result_sha256'] != ag.DECISION_SEAL:
        raise ValueError('Changed original training decision')
    for item in decision['inventory']:
        p = (training_root/item['file']).resolve()
        if not p.is_relative_to((training_root/'results_m43af_response/records').resolve()):
            raise ValueError('Training input outside frozen record directory')
        if ag.sha(p.read_bytes()) != item['file_sha256']:
            raise ValueError('Changed original record bytes')
        record = ag.sealed_read(p)
        ah.check_record(record, item, decision)
        cases.append(record['summary'])
    required = values['summary.json']['required_signal_cases']
    ag.validate_cases(cases, required)
    if (len(cases) != 241 or len(required) != 57 or sum(c['signal_present'] for c in cases) != 64):
        raise ValueError('Changed training denominators')
    return cases, values['features.json'], {m: values[m+'.json'] for m in METHODS}, required


def verify_public_receipt(path, expected_kind, expected_files):
    receipt = verify_seal(json.loads(path.read_text()))
    if receipt.get('kind') != expected_kind or receipt.get('remote_verified') is not True:
        raise ValueError('Verified public receipt required')
    if receipt.get('files') != expected_files:
        raise ValueError('Public receipt does not bind current bytes')
    if not isinstance(receipt.get('commit'), str) or len(receipt['commit']) != 40:
        raise ValueError('Exact public commit required')
    return receipt


def train(training_root, output):
    cfg_path = ROOT/'config/m43ai_combined_rule.json'
    cfg = json.loads(cfg_path.read_text())
    files = {p: ag.sha((ROOT/p).read_bytes()) for p in cfg['protocol_files']}
    files['config/m43ai_combined_rule.json'] = ag.sha(cfg_path.read_bytes())
    receipt = verify_public_receipt(ROOT/'results_m43ai_preparation/public_freeze.json', 'protocol', files)
    cases, ledger, families, required = training_sources(training_root)
    model = select_model(families)
    outcomes = [case_endpoint(c, f['members'], model) for c, f in zip(cases, ledger, strict=True)]
    audit = scalar_endpoint_audit(cases, ledger, model, outcomes)
    summary = summarize(outcomes)
    if summary['required_signal_cases'] != required:
        raise ValueError('Required training set differs')
    # This case-union certificate is independent of new member acceptance.
    expected_union = set()
    for branch in model['branches']:
        accounting = families[branch['feature']]['recovery_accounting']['zero_leak_optimal_states']
        row = next(r for r in accounting if r['state_index'] == branch['source_state_index'])
        expected_union.update(row['recovered_signal_cases'])
    if sorted(expected_union) != summary['recovered_signal_cases']:
        raise ValueError('Published single-family recovery union differs')
    model.update(protocol_commit=receipt['commit'], config_sha256=ag.sha(cfg_path.read_bytes()),
        training_eligible=summary['joint_case_requirements_passed'],
        required_training_signal_cases=required)
    model = sealed(model)
    summary.update(milestone='M43AI', phase='closed_training_selection',
        model_sha256=model['result_sha256'], public_protocol_commit=receipt['commit'],
        model_selected=True, detector_adopted=False, independent_validation_passed=False,
        old_heldout_opened=False, new_native_inputs_evaluated=0, new_observing_sequences=0,
        published_case_union_certificate_passed=True, scalar_audit=audit)
    payloads={'model.json':model,'training_endpoints.json':outcomes,'training_summary.json':summary}
    for name, value in payloads.items():
        data=ag.canonical(value)
        if (output/name).exists() and (output/name).read_bytes()!=data:
            raise ValueError('Preserve closed selection outputs')
    for name, value in payloads.items():
        save(output/name, value)
    save(output/'training_manifest.json', dict(files=[dict(path=n,sha256=ag.sha(ag.canonical(v))) for n,v in payloads.items()]))
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--training-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'results_m43ai_combined_rule')
    a=p.parse_args()
    train(a.training_root.resolve(),a.output)
