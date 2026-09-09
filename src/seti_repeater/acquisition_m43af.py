"""M43AF pre-confirmation acquisition adapter; not an execution certificate.

The caller must verify native source/anchor/overlay identities. This module
has no truth labels, fitted lag, detector execution or calibration binding.
"""
import copy

import numpy as np

from .attribution_m43ae import response_profile
from .response_m43af import query_inventory, measure_member


def acquire(audit, store, grid, on_factors, off_factors,
            reused_profiles=None, direct_check=None):
    members = audit['members']
    links, queries = query_inventory(members)
    old = {} if reused_profiles is None else reused_profiles
    cache, profiles, reused, checked = {}, {}, [], set()

    def arrays(t, w):
        if (t, w) not in cache:
            on, oid = store.get('on', t, w)
            off, fid = store.get('off', t, w)
            if oid != store.expected_ids['on', t, w] or fid != store.expected_ids['off', t, w]:
                raise ValueError('changed score identity')
            cache[t, w] = on, off
        return cache[t, w]

    # Validate retained scores even for members outside query eligibility.
    for m in members:
        t, q, w = (m[k] for k in ('template_index', 'proxy_carrier_index',
                                  'spectral_width_channels'))
        on, _ = arrays(t, w)
        if not np.array_equal(on[:, grid.score_slice.start+q].astype(float),
                              np.asarray(m['epoch_values_at_proxy_carrier'], dtype=float)):
            raise ValueError('retained ON scores changed')

    for pid, query in queries.items():
        t, q, w, e, h = (query[k] for k in
                         ('template', 'score_index', 'width', 'epoch', 'hypothesis'))
        on, off = arrays(t, w)
        measured = response_profile(on[e], off[e], grid, q, w,
                                    on_factors[e][t], off_factors[e][t], h)
        measured.update(template=t, score_index=q, width=w, epoch=e)
        if pid in old:
            previous = old[pid]
            if any(previous.get(k) != v for k, v in query.items()):
                raise ValueError('reused profile identity mismatch')
            # Old neutral links are never a profile. Incomplete real profiles
            # must also reproduce exactly, but do not count as complete reuse.
            if previous != measured:
                raise ValueError('reused profile differs from current native overlay')
            if previous['complete'] is True:
                reused.append(pid)
            measured = copy.deepcopy(previous)
        profiles[pid] = measured
        if measured['complete'] and direct_check is not None and (e, w, h) not in checked:
            for j in (0, w, 2*w):
                direct_check('on', e, t, w,
                             measured['first_support_index']+j, measured['on_values'][j])
                for side in ('left', 'right'):
                    direct_check('off', e, t, w,
                                 measured[f'off_{side}_indices'][j],
                                 measured[f'off_{side}_values'][j])
            checked.add((e, w, h))

    measurements = [
        measure_member(m, profiles) for m, link in zip(members, links)
        if link['eligible_before_remaining']
    ]
    counts = dict(
        retained_members=len(members),
        eligible_before_remaining=len(measurements),
        eligible_passing_old_remaining=sum(
            link['eligible_before_remaining'] and link['old_remaining']['remaining_passed']
            for link in links),
        requested_unique_profiles=len(queries),
        reused_complete_profiles=len(reused),
        newly_acquired_complete_profiles=sum(p['complete'] for p in profiles.values())-len(reused),
        incomplete_profiles=sum(not p['complete'] for p in profiles.values()),
        member_profile_links=sum(len(link['profile_ids']) for link in links),
        undefined_member_measurements=sum(
            not r['on']['defined'] or any(not v['defined'] for v in r['off'].values())
            for r in measurements))
    return dict(links=links, profiles=profiles, reused_complete_profile_ids=reused,
                measurements=measurements, counts=counts)
