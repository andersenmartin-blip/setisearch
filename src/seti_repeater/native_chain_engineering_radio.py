"""Eight fresh engineering cases and an explicitly uncalibrated four-unit seam.

The 127-unit public entry points reject this threshold. Engineering gates count
physical survivors, never the production-shaped 1/100 diagnostic final flag.
No restored archive or threshold can construct a random lease.
"""
from dataclasses import dataclass
import hashlib
import json
import numpy as np

from . import gaussian_engineering_radio as gaussian
from . import whole_cadence_journal_radio as journal
from . import whole_cadence_physical_radio as physical
from . import receiver_bank_radio as received
from .empty_null_radio import canonical, Maximum, maximum
from .whole_cadence_reference_radio import Family, CadenceMaximum, digest, reduce_native_run
from .whole_cadence_downstream_radio import _execute_core

NAMESPACE = 'radio-native-chain-engineering-20260929b'
LAW = {**gaussian.LAW, 'namespace': NAMESPACE,
       'purpose': 'four-reference-uncalibrated-physical-engineering',
       'same_window_only': True}
LAW_SHA = digest(LAW)
SPECS = tuple(
    {'name': f'noise-reference-{i}', 'kind': 'noise_null', 'reference': True,
     'rate_label_hz_s': 0, 'injection_width_channels': 0,
     'total_digital_power': 0., 'on_epochs': [], 'off_epochs': []}
    for i in range(4)) + (
    {'name': 'on-width129', 'kind': 'on_signal', 'reference': False,
     'rate_label_hz_s': -2, 'injection_width_channels': 129,
     'total_digital_power': 500., 'on_epochs': [0, 1, 2], 'off_epochs': []},
    {'name': 'on-width1', 'kind': 'on_signal', 'reference': False,
     'rate_label_hz_s': -2, 'injection_width_channels': 1,
     'total_digital_power': 500., 'on_epochs': [0, 1, 2], 'off_epochs': []},
    {'name': 'matched-on-off-width129', 'kind': 'matched_on_off', 'reference': False,
     'rate_label_hz_s': -2, 'injection_width_channels': 129,
     'total_digital_power': 500., 'on_epochs': [0, 1, 2], 'off_epochs': [0, 1, 2]},
    {'name': 'fresh-null', 'kind': 'noise_null', 'reference': False,
     'rate_label_hz_s': 0, 'injection_width_channels': 0,
     'total_digital_power': 0., 'on_epochs': [], 'off_epochs': []},
)
ARTIFACTS = [*gaussian.ARTIFACTS, 'physical.json', 'engineering_gate.json']


def family(context):
    return Family(context.identity, context.factor_contract.factors.identity,
                  len(context.bank), context.grid)


def make_plan(context, ordinal):
    context.validate()
    if context.native_window['role'] != 'validation':
        raise ValueError('Same validation window required for every engineering case')
    if type(ordinal) is not int or not 0 <= ordinal < 8:
        raise ValueError('Eight fixed engineering cases only')
    name = NAMESPACE + '/' + SPECS[ordinal]['name']
    seed = int.from_bytes(hashlib.sha256((name + '/seed-v1').encode()).digest()[:8], 'big')
    c = {'namespace': NAMESPACE, 'ordinal': ordinal, 'spec': SPECS[ordinal],
         'context_sha256': context.identity, 'seed': seed,
         'source_contract_sha256': hashlib.sha256(context.factor_contract.source_contract_bytes).hexdigest(),
         'receiver_bank_sha256': context.factor_contract.factors.identity,
         'noise_law_sha256': LAW_SHA, 'scientific_allocation_charged': False}
    c['identity'] = digest(c)
    p = {'schema': 'radio-native-chain-engineering-plan-v1', 'case': c, 'law': LAW,
         'window': context.native_window,
         'streams': [{'scan_index': i, 'scan': s['label'], 'entropy': [seed, i],
                      'normal_calls': 16, 'arguments': [100., 1., 65536]}
                     for i, s in enumerate(context.scans)]}
    p['plan_sha256'] = digest(p)
    return json.loads(canonical(p))


binding = gaussian.binding


def validate_plan(context, plan, forbidden):
    if plan != make_plan(context, plan['case']['ordinal']):
        raise ValueError('Exact fresh engineering plan required')
    if any(plan['case']['identity'] == c['identity'] or plan['case']['seed'] == c['seed'] for c in forbidden):
        raise ValueError('Historical/reserved identity or seed collision')


def render(context, plan, *, lease, forbidden_cases, verify_freeze):
    validate_plan(context, plan, forbidden_cases)
    if type(lease) is not journal.Lease:
        raise ValueError('Fresh engineering journal lease required')
    if (lease.manifest['mode'] != 'engineering' or lease.manifest['namespace'] != NAMESPACE
            or lease.case['binding'] != binding(plan) or lease.manifest['required_artifacts'] != ARTIFACTS):
        raise ValueError('Engineering lease domain or binding differs')
    lease.budget(); verify_freeze(lease.manifest)
    marker = {'schema': 'radio-native-chain-engineering-start-v1',
              'case_identity': plan['case']['identity'], 'plan_sha256': plan['plan_sha256'],
              'manifest_sha256': lease.manifest_sha, 'nonce': lease.case['nonce'],
              'consumption_event_sha256': lease.case['consumption_event_sha256'],
              'scientific_allocation_charged': False, 'restart_authorized': False}
    lease.write_artifact('rng_start.json', canonical(marker))
    def factory(entropy):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
    return gaussian._rows(context, plan, factory, lease.budget, marker,
                          receipt_schema='radio-native-chain-gaussian-receipt-v1')


def _threshold_record(context, records):
    f = family(context); expected = [make_plan(context, i)['case']['identity'] for i in range(4)]
    if len(records) != 4: raise ValueError('Exactly four genuine engineering receipts required')
    checked = []
    for raw, identity in zip(records, expected, strict=True):
        r = CadenceMaximum(canonical(raw)).record()
        n = len(context.bank)*len(f.record()['widths'])*len(f.record()['activity_subsets'])
        if (r['case_identity'] != identity or r['family'] != f.record()
                or r['family_sha256'] != digest(f.record()) or r['noise_law_sha256'] != LAW_SHA
                or r['domain'] != 'synthetic-native' or r['all_hypotheses_evaluated'] is not True
                or r['score_shift_resampling'] is not False or r['visited_hypotheses'] != n
                or r['scored_cells'] != n*context.grid.score_bin_count
                or not 0 <= r['eligible_cells'] <= r['scored_cells']
                or (r['maximum']['kind'] == 'empty') != (r['eligible_cells'] == 0)):
            raise ValueError('Four-reference source/order/law/completeness differs')
        checked.append(r)
    maxima = [Maximum.from_record(r['maximum']) for r in checked]
    t = {'schema': 'radio-four-reference-engineering-threshold-v1',
         'status': 'UNCALIBRATED_ENGINEERING_ONLY', 'reference_records': checked,
         'reference_bundle': {'ordered_maxima': [m.record() for m in maxima],
                              'ordered_case_identities': expected, 'reference_count': 4},
         'destination_family': f.record(), 'noise_law_sha256': LAW_SHA,
         'operational_threshold': maximum((Maximum('finite', 10.), *maxima)).value,
         'reference_denominator': 5, 'minimum_possible_rank_p': 0.2,
         'rank_ceiling': [1, 100], 'calibrated_1_percent_test': False,
         'production_threshold': False, 'scientific_candidate_selection_authorized': False,
         'telescope_admission_authorized': False}
    t['threshold_receipt_sha256'] = digest(t)
    return t


@dataclass(frozen=True)
class EngineeringThreshold:
    payload: bytes
    context: object

    def record(self):
        r = json.loads(self.payload)
        if canonical(r) != self.payload or r != _threshold_record(self.context, r['reference_records']):
            raise ValueError('Engineering threshold semantics changed')
        return r

    def validate(self, candidate_family, *, case_identity, noise_law_sha256, domain):
        r = self.record()
        expected = {make_plan(self.context, i)['case']['identity'] for i in range(4, 8)}
        if (candidate_family.record() != r['destination_family'] or case_identity not in expected
                or noise_law_sha256 != LAW_SHA or domain != 'synthetic-native'):
            raise ValueError('Engineering observation family/law/domain/case differs')
        return r


def bind_threshold(context, units):
    return EngineeringThreshold(canonical(_threshold_record(context, [u.record() for u in units])), context)


def run_physical(run, store, threshold, plan):
    validate_plan(run.context, plan, [])
    if type(threshold) is not EngineeringThreshold or plan['case']['spec']['reference']:
        raise ValueError('Distinct engineering evaluation threshold required')
    c = run.context; f = family(c); factors = c.factor_contract
    unit = reduce_native_run(run, store, case_identity=plan['case']['identity'], noise_law_sha256=LAW_SHA)
    retention = _execute_core(f, store, threshold, unit)
    def receiver(records):
        signatures, receipt = run.receiver(records, c.bank)
        return signatures, physical.native_receiver_receipt(signatures, receipt, c, run.source_ids)
    return physical._execute(f, store, retention, factors.matrix_for_kind('on'),
        factors.matrix_for_kind('off'), receiver,
        {'domain': 'uncalibrated-four-reference-native-engineering',
         'context_sha256': c.identity, 'factor_contract_sha256': factors.identity,
         'source_ids': run.source_ids, 'native_receiver_measured': True,
         'production_recovery_rfi_null_qualification': False})


def evaluate(report, context, plan):
    """Truth association only after immutable physical decisions; no 1% gate."""
    validate_plan(context, plan, [])
    if (plan['case']['spec']['reference'] or report.get('complete') is not True
            or report['result_sha256'] != digest({k:v for k,v in report.items() if k!='result_sha256'})
            or report['retention']['case_identity'] != plan['case']['identity']
            or report['family_sha256'] != digest(family(context).record())
            or report['factor_provider_receipt']['domain'] != 'uncalibrated-four-reference-native-engineering'):
        raise ValueError('Complete matching engineering physical report required')
    rows = report['retention']['retained']['on']; decisions = report['decisions']
    by_id = {d['record_id']: d for d in decisions}
    if len(by_id) != len(decisions) or set(by_id) != {r['record_id'] for r in rows}:
        raise ValueError('Complete unique decision inventory required')
    spec = plan['case']['spec']; q = context.grid.center_mhz*1e6
    center = json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock = received.clock(json.loads(context.factor_contract.source_contract_bytes))
    truth = np.array([q*(1+spec['rate_label_hz_s']*float(t[1])/center)
                      for si in (0, 2, 4) for t in clock[si*16:(si+1)*16]])
    factors = context.factor_contract.matrix_for_kind('on'); association = []
    for r in rows:
        if digest({k:v for k,v in r.items() if k!='record_id'}) != r['record_id']:
            raise ValueError('Retained member changed')
        d = by_id[r['record_id']]
        if d['diagnostic_final'] or d['meets_diagnostic_rank_cut'] or d['scientific_candidate']:
            raise ValueError('Four references cannot pass the unchanged 1/100 rank cut')
        idx = [e*16+i for e in r['active_epochs_zero_based'] for i in range(16)]
        error = abs(r['carrier_hz']*factors[r['template_index'], idx]-truth[idx])
        associated = bool(spec['on_epochs'] and set(r['active_epochs_zero_based']).issubset(spec['on_epochs'])
                          and np.all(error <= 2*context.geometry.channel_width_hz))
        association.append({'record_id': r['record_id'], 'engineering_survivor': d['passes_evaluated_physical_vetoes'],
                            'associated': associated, 'maximum_truth_track_error_hz': float(error.max()),
                            'width': r['spectral_width_channels']})
    survivors = {a['record_id'] for a in association if a['engineering_survivor']}
    associated = {a['record_id'] for a in association if a['engineering_survivor'] and a['associated']}
    members = [rid for c in report['clusters'] for rid in c['member_ids']]
    if len(members) != len(set(members)) or set(members) != set(by_id):
        raise ValueError('Complete physical cluster partition required')
    counts = {'physical_survivors': len(survivors), 'associated_physical_survivors': len(associated),
              'unassociated_physical_survivors': len(survivors-associated),
              'physical_survivor_clusters': sum(bool(survivors.intersection(c['member_ids'])) for c in report['clusters'])}
    gate = bool(associated) if spec['kind']=='on_signal' else not survivors
    result = {'schema': 'radio-native-chain-engineering-gate-v1', 'case_identity': plan['case']['identity'],
              'physical_report_sha256': report['result_sha256'], 'kind': spec['kind'],
              'counts': counts, 'association': association, 'engineering_gate_pass': gate,
              'broad_unassociated_survivors': {str(w): sum(a['engineering_survivor'] and not a['associated'] and a['width']==w for a in association) for w in (65,129)},
              'truth_used_only_after_decisions': True, 'calibrated_rank_gate_pass': False,
              'production_recovery_rfi_null_qualification': False, 'scientific_candidate': False}
    result['result_sha256'] = digest(result)
    return result
