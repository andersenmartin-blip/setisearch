"""Complete empty-aware maxima and reference bundles, without admission.

This is a distinct whole-cadence interface. It does not construct legacy
CalibrationAccumulator/ThresholdCertificate objects or any scramble receipt.
"""
from dataclasses import dataclass
import hashlib
import json

import numpy as np

from . import search_v0p6 as core
from .detector_m43u import checked_vectors
from .empty_null_radio import EMPTY, Maximum, canonical, higher_quantile, maximum
from .mask_m43u import build_mask


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _sha(value, label):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in '0123456789abcdef' for c in value)):
        raise ValueError(label+' must be a lowercase SHA256')
    return value


@dataclass(frozen=True)
class Family:
    context_sha256: str
    receiver_bank_sha256: str
    template_count: int
    grid: object

    def record(self):
        _sha(self.context_sha256, 'context'); _sha(self.receiver_bank_sha256, 'bank')
        if isinstance(self.template_count, bool) or not isinstance(self.template_count, int) or self.template_count < 1:
            raise ValueError('Positive integer template count required')
        if not isinstance(self.grid, core.ProxyCarrierGrid):
            raise ValueError('Explicit carrier grid required')
        return {'schema': 'radio-whole-cadence-family-v1',
            'context_sha256': self.context_sha256,
            'receiver_bank_sha256': self.receiver_bank_sha256,
            'template_count': self.template_count,
            'proxy_grid_sha256': core.proxy_carrier_grid_sha256(self.grid),
            'score_carrier_count': self.grid.score_bin_count,
            'support_carrier_count': self.grid.support_bin_count,
            'scan_kind': 'on', 'mask_policy': 'neighbor9',
            'widths': list(core.M37_SPECTRAL_WIDTHS),
            'activity_subsets': [list(x) for x in core.M37_ACTIVITY_SUBSETS],
            'minimum_active_epoch_snr': 3., 'stack_statistic': 'sum',
            'empty_rule': 'no eligible cell after complete family enumeration'}


@dataclass(frozen=True)
class CadenceMaximum:
    """Immutable canonical computation receipt, not a scientific certificate."""
    payload: bytes

    def record(self):
        value = json.loads(self.payload)
        if canonical(value) != self.payload:
            raise ValueError('Noncanonical cadence receipt')
        checksum = value.pop('receipt_sha256')
        if checksum != digest(value):
            raise ValueError('Cadence receipt changed')
        value['receipt_sha256'] = checksum
        if value.get('schema') != 'radio-whole-cadence-maximum-v1':
            raise ValueError('Wrong cadence receipt schema')
        Maximum.from_record(value['maximum'])
        return value


def _reduce(family, store, case_identity, noise_law_sha256, domain, ancestry):
    family_record = family.record()
    _sha(case_identity, 'case'); _sha(noise_law_sha256, 'noise law')
    if store.provenance.get('context_sha256') != family.context_sha256:
        raise ValueError('Score/context mismatch')
    expected = {(kind, t, width) for kind in ('on', 'off')
                for t in range(family.template_count) for width in core.M37_SPECTRAL_WIDTHS}
    if set(store.arrays) != expected or set(store.expected_ids) != expected:
        raise ValueError('Missing or extra full-cadence vector')
    ids = dict(store.expected_ids)
    # Validate OFF inputs too: this receipt represents a complete cadence,
    # even though its null statistic is the eligible ON-family maximum.
    for kind, t, width in sorted(expected):
        checked_vectors(store, kind, t, width, family.grid, ids[kind, t, width])
    inventory = [[*key, ids[key]] for key in sorted(expected)]
    best = EMPTY; eligible_cells = 0; visited = []; masks = []
    for t in range(family.template_count):
        arrays = {w: checked_vectors(store, 'on', t, w, family.grid, ids['on', t, w])
                  for w in core.M37_SPECTRAL_WIDTHS}
        mask = build_mask(arrays.__getitem__, 'neighbor9')[:, family.grid.score_slice]
        masks.append({'template': t, 'masked_cells': int(mask.sum()),
                      'sha256': hashlib.sha256(mask.tobytes()).hexdigest()})
        for wi, width in enumerate(core.M37_SPECTRAL_WIDTHS):
            values = arrays[width][:, family.grid.score_slice]
            for subset in core.M37_ACTIVITY_SUBSETS:
                active = list(subset)
                eligible = np.all(values[active] >= 3., axis=0) & ~np.any(mask[active], axis=0)
                # stack_hypothesis intentionally maps nonfinite arithmetic to
                # -inf in the old interface. The new tagged EMPTY boundary
                # must reject an overflow on an otherwise eligible cell.
                with np.errstate(over='ignore', invalid='ignore'):
                    scores = core.stack_hypothesis(values, subset,
                        minimum_active_epoch_snr=3., stack_statistic='sum', exclusion_mask=mask)
                if not np.array_equal(np.isfinite(scores), eligible):
                    raise ValueError('Eligible score arithmetic became nonfinite; not EMPTY')
                count = int(eligible.sum())
                eligible_cells += count
                if count:
                    best = maximum((best, Maximum('finite', float(np.max(scores[eligible])))))
                visited.append([t, wi, list(subset)])
    expected_count = family.template_count * len(core.M37_SPECTRAL_WIDTHS) * len(core.M37_ACTIVITY_SUBSETS)
    if len(visited) != expected_count or len({(a,b,tuple(c)) for a,b,c in visited}) != expected_count:
        raise ValueError('Incomplete hypothesis enumeration')
    value = {'schema': 'radio-whole-cadence-maximum-v1',
        'case_identity': case_identity, 'noise_law_sha256': noise_law_sha256,
        'domain': domain, 'family': family_record, 'family_sha256': digest(family_record),
        'input_vector_count': len(expected), 'input_inventory_sha256': digest(inventory),
        'source_provenance_sha256': digest(store.provenance), 'source_ancestry': ancestry,
        'visited_hypotheses': expected_count, 'hypothesis_inventory_sha256': digest(visited),
        'scored_cells': expected_count * family.grid.score_bin_count,
        'eligible_cells': eligible_cells, 'mask_receipts': masks, 'maximum': best.record(),
        'all_hypotheses_evaluated': True, 'score_shift_resampling': False,
        'detector_certificate_issued': False, 'telescope_admission_authorized': False}
    value['receipt_sha256'] = digest(value)
    return CadenceMaximum(canonical(value))


def reduce_fixture(family, store, *, case_identity, noise_law_sha256):
    if (store.provenance.get('source_domain') != 'deterministic-score-fixture'
            or store.provenance.get('case_identity') != case_identity):
        raise ValueError('Explicit case-bound deterministic fixture required')
    return _reduce(family, store, case_identity, noise_law_sha256,
                   'deterministic-score-fixture', {'native_runtime_verified': False})


def reduce_native_run(run, store, *, case_identity, noise_law_sha256):
    """Unexercised native-success path; source/code/runtime freeze still needed."""
    from .pipeline_receiver_radio import NativeRun
    if not isinstance(run, NativeRun):
        raise ValueError('A validated receiver NativeRun is required')
    run.validate_store(store)
    for source in run.sources.values():
        scope = json.loads(source.scope_json)
        if scope.get('case_identity') != case_identity or scope.get('noise_law_sha256') != noise_law_sha256:
            raise ValueError('Native source case/noise-law receipt mismatch')
    context = run.context
    family = Family(context.identity, context.factor_contract.factors.identity,
                    len(context.bank), context.grid)
    return _reduce(family, store, case_identity, noise_law_sha256, 'synthetic-native',
        {'source_ids': run.source_ids, 'native_store_validated': True,
         'noise_distribution_verified_by_bytes': False,
         'independent_draws_established_by_receipt_alone': False})


def reference_bundle(units, *, expected_case_identities, expected_family_sha256,
                     expected_noise_law_sha256, destination_context_sha256,
                     operator_translation_proof_sha256):
    """Bind exactly 127 ordered outcomes; cannot activate the proposed design."""
    units = tuple(units); expected = tuple(expected_case_identities)
    for value, label in ((expected_family_sha256, 'family'),
                         (expected_noise_law_sha256, 'noise law'),
                         (destination_context_sha256, 'destination'),
                         (operator_translation_proof_sha256, 'translation proof')):
        _sha(value, label)
    if len(units) != 127 or len(expected) != 127 or len(set(expected)) != 127:
        raise ValueError('Exactly 127 distinct ordered whole-cadence units required')
    for value in expected:
        _sha(value, 'expected case')
    records = []
    for unit, identity in zip(units, expected, strict=True):
        if not isinstance(unit, CadenceMaximum):
            raise ValueError('Typed whole-cadence receipts required')
        row = unit.record()
        if (row['case_identity'] != identity or row['family_sha256'] != expected_family_sha256
                or row['noise_law_sha256'] != expected_noise_law_sha256
                or row['family_sha256'] != digest(row['family'])
                or row['all_hypotheses_evaluated'] is not True
                or row['score_shift_resampling'] is not False):
            raise ValueError('Whole-cadence reference binding mismatch')
        family = row['family']
        nh = family['template_count'] * len(family['widths']) * len(family['activity_subsets'])
        if row['visited_hypotheses'] != nh or row['scored_cells'] != nh*family['score_carrier_count']:
            raise ValueError('Incomplete reference hypothesis count')
        if not 0 <= row['eligible_cells'] <= row['scored_cells']:
            raise ValueError('Invalid eligible count')
        if (row['maximum']['kind'] == 'empty') != (row['eligible_cells'] == 0):
            raise ValueError('Empty/eligible-count contradiction')
        records.append(row)
    domains = {r['domain'] for r in records}
    if len(domains) != 1 or not domains <= {'deterministic-score-fixture', 'synthetic-native'}:
        raise ValueError('Mixed or unsupported reference domains')
    outcomes = [Maximum.from_record(row['maximum']) for row in records]
    empirical = higher_quantile(outcomes)
    result = {'schema': 'radio-whole-cadence-reference-bundle-v1',
        'status': 'ENGINEERING_REFERENCE_NO_DETECTOR_CERTIFICATE',
        'domain': records[0]['domain'], 'reference_count': 127,
        'empty_count': sum(x.kind == 'empty' for x in outcomes),
        'finite_count': sum(x.kind == 'finite' for x in outcomes),
        'ordered_case_identities': list(expected),
        'ordered_unit_receipt_sha256s': [r['receipt_sha256'] for r in records],
        'ordered_maxima': [x.record() for x in outcomes],
        'family_sha256': expected_family_sha256,
        'noise_law_sha256': expected_noise_law_sha256,
        'destination_context_sha256': destination_context_sha256,
        'operator_translation_proof_sha256': operator_translation_proof_sha256,
        'operator_translation_proof_semantics_verified_here': False,
        'higher_quantile': empirical.record(),
        'floor_or_maximum': maximum((Maximum('finite', 10.), empirical)).record(),
        'joint_exchangeability_proved_by_receipts': False,
        'budget_charged': False, 'detector_certificate_issued': False,
        'telescope_admission_authorized': False}
    result['bundle_sha256'] = digest(result)
    return result
