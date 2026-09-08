"""Named M43AB development endpoints; the production detector is unchanged."""
import copy
import math
import numpy as np
from . import search_v0p6 as core
from .receiver_v0p6 import _predicted_midpoint_hz
from .alias_v0p6 import match_receiver_frame_aliases
from .detector_m43u import digest
from .confirmation_m43w import off_window
from .confirmation_m43x import remaining_evidence

POLICIES = ('centered_receiver', 'centered_receiver_off_match',
            'centered_receiver_off_match_aggregate')
ON_OFF_CORRELATION_FLOOR = 0.8


def centered_signature(cache, factors, carrier_hz, patches=None):
    """Sample the nearest native channel to the predicted midpoint, no peak hunt.

    This is a stationary receiver measurement, not a de-drifted ON score.
    Ascending channel order and nearest-even rounding follow existing geometry.
    """
    pred = _predicted_midpoint_hz(float(carrier_hz), factors)/1e6
    g = cache.source.geometry
    raw = int(core.nearest_native_indices(g, np.asarray([pred*1e6]))[0])
    half = cache.width//2
    if raw < half or raw >= g.channel_count-half:
        raise core.V0P6CoverageError('centered receiver window incomplete')
    value = np.float32(0)
    for row in range(cache.source.integration_count):
        v = cache.values[row, raw-half]
        if patches is not None:
            start, patch = patches[row]
            if 0 <= raw-start < len(patch):
                v = patch[raw-start]
        value += v
    value /= np.float32(math.sqrt(cache.source.integration_count))
    freq = float((g.raw_zero_hz+raw*g.channel_width_hz)/1e6)
    return dict(predicted_mid_mhz=pred, peak_frequency_mhz=freq,
                peak_snr=float(value), offset_from_prediction_hz=float((freq-pred)*1e6)), raw


def centered_signatures(overlay, records, direct_check=None):
    signatures = {}; queries = []; memo = {}; checked = set()
    for r in records:
        t, q, w = r['template_index'], r['proxy_carrier_index'], r['spectral_width_channels']
        entries = []
        for e in r['active_epochs_zero_based']:
            key = (t, q, w, e)
            if key not in memo:
                cache = overlay.receiver.cache(f'epoch{e+1}_on', w)
                sig, raw = centered_signature(cache, overlay.factors[e][t],
                    overlay.grid.score_hz[q], overlay.patches.get((e, w)))
                memo[key] = sig, raw
                if direct_check is not None and (e, w) not in checked:
                    direct_check(e, w, raw, sig['peak_snr'])
                    checked.add((e, w))
            sig, raw = memo[key]
            entries.append(dict(epoch_zero_based=e, **sig))
            queries.append(dict(record_id=r['record_id'], epoch=e, template=t,
                                score_index=q, width=w, native_center=raw))
        signatures[r['record_id']] = entries
    return signatures, dict(schema='m43ab-nearest-predicted-native-channel-v1',
        signatures_sha256=digest(signatures), queries=queries, queries_sha256=digest(queries),
        unique_queries=len(memo), direct_anchor_checks=len(checked),
        stationary_sample_not_local_maximum=True, overlay_sha256=digest(overlay.overlay_receipt))


def reclassify(result, signatures, receipt, grid, bank, table, basis, scans, window, cap):
    """Keep retention, prior OFF checks, alias identities, tolerances and rank."""
    if receipt['signatures_sha256'] != digest(signatures):
        raise ValueError('centered signature receipt mismatch')
    aliases = match_receiver_frame_aliases(result['off_track']['records'],
        result['retention_certificates']['on'], grid,
        core.factor_matrix_for_kind(table, basis, scans, 'on'), signatures,
        off_match_certificate=result['off_track']['certificate'],
        single_adjacent_off_evidence=result['adjacent_off']['evidence'],
        single_adjacent_off_certificate=result['adjacent_off']['certificate'],
        expected_off_match_certificate_sha256=result['off_track']['certificate']['off_match_certificate_sha256'],
        expected_single_adjacent_off_certificate_sha256=result['adjacent_off']['certificate']['single_adjacent_off_certificate_sha256'],
        window_order=(window,), track_tolerance_hz=20., local_half_width_hz=100.,
        local_peak_snr_floor=5.5, minimum_shared_active_epochs=2, maximum_records=cap,
        maximum_bucket_entries=cap, maximum_identity_track_comparisons=5_000_000,
        maximum_distinct_candidate_visits_per_window=5_000_000, template_bank=bank)
    out = copy.deepcopy(result)
    out['schema'] = 'm43ab-centered-receiver-diagnostic-v1'
    out['receiver_signatures'] = signatures; out['receiver_receipt'] = receipt
    out['receiver_alias'] = aliases
    dispositions = {r['record_id']: r['member_disposition'] for r in aliases['records']}
    for d in out['decisions']:
        d['physical_disposition'] = dispositions[d['record_id']]
        d['passes_evaluated_physical_vetoes'] = d['physical_disposition'] == 'pending_receiver_alias_evaluation'
    out.pop('result_sha256')
    out['result_sha256'] = digest(out)
    return out


def centered_agreement(on, off, grid, q, width, active):
    """Unshifted, mean-subtracted ON/OFF correlation in the same centered window.

    An explicitly experimental 0.8 floor qualifies the existing OFF-window
    rejection; it never overrides an earlier veto. No background subtraction,
    fitted shift, truth label or cross-epoch correlation is used.
    """
    prior = off_window(off, grid, q, width, active)
    radius = max(1, width//2); center = grid.score_slice.start+q
    lo, hi = center-radius, center+radius+1
    if lo < 0 or hi > on.shape[1]:
        raise core.V0P6CoverageError('centered ON/OFF response incomplete')
    rows = []
    for i, e in enumerate(active):
        a = on[e, lo:hi].astype(float); b = off[e, lo:hi].astype(float)
        a -= a.mean(); b -= b.mean()
        denom = float(np.linalg.norm(a)*np.linalg.norm(b))
        corr = None if denom == 0 else float(np.dot(a, b)/denom)
        veto = prior['maxima'][i] >= 5.5 and corr is not None and corr >= ON_OFF_CORRELATION_FLOOR
        rows.append(dict(epoch=e, correlation=corr, off_maximum=prior['maxima'][i], vetoed=bool(veto)))
    return dict(radius_proxy_bins=radius, correlation_floor=ON_OFF_CORRELATION_FLOOR,
                epochs=rows, vetoed=any(r['vetoed'] for r in rows))


def apply_controls(audit, store, grid):
    evidence = []
    for m in audit['members']:
        t, q, w = m['template_index'], m['proxy_carrier_index'], m['spectral_width_channels']
        on, oid = store.get('on', t, w); off, fid = store.get('off', t, w)
        if oid != store.expected_ids['on', t, w] or fid != store.expected_ids['off', t, w]:
            raise ValueError('changed score identity')
        if not np.array_equal(on[:, grid.score_slice.start+q], np.asarray(m['epoch_values_at_proxy_carrier'], dtype='<f4')):
            raise ValueError('retained ON scores changed')
        evidence.append(dict(record_id=m['record_id'],
            agreement=centered_agreement(on, off, grid, q, w, m['active_epochs_zero_based']),
            remaining=remaining_evidence(m['epoch_values_at_proxy_carrier'], m['active_epochs_zero_based'])))
    outputs = {}
    for policy in POLICIES:
        a = copy.deepcopy(audit); a['confirmation_policy'] = policy
        for m, e in zip(a['members'], evidence):
            reasons = []
            if policy != 'centered_receiver' and e['agreement']['vetoed']:
                reasons.append('centered_ON_OFF_agreement')
            if policy == POLICIES[-1] and not e['remaining']['remaining_passed']:
                reasons.append('remaining_aggregate_below_5p5')
            m['m43ab_rejections'] = reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes'] = False
                m['physical_disposition'] = 'm43ab_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors'] = sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors'] = sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[policy] = a
    return outputs, evidence
