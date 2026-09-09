"""Uncalibrated response measurements for the proposed M43AF study.

No new detector decision or probability is produced. No truth label or fitted
lag enters the measurements. Coordinates come from the fixed M43AE mappings.
"""
import math

import numpy as np

from .confirmation_m43x import remaining_evidence
from .search_v0p6 import M37_ACTIVITY_SUBSETS, M37_SPECTRAL_WIDTHS

HYPOTHESES = ('receiver_mean', 'candidate_track')


def _vector(values):
    a = np.asarray(values, dtype=np.float64)
    if a.ndim != 1 or len(a) < 3 or not np.isfinite(a).all():
        raise ValueError('a complete finite response vector is required')
    return a


def projection(template, response):
    """Signed projection onto the centered, unit-norm template, at zero lag.

    This is in input score units, not sigma units. Correlated profile samples
    require empirical calibration; neither width nor epoch count is an
    independent-sample count.
    """
    a, b = _vector(template), _vector(response)
    if a.shape != b.shape:
        raise ValueError('profile lengths differ')
    ca, cb = a - a.mean(), b - b.mean()
    norm_a, norm_b = float(np.linalg.norm(ca)), float(np.linalg.norm(cb))
    if not math.isfinite(norm_a) or not math.isfinite(norm_b):
        raise ValueError('nonfinite centered norm')
    if norm_a == 0:
        return dict(defined=False, reason='constant_template', projection=None,
                    correlation=None, template_norm=0., response_norm=norm_b)
    value = float(np.dot(ca / norm_a, cb))
    if not math.isfinite(value):
        raise ValueError('nonfinite projection')
    return dict(defined=True, reason=None, projection=value,
                correlation=None if norm_b == 0 else value / norm_b,
                template_norm=norm_a, response_norm=norm_b)


def query_inventory(members):
    """Request both complete mappings BEFORE the remaining-epoch requirement.

    Keeping the M43AE post-confirmation query selection would conceal exactly
    the weak epochs this study must measure. Prior geometry and rank selection
    are retained and must also be reproduced by a future null calibration.
    """
    links, queries, seen = [], {}, set()
    for m in members:
        rid = m['record_id']
        if rid in seen:
            raise ValueError('duplicate member identity')
        seen.add(rid)
        active = tuple(m['active_epochs_zero_based'])
        remaining = remaining_evidence(m['epoch_values_at_proxy_carrier'], active)
        eligible = bool(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'])
        member_queries = []
        if eligible:
            t, q, w = (m[k] for k in ('template_index', 'proxy_carrier_index',
                                      'spectral_width_channels'))
            if type(t) is not int or t < 0 or type(q) is not int or q < 0:
                raise ValueError('invalid member coordinate')
            if type(w) is not int or w not in M37_SPECTRAL_WIDTHS:
                raise ValueError('invalid spectral width')
            for e in active:
                for h in HYPOTHESES:
                    pid = f'{t}:{q}:{w}:{e}:{h}'
                    queries[pid] = dict(template=t, score_index=q, width=w,
                                        epoch=e, hypothesis=h)
                    member_queries.append(pid)
        links.append(dict(record_id=rid, eligible_before_remaining=eligible,
                          old_remaining=remaining, profile_ids=member_queries))
    return links, queries


def measure_member(member, profiles):
    """Measure OFF shape amplitude and cross-epoch ON support without cuts.

    Missing profiles, incomplete mappings, and constant templates remain
    distinct. No partial-epoch average is substituted for missing evidence.
    """
    active = tuple(member['active_epochs_zero_based'])
    if active not in M37_ACTIVITY_SUBSETS:
        raise ValueError('canonical activity subset required')
    values = np.asarray(member['epoch_values_at_proxy_carrier'], dtype=np.float64)
    remaining = remaining_evidence(values, active)
    strongest = remaining['excluded_epoch']
    t, q, w = (member[k] for k in ('template_index', 'proxy_carrier_index',
                                  'spectral_width_channels'))
    if type(w) is not int or w not in M37_SPECTRAL_WIDTHS:
        raise ValueError('invalid spectral width')
    report = dict(record_id=member['record_id'], old_remaining=remaining,
                  spectral_width=w, active_epochs=list(active), off={}, on=None)
    by_hypothesis = {}
    for h in HYPOTHESES:
        epoch_rows, arrays = [], {}
        for e in active:
            pid = f'{t}:{q}:{w}:{e}:{h}'
            p = profiles.get(pid)
            row = dict(epoch=e, profile_id=pid, available=p is not None,
                       complete=False, measurement=None)
            if p is not None:
                if any(p[k] != v for k, v in dict(template=t, score_index=q,
                           width=w, epoch=e, hypothesis=h).items()):
                    raise ValueError('profile identity mismatch')
                row['complete'] = p['complete'] is True
                if row['complete']:
                    a, b = _vector(p['on_values']), _vector(p['aligned_off_values'])
                    if len(a) != 2*w+1 or len(b) != len(a):
                        raise ValueError('incomplete response span')
                    if a[w] != values[e]:
                        raise ValueError('ON profile center differs from retained score')
                    arrays[e] = (a, b)
                    row.update(measurement=projection(a, b),
                               on_center=float(a[w]), off_center=float(b[w]))
            epoch_rows.append(row)
        complete = all(r['complete'] for r in epoch_rows)
        defined = complete and all(r['measurement']['defined'] for r in epoch_rows)
        report['off'][h] = dict(epochs=epoch_rows, complete=complete, defined=defined,
            projection_mean=(float(np.mean([r['measurement']['projection'] for r in epoch_rows]))
                             if defined else None))
        by_hypothesis[h] = arrays
    # ON coordinates are identical for the two OFF hypotheses. Use the direct
    # candidate-track copy; the receiver-mean copy must agree wherever present.
    on_arrays = by_hypothesis['candidate_track']
    for e in set(on_arrays) & set(by_hypothesis['receiver_mean']):
        if not np.array_equal(on_arrays[e][0], by_hypothesis['receiver_mean'][e][0]):
            raise ValueError('hypotheses disagree on the same ON samples')
    complete = all(e in on_arrays for e in active)
    on_rows = []
    if complete:
        template = on_arrays[strongest][0]
        for e in remaining['remaining_epochs']:
            on_rows.append(dict(epoch=e, **projection(template, on_arrays[e][0])))
    defined = complete and all(r['defined'] for r in on_rows)
    report['on'] = dict(complete=complete, defined=defined,
        template_epoch=strongest, remaining_epochs=remaining['remaining_epochs'],
        epochs=on_rows, projection_mean=(float(np.mean([r['projection'] for r in on_rows]))
                                       if defined else None))
    return report
