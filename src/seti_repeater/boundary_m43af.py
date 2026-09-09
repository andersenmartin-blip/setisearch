"""Draft deterministic joint boundary; no calibration or adoption certificate.

Training labels belong here, outside raw measurement/acquisition. The caller
must validate the frozen case inventory, provenance and joint null pipeline.
"""
import math

from .response_m43af import HYPOTHESES

POLICY = 'm43af_joint_profile'
REFERENCES = ('neighbor9', 'centered_receiver_off_match_aggregate')


def coordinates(measurement):
    """Algebraic length scaling, NOT independent-sample/SNR normalization."""
    if (not measurement['on']['complete'] or not measurement['on']['defined']
            or any(not measurement['off'][h]['complete'] or not measurement['off'][h]['defined']
                   for h in HYPOTHESES)):
        return None
    scale = math.sqrt(2*measurement['spectral_width']+1)
    x = measurement['on']['projection_mean']/scale
    y = max(measurement['off'][h]['projection_mean'] for h in HYPOTHESES)/scale
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError('nonfinite joint coordinate')
    return dict(on=x, off=y)


def accepts(coordinate, boundary):
    if coordinate is None:
        return False
    lower, upper = boundary['on_lower'], boundary['off_upper']
    # None explicitly denotes no bound; it is never a missing measurement.
    return ((lower is None or coordinate['on'] >= lower)
            and (upper is None or coordinate['off'] < upper))


def higher_grid(values):
    """33 fixed order-statistic quantiles; no numpy version dependence."""
    ordered = sorted(values)
    if not ordered or not all(math.isfinite(v) for v in ordered):
        raise ValueError('finite nonempty training coordinate list required')
    return sorted({ordered[(i*(len(ordered)-1)+31)//32] for i in range(33)})


def case_outcome(case, boundary):
    surviving = [r['record_id'] for r in case['members'] if accepts(r['coordinate'], boundary)]
    associated = set(case['associated_record_ids'])
    return dict(name=case['name'], signal_present=case['signal_present'],
                recovered=bool(associated.intersection(surviving)),
                final_members=len(surviving), surviving_record_ids=surviving)


def fit(training_cases, baseline, null_cases=()):
    """Fit only an explicitly validated training panel, with a failure outcome.

    Input members must be exactly the pre-remaining geometry/rank inventory.
    Reference outcomes/association labels never enter the raw coordinates.
    """
    if not training_cases or any(c['panel'] != 'training' for c in training_cases):
        raise ValueError('only training cases may select a boundary')
    if baseline['panel'] != 'baseline' or baseline['signal_present']:
        raise ValueError('separate uninjected baseline required')
    if any(c['panel'] != 'null_training' or c['signal_present'] for c in null_cases):
        raise ValueError('only uninjected training nulls may constrain the fit')
    all_cases = training_cases+[baseline]+list(null_cases)
    if len({c['name'] for c in all_cases}) != len(all_cases):
        raise ValueError('duplicate case identity')
    for c in all_cases:
        if len({m['record_id'] for m in c['members']}) != len(c['members']):
            raise ValueError('duplicate member identity')
        for r in c['members']:
            v = r['coordinate']
            if v is not None and not all(math.isfinite(v[k]) for k in ('on', 'off')):
                raise ValueError('nonfinite joint coordinate')
    signals = [c for c in training_cases if c['signal_present']]
    controls = [c for c in training_cases if not c['signal_present']]
    if not signals or not controls:
        raise ValueError('both signal and control cases required')
    required = {
        c['name'] for c in signals
        if any(c['reference_recovered'][p] for p in REFERENCES)
    }
    if not required:
        raise ValueError('nonzero reference signal recovery required')
    incomplete = [c['name'] for c in all_cases if
                  not c['complete'] or any(r['coordinate'] is None for r in c['members'])]
    if incomplete:
        return dict(policy=POLICY, feasible=False, boundary=None, grid=[],
                    reason='incomplete_or_undefined_evidence', affected_cases=incomplete)
    values = [r['coordinate'] for c in training_cases for r in c['members']]
    if not values:
        return dict(policy=POLICY, feasible=False, boundary=None, grid=[],
                    reason='no_training_members', affected_cases=[])
    lower = [None]+higher_grid([r['on'] for r in values])
    upper = higher_grid([r['off'] for r in values])+[None]
    ledger, candidates = [], []
    for a in lower:
        for b in upper:
            boundary = dict(on_lower=a, off_upper=b)
            rows = [case_outcome(c, boundary) for c in all_cases]
            recovered = {r['name'] for r in rows if r['signal_present'] and r['recovered']}
            leaks = [r['name'] for r in rows if not r['signal_present'] and r['final_members']]
            losses = sorted(required-recovered)
            feasible = not losses and not leaks
            entry = dict(boundary=boundary, feasible=feasible,
                         recovered_signal_cases=len(recovered),
                         required_signal_losses=losses, leaking_control_or_baseline_cases=leaks,
                         outcomes=rows)
            ledger.append(entry)
            if feasible:
                # Max recovery, then most permissive lower/upper limits.
                key = (-len(recovered), -math.inf if a is None else a,
                       -math.inf if b is None else -b)
                candidates.append((key, boundary))
    chosen = min(candidates, key=lambda item:item[0])[1] if candidates else None
    return dict(policy=POLICY, feasible=chosen is not None, boundary=chosen,
                reason=None if chosen is not None else 'no_feasible_joint_boundary',
                affected_cases=[], required_signal_cases=sorted(required), grid=ledger)
