"""Frozen retrospective M43AH epoch-support development study.

Only the 241 public M43AF training records are read. Features use observable
epoch/profile measurements; truth is used solely for labelled case accounting.
No native acquisition, held-out evaluation, or detector adoption occurs.
"""
import argparse
import collections
import copy
import itertools
import json
import math
from pathlib import Path

import m43ag_boundary_obstruction as ag

ROOT = Path(__file__).resolve().parents[1]
AG_CODE_SHA256 = '965811aad83defa0d626dc67131cde5d263316d3575a1246c239bbc325bbeec6'
AG_SUMMARY_SHA256 = 'a484805b972ec9b87e3fb46fdf6396b33703924bd447b42e517f80d428313f16'
METHODS = ('second_epoch_on', 'second_epoch_excess')
HYPOTHESES = ('receiver_mean', 'candidate_track')
TOLERANCE = 1e-11


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite numeric evidence required')
    return value


def close(a, b):
    return math.isclose(finite(a), finite(b), rel_tol=TOLERANCE, abs_tol=TOLERANCE)


def second_largest(values):
    if len(values) not in (2, 3):
        raise ValueError('Exactly two or three active epochs required')
    return sorted(finite(x) for x in values)[-2]


def identity(member):
    active = member['active_epochs_zero_based']
    if (len(active) not in (2, 3) or active != sorted(set(active))
        or any(type(e) is not int or e not in (0, 1, 2) for e in active)):
        raise ValueError('Canonical active-epoch subset required')
    t, q, w = (member[k] for k in
               ('template_index', 'proxy_carrier_index', 'spectral_width_channels'))
    if any(type(v) is not int or v < 0 for v in (t, q, w)) or w < 1:
        raise ValueError('Invalid observable member identity')
    if len(member['epoch_values_at_proxy_carrier']) != 3:
        raise ValueError('Three original epoch values required')
    for x in member['epoch_values_at_proxy_carrier']:
        finite(x)
    return active, t, q, w


def member_features(member, measurement):
    """Primary extraction from retained ON centers and sealed OFF measurements.

    This function takes no case, injection specification or truth association.
    An inactive epoch is never substituted for missing active evidence.
    """
    active, t, q, w = identity(member)
    if (measurement['record_id'] != member['record_id']
        or measurement['active_epochs'] != active or measurement['spectral_width'] != w):
        raise ValueError('Member/measurement identity differs')
    on = [member['epoch_values_at_proxy_carrier'][e] for e in active]
    off_by_h = {}
    for h in HYPOTHESES:
        block = measurement['off'][h]
        if block['complete'] is not True or block['defined'] is not True:
            raise ValueError('Complete defined OFF evidence required')
        rows = block['epochs']
        if [r['epoch'] for r in rows] != active:
            raise ValueError('OFF epoch inventory differs')
        centers = []
        for e, r in zip(active, rows):
            if (r['available'] is not True or r['complete'] is not True
                or r['profile_id'] != f'{t}:{q}:{w}:{e}:{h}'
                or finite(r['on_center']) != member['epoch_values_at_proxy_carrier'][e]):
                raise ValueError('OFF measurement binding differs')
            centers.append(finite(r['off_center']))
        off_by_h[h] = centers
    off_max = [max(0.0, *(off_by_h[h][i] for h in HYPOTHESES))
               for i in range(len(active))]
    excess = [finite(a-b) for a, b in zip(on, off_max)]
    return dict(active_epochs=list(active), on_centers=on, off_centers=off_by_h,
                off_penalty=off_max, epoch_excess=excess,
                second_epoch_on=second_largest(on),
                second_epoch_excess=second_largest(excess))


def raw_profile_audit(member, profiles, feature):
    """Independent extraction from original ON vectors and OFF interpolation.

    The order statistic is independently evaluated by maximum pair minima;
    this path does not call member_features or second_largest.
    """
    active, t, q, w = identity(member)
    ons, excesses, off_by_h = [], [], {h: [] for h in HYPOTHESES}
    profile_count = 0
    for e in active:
        same_on, off_values = None, []
        for h in HYPOTHESES:
            pid = f'{t}:{q}:{w}:{e}:{h}'
            p = profiles.get(pid)
            if p is None or p['complete'] is not True:
                raise ValueError('Missing complete original profile')
            if any(p[k] != v for k, v in dict(template=t, score_index=q,
                   width=w, epoch=e, hypothesis=h).items()):
                raise ValueError('Original profile identity differs')
            names = ('on_values', 'aligned_off_values', 'off_left_values',
                     'off_right_values', 'interpolation_weights')
            if any(len(p[k]) != 2*w+1 for k in names):
                raise ValueError('Original profile span is incomplete')
            on = finite(p['on_values'][w])
            if on != member['epoch_values_at_proxy_carrier'][e]:
                raise ValueError('Original ON center differs')
            if same_on is not None and p['on_values'] != same_on:
                raise ValueError('ON copies disagree between mappings')
            same_on = p['on_values']
            weight = finite(p['interpolation_weights'][w])
            if not 0 <= weight <= 1:
                raise ValueError('Invalid OFF interpolation weight')
            off = ((1-weight)*finite(p['off_left_values'][w])
                   + weight*finite(p['off_right_values'][w]))
            if not close(off, p['aligned_off_values'][w]):
                raise ValueError('Original OFF interpolation differs')
            off_values.append(off)
            off_by_h[h].append(off)
            profile_count += 1
        ons.append(on)
        excesses.append(on-max([0.0]+off_values))
    if feature['active_epochs'] != active or feature['on_centers'] != ons:
        raise ValueError('Feature epoch/ON evidence differs')
    for h in HYPOTHESES:
        if len(feature['off_centers'][h]) != len(active) or any(
                not close(a, b) for a, b in zip(feature['off_centers'][h], off_by_h[h])):
            raise ValueError('Feature OFF evidence differs')
    expected_penalty = [max(0.0, *(off_by_h[h][i] for h in HYPOTHESES))
                        for i in range(len(active))]
    for key, expected in (('off_penalty', expected_penalty), ('epoch_excess', excesses)):
        if len(feature[key]) != len(expected) or any(
                not close(a, b) for a, b in zip(feature[key], expected)):
            raise ValueError('Feature epoch arithmetic differs')
    for name, values in zip(METHODS, (ons, excesses)):
        oracle = max(min(a, b) for a, b in itertools.combinations(values, 2))
        if not close(feature[name], oracle):
            raise ValueError('Independent second-epoch feature differs')
    return profile_count


def check_record(record, item, decision):
    summary = record['summary']
    if (record['result_sha256'] != item['record_sha256']
        or record['phase'] != item['phase']
        or record['freeze_commit'] != decision['freeze_commit']
        or record['config_sha256'] != decision['config_sha256']
        or summary['name'] != item['name'] or summary['panel'] != item['phase']
        or record['native_payload_identity'] != item['native_payload_identity']):
        raise ValueError('Sealed input provenance differs')
    if item['phase'] not in ('training', 'baseline', 'null_training'):
        raise ValueError('Only closed training inputs allowed')


def derive_cases(root):
    source = root/'results_m43af_response'
    decision = ag.sealed_read(source/'model_decision.json')
    if (decision['result_sha256'] != ag.DECISION_SEAL or decision['feasible']
        or decision['native_validation_opened']):
        raise ValueError('Expected immutable failed M43AF training decision')
    cases, ledger, inputs = [], [], []
    phases, profile_checks, count = collections.Counter(), 0, 0
    for item in decision['inventory']:
        path = (root/item['file']).resolve()
        if not path.is_relative_to((source/'records').resolve()):
            raise ValueError('Input outside closed records')
        if ag.sha(path.read_bytes()) != item['file_sha256']:
            raise ValueError('Input file bytes changed')
        record = ag.sealed_read(path)
        check_record(record, item, decision)
        case = record['summary']
        if case['complete'] is not True:
            raise ValueError('Incomplete source summary')
        geometry_rows = record['geometry_member_audit']['members']
        geometry = {m['record_id']: m for m in geometry_rows}
        measured_rows = record['acquisition']['measurements']
        measured = {m['record_id']: m for m in measured_rows}
        if len(geometry) != len(geometry_rows) or len(measured) != len(measured_rows):
            raise ValueError('Duplicate geometry/measurement identity')
        eligible = {m['record_id'] for m in geometry_rows
                    if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
        if eligible != {m['record_id'] for m in case['members']} or eligible != set(measured):
            raise ValueError('Eligible member inventory changed')
        features = []
        for original in case['members']:
            rid = original['record_id']
            feature = member_features(geometry[rid], measured[rid])
            profile_checks += raw_profile_audit(geometry[rid], record['acquisition']['profiles'], feature)
            features.append(dict(record_id=rid, original_m43af_coordinate=original['coordinate'], **feature))
            count += 1
        cases.append(case)
        ledger.append(dict(name=case['name'], panel=case['panel'], members=features))
        inputs.append(dict(path=item['file'], sha256=item['file_sha256'],
                           record_sha256=item['record_sha256'],
                           native_payload_identity=item['native_payload_identity']))
        phases[item['phase']] += 1
    if dict(phases) != {'baseline': 1, 'training': 112, 'null_training': 128} or len(cases) != 241:
        raise ValueError('Unexpected source inventory')
    required = sorted(c['name'] for c in cases if c['signal_present']
                      and any(c['reference_recovered'][p] for p in ag.REFERENCES))
    if len(required) != 57:
        raise ValueError('Required recovery denominator changed')
    ag.validate_cases(cases, required)
    return cases, ledger, inputs, required, dict(passed=True, audited_members=count,
        original_profile_center_checks=profile_checks,
        scalar_absolute_and_relative_tolerance=TOLERANCE,
        feature_selection_uses_truth=False)


def transformed_cases(cases, ledger, method):
    if method not in METHODS:
        raise ValueError('Unfrozen feature method')
    output = copy.deepcopy(cases)
    by_case = {row['name']: row for row in ledger}
    if set(by_case) != {c['name'] for c in cases} or len(by_case) != len(ledger):
        raise ValueError('Feature case inventory differs')
    for case in output:
        features = {m['record_id']: m for m in by_case[case['name']]['members']}
        if len(features) != len(by_case[case['name']]['members']) or set(features) != {
                m['record_id'] for m in case['members']}:
            raise ValueError('Feature member inventory differs')
        for member in case['members']:
            feature = features[member['record_id']]
            if feature['original_m43af_coordinate'] != member['coordinate']:
                raise ValueError('Old coordinate binding changed')
            member['coordinate'] = dict(on=finite(feature[method]), off=member['coordinate']['off'])
    return output


def recovery_accounting(cases, result):
    signals = {c['name'] for c in cases if c['signal_present']}
    refs = {p: {c['name'] for c in cases if c['signal_present'] and c['reference_recovered'][p]}
            for p in ag.REFERENCES}
    rows = []
    for index in result['control_free_optimal_state_indices']:
        state = result['sweep'][index]
        recovered, leaked = set(), set()
        for case in cases:
            accepted = {m['record_id'] for m in case['members']
                if state['lower_kind'] == 'finite' and m['coordinate']['on'] >= state['on_lower']
                and (state['control_free_off_upper'] is None
                     or m['coordinate']['off'] < state['control_free_off_upper'])}
            if case['signal_present'] and accepted.intersection(case['associated_record_ids']):
                recovered.add(case['name'])
            if not case['signal_present'] and accepted:
                leaked.add(case['name'])
        if leaked or sorted(set(result['required_signal_cases'])-recovered) != state['control_free_required_losses']:
            raise ValueError('Independent case reduction differs at zero-leak optimum')
        rows.append(dict(state_index=index, recovered_signal_cases=sorted(recovered),
            lost_signal_cases=sorted(signals-recovered),
            reference_signal_losses={p: sorted(names-recovered) for p, names in refs.items()},
            reference_signal_gains={p: sorted(recovered-names) for p, names in refs.items()}))
    counts = [len(r['recovered_signal_cases']) for r in rows]
    return dict(total_signal_cases=len(signals),
        reference_recovered_counts={p: len(v) for p, v in refs.items()},
        all_signal_recovery_range=[min(counts), max(counts)],
        zero_leak_optimal_states=rows)


def run(root, output):
    if ag.sha(Path(ag.__file__).read_bytes()) != AG_CODE_SHA256:
        raise ValueError('Frozen M43AG exact sweep/auditor dependency changed')
    reference_data = (ROOT/'results_m43ag_obstruction/summary.json').read_bytes()
    if ag.sha(reference_data) != AG_SUMMARY_SHA256:
        raise ValueError('Published M43AG reference changed')
    reference = json.loads(reference_data)
    cases, features, inputs, required, feature_audit = derive_cases(root)
    payloads = {'features.json': features, 'input_manifest.json': inputs,
                'feature_audit.json': feature_audit}
    methods = {}
    for method in METHODS:
        derived = transformed_cases(cases, features, method)
        result = ag.exact_sweep(derived, required)
        certificates = ag.dominance_certificates(derived, required)
        audit = ag.direct_audit(derived, result, certificates, required)
        accounting = recovery_accounting(derived, result)
        payloads[method+'.json'] = dict(result=result, certificates=certificates,
                                        independent_audit=audit, recovery_accounting=accounting)
        methods[method] = dict(
            minimum_required_losses_with_zero_leaks=result['minimum_required_losses_with_zero_leaks'],
            minimum_leaking_cases_with_all_required=result['minimum_leaking_cases_with_all_required'],
            joint_training_feasible=result['minimum_required_losses_with_zero_leaks'] == 0,
            on_cut_equivalence_classes=result['on_cut_equivalence_classes'],
            individually_impossible_cases=[c['case'] for c in certificates if c['individually_impossible_without_leaks']],
            all_signal_recovery_range=accounting['all_signal_recovery_range'],
            independent_audit=audit)
    summary = dict(milestone='M43AH', scope='retrospective_closed_training_epoch_support_development',
        source_publication=ag.SOURCE_COMMIT, model_decision_sha256=ag.DECISION_SEAL,
        source_records=len(cases), eligible_members=feature_audit['audited_members'],
        required_signal_cases=required, total_signal_cases=sum(c['signal_present'] for c in cases),
        training_control_cases=sum(not c['signal_present'] and c['panel']=='training' for c in cases),
        baseline_eligible_members=sum(len(c['members']) for c in cases if c['panel']=='baseline'),
        native_null_eligible_members=sum(len(c['members']) for c in cases if c['panel']=='null_training'),
        source_m43ag_summary_sha256=AG_SUMMARY_SHA256,
        old_m43ag_costs={k: reference[k] for k in
            ('minimum_required_losses_with_zero_leaks', 'minimum_leaking_cases_with_all_required')},
        methods=methods, feature_audit=feature_audit,
        method_selected=None, boundary_selected=None, detector_adopted=False,
        development_qualification_claimed=False, validation_opened=False,
        new_native_acquisitions=0, new_detector_executions=0,
        detector_execution_count_scope='full_upstream_native_pipeline_only',
        new_member_feature_evaluations=feature_audit['audited_members'],
        new_downstream_rule_family_evaluations=len(METHODS), new_observing_sequences=0,
        physical_false_alarm_probability_measured=False, astronomical_candidate_claimed=False)
    payloads['summary.json'] = summary
    encoded = {name: ag.canonical(value) for name, value in payloads.items()}
    manifest = ag.canonical(dict(format='m43ah-derived-development-v1',
        files=[dict(path=name, bytes=len(data), sha256=ag.sha(data)) for name, data in encoded.items()]))
    encoded['manifest.json'] = manifest
    # Check every destination before any output writes, preserving completed evidence.
    for name, data in encoded.items():
        path = output/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Preserve differing completed M43AH evidence: '+name)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in encoded.items():
        (output/name).write_bytes(data)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    run(args.root.resolve(), args.output or args.root/'results_m43ah_epoch_support')
