"""LS7H: closed-data morphology diagnosis at the unchanged LS7G cut.

The background-removed vectors use injection truth and cannot classify native
events. The one augmented bank is a development comparison, not qualification.
"""
from collections import Counter

import numpy as np

from .tess_joint_spatial import event_difference
from .tess_transfer import group_key


def shape_bank(aperture, families):
    """All in-stamp placements; fixed family/rotation/row-major order.

    Keep duplicate aperture projections and their physical placement labels.
    The triangle's four rotations cover its four possible diagonal corners.
    """
    aperture = np.asarray(aperture, dtype=bool)
    if aperture.ndim != 2 or min(aperture.shape) < 3 or aperture.sum() < 4:
        raise ValueError('invalid aperture')
    masks = {'cross3x3': np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]),
             'ring3x3': np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]),
             'triangle3x3': np.triu(np.ones((3, 3), dtype=int))}
    templates, labels = [], []
    for name in families:
        mask = masks[name]
        for rotation in (range(4) if name == 'triangle3x3' else [0]):
            rotated = np.rot90(mask, rotation)
            for y in range(aperture.shape[0]-2):
                for x in range(aperture.shape[1]-2):
                    p = np.zeros(aperture.shape)
                    p[y:y+3, x:x+3] = rotated
                    if p[aperture].sum():
                        templates.append(p[aperture])
                        labels.append(f'{name}_r{rotation}_{y}_{x}')
    return np.asarray(templates), labels


def integrated_pulse(seconds, phase, shape):
    centers = [phase-43.5, phase+43.5] if shape == 'doublet30sep87' else [phase]
    width = 30. if shape == 'doublet30sep87' else float(shape[3:])
    times = np.asarray(seconds)
    return sum(np.maximum(0., np.minimum(times+10, c+width/2)-np.maximum(times-10, c-width/2))/20 for c in centers)


def components(native, seconds, aperture, pattern, row):
    """Exact selected-window counterfactual; do not reselect a temporal window.

    clean = observed - native includes any response of the sideband median.
    pure is the event statistic of the injected cube by itself. Their difference
    explicitly measures nonadditivity; no linear median assumption is made.
    """
    pulse = integrated_pulse(seconds, row['phase_seconds'], row['shape'])
    addition = (row['pattern_scale']*pulse)[:, None, None]*np.asarray(pattern)
    if row['residual'] is not None:
        d = row['residual']; y, x = d['pixel_yx']
        addition[d['start']:d['stop'], y, x] += d['amplitude_e_per_s']
    lo, hi = row['best']['start'], row['best']['stop']
    sign = row['sign']
    background = sign*event_difference(native[:, aperture], lo, hi)[0]
    observed = sign*event_difference((native+addition)[:, aperture], lo, hi)[0]
    pure = sign*event_difference(addition[:, aperture], lo, hi)[0]
    return background, observed-background, pure, observed


def residual_map(covariance, template, fit):
    """Residual precision for the observed winner's active linear design.

    The selected pixel/template and source active set stay fixed. This is an
    algebraic attribution, not a counterfactual nonnegative refit.
    """
    c = np.asarray(covariance)
    n = len(c)
    columns = [np.ones(n)]
    if fit['sparse_pixel'] is not None:
        columns.append(np.eye(n)[:, fit['sparse_pixel']])
    if fit['amplitude'] > 0:
        columns.append(np.asarray(template))
    design = np.column_stack(columns)
    precision = np.linalg.inv(c)
    wd = precision@design
    q = precision-wd@np.linalg.solve(design.T@wd, wd.T)
    return (q+q.T)/2


def margin_components(background, clean, covariance, star_template, nuisance_template, star, nuisance, penalty):
    contrast = (residual_map(covariance, nuisance_template, nuisance)
                - residual_map(covariance, star_template, star))
    shape = float(clean@contrast@clean)
    baseline = float(background@contrast@background)
    cross = float(2*background@contrast@clean)
    offset = float(penalty*((nuisance['sparse_pixel'] is not None)-(star['sparse_pixel'] is not None)))
    return {'injected_shape': shape, 'native_background': baseline,
            'interaction': cross, 'penalty_difference': offset,
            'sum': shape+baseline+cross+offset}


def decision(row, star, margin, cfg):
    accepted = bool(row['screen_detected'] and star['amplitude_noise_score'] >= cfg['source_score_min']
                    and star['chi2']/star['residual_dof'] <= cfg['reduced_chi2_max']
                    and margin >= cfg['margin'])
    recovered = bool(accepted and not row['baseline_confounded'])
    if not row['screen_detected']:
        reason = 'temporal'
    elif star['amplitude_noise_score'] < cfg['source_score_min']:
        reason = 'source_score'
    elif star['chi2']/star['residual_dof'] > cfg['reduced_chi2_max']:
        reason = 'residual'
    elif margin < cfg['margin']:
        reason = 'nuisance_margin'
    elif row['baseline_confounded']:
        reason = 'confounded'
    else:
        reason = 'recovered'
    return {'accepted': accepted, 'recovered': recovered, 'recovery_path': reason,
            'nuisance_preferred_acceptance': bool(accepted and margin < 0)}


def summarize(rows, features, original_summary, cfg):
    rules = ['ls7g', 'augmented', 'plain_ablation']
    groups, core, backgrounds = [], [], []
    for key in sorted({group_key(r) for r in rows}, key=str):
        ids = [i for i, r in enumerate(rows) if group_key(r) == key]
        groups.append({'key': list(key), 'trials': len(ids), 'rules': {
            rule: {**{field: sum(features[i]['decisions'][rule][field] for i in ids)
                       for field in ['accepted', 'recovered', 'nuisance_preferred_acceptance']},
                   'recovery_paths': dict(Counter(features[i]['decisions'][rule]['recovery_path'] for i in ids))}
            for rule in rules}})
    for old in original_summary['core_cells']:
        key = old['key']
        ids = [i for i, r in enumerate(rows) if list(group_key(r)) == key]
        field = 'recovered' if old['signal'] else 'accepted'
        entry = {k: old[k] for k in ['key', 'trials', 'signal', 'limit']}
        entry['rules'] = {}
        for rule in rules:
            count = sum(features[i]['decisions'][rule][field] for i in ids)
            entry['rules'][rule] = {'count': count, 'pass': count >= old['limit'] if old['signal'] else count <= old['limit']}
        assert entry['rules']['ls7g'] == old['rules'][original_summary['primary_rule']]
        core.append(entry)
        for anchor in range(10):
            selected = [i for i in ids if rows[i]['anchor'] == anchor]
            backgrounds.append({'anchor': anchor, 'key': key, 'trials': len(selected), 'rules': {
                rule: sum(features[i]['decisions'][rule][field] for i in selected) for rule in rules}})
    bright = [i for i, r in enumerate(rows) if r['suite'] == 'base' and r['kind'] == 'stellar'
              and r.get('amplitude_fraction') == .1 and r['shape'] != 'doublet30sep87']
    nulls = [i for i, r in enumerate(rows) if r['suite'] == 'base' and r['kind'] == 'null']
    signals = [i for i, r in enumerate(rows) if r['kind'] in ('stellar', 'off_profile')]
    physical = [i for i, r in enumerate(rows) if r['suite'] == 'bounded_pointing' and r['screen_detected']]
    rule_gates = {}
    for rule in rules:
        g = {'all_core_cells': all(c['rules'][rule]['pass'] for c in core),
             'all_target_strengths_matched': all(r['strength_matched'] for r in rows if r['tuning'] is not None),
             'ten_percent_single_recovery': sum(features[i]['decisions'][rule]['recovered'] for i in bright) >= 54,
             'no_base_null_acceptance': not any(features[i]['decisions'][rule]['accepted'] for i in nulls),
             'confounding_at_most_20_percent': sum(rows[i]['baseline_confounded'] for i in signals) <= .2*len(signals),
             'bounded_pointing_screened_acceptance': bool(physical) and sum(features[i]['decisions'][rule]['accepted'] for i in physical) <= .05*len(physical)}
        rule_gates[rule] = {'pass': all(g.values()), 'gates': g}
    assert rule_gates['ls7g'] == original_summary['rules'][original_summary['primary_rule']]
    lost = [rows[i]['trial_id'] for i in signals if features[i]['decisions']['ls7g']['recovered']
            and not features[i]['decisions']['augmented']['recovered']]
    newly_rejected = [r['trial_id'] for r, f in zip(rows, features) if r['kind'] not in ('stellar', 'off_profile')
                      and f['decisions']['ls7g']['accepted'] and not f['decisions']['augmented']['accepted']]
    focus = []
    for suite, kind, target in cfg['focus_cells']:
        ids = [i for i, r in enumerate(rows) if [r['suite'], r['kind'], r.get('target_score')] == [suite, kind, target]]
        accepted = [i for i in ids if features[i]['decisions']['ls7g']['accepted']]
        focus.append({'key': [suite, kind, target], 'trials': len(ids), 'accepted_ids': [rows[i]['trial_id'] for i in accepted],
                      'augmented_accepted_ids': [rows[i]['trial_id'] for i in ids if features[i]['decisions']['augmented']['accepted']],
                      'clean_margin_rejects_ids': [rows[i]['trial_id'] for i in accepted if features[i]['clean']['margin_broad'] < cfg['margin']],
                      'star_sparse_ids': [rows[i]['trial_id'] for i in accepted if rows[i]['methods']['covariance_sparse']['star']['sparse_pixel'] is not None],
                      'plain_accepted_ids': [rows[i]['trial_id'] for i in ids if features[i]['decisions']['plain_ablation']['accepted']]})
    return {'groups': groups, 'core_cells': core, 'per_background': backgrounds, 'rules': rule_gates,
            'focus_cells': focus, 'lost_stellar_ids': lost, 'newly_rejected_nonstellar_ids': newly_rejected,
            'signal_recovery_paths': {rule: dict(Counter(features[i]['decisions'][rule]['recovery_path'] for i in signals)) for rule in rules}}
