"""Independent scalar measurement checks, plus the existing coordinate oracle.

This draft audits supplied evidence; it does not acquire native data or claim a
completed M43AF study. The release audit/runner must additionally verify seals,
pin inventories, native identities, query completeness and training/holdout use.
"""
import math

from m43ae_audit import profile_oracle

HYPOTHESES = ('receiver_mean', 'candidate_track')


def scalar_projection(a, b):
    if len(a) != len(b) or len(a) < 3:
        raise ValueError('incompatible vectors')
    if not all(math.isfinite(float(x)) for x in list(a)+list(b)):
        raise ValueError('nonfinite vector')
    ca = [float(x)-math.fsum(a)/len(a) for x in a]
    cb = [float(x)-math.fsum(b)/len(b) for x in b]
    na = math.sqrt(math.fsum(x*x for x in ca))
    nb = math.sqrt(math.fsum(x*x for x in cb))
    p = None if na == 0 else math.fsum((x/na)*y for x, y in zip(ca, cb))
    return dict(defined=na != 0, projection=p, template_norm=na, response_norm=nb,
                correlation=None if p is None or nb == 0 else p/nb)


def close(actual, expected):
    if actual is None or expected is None:
        assert actual is expected
    else:
        assert math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-11)


def check_projection(actual, expected):
    assert actual['defined'] == expected['defined']
    for k in ('projection', 'template_norm', 'response_norm', 'correlation'):
        close(actual[k], expected[k])


def audit_remaining(member, actual):
    active = member['active_epochs_zero_based']
    values = member['epoch_values_at_proxy_carrier']
    strongest = min(active, key=lambda e:(-values[e], e))
    others = [e for e in active if e != strongest]
    total = math.fsum(values[e] for e in others)
    score = total/math.sqrt(len(others))
    assert actual['active_epochs'] == active and actual['excluded_epoch'] == strongest
    assert actual['remaining_epochs'] == others
    close(actual['remaining_sum'], total)
    close(actual['remaining_score'], score)
    assert actual['remaining_passed'] == (score >= 5.5)
    assert actual['minimum_active_ON_score'] == min(values[e] for e in active)
    assert actual['active_confirmation_passed'] == all(values[e] >= 5.5 for e in active)


def audit_member(member, profiles, measured):
    audit_remaining(member, measured['old_remaining'])
    active = member['active_epochs_zero_based']
    values = member['epoch_values_at_proxy_carrier']
    strongest = min(active, key=lambda e:(-values[e], e))
    others = [e for e in active if e != strongest]
    assert measured['record_id'] == member['record_id']
    assert measured['active_epochs'] == active
    assert measured['spectral_width'] == member['spectral_width_channels']
    assert measured['on']['template_epoch'] == strongest
    assert measured['on']['remaining_epochs'] == others
    t, q, w = (member[k] for k in ('template_index', 'proxy_carrier_index', 'spectral_width_channels'))
    arrays = {}
    for h in HYPOTHESES:
        rows = measured['off'][h]['epochs']
        assert len(rows) == len(active)
        samples, defined = [], True
        complete = True
        for e, row in zip(active, rows):
            pid = f'{t}:{q}:{w}:{e}:{h}'
            p = profiles.get(pid)
            assert row['epoch'] == e and row['profile_id'] == pid
            assert row['available'] == (p is not None)
            is_complete = p is not None and p['complete'] is True
            assert row['complete'] == is_complete
            complete = complete and is_complete
            if is_complete:
                assert all(p[k] == v for k, v in dict(template=t, score_index=q,
                    width=w, epoch=e, hypothesis=h).items())
                a, b = p['on_values'], p['aligned_off_values']
                assert len(a) == len(b) == 2*w+1 and a[w] == values[e]
                arrays[h, e] = a
                expected = scalar_projection(a, b)
                check_projection(row['measurement'], expected)
                assert row['on_center'] == a[w] and row['off_center'] == b[w]
                defined = defined and expected['defined']
                samples.append(expected['projection'])
            else:
                assert row['measurement'] is None
                defined = False
        assert measured['off'][h]['complete'] == complete
        assert measured['off'][h]['defined'] == defined
        close(measured['off'][h]['projection_mean'],
              math.fsum(samples)/len(samples) if defined else None)
    for e in active:
        if ('receiver_mean', e) in arrays and ('candidate_track', e) in arrays:
            assert arrays['receiver_mean', e] == arrays['candidate_track', e]
    complete = all(('candidate_track', e) in arrays for e in active)
    expected_rows = []
    if complete:
        expected_rows = [scalar_projection(arrays['candidate_track', strongest],
                                          arrays['candidate_track', e]) for e in others]
    defined = complete and all(r['defined'] for r in expected_rows)
    assert measured['on']['complete'] == complete
    assert measured['on']['defined'] == defined
    assert len(measured['on']['epochs']) == len(expected_rows)
    for e, actual, expected in zip(others, measured['on']['epochs'], expected_rows):
        assert actual['epoch'] == e
        check_projection(actual, expected)
    close(measured['on']['projection_mean'],
          math.fsum(r['projection'] for r in expected_rows)/len(expected_rows) if defined else None)
    return True


def audit_acquisition(audit, evidence, grid, on_factors, off_factors):
    members = audit['members']
    links = evidence['links']
    assert len(links) == len(members)
    profiles = evidence['profiles']
    expected_queries, eligible = set(), []
    for m, link in zip(members, links):
        assert m['record_id'] == link['record_id']
        audit_remaining(m, link['old_remaining'])
        is_eligible = bool(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'])
        assert link['eligible_before_remaining'] == is_eligible
        pids = []
        if is_eligible:
            eligible.append(m)
            for e in m['active_epochs_zero_based']:
                for h in HYPOTHESES:
                    pid = '{}:{}:{}:{}:{}'.format(m['template_index'], m['proxy_carrier_index'],
                        m['spectral_width_channels'], e, h)
                    pids.append(pid)
                    expected_queries.add(pid)
        assert link['profile_ids'] == pids
    assert set(profiles) == expected_queries
    for p in profiles.values():
        profile_oracle(p, grid, on_factors, off_factors)
    assert len(eligible) == len(evidence['measurements'])
    for m, measured in zip(eligible, evidence['measurements']):
        audit_member(m, profiles, measured)
    return dict(eligible_members=len(eligible), profiles=len(profiles),
                scalar_relative_tolerance=1e-11, scalar_absolute_tolerance=1e-11)
