"""Prospective synthetic receiver controls; no telescope entry point.

Calibration scores may be translated only through an externally pinned proof.
The original native-cache receipts remain source receipts, never destination
measurements. Empty conditional null support is a failed prerequisite.
"""
import hashlib
import json
import math

import numpy as np

from . import receiver_bank_radio as received
from . import receiver_development_radio as render
from . import pipeline_receiver_radio as pipeline
from . import detector_receiver_radio as detector
from . import mask_m43u as masks
from . import search_v0p6 as core
from . import transfer_m43g as native
from .injection_m43r import ScoreStore


def render_case(context, case, *, budget=lambda: None):
    """One reserved realization; exact published header clock and row order."""
    context.validate()
    recipe = case['recipe']
    if case['role'] not in ('calibration', 'evaluation'):
        raise ValueError('Closed development identities cannot be consumed here')
    kind = recipe['kind']
    if kind in ('noise_only', 'noise_null'):
        active = {'on_epochs_zero_based': [], 'off_epochs_zero_based': []}
        width = power = rate = 0
    else:
        active = recipe['activity_patterns'][kind]
        width = recipe['injection_width_channels']
        power = recipe['total_digital_power']
        rate = recipe['rate_label_hz_s']
    q = context.grid.center_mhz * 1e6
    center = json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock = received.clock(json.loads(context.factor_contract.source_contract_bytes))
    sources = {}; receipts = []; mass_error = 0.
    for scan_index, scan in enumerate(context.scans):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([case['seed'], scan_index])))
        rows = []
        injected = scan['epoch']-1 in active[scan['kind']+'_epochs_zero_based']
        def reader(row):
            nonlocal mass_error
            base = rng.normal(100., 1., 65536).astype('<f4')
            value = base.astype('<f8')
            row_receipt = {'row': row, 'background_sha256': native.array_hash(base),
                           'injected': injected, 'added_total_power_before_float32': 0.}
            if injected:
                times = clock[scan_index*16+row]
                t = float(times[1]); dt = float(times[2]-times[0])
                position = (q*(1+rate*t/center)-context.geometry.raw_zero_hz)/context.geometry.channel_width_hz
                sweep = q*rate/center*dt/context.geometry.channel_width_hz
                indices, mass = render.pixel_masses(position, sweep, width, 65536)
                mass_error = max(mass_error, abs(float(mass.sum())-1))
                value[indices] += power*mass
                row_receipt.update(added_total_power_before_float32=float(power*mass.sum()),
                                   center_channel=position, sweep_channels=sweep,
                                   support_channel_interval=[int(indices[0]), int(indices[-1])+1])
            result = value.astype('<f4')
            row_receipt['raw_sha256'] = native.array_hash(result); rows.append(row_receipt)
            return result
        source = native.normalize_synthetic_rows(reader, context.geometry, 16, input_orientation='ascending',
            scope={'kind': 'synthetic', 'input_domain': 'reserved-receiver-panel',
                   'scan': scan['label'], 'context_sha256': context.identity,
                   'case_identity': case['identity'],
                   'receiver_factor_bank_sha256': context.factor_contract.factors.identity,
                   'telescope_provenance': False})
        for receipt, row in zip(rows, source.values, strict=True):
            receipt['normalized_sha256'] = native.array_hash(row)
        sources[scan['label']] = source
        receipts.append({'scan': scan['label'], 'source_identity': source.identity, 'rows': rows})
        budget()
    return sources, {'row_receipts': receipts, 'max_mass_error': mass_error,
                     'background': 'iid digital Gaussian mean 100 sigma 1; no calibration comb',
                     'source_domain': 'synthetic', 'real_telescope_distribution_claimed': False}


def translate_calibration_scores(run, store, destination, proof_bytes, expected_proof_sha256):
    """Explicit synthetic-only score translation, preserving original ancestry."""
    run.validate_store(store); destination.validate()
    if hashlib.sha256(proof_bytes).hexdigest() != expected_proof_sha256:
        raise ValueError('Score-map proof external pin mismatch')
    proof = json.loads(proof_bytes)
    if proof.get('status') != 'SCORE_OPERATOR_IDENTICAL_ON_TRANSLATED_ARRAYS':
        raise ValueError('Score-map proof did not qualify the arithmetic')
    tables = {x['role']: x for x in proof['tables']}
    src = tables['calibration']; dst = tables['validation']
    if (src['context_sha256'] != run.context.identity or dst['context_sha256'] != destination.identity
            or src['relative_index_sha256'] != dst['relative_index_sha256']
            or src['shape'] != dst['shape'] or src['widths'] != dst['widths']
            or src['block_length'] != dst['block_length']
            or src['native_normalization_origin'] != dst['native_normalization_origin']):
        raise ValueError('Only the pinned calibration-to-validation operator is allowed')
    receipt = {'schema': 'radio-receiver-synthetic-score-translation-v1',
        'source_context_sha256': run.context.identity, 'destination_context_sha256': destination.identity,
        'proof_sha256': expected_proof_sha256, 'source_provenance': store.provenance,
        'source_score_vector_ids': [{'key': list(k), 'id': store.expected_ids[k]} for k in sorted(store.arrays)],
        'destination_is_new_native_measurement': False, 'values_changed': False,
        'synthetic_distribution_assumption': 'same pinned iid digital-noise generator on relative native indices',
        'telescope_noise_exchangeability_claimed': False, 'absolute_frequency_veto_transfer_claimed': False}
    receipt['receipt_sha256'] = native.digest(receipt)
    return ScoreStore({k: v.copy() for k,v in store.arrays.items()},
        {'source_domain': 'synthetic-translated-calibration-scores',
         'translation_receipt': receipt, 'context_sha256': destination.identity}), receipt


def accumulate(context, store, shifts, minimum_shift_bins=32, budget=lambda: None):
    """Same calibration loop; inspect empty support before destructive finalize."""
    context.validate(); f = context.factor_contract; widths = core.M37_SPECTRAL_WIDTHS
    acc = core.CalibrationAccumulator.create(
        window_id=context.window, score_bin_count=context.grid.score_bin_count,
        template_count=len(f.bank), template_bank_sha256_value=core.template_bank_sha256(f.bank),
        factor_basis_sha256_value=f.factors.identity, factor_basis_labels_sha256_value=f.labels_sha256,
        scan_inventory_sha256_value=core.scan_inventory_sha256(context.scans),
        factor_row_selection_sha256_value=f.row_selection_sha256('on'),
        factor_table_sha256_value=f.factor_table_sha256, spectral_widths=widths,
        activity_subsets=core.M37_ACTIVITY_SUBSETS, minimum_active_epoch_snr=3., stack_statistic='sum',
        scramble_shifts=shifts, minimum_shift_bins=minimum_shift_bins,
        expected_scramble_sha256=core.scramble_table_sha256(shifts))
    mask_hashes = {}; mask_counts = {}
    for t in range(len(f.bank)):
        arrays = {w: detector.checked_vectors(store, 'on', t, w, context.grid) for w in widths}
        mask = masks.build_mask(arrays.__getitem__, 'neighbor9')[:, context.grid.score_slice]
        mask_hashes[str(t)] = hashlib.sha256(mask.tobytes()).hexdigest()
        mask_counts[str(t)] = int(mask.sum())
        for wi,w in enumerate(widths):
            core.update_calibration(acc, arrays[w][:,context.grid.score_slice],
                                    template_index=t, width_index=wi, exclusion_mask=mask)
        budget()
    receipt = {'schema': 'radio-receiver-calibration-support-v1',
        'context_sha256': context.identity, 'mask_sha256s': mask_hashes, 'masked_cell_counts': mask_counts,
        'observed_maximum': finite_value(acc.observed_maximum),
        'null_maxima': [finite_value(x) for x in acc.null_maxima],
        'null_maxima_f64le_sha256': hashlib.sha256(acc.null_maxima.astype('<f8').tobytes()).hexdigest(),
        'finite_null_count': int(np.isfinite(acc.null_maxima).sum()), 'null_count': len(acc.null_maxima),
        'distinct_shift_rows': len(np.unique(shifts,axis=0)),
        'observed_score_cells': acc.observed_score_cells, 'null_score_cells': acc.null_score_cells,
        'visited_hypotheses': len(acc._visited_hypothesis_keys),
        'empty_value_encoding': 'null means minus infinity: no eligible hypothesis; not a finite null observation'}
    receipt['complete_hypothesis_inventory'] = acc._visited_hypothesis_keys == set(acc.expected_hypothesis_keys)
    if not receipt['complete_hypothesis_inventory']:
        raise ValueError('Incomplete calibration hypothesis inventory')
    if not math.isfinite(acc.observed_maximum) or not np.isfinite(acc.null_maxima).all():
        receipt['status'] = 'FAILED_EMPTY_CONDITIONAL_NULL_SUPPORT'
        return None, receipt
    receipt['sealed_summary'] = acc.finalize()
    receipt['status'] = 'FINITE_CONDITIONAL_NULL_SUPPORT'
    return acc, receipt


def finite_value(value):
    value = float(value)
    if math.isfinite(value): return value
    if value == -math.inf: return None
    raise ValueError('Unexpected NaN or positive infinity')


def bind_calibration(context, accumulator, support_receipt, translation_receipt):
    threshold = core.calibrated_threshold([accumulator], expected_window_ids=[context.window],
        reference_floor=10., quantile=1., scientific_p_ceiling=.01)
    binding = masks.bind_calibration(accumulator, threshold, 'neighbor9')
    receipt = {'schema': 'radio-receiver-translated-synthetic-calibration-v1',
        'context_sha256': context.identity, 'support': support_receipt,
        'translation': translation_receipt, 'null_maxima': accumulator.null_maxima.tolist(),
        'threshold': threshold.as_record(), 'binding': binding,
        'independent_observations': False, 'conditional_resampling_only': True,
        'telescope_threshold_transfer_authorized': False}
    return pipeline.Calibration(context.identity, accumulator, threshold, binding, receipt, native.digest(receipt))


def classify(report, context, case):
    """Truth used only after every fixed decision; every final member accounted."""
    recipe = case['recipe']; kind = recipe['kind']; r = report['detector']
    active = [] if kind == 'noise_null' else recipe['activity_patterns'][kind]['on_epochs_zero_based']
    q = context.grid.center_mhz*1e6; rate = recipe['rate_label_hz_s']
    center = json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock = received.clock(json.loads(context.factor_contract.source_contract_bytes))
    truth = np.array([q*(1+rate*float(row[1])/center) for si in (0,2,4) for row in clock[si*16:(si+1)*16]])
    factors = context.factor_contract.matrix_for_kind('on')
    decisions = {x['record_id']: x for x in r['decisions']}
    association = []
    for rec in r['retained']['on']:
        decision = decisions[rec['record_id']]
        final = decision['passes_evaluated_physical_vetoes'] and decision['meets_diagnostic_rank_cut']
        epochs = rec['active_epochs_zero_based']
        indices = [e*16+i for e in epochs for i in range(16)]
        errors = abs(rec['proxy_carrier_hz']*factors[rec['template_index'],indices]-truth[indices])
        associated = bool(active and set(epochs).issubset(active) and np.all(errors <= 2*context.geometry.channel_width_hz))
        association.append({'record_id': rec['record_id'], 'final': final, 'associated': associated,
            'maximum_truth_track_error_hz': float(errors.max()), 'width': rec['spectral_width_channels']})
    final = [x for x in association if x['final']]
    ids = {x['record_id'] for x in final}; associated_ids = {x['record_id'] for x in final if x['associated']}
    clusters = report['clusters']
    partition = [rid for c in clusters for rid in c['diagnostic_final_ids']]
    if len(partition) != len(set(partition)) or set(partition) != ids:
        raise ValueError('Final-member cluster partition incomplete')
    finals = [c for c in clusters if c['diagnostic_final_ids']]
    counts = {'final_members': len(final), 'associated_final_members': len(associated_ids),
        'unassociated_final_members': len(ids-associated_ids), 'final_clusters': len(finals),
        'associated_final_clusters': sum(bool(set(c['diagnostic_final_ids'])&associated_ids) for c in finals),
        'unassociated_final_clusters': sum(bool(set(c['diagnostic_final_ids'])&(ids-associated_ids)) for c in finals)}
    # A mixed component is counted in both cluster categories, explicitly.
    primary_pass = counts['associated_final_members']>=1 and counts['associated_final_clusters']>=1 if kind=='on_signal' else not final
    width_gate = {}
    for w in (65,129):
        bad = {x['record_id'] for x in final if not x['associated'] and x['width']==w}
        width_gate[str(w)] = {'unassociated_final_members': len(bad),
            'unassociated_final_clusters': sum(bool(set(c['diagnostic_final_ids'])&bad) for c in finals)}
    # The separate broad-width leakage gate is applied to RFI/null controls.
    # On-signal unassociated counts remain reported, per the reserved recovery rule.
    broad_pass = kind=='on_signal' or all(v['unassociated_final_members']==0 for v in width_gate.values())
    return {'case_id': recipe['case_id'], 'case_identity': case['identity'], 'kind': kind,
        'counts': counts, 'association': association, 'broad_width_counts': width_gate,
        'mixed_cluster_counts_can_overlap': True, 'complete_partition': True,
        'recovery_or_zero_control_gate_pass': bool(primary_pass), 'broad_width_gate_pass': broad_pass,
        'gate_pass': bool(primary_pass and broad_pass), 'truth_not_used_by_detector': True}
