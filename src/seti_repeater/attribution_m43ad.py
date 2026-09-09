"""M43AD development endpoints. No production detector or threshold change."""
import copy
import math
import numpy as np

from . import search_v0p6 as core
from .detector_m43u import digest
from .receiver_v0p6 import _predicted_midpoint_hz
from .confirmation_m43w import off_window
from .confirmation_m43x import remaining_evidence

POLICIES = ('geometry_receiver', 'geometry_receiver_off_aggregate',
            'geometry_receiver_aligned_off_aggregate')
CORRELATION_FLOOR = 0.8


def attribute_peak(original, centered, carrier_hz, factors, width, spacing_hz):
    """Choose by track/filter geometry alone; retain both unmodified inputs.

    A peak inside the full integration track plus filter half width and half
    a native channel remains the receiver witness. Outside, use the centered
    measurement. Inclusion is not a claim of common physical origin.
    """
    factors = np.asarray(factors, dtype=float)
    if (factors.ndim != 1 or not len(factors) or not np.isfinite(factors).all()
            or np.any(factors <= 0) or width not in core.M37_SPECTRAL_WIDTHS
            or not math.isfinite(spacing_hz) or spacing_hz <= 0
            or not math.isfinite(carrier_hz) or carrier_hz <= 0):
        raise ValueError('invalid attribution geometry')
    if original['epoch_zero_based'] != centered['epoch_zero_based']:
        raise ValueError('receiver epochs differ')
    if original['predicted_mid_mhz'] != centered['predicted_mid_mhz']:
        raise ValueError('receiver predictions differ')
    for sig in (original, centered):
        for k in ('predicted_mid_mhz', 'peak_frequency_mhz', 'peak_snr', 'offset_from_prediction_hz'):
            if not math.isfinite(sig[k]):
                raise ValueError('nonfinite receiver evidence')
        if (sig['peak_frequency_mhz']-sig['predicted_mid_mhz'])*1e6 != sig['offset_from_prediction_hz']:
            raise ValueError('inconsistent receiver frequency')
    midpoint = original['predicted_mid_mhz']*1e6
    if _predicted_midpoint_hz(carrier_hz, factors)/1e6 != original['predicted_mid_mhz']:
        raise ValueError('receiver prediction differs from the factor table')
    track = carrier_hz*factors
    padding = (width//2 + 0.5)*spacing_hz
    lo, hi = float(track.min()-midpoint-padding), float(track.max()-midpoint+padding)
    inside = lo <= original['offset_from_prediction_hz'] <= hi
    selected = copy.deepcopy(original if inside else centered)
    evidence = dict(epoch=original['epoch_zero_based'], original=original, centered=centered,
        track_filter_envelope_offsets_hz=[lo, hi], track_span_hz=float(np.ptp(track)),
        width_channels=width, native_channel_spacing_hz=spacing_hz,
        selected_measurement='local_peak' if inside else 'centered',
        peak_inside_envelope=inside)
    return selected, evidence


def attributed_signatures(records, original, centered, factors, grid):
    ids = {r['record_id'] for r in records}
    if len(ids) != len(records) or set(original) != ids or set(centered) != ids:
        raise ValueError('receiver inventories differ')
    selected, evidence = {}, {}
    for r in records:
        rid = r['record_id']; active = r['active_epochs_zero_based']
        old = {s['epoch_zero_based']: s for s in original[rid]}
        new = {s['epoch_zero_based']: s for s in centered[rid]}
        if (len(old) != len(original[rid]) or len(new) != len(centered[rid])
                or set(old) != set(active) or set(new) != set(active)):
            raise ValueError('active receiver epochs differ')
        selected[rid], evidence[rid] = [], []
        for e in active:
            sig, row = attribute_peak(old[e], new[e], float(grid.score_hz[r['proxy_carrier_index']]),
                factors[e][r['template_index']], r['spectral_width_channels'], abs(grid.channel_width_hz))
            selected[rid].append(sig); evidence[rid].append(row)
    return selected, dict(schema='m43ad-width-track-dual-receiver-v1',
        signatures_sha256=digest(selected), original_sha256=digest(original),
        centered_sha256=digest(centered), evidence_sha256=digest(evidence)), evidence


def aligned_profile(on_row, off_row, grid, q, width, on_factors, off_factors):
    """Compare profiles at equal predicted midpoint receiver frequencies.

    The stationary-receiver hypothesis fixes the coordinate transform BEFORE
    looking at scores. Linear interpolation samples the existing OFF proxy
    scores. No fitted lag, background subtraction, or injected truth is used.
    One full filter width each side includes response shoulders. The midpoint
    transform is not an exact equality of the ON/OFF integration tracks.
    """
    if (width not in core.M37_SPECTRAL_WIDTHS or type(q) is not int
            or not 0 <= q < grid.score_bin_count):
        raise ValueError('invalid profile coordinate')
    for a in (on_row, off_row):
        if a.dtype != np.dtype('<f4') or a.shape != (grid.support_bin_count,) or not np.isfinite(a).all():
            raise ValueError('complete finite float32 profile required')
    for f in (on_factors, off_factors):
        if np.ndim(f) != 1 or not len(f) or not np.isfinite(f).all() or np.any(np.asarray(f) <= 0):
            raise ValueError('finite positive factor rows required')
    center = grid.score_slice.start+q; radius = width
    first, stop = center-radius, center+radius+1
    if first < 0 or stop > grid.support_bin_count:
        return dict(complete=False, reason='ON_profile_outside_stored_support')
    # Use the inherited sequential midpoint reduction, not Python sum/np.mean.
    mean_off = _predicted_midpoint_hz(1., off_factors)
    frequencies = grid.support_hz[first:stop]
    receiver_hz = np.asarray([_predicted_midpoint_hz(float(f), on_factors) for f in frequencies])
    mapped_hz = receiver_hz/mean_off
    positions = (mapped_hz-grid.support_hz[0])/grid.channel_width_hz
    if np.any(positions < 0) or np.any(positions > grid.support_bin_count-1):
        return dict(complete=False, reason='aligned_OFF_profile_outside_stored_support',
            off_position_range=[float(positions.min()), float(positions.max())])
    left = np.floor(positions).astype(int); right = np.minimum(left+1, grid.support_bin_count-1)
    weights = positions-left
    on = on_row[first:stop].astype(float)
    off = (1-weights)*off_row[left].astype(float)+weights*off_row[right].astype(float)
    a = on-on.mean(); b = off-off.mean()
    denominator = float(np.linalg.norm(a)*np.linalg.norm(b))
    correlation = None if denominator == 0 else float(np.dot(a, b)/denominator)
    qhz = float(grid.score_hz[q])
    return dict(complete=True, radius_proxy_bins=radius, first_support_index=first,
        stop_support_index=stop, off_positions=positions.tolist(), off_left_indices=left.tolist(),
        off_right_indices=right.tolist(), interpolation_weights=weights.tolist(),
        on_values=on.tolist(), off_left_values=off_row[left].tolist(),
        off_right_values=off_row[right].tolist(), aligned_off_values=off.tolist(),
        correlation=correlation, correlation_floor=CORRELATION_FLOOR,
        center_shift_bins=float(positions[radius]-center),
        on_track_span_hz=float(np.ptp(qhz*np.asarray(on_factors))),
        off_track_span_hz=float(np.ptp(qhz*np.asarray(off_factors))))


def apply_controls(audit, store, grid, on_factors, off_factors, direct_check=None):
    evidence = []; cache = {}; profiles = {}; checked = set()
    for m in audit['members']:
        t, q, w = m['template_index'], m['proxy_carrier_index'], m['spectral_width_channels']
        if (t, w) not in cache:
            on, oid = store.get('on', t, w); off, fid = store.get('off', t, w)
            if oid != store.expected_ids['on', t, w] or fid != store.expected_ids['off', t, w]:
                raise ValueError('changed score identity')
            cache[t, w] = on, off
        on, off = cache[t, w]; active = m['active_epochs_zero_based']
        if not np.array_equal(on[:, grid.score_slice.start+q], np.asarray(m['epoch_values_at_proxy_carrier'], dtype='<f4')):
            raise ValueError('retained scores changed')
        prior = off_window(off, grid, q, w, active)
        remaining = remaining_evidence(m['epoch_values_at_proxy_carrier'], active)
        rows = []
        # Only potentially final candidates need the additional response query.
        eligible = m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']
        for i, e in enumerate(active):
            row = dict(epoch=e, off_maximum=prior['maxima'][i], vetoed=False,
                       queried=False, complete=True)
            if eligible and remaining['remaining_passed'] and prior['maxima'][i] >= 5.5:
                key = (t, q, w, e)
                if key not in profiles:
                    profiles[key] = aligned_profile(on[e], off[e], grid, q, w,
                        on_factors[e][t], off_factors[e][t])
                p = profiles[key]; row.update(queried=True, complete=p['complete'], profile=p)
                if p['complete']:
                    row['vetoed'] = p['correlation'] is not None and p['correlation'] >= CORRELATION_FLOOR
                    if direct_check is not None and (e, w) not in checked:
                        # Check center and both shoulders, including each OFF
                        # interpolation bracket, against direct native windows.
                        for j in (0, w, 2*w):
                            direct_check('on', e, t, w, p['first_support_index']+j, p['on_values'][j])
                            for side in ('left', 'right'):
                                direct_check('off', e, t, w, p[f'off_{side}_indices'][j], p[f'off_{side}_values'][j])
                        checked.add((e, w))
            rows.append(row)
        evidence.append(dict(record_id=m['record_id'], off_window=prior, remaining=remaining,
            aligned=rows, aligned_vetoed=any(r['vetoed'] for r in rows),
            aligned_complete=all(r['complete'] for r in rows)))
    outputs = {}
    for policy in POLICIES:
        a = copy.deepcopy(audit); a['confirmation_policy'] = policy
        for m, ev in zip(a['members'], evidence):
            reasons = []
            if policy != POLICIES[0] and not ev['remaining']['remaining_passed']:
                reasons.append('remaining_aggregate_below_5p5')
            if policy == POLICIES[1] and ev['off_window']['vetoed']:
                reasons.append('width_aware_OFF')
            if policy == POLICIES[2]:
                if ev['aligned_vetoed']: reasons.append('receiver_aligned_ON_OFF_agreement')
                if not ev['aligned_complete']: reasons.append('incomplete_aligned_OFF_evidence')
            m['m43ad_rejections'] = reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes'] = False
                m['physical_disposition'] = 'm43ad_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors'] = sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors'] = sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[policy] = a
    return outputs, evidence
