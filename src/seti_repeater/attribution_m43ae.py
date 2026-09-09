"""M43AE development rules: co-located OFF amplitude and profile evidence."""
import copy
import numpy as np
from . import search_v0p6 as core
from .attribution_m43ad import aligned_profile
from .confirmation_m43w import off_window
from .confirmation_m43x import remaining_evidence

HYPOTHESES = ('receiver_mean', 'candidate_track')
POLICY_HYPOTHESES = {
    'joint_receiver_off_aggregate': ('receiver_mean',),
    'joint_track_off_aggregate': ('candidate_track',),
    'joint_dual_off_aggregate': HYPOTHESES,
}
POLICIES = tuple(POLICY_HYPOTHESES)
SCORE_FLOOR = 5.5
CORRELATION_FLOOR = 0.8


def track_profile(on, off, grid, q, width):
    """Use exactly the same candidate carrier/template in both scan kinds."""
    if (type(q) is not int or not 0 <= q < grid.score_bin_count
            or width not in core.M37_SPECTRAL_WIDTHS):
        raise ValueError('invalid profile coordinate')
    for a in (on, off):
        if (a.dtype != np.dtype('<f4') or a.shape != (grid.support_bin_count,)
                or not np.isfinite(a).all()):
            raise ValueError('complete finite float32 profile required')
    center = grid.score_slice.start + q
    first, stop = center-width, center+width+1
    if first < 0 or stop > grid.support_bin_count:
        return dict(complete=False, reason='candidate_track_profile_outside_stored_support')
    a, b = on[first:stop].astype(float), off[first:stop].astype(float)
    ca, cb = a-a.mean(), b-b.mean()
    denominator = float(np.linalg.norm(ca)*np.linalg.norm(cb))
    correlation = None if denominator == 0 else float(np.dot(ca, cb)/denominator)
    positions = list(range(first, stop))
    return dict(complete=True, radius_proxy_bins=width,
        first_support_index=first, stop_support_index=stop,
        off_positions=[float(i) for i in positions], off_left_indices=positions,
        off_right_indices=positions, interpolation_weights=[0.]*len(positions),
        on_values=a.tolist(), off_left_values=b.tolist(), off_right_values=b.tolist(),
        aligned_off_values=b.tolist(), correlation=correlation,
        correlation_floor=CORRELATION_FLOOR, center_shift_bins=0.)


def response_profile(on, off, grid, q, width, on_factors, off_factors, hypothesis):
    if hypothesis == 'receiver_mean':
        p = aligned_profile(on, off, grid, q, width, on_factors, off_factors)
    elif hypothesis == 'candidate_track':
        p = track_profile(on, off, grid, q, width)
    else:
        raise ValueError('unknown response hypothesis')
    p.update(hypothesis=hypothesis, score_floor=SCORE_FLOOR,
             amplitude_and_shape_share_center=True, vetoed=False)
    if p['complete']:
        p['on_center_score'] = p['on_values'][width]
        p['off_center_score'] = p['aligned_off_values'][width]
        p['both_centers_above_floor'] = (p['on_center_score'] >= SCORE_FLOOR
                                        and p['off_center_score'] >= SCORE_FLOOR)
        p['vetoed'] = bool(p['both_centers_above_floor']
            and p['correlation'] is not None and p['correlation'] >= CORRELATION_FLOOR)
    return p


def apply_controls(audit, store, grid, on_factors, off_factors, direct_check=None):
    """Preserve geometry receiver decisions and add each named joint OFF rule.

    Both profiles are requested for every eligible member passing the unchanged
    remaining-epoch floor. The old OFF maximum is diagnostic only. No maximum,
    fitted lag, injected truth, or background subtraction selects a profile.
    """
    evidence, profiles, cache, checked = [], {}, {}, set()
    for m in audit['members']:
        t, q, w = m['template_index'], m['proxy_carrier_index'], m['spectral_width_channels']
        if (t, w) not in cache:
            on, oid = store.get('on', t, w); off, fid = store.get('off', t, w)
            if oid != store.expected_ids['on', t, w] or fid != store.expected_ids['off', t, w]:
                raise ValueError('changed score identity')
            cache[t, w] = on, off
        on, off = cache[t, w]
        if not np.array_equal(on[:, grid.score_slice.start+q],
                              np.asarray(m['epoch_values_at_proxy_carrier'], dtype='<f4')):
            raise ValueError('retained ON scores changed')
        remaining = remaining_evidence(m['epoch_values_at_proxy_carrier'], m['active_epochs_zero_based'])
        previous_off = off_window(off, grid, q, w, m['active_epochs_zero_based'])
        eligible = bool(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']
                        and remaining['remaining_passed'])
        rows = []
        for e in m['active_epochs_zero_based']:
            row = dict(epoch=e, queried=eligible, hypotheses={})
            for h in HYPOTHESES:
                query = dict(complete=True, vetoed=False, profile_id=None)
                if eligible:
                    pid = f'{t}:{q}:{w}:{e}:{h}'
                    if pid not in profiles:
                        p = response_profile(on[e], off[e], grid, q, w, on_factors[e][t], off_factors[e][t], h)
                        p.update(template=t, score_index=q, width=w, epoch=e)
                        profiles[pid] = p
                        if p['complete'] and direct_check is not None and (e, w, h) not in checked:
                            for j in (0, w, 2*w):
                                direct_check('on', e, t, w, p['first_support_index']+j, p['on_values'][j])
                                for side in ('left', 'right'):
                                    direct_check('off', e, t, w, p[f'off_{side}_indices'][j], p[f'off_{side}_values'][j])
                            checked.add((e, w, h))
                    p = profiles[pid]
                    query = dict(complete=p['complete'], vetoed=p['vetoed'], profile_id=pid)
                row['hypotheses'][h] = query
            rows.append(row)
        evidence.append(dict(record_id=m['record_id'], remaining=remaining,
            diagnostic_original_off_window=previous_off, epochs=rows))
    outputs = {}
    for policy, hypotheses in POLICY_HYPOTHESES.items():
        a = copy.deepcopy(audit); a['confirmation_policy'] = policy
        for m, ev in zip(a['members'], evidence):
            reasons = []
            if not ev['remaining']['remaining_passed']:
                reasons.append('remaining_aggregate_below_5p5')
            for h in hypotheses:
                if any(r['hypotheses'][h]['vetoed'] for r in ev['epochs']):
                    reasons.append('co_located_'+h+'_ON_OFF')
                if not all(r['hypotheses'][h]['complete'] for r in ev['epochs']):
                    reasons.append('incomplete_'+h+'_evidence')
            m['m43ae_rejections'] = reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes'] = False
                m['physical_disposition'] = 'm43ae_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors'] = sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors'] = sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[policy] = a
    return outputs, evidence, profiles


def evidence_complete(evidence, policy):
    return all(row['hypotheses'][h]['complete'] for ev in evidence
               for row in ev['epochs'] for h in POLICY_HYPOTHESES[policy])
