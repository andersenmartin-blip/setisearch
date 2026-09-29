"""Fresh Gaussian/native engineering plans; never a scientific draw-plan lease.

Only two fixed, separately named engineering cases are supported. A durable
engineering start artifact precedes every PRNG constructor. The original
whole_cadence_render_radio.render_gaussian gate remains unchanged.
"""
from dataclasses import asdict
import hashlib
import json
import numpy as np

from . import receiver_bank_radio as received
from . import receiver_development_radio as inject
from . import transfer_m43g as native
from . import whole_cadence_journal_radio as journal
from .empty_null_radio import canonical
from .pipeline_receiver_radio import Context, NativeRun
from .whole_cadence_reference_radio import digest, reduce_native_run
from .whole_cadence_archive_radio import npz_bytes

NAMESPACE = 'radio-gaussian-native-engineering-20260929a'
LAW = {'schema': 'radio-engineering-gaussian-law-v1', 'namespace': NAMESPACE,
       'generator': 'numpy.Generator(PCG64(SeedSequence([case_seed,scan_index])))',
       'row_call': [100.0, 1.0, 65536], 'scans': 6, 'rows_per_scan': 16,
       'cast_before_injection': '<f4', 'injection_accumulator': '<f8',
       'raw_storage': '<f4', 'scientific_reference': False,
       'independence_established_by_seed_labels': False}
LAW_SHA = digest(LAW)
SPECS = (
    {'name': 'gaussian-null-calibration-window', 'role': 'calibration',
     'kind': 'noise_null', 'rate_label_hz_s': 0, 'injection_width_channels': 0,
     'total_digital_power': 0.0, 'on_epochs': [], 'off_epochs': []},
    {'name': 'gaussian-on-w129-validation-window', 'role': 'validation',
     'kind': 'on_signal', 'rate_label_hz_s': -2, 'injection_width_channels': 129,
     'total_digital_power': 500.0, 'on_epochs': [0, 1, 2], 'off_epochs': []},
)
ARTIFACTS = ['rng_start.json', 'sources.json', 'scores.json', 'scores.npz',
             'maximum.json', 'renderer.json', 'compact_audit.json']


def make_plan(context, ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < len(SPECS):
        raise ValueError('Bounded engineering case ordinal required')
    if not isinstance(context, Context):
        raise ValueError('Actual metadata receiver context required')
    context.validate()
    spec = SPECS[ordinal]
    if context.native_window['role'] != spec['role']:
        raise ValueError('Engineering context/window role differs')
    name = NAMESPACE + '/' + spec['name']
    seed = int.from_bytes(hashlib.sha256((name + '/seed-v1').encode()).digest()[:8], 'big')
    case = {'namespace': NAMESPACE, 'ordinal': ordinal, 'spec': spec,
            'context_sha256': context.identity,
            'source_contract_sha256': hashlib.sha256(context.factor_contract.source_contract_bytes).hexdigest(),
            'receiver_bank_sha256': context.factor_contract.factors.identity,
            'noise_law_sha256': LAW_SHA, 'seed': seed,
            'scientific_allocation_charged': False}
    case['identity'] = digest(case)
    plan = {'schema': 'radio-gaussian-native-engineering-plan-v1', 'case': case,
            'law': LAW, 'window': context.native_window,
            'grid': {'center_mhz': context.grid.center_mhz,
                     'channel_width_hz': context.geometry.channel_width_hz,
                     'score_bins': context.grid.score_bin_count,
                     'support_bins': context.grid.support_bin_count},
            'streams': [{'scan_index': i, 'scan': s['label'], 'entropy': [seed, i],
                         'normal_calls': 16, 'arguments': [100.0, 1.0, 65536]}
                        for i, s in enumerate(context.scans)]}
    plan['plan_sha256'] = digest(plan)
    return json.loads(canonical(plan))


def binding(plan):
    c = plan['case']
    return {'case_identity': c['identity'], 'plan_sha256': plan['plan_sha256'],
            'context_sha256': c['context_sha256'],
            'source_contract_sha256': c['source_contract_sha256'],
            'noise_law_sha256': c['noise_law_sha256'], 'role': 'engineering'}


def validate_plan(context, plan, forbidden_cases):
    # Reconstruct all fields from fixed metadata rules, not a self-rehashed plan.
    expected = make_plan(context, plan['case']['ordinal'])
    if plan != expected:
        raise ValueError('Exact engineering plan/context/schedule differs')
    identities = {c['identity'] for c in forbidden_cases}
    seeds = {c['seed'] for c in forbidden_cases}
    if plan['case']['identity'] in identities or plan['case']['seed'] in seeds:
        raise ValueError('Reserved scientific identity or seed collision')
    return plan


def begin(context, plan, lease, forbidden_cases, verify_freeze):
    validate_plan(context, plan, forbidden_cases)
    if type(lease) is not journal.Lease:
        raise ValueError('Fresh engineering journal lease required')
    if (lease.manifest['mode'] != 'engineering' or
            lease.manifest['namespace'] != NAMESPACE or
            lease.case['binding'] != binding(plan) or
            lease.manifest['required_artifacts'] != ARTIFACTS):
        raise ValueError('Engineering lease domain/binding differs')
    lease.budget()
    verify_freeze(lease.manifest)
    marker = {'schema': 'radio-engineering-gaussian-start-v1',
              'plan_sha256': plan['plan_sha256'], 'case_identity': plan['case']['identity'],
              'manifest_sha256': lease.manifest_sha, 'nonce': lease.case['nonce'],
              'consumption_event_sha256': lease.case['consumption_event_sha256'],
              'scientific_allocation_charged': False, 'restart_authorized': False}
    # Duplicate, uncertain, partial or cross-process attempts are refused by the
    # durable artifact journal before the first PRNG constructor is reached.
    lease.write_artifact('rng_start.json', canonical(marker))
    return marker


def render(context, plan, *, lease, forbidden_cases, verify_freeze):
    marker = begin(context, plan, lease, forbidden_cases, verify_freeze)
    def factory(entropy):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
    return _rows(context, plan, factory, lease.budget, marker)


def _rows(context, plan, factory, budget, marker):
    """Shared arithmetic exercised with a deterministic provider in unit tests."""
    spec = plan['case']['spec']; sources = {}; receipts = []; max_error = 0.0
    q = context.grid.center_mhz * 1e6
    center = json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock = received.clock(json.loads(context.factor_contract.source_contract_bytes))
    for i, scan in enumerate(context.scans):
        budget(); rng = factory(plan['streams'][i]['entropy']); rows = []
        def read_row(row):
            nonlocal max_error
            if row != len(rows):
                raise ValueError('Engineering row ordering changed')
            budget(); sample = np.asarray(rng.normal(100.0, 1.0, 65536))
            if sample.dtype != np.dtype('<f8') or sample.shape != (65536,) or not np.isfinite(sample).all():
                raise ValueError('Complete finite float64 Gaussian/provider row required')
            background = sample.astype('<f4'); value = background.astype('<f8')
            active = scan['epoch'] - 1 in spec[scan['kind'] + '_epochs']
            receipt = {'row': row, 'generator_call_arguments': [100.0, 1.0, 65536],
                       'background_sha256': native.array_hash(background), 'injected': active,
                       'added_total_power_before_float32': 0.0}
            if active:
                times = clock[i * 16 + row]; mid = float(times[1]); dt = float(times[2] - times[0])
                rate = spec['rate_label_hz_s']
                pos = (q * (1 + rate * mid / center) - context.geometry.raw_zero_hz) / context.geometry.channel_width_hz
                sweep = q * rate / center * dt / context.geometry.channel_width_hz
                indices, mass = inject.pixel_masses(pos, sweep, spec['injection_width_channels'], 65536)
                max_error = max(max_error, abs(float(mass.sum()) - 1.0))
                value[indices] += spec['total_digital_power'] * mass
                receipt.update(center_channel=pos, sweep_channels=sweep,
                               support_channel_interval=[int(indices[0]), int(indices[-1]) + 1],
                               added_total_power_before_float32=float(spec['total_digital_power'] * mass.sum()))
            value = value.astype('<f4'); receipt['raw_sha256'] = native.array_hash(value)
            rows.append(receipt)
            return value
        scope = {'kind': 'synthetic', 'input_domain': 'engineering-gaussian-native',
                 'case_identity': plan['case']['identity'], 'context_sha256': context.identity,
                 'scan': scan['label'], 'receiver_factor_bank_sha256': context.factor_contract.factors.identity,
                 'noise_law': LAW, 'noise_law_sha256': LAW_SHA,
                 'draw_plan_sha256': plan['plan_sha256'], 'engineering_start': marker,
                 'scientific_allocation_charged': False, 'telescope_provenance': False}
        source = native.normalize_synthetic_rows(read_row, context.geometry, 16,
                                                 input_orientation='ascending', scope=scope)
        for row, value in zip(rows, source.values, strict=True):
            row['normalized_sha256'] = native.array_hash(value)
        sources[scan['label']] = source
        receipts.append({'scan': scan['label'], 'source_identity': source.identity, 'rows': rows})
        budget()
    run = NativeRun(context, sources); budget(run.modelled_bytes)
    receipt = {'schema': 'radio-engineering-gaussian-native-receipt-v1',
               'case_identity': plan['case']['identity'], 'draw_plan_sha256': plan['plan_sha256'],
               'noise_law': LAW, 'noise_law_sha256': LAW_SHA,
               'source_ids': run.source_ids, 'row_receipts': receipts,
               'normal_calls': 96, 'maximum_mass_error': max_error,
               'scientific_allocation_charged': False, 'telescope_values_opened': False,
               'engineering_start': marker}
    receipt['receipt_sha256'] = digest(receipt)
    return run, receipt


def compact_parts(run, store, plan, receipt):
    unit = reduce_native_run(run, store, case_identity=plan['case']['identity'], noise_law_sha256=LAW_SHA)
    sources = {'schema': 'radio-whole-cadence-native-source-archive-v1',
               'context_sha256': run.context.identity, 'case_identity': plan['case']['identity'],
               'noise_law_sha256': LAW_SHA, 'sources': {}}
    for name, s in run.sources.items():
        sources['sources'][name] = {'geometry': asdict(s.geometry), 'integration_count': s.integration_count,
                                   'scope': json.loads(s.scope_json), 'raw_sha256': s.raw_sha256,
                                   'normalized_sha256': s.normalized_sha256, 'identity': s.identity}
    scores = {'schema': 'radio-whole-cadence-score-archive-v1', 'provenance': store.provenance,
              'vectors': [{'key': list(k), 'npz_key': f'{k[0]}_{k[1]:03d}_{k[2]:03d}',
                           'identity': store.expected_ids[k]} for k in sorted(store.arrays)]}
    return {'sources.json': canonical(sources), 'scores.json': canonical(scores),
            'scores.npz': npz_bytes({v['npz_key']: store.arrays[tuple(v['key'])] for v in scores['vectors']}),
            'maximum.json': unit.payload, 'renderer.json': canonical(receipt)}
