"""Distinct empty-aware threshold, exhaustive retention and rank receipts.

Engineering-only. No legacy ThresholdCertificate, scramble declaration,
physical-veto certificate, scientific candidate or acquisition authority.
"""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json

import numpy as np

from . import search_v0p6 as core
from .detector_m43u import checked_vectors
from .empty_null_radio import EMPTY, Maximum, canonical, higher_quantile, inclusive_rank, maximum
from .mask_m43u import build_mask
from .whole_cadence_reference_radio import (
    Family, _sha, digest, reduce_fixture, reduce_native_run, reference_bundle,
)

MAP_PROOF_SHA256 = '9001e54ca2014e2de801837042995164fb725efe6ce4da65d85d90479f83c18d'


def _sealed(value, key):
    value = dict(value); value[key] = digest(value)
    return canonical(value)


def _unseal(payload, key, schema):
    value = json.loads(payload)
    if canonical(value) != payload or value.get('schema') != schema:
        raise ValueError('Noncanonical or wrong receipt schema')
    checksum = value.pop(key)
    if checksum != digest(value): raise ValueError('Receipt changed')
    value[key] = checksum
    return value


def operator_binding(source_family, destination_family, proof_bytes=None, translation_contexts=None):
    """Consume the retained metadata proof; do not rerun its numerical study."""
    source = source_family.record(); destination = destination_family.record()
    if source == destination:
        if proof_bytes is not None or translation_contexts is not None:
            raise ValueError('Same family needs no translation proof')
        return {'kind': 'identical-family', 'source_family_sha256': digest(source),
                'destination_family_sha256': digest(destination)}
    if not isinstance(proof_bytes, bytes) or hashlib.sha256(proof_bytes).hexdigest() != MAP_PROOF_SHA256:
        raise ValueError('Exact published score-map proof required')
    from .pipeline_receiver_radio import Context
    if not isinstance(translation_contexts, tuple) or len(translation_contexts) != 2:
        raise ValueError('Both validated receiver contexts required for translation')
    for context, family in zip(translation_contexts, (source_family, destination_family), strict=True):
        if not isinstance(context, Context): raise ValueError('Actual receiver Context required')
        context.validate()
        expected = Family(context.identity, context.factor_contract.factors.identity, len(context.bank), context.grid)
        if family.record() != expected.record(): raise ValueError('Grid/family differs from receiver context')
    proof = json.loads(proof_bytes)
    if (proof.get('score_operator_equivalence_proved') is not True
            or proof.get('status') != 'SCORE_OPERATOR_IDENTICAL_ON_TRANSLATED_ARRAYS'):
        raise ValueError('Score-map equivalence absent')
    tables = []
    for family in (source, destination):
        rows = [x for x in proof['tables'] if x['context_sha256'] == family['context_sha256']
                and x['bank_sha256'] == family['receiver_bank_sha256']]
        if len(rows) != 1: raise ValueError('Family absent from score-map proof')
        row = rows[0]
        if (row['shape'] != [family['template_count'], 96, family['support_carrier_count']]
                or row['widths'] != family['widths'] or family['score_carrier_count'] != 81
                or family['support_carrier_count'] != 99):
            raise ValueError('Score-map family dimensions changed')
        tables.append(row)
    common = lambda r: {k: v for k, v in r.items() if k not in (
        'context_sha256', 'receiver_bank_sha256', 'proxy_grid_sha256')}
    if common(source) != common(destination): raise ValueError('Translated family rules differ')
    for key in ('relative_index_sha256', 'shape', 'widths', 'block_length',
                'native_normalization_origin', 'native_normalization_blocks'):
        if tables[0][key] != tables[1][key]: raise ValueError('Score operator evidence differs')
    return {'kind': 'published-translated-score-operator', 'proof_sha256': MAP_PROOF_SHA256,
        'source_family_sha256': digest(source), 'destination_family_sha256': digest(destination),
        'relative_index_sha256': tables[0]['relative_index_sha256'],
        'noise_distribution_transfer_qualified': False,
        'absolute_frequency_veto_transfer_qualified': False}


@dataclass(frozen=True)
class WholeCadenceThreshold:
    payload: bytes

    def record(self):
        r = _unseal(self.payload, 'threshold_receipt_sha256', 'radio-whole-cadence-threshold-v1')
        b = r['reference_bundle']; checksum = b['bundle_sha256']
        if digest({k: v for k, v in b.items() if k != 'bundle_sha256'}) != checksum:
            raise ValueError('Reference bundle changed')
        refs = tuple(Maximum.from_record(x) for x in b['ordered_maxima'])
        identities = b['ordered_case_identities']
        if (len(refs) != 127 or b['reference_count'] != 127 or len(identities) != 127
                or len(set(identities)) != 127 or len(b['ordered_unit_receipt_sha256s']) != 127):
            raise ValueError('Complete distinct 127-unit reference required')
        for identity in identities + b['ordered_unit_receipt_sha256s']: _sha(identity, 'reference identity')
        if (b['empty_count'] != sum(x.kind == 'empty' for x in refs)
                or b['finite_count'] != sum(x.kind == 'finite' for x in refs)
                or b['higher_quantile'] != higher_quantile(refs).record()
                or b['floor_or_maximum'] != maximum((Maximum('finite', 10.), *refs)).record()
                or r['operational_threshold'] != b['floor_or_maximum']['value']
                or r['floor'] != 10. or r['quantile'] != [1, 1]
                or r['rank_ceiling'] != [1, 100]
                or r['destination_family_sha256'] != digest(r['destination_family'])
                or r['source_family_sha256'] != digest(r['source_family'])
                or b['family_sha256'] != r['source_family_sha256']
                or b['destination_context_sha256'] != r['destination_family']['context_sha256']
                or b['operator_translation_proof_sha256'] != digest(r['operator_binding'])):
            raise ValueError('Threshold/reference semantics changed')
        binding = r['operator_binding']
        if (binding.get('source_family_sha256') != r['source_family_sha256']
                or binding.get('destination_family_sha256') != r['destination_family_sha256']
                or binding.get('kind') not in ('identical-family', 'published-translated-score-operator')
                or (binding['kind'] == 'identical-family' and r['source_family'] != r['destination_family'])
                or b['domain'] not in ('deterministic-score-fixture', 'synthetic-native')):
            raise ValueError('Operator/domain binding changed')
        for key in ('budget_charged', 'detector_certificate_issued', 'telescope_admission_authorized',
                    'joint_exchangeability_proved_by_receipts', 'operator_translation_proof_semantics_verified_here'):
            if b[key] is not False: raise ValueError('Reference bundle has no admission authority')
        for key in ('scientific_candidate_selection_authorized', 'telescope_admission_authorized',
                    'joint_exchangeability_established', 'legacy_certificate_issued'):
            if r[key] is not False: raise ValueError('Engineering threshold has no admission authority')
        return r

    def validate(self, family, *, case_identity, noise_law_sha256, domain):
        r = self.record(); b = r['reference_bundle']
        _sha(case_identity, 'case'); _sha(noise_law_sha256, 'noise law')
        if r['destination_family'] != family.record(): raise ValueError('Destination family differs')
        if case_identity in b['ordered_case_identities']: raise ValueError('Reference/evaluation case overlap')
        if noise_law_sha256 != b['noise_law_sha256']: raise ValueError('Noise law differs')
        if domain != b['domain']: raise ValueError('Reference/observation domain differs')
        return r


def bind_threshold(units, *, source_family, destination_family,
                   expected_case_identities, noise_law_sha256, proof_bytes=None, translation_contexts=None):
    binding = operator_binding(source_family, destination_family, proof_bytes, translation_contexts)
    bundle = reference_bundle(units, expected_case_identities=expected_case_identities,
        expected_family_sha256=digest(source_family.record()), expected_noise_law_sha256=noise_law_sha256,
        destination_context_sha256=destination_family.context_sha256,
        operator_translation_proof_sha256=digest(binding))
    value = {'schema': 'radio-whole-cadence-threshold-v1',
        'status': 'ENGINEERING_ONLY_PHYSICAL_STAGES_NOT_INTEGRATED',
        'source_family': source_family.record(), 'source_family_sha256': digest(source_family.record()),
        'destination_family': destination_family.record(),
        'destination_family_sha256': digest(destination_family.record()),
        'operator_binding': binding, 'reference_bundle': bundle,
        'operational_threshold': bundle['floor_or_maximum']['value'],
        'floor': 10., 'quantile': [1, 1], 'rank_ceiling': [1, 100],
        'reference_unit': 'complete-cadence-maximum-including-EMPTY',
        'legacy_certificate_issued': False, 'joint_exchangeability_established': False,
        'scientific_candidate_selection_authorized': False, 'telescope_admission_authorized': False}
    threshold = WholeCadenceThreshold(_sealed(value, 'threshold_receipt_sha256'))
    threshold.record(); return threshold


class IncompleteRetention(ValueError):
    """Carries all partial triggers and the first capacity-crossing trigger."""
    def __init__(self, reason, evidence):
        super().__init__(reason)
        self.evidence = json.loads(canonical(evidence))


def _execute_core(family, store, threshold, unit, *, maximum_records=10000,
             maximum_evidence_bytes=128_000_000):
    for v, limit in ((maximum_records, 10000), (maximum_evidence_bytes, 128_000_000)):
        if type(v) is not int or not 0 <= v <= limit: raise ValueError('Invalid retention cap')
    u = unit.record()
    t = threshold.validate(family, case_identity=u['case_identity'], noise_law_sha256=u['noise_law_sha256'], domain=u['domain'])
    refs = tuple(Maximum.from_record(x) for x in t['reference_bundle']['ordered_maxima'])
    expected = {(kind, i, width) for kind in ('on', 'off') for i in range(family.template_count)
                for width in core.M37_SPECTRAL_WIDTHS}
    if set(store.arrays) != expected or set(store.expected_ids) != expected: raise ValueError('Complete cadence required')
    ids = dict(store.expected_ids); inventory = [[*k, ids[k]] for k in sorted(expected)]
    if digest(inventory) != u['input_inventory_sha256'] or digest(store.provenance) != u['source_provenance_sha256']:
        raise ValueError('Maximum/retention source binding differs')
    result = {'schema': 'radio-whole-cadence-retention-rank-v1', 'case_identity': u['case_identity'],
        'domain': u['domain'], 'noise_law_sha256': u['noise_law_sha256'],
        'threshold_receipt_sha256': t['threshold_receipt_sha256'],
        'cadence_maximum_receipt': u, 'input_inventory_sha256': digest(inventory),
        'source_provenance': store.provenance, 'retained': {'on': [], 'off': []},
        'mask_receipts': [], 'enumeration': {}, 'complete': False,
        'physical_vetoes_evaluated': False, 'scientific_candidate_selection_authorized': False,
        'legacy_certificate_issued': False, 'telescope_admission_authorized': False,
        'caps': {'records_per_kind': maximum_records, 'canonical_record_bytes_per_kind': maximum_evidence_bytes}}
    for kind in ('on', 'off'):
        visited = []; count = 0; byte_count = 0; best = EMPTY
        result['enumeration'][kind] = {'visited_hypotheses': 0, 'scored_cells': 0, 'eligible_cells': 0}
        for index in range(family.template_count):
            arrays = {width: checked_vectors(store, kind, index, width, family.grid, ids[kind,index,width])
                      for width in core.M37_SPECTRAL_WIDTHS}
            mask = build_mask(arrays.__getitem__, 'neighbor9')[:, family.grid.score_slice]
            result['mask_receipts'].append({'kind': kind, 'template': index,
                'sha256': hashlib.sha256(mask.tobytes()).hexdigest(), 'masked_cells': int(mask.sum())})
            for wi, width in enumerate(core.M37_SPECTRAL_WIDTHS):
                values = arrays[width][:, family.grid.score_slice]
                for subset in core.M37_ACTIVITY_SUBSETS:
                    active = list(subset)
                    eligible = np.all(values[active] >= 3., axis=0) & ~np.any(mask[active], axis=0)
                    with np.errstate(over='ignore', invalid='ignore'):
                        scores = core.stack_hypothesis(values, subset, minimum_active_epoch_snr=3.,
                            stack_statistic='sum', exclusion_mask=mask)
                    if not np.array_equal(np.isfinite(scores), eligible):
                        result['failure'] = {'reason': 'Eligible arithmetic nonfinite', 'kind': kind,
                            'template': index, 'width': width, 'subset': active}
                        raise IncompleteRetention('Eligible arithmetic nonfinite', result)
                    visited.append([index, wi, active]); count += int(eligible.sum())
                    result['enumeration'][kind] = {'visited_hypotheses': len(visited),
                        'scored_cells': len(visited)*family.grid.score_bin_count, 'eligible_cells': count}
                    if eligible.any(): best = maximum((best, Maximum('finite', float(scores[eligible].max()))))
                    for q in np.flatnonzero(eligible & (scores >= t['operational_threshold'])):
                        score = float(scores[q]); rank = inclusive_rank(Maximum('finite', score), refs)
                        ge = sum(x.order_key >= Maximum('finite', score).order_key for x in refs)
                        record = {'schema': 'radio-whole-cadence-retained-member-v1',
                            'case_identity': u['case_identity'], 'scan_kind': kind,
                            'family_sha256': digest(family.record()), 'template_index': index,
                            'spectral_width_index': wi, 'spectral_width_channels': width,
                            'active_epochs_zero_based': active, 'proxy_carrier_index': int(q),
                            'carrier_hz': float(family.grid.score_hz[q]), 'stack_snr': score,
                            'epoch_snr': [float(x) for x in values[:,q]],
                            'threshold_receipt_sha256': t['threshold_receipt_sha256'],
                            'physical_disposition': 'PENDING_PHYSICAL_STAGES',
                            'scientific_candidate': False}
                        # ON null maxima calibrate ON-family members only. OFF
                        # records are physical-control evidence, never ranked here.
                        if kind == 'on':
                            record['rank'] = {'greater_or_equal_reference_count': ge,
                                'unreduced_numerator': 1+ge, 'reference_denominator': len(refs)+1,
                                'exact_fraction': [rank.numerator, rank.denominator],
                                'inclusive_p': float(rank), 'meets_rank_cut': rank <= Fraction(1,100)}
                        record['record_id'] = digest(record)
                        size = len(canonical(record))
                        if len(result['retained'][kind]) >= maximum_records or byte_count+size > maximum_evidence_bytes:
                            result['failure'] = {'reason': 'Retention capacity exceeded',
                                'kind': kind, 'first_unstored_trigger': record,
                                'canonical_bytes_before': byte_count, 'next_record_bytes': size}
                            raise IncompleteRetention('Retention capacity exceeded', result)
                        result['retained'][kind].append(record); byte_count += size
        expected_count = family.template_count*len(core.M37_SPECTRAL_WIDTHS)*len(core.M37_ACTIVITY_SUBSETS)
        if len(visited) != expected_count or len({(a,b,tuple(c)) for a,b,c in visited}) != expected_count:
            raise IncompleteRetention('Incomplete hypothesis inventory', result)
        result['enumeration'][kind].update({'hypothesis_inventory_sha256': digest(visited),
            'retained_count': len(result['retained'][kind]), 'canonical_record_bytes': byte_count,
            'maximum': best.record(), 'all_hypotheses_evaluated': True})
        if kind == 'on' and (best.record() != u['maximum'] or count != u['eligible_cells']):
            raise IncompleteRetention('Maximum/retention arithmetic disagrees', result)
    rank = inclusive_rank(Maximum.from_record(u['maximum']), refs)
    result['observed_maximum_rank'] = {'exact_fraction': [rank.numerator, rank.denominator],
        'inclusive_p': float(rank), 'empty_is_probability_one': u['maximum']['kind'] == 'empty'}
    result['complete'] = True; result['result_sha256'] = digest(result)
    return result


def _execute(family, store, threshold, unit, **caps):
    # Public production-shaped entry points retain their exact 127-unit type gate.
    if not isinstance(threshold, WholeCadenceThreshold):
        raise ValueError('Distinct whole-cadence threshold required')
    return _execute_core(family, store, threshold, unit, **caps)


def execute_fixture(family, store, threshold, *, case_identity, noise_law_sha256, **caps):
    unit = reduce_fixture(family, store, case_identity=case_identity, noise_law_sha256=noise_law_sha256)
    return _execute(family, store, threshold, unit, **caps)


def execute_native(run, store, threshold, *, case_identity, noise_law_sha256, **caps):
    unit = reduce_native_run(run, store, case_identity=case_identity, noise_law_sha256=noise_law_sha256)
    context = run.context
    family = Family(context.identity, context.factor_contract.factors.identity, len(context.bank), context.grid)
    return _execute(family, store, threshold, unit, **caps)
