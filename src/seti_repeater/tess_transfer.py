"""LS7G fixed transfer utilities. No threshold optimization on sector 29."""
from itertools import product
import numpy as np

from .light_sail_tess import pulse_shape
from .light_sail_tess_v2 import shifted_profile, pointing_delta
from .light_sail_tess_v3 import (
    empirical_profile, matched_window, nuisance_pattern, strength_amplitude, trial_specs,
)
from .tess_joint_spatial import event_difference, training_covariance, template_bank, FitBank
from .tess_separation import rectangle_bank


def spatial_mask(kind):
    masks = {'block3x3': np.ones((3, 3)), 'row1x5': np.ones((1, 5)),
             'column5x1': np.ones((5, 1)),
             'cross3x3': np.array([[0., 1., 0.], [1., 1., 1.], [0., 1., 0.]]),
             'ring3x3': np.array([[1., 1., 1.], [1., 0., 1.], [1., 1., 1.]]),
             'triangle3x3': np.triu(np.ones((3, 3)))}
    return masks[kind].copy()


def placed_pattern(kind, profile, aperture):
    mask = spatial_mask(kind)
    h, w = mask.shape
    choices = [(float(np.sum(profile[y:y+h, x:x+w]*mask)), y, x)
               for y in range(profile.shape[0]-h+1) for x in range(profile.shape[1]-w+1)]
    _, y, x = max(choices, key=lambda item: item[0])
    p = np.zeros(profile.shape)
    p[y:y+h, x:x+w] = mask
    norm = float(p[aperture].sum())
    if norm <= 0:
        raise ValueError('no aperture overlap for declared control')
    return p/norm, [int(y), int(x)]


def decisions(star, nuisance, detected, confounded, thresholds):
    margin = nuisance['objective']-star['objective']
    eligible = bool(detected and star['amplitude_noise_score'] >= 5
                    and star['chi2']/star['residual_dof'] <= 2)
    return {str(t): {'accepted': bool(eligible and margin >= t),
                     'recovered': bool(eligible and margin >= t and not confounded),
                     'nuisance_preferred_acceptance': bool(eligible and t <= margin < 0)}
            for t in thresholds}


def expected_suites():
    return {'base': 1460, 'sparse_stress': 1040, 'known_extended': 360,
            'unmodeled_shapes': 360, 'bounded_pointing': 320}


def evaluate_contexts(native, seconds, aperture, sigmas, cfg, basecfg, progress=None):
    """Return complete trials, covariance training, models and input patterns."""
    if native.shape != (10, 401, 11, 11) or seconds.shape != (10, 401) or aperture.sum() != 21:
        raise ValueError('wrong frozen sector-29 dimensions')
    if not np.all(np.isfinite(native[:, :, aperture])) or aperture[0, 0]:
        raise ValueError('invalid aperture data or exterior stress pixel')
    contexts, training = {}, []
    for a in range(10):
        reference = np.median(native[a], axis=0)
        profile = empirical_profile(reference, aperture)
        contexts[a] = {'reference': reference, 'profile': profile,
                       'flux': native[a][:, aperture].sum(axis=1),
                       'level': float(np.median(native[a][:, aperture].sum(axis=1)))}
        for width, start in product(basecfg['box_samples'], cfg['training_starts']):
            d, _ = event_difference(native[a][:, aperture], start, start+width)
            training.append({'sample_id': f'a{a:02d}_w{width}_s{start}', 'anchor': a,
                             'width': width, 'start': start, 'sigma': float(sigmas[a]),
                             'normalized_delta': (d/sigmas[a]).tolist()})
    covariances, folds = {}, []
    for a, width in product(range(10), basecfg['box_samples']):
        c, fold = training_covariance(training, a, width, cfg['shrinkage'])
        folds.append(fold)
        covariances[a, width] = c*sigmas[a]**2
    extended, extended_labels = rectangle_bank(np.argwhere(aperture), [11, 11], cfg['rectangle_shapes'])
    rows, models, patterns, banks, tuning_cache = [], {}, {}, {}, {}

    def get_pattern(a, kind, shift=None):
        shift = [0., 0.] if shift is None else shift
        key = f'a{a}/{kind}/{shift[0]:g},{shift[1]:g}'
        if key not in patterns:
            ctx, corner = contexts[a], None
            if kind in ('stellar', 'off_profile', 'null'):
                p = shifted_profile(ctx['profile'], aperture, shift)
                sign, norm = 1, 1.
            elif kind in cfg['known_extended']+cfg['unmodeled_shapes']:
                p, corner = placed_pattern(kind, ctx['profile'], aperture)
                sign, norm = 1, 1.
            elif kind == 'bounded_pointing':
                p = pointing_delta(ctx['reference'], shift)
                norm = abs(float(p[aperture].sum()))
                sign = 1 if p[aperture].sum() >= 0 else -1
            else:
                p, sign, norm = nuisance_pattern(kind, ctx['reference'], ctx['profile'], aperture, shift)
            patterns[key] = {'pattern_id': key, 'anchor': a, 'kind': kind, 'shift_yx': shift,
                             'corner_yx': corner, 'sign': sign, 'original_projection_magnitude': norm,
                             'vector': p.tolist()}
        return patterns[key]

    def strength(a, pulse, centers, phase, shape, target, sign):
        key = (a, phase, shape, target, sign)
        if key not in tuning_cache:
            tuning_cache[key] = strength_amplitude(contexts[a]['flux'], pulse, seconds[a], centers,
                                                    sigmas[a], target, basecfg, sign)
        return tuning_cache[key]

    def append(a, pattern, scale, phase, shape, spec, tuning=None, residual=None):
        pulse, centers = pulse_shape(seconds[a], phase, shape, 20.)
        p = np.asarray(pattern['vector'])
        injected = native[a]+(scale*pulse)[:, None, None]*p
        if residual is not None:
            y, x = residual['pixel_yx']
            injected[residual['start']:residual['stop'], y, x] += residual['amplitude_e_per_s']
        sign = pattern['sign']
        best = matched_window(injected[:, aperture].sum(axis=1), seconds[a], centers, sigmas[a], basecfg, sign)
        original = matched_window(contexts[a]['flux'], seconds[a], centers, sigmas[a], basecfg, sign)
        detected, confounded = best['score'] >= 8., original['score'] >= 8.
        lo, hi = best['start'], best['stop']
        key = f'a{a}_s{lo}_e{hi}'
        if key not in banks:
            side = np.concatenate([native[a, lo-60:lo-5], native[a, hi+5:hi+60]])
            ref = np.median(side, axis=0)
            stars, old, labels = template_bank(ref, aperture, basecfg['spatial']['fit_shifts_yx'],
                                               basecfg['spatial']['pointing_template_shifts_yx'])
            broad, labels_broad = np.vstack([old, extended]), labels+extended_labels
            c = covariances[a, hi-lo]
            models[key] = {'model_id': key, 'anchor': a, 'start': lo, 'stop': hi,
                           'covariance': c.tolist(), 'star_templates': stars.tolist(),
                           'original_templates': old.tolist(), 'original_labels': labels,
                           'broad_templates': broad.tolist(), 'broad_labels': labels_broad}
            banks[key] = {method: (FitBank(c, stars, method == 'covariance_sparse', 9.),
                                    FitBank(c, old, method == 'covariance_sparse', 9.),
                                    FitBank(c, broad, method == 'covariance_sparse', 9.)) for method in cfg['methods']}
        event, _ = event_difference(injected[:, aperture], lo, hi)
        event *= sign
        methods = {}
        for method, (star_bank, old_bank, broad_bank) in banks[key].items():
            star, old, broad = star_bank.fit(event), old_bank.fit(event), broad_bank.fit(event)
            if broad['objective'] > old['objective']+1e-7:
                raise AssertionError('enlarging bank raised minimum objective')
            methods[method] = {'star': star, 'original_nuisance': old, 'broad_nuisance': broad,
                               'margins': {'original': old['objective']-star['objective'], 'broad': broad['objective']-star['objective']},
                               'decisions': {bank: decisions(star, nuisance, detected, confounded, cfg['thresholds'])
                                             for bank, nuisance in [('original', old), ('broad', broad)]}}
        row = {**spec, 'anchor': a, 'phase_seconds': phase, 'shape': shape, 'pattern_id': pattern['pattern_id'],
               'pattern_scale': float(scale), 'aperture_amplitude_e_per_s': float(scale*p[aperture].sum()),
               'sign': sign, 'tuning': tuning, 'residual': residual, 'best': best, 'native_best': original,
               'screen_detected': bool(detected), 'baseline_confounded': bool(confounded),
               'model_id': key, 'event_vector': event.tolist(), 'methods': methods,
               'strength_matched': None if tuning is None else bool(tuning['matched'] and abs(best['score']-spec['target_score']) <= .01)}
        rows.append(row)
        return row

    for a in range(10):
        for phase in basecfg['injections']['phases_seconds']:
            for spec in trial_specs(basecfg):
                pattern = get_pattern(a, spec['kind'], spec['shift_yx'])
                pulse, centers = pulse_shape(seconds[a], phase, spec['shape'], 20.)
                tuning = None
                if spec['group'] == 'matched':
                    tuning = strength(a, pulse, centers, phase, spec['shape'], spec['target_score'], pattern['sign'])
                    scale = tuning['amplitude_e_per_s']
                else:
                    scale = contexts[a]['level']*spec['amplitude_fraction']
                trial_id = f'base_a{a:02d}_p{phase:g}_c{spec["case_index"]:02d}'
                parent = append(a, pattern, scale, phase, spec['shape'], {**spec, 'trial_id': trial_id, 'suite': 'base'}, tuning)
                if (spec['group'] == 'matched' and spec['kind'] in ('stellar', 'block_2x2')) or spec['kind'] == 'null':
                    j = int(np.argmin(contexts[a]['profile'][aperture]))
                    inside = np.argwhere(aperture)[j].tolist()
                    width = parent['best']['stop']-parent['best']['start']
                    magnitude = cfg['residual_sigma']*np.sqrt(covariances[a, width][j, j])
                    for location, pixel in [('inside', inside), ('outside', [0, 0])]:
                        for polarity in (-1, 1):
                            residual = {'pixel_yx': pixel, 'location': location, 'polarity': polarity,
                                        'start': parent['best']['start'], 'stop': parent['best']['stop'],
                                        'amplitude_e_per_s': float(polarity*magnitude), 'reference_pixel_index': j}
                            append(a, pattern, scale, phase, spec['shape'], {**spec, 'trial_id': trial_id+f'_{location}_{polarity}',
                                   'suite': 'sparse_stress', 'parent_trial_id': trial_id}, None, residual)
            for shape in basecfg['strength_trials']['shapes']:
                pulse, centers = pulse_shape(seconds[a], phase, shape, 20.)
                for target in basecfg['strength_trials']['scores']:
                    tuning = strength(a, pulse, centers, phase, shape, target, 1)
                    for suite, kinds in [('known_extended', cfg['known_extended']), ('unmodeled_shapes', cfg['unmodeled_shapes'])]:
                        for kind in kinds:
                            pattern = get_pattern(a, kind)
                            append(a, pattern, tuning['amplitude_e_per_s'], phase, shape,
                                   {'suite': suite, 'kind': kind, 'group': 'matched', 'target_score': target,
                                    'trial_id': f'{suite}_a{a}_p{phase:g}_{shape}_t{target:g}_{kind}'}, tuning)
                for shift in cfg['physical_pointing_shifts_yx']:
                    pattern = get_pattern(a, 'bounded_pointing', shift)
                    append(a, pattern, 1., phase, shape, {'suite': 'bounded_pointing', 'kind': 'pointing',
                           'group': 'physical', 'shift_yx': shift, 'pattern_multiplier': 1.,
                           'trial_id': f'physical_a{a}_p{phase:g}_{shape}_d{shift[0]:g}_{shift[1]:g}'})
        if progress:
            progress({'anchor_completed': a, 'trials': len(rows)})
    return rows, {'samples': training, 'folds': folds}, list(models.values()), list(patterns.values())


def group_key(r):
    key = [r['suite'], r['kind'], r.get('target_score')]
    if r['suite'] == 'base' and r.get('target_score') is None:
        key += [r.get('amplitude_fraction'), r['shape']]
    if r['suite'] == 'sparse_stress':
        key += [r['residual']['location'], r['residual']['polarity']]
    return tuple(key)


def summarize(rows, cfg):
    groups, core = [], []
    for key in sorted({group_key(r) for r in rows}, key=str):
        selected = [r for r in rows if group_key(r) == key]
        entry = {'key': list(key), 'trials': len(selected), 'screen_detected': sum(r['screen_detected'] for r in selected),
                 'confounded': sum(r['baseline_confounded'] for r in selected),
                 'matched': sum(r['strength_matched'] is True for r in selected), 'rules': {}}
        for method, bank, threshold in product(cfg['methods'], ['original', 'broad'], cfg['thresholds']):
            rule = f'{method}/{bank}/{threshold}'
            entry['rules'][rule] = {field: sum(r['methods'][method]['decisions'][bank][str(threshold)][field] for r in selected)
                                    for field in ['accepted', 'recovered', 'nuisance_preferred_acceptance']}
        groups.append(entry)
        if key[0] in ('base', 'known_extended', 'unmodeled_shapes') and key[2] is not None:
            signal = key[1] in ('stellar', 'off_profile')
            limit = int(np.ceil((.9 if key[1] == 'stellar' else .8)*len(selected))) if signal else len(selected)//20
            core.append({'key': list(key), 'trials': len(selected), 'signal': signal, 'limit': limit,
                         'rules': {rule: {'count': counts['recovered' if signal else 'accepted'],
                                          'pass': counts['recovered' if signal else 'accepted'] >= limit if signal
                                                  else counts['accepted'] <= limit}
                                   for rule, counts in entry['rules'].items()}})
    assert len(core) == 36
    gates = {}
    for method, bank, threshold in product(cfg['methods'], ['original', 'broad'], cfg['thresholds']):
        rule = f'{method}/{bank}/{threshold}'
        bright = [r for r in rows if r['suite'] == 'base' and r['kind'] == 'stellar'
                  and r.get('amplitude_fraction') == .1 and r['shape'] != 'doublet30sep87']
        nulls = [r for r in rows if r['suite'] == 'base' and r['kind'] == 'null']
        signals = [r for r in rows if r['kind'] in ('stellar', 'off_profile')]
        physical = [r for r in rows if r['suite'] == 'bounded_pointing' and r['screen_detected']]
        decision = lambda r: r['methods'][method]['decisions'][bank][str(threshold)]
        g = {'all_core_cells': all(c['rules'][rule]['pass'] for c in core),
             'all_target_strengths_matched': all(r['strength_matched'] for r in rows if r['tuning'] is not None),
             'ten_percent_single_recovery': sum(decision(r)['recovered'] for r in bright) >= 54,
             'no_base_null_acceptance': not any(decision(r)['accepted'] for r in nulls),
             'confounding_at_most_20_percent': sum(r['baseline_confounded'] for r in signals) <= .2*len(signals),
             'bounded_pointing_screened_acceptance': bool(physical) and sum(decision(r)['accepted'] for r in physical) <= .05*len(physical)}
        gates[rule] = {'pass': all(g.values()), 'gates': g}
    backgrounds = []
    for a in sorted({r['anchor'] for r in rows}):
        for cell in core:
            selected = [r for r in rows if r['anchor'] == a and list(group_key(r)) == cell['key']]
            backgrounds.append({'anchor': a, 'key': cell['key'], 'trials': len(selected),
                                'screen_detected': sum(r['screen_detected'] for r in selected),
                                'rules': {f'{m}/{b}/{t}': sum(r['methods'][m]['decisions'][b][str(t)]['recovered' if cell['signal'] else 'accepted'] for r in selected)
                                          for m, b, t in product(cfg['methods'], ['original', 'broad'], cfg['thresholds'])}})
    return {'groups': groups, 'core_cells': core, 'rules': gates, 'per_background': backgrounds}
