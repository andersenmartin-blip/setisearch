"""Lossless, truth-labelled recipes for the closed LS7E/LS7G input archives.

These recipes are evaluation inputs, never inference features. No detector,
threshold, amplitude tuning, covariance or historical decision is changed.
"""
import numpy as np

from .light_sail_tess import pulse_shape
from .light_sail_tess_v2 import shifted_profile, pointing_delta
from .light_sail_tess_v3 import empirical_profile, nuisance_pattern


SUITES_32 = {'ls7c_replay': 'base', 'sparse_stress': 'sparse_stress',
             'extended': 'known_extended', 'physical_pointing': 'bounded_pointing'}


def row_identity(sector, row, index, ledger):
    return {'case_id': f's{sector:03d}/{row["trial_id"]}', 'sector': sector,
            'source_ledger': ledger, 'source_row': index,
            'source_trial_id': row['trial_id'], 'source_suite': row['suite'],
            'source_model_id': row['model_id'], 'anchor': row['anchor'],
            'suite': SUITES_32[row['suite']] if sector == 32 else row['suite'],
            'kind': row['kind'], 'shape': row['shape'], 'target_score': row.get('target_score'),
            'amplitude_fraction': row.get('amplitude_fraction'),
            'shift_yx': row.get('shift_yx', [0., 0.]), 'phase_seconds': row['phase_seconds'],
            'sign': row['sign'], 'best': row['best'], 'native_best': row['native_best'],
            'screen_detected': row['screen_detected'], 'baseline_confounded': row['baseline_confounded']}


def sector32_recipe(row, original, native, aperture):
    """Reconstruct LS7E injection metadata without rerunning amplitude tuning."""
    reference = np.median(native, axis=0)
    profile = empirical_profile(reference, aperture)
    residual, parent = None, None
    if row['suite'] in ('ls7c_replay', 'sparse_stress'):
        parent = original[row['original']['trial_id'] if row['suite'] == 'ls7c_replay' else row['parent_trial_id']]
        assert parent['anchor'] == row['anchor']
        for key in ['kind', 'shape', 'phase_seconds', 'shift_yx', 'sign']:
            assert row[key] == parent[key]
        if parent['kind'] in ('stellar', 'off_profile', 'null'):
            pattern = shifted_profile(profile, aperture, parent['shift_yx'])
        else:
            pattern, sign, _ = nuisance_pattern(parent['kind'], reference, profile, aperture, parent['shift_yx'])
            assert sign == row['sign']
        scale = (parent['tuning']['amplitude_e_per_s'] if parent['tuning'] is not None
                 else float(np.median(native[:, aperture].sum(axis=1)))*parent['amplitude_fraction'])
        if row['suite'] == 'sparse_stress':
            # Stress lives at the parent window even if the altered trial reselects.
            residual = {'pixel_yx': row['residual_yx'], 'start': parent['best']['start'],
                        'stop': parent['best']['stop'], 'amplitude_e_per_s': row['residual_e_per_s'],
                        'location': row['residual_location']}
    elif row['suite'] == 'extended':
        h, w = {'block3x3': (3, 3), 'row1x5': (1, 5), 'column5x1': (5, 1)}[row['kind']]
        choices = [(profile[y:y+h, x:x+w].sum(), y, x)
                   for y in range(profile.shape[0]-h+1) for x in range(profile.shape[1]-w+1)]
        _, y, x = max(choices, key=lambda p: p[0])
        assert row['corner_yx'] == [y, x]
        pattern = np.zeros(aperture.shape); pattern[y:y+h, x:x+w] = 1.
        pattern /= pattern[aperture].sum()
        scale = row['amplitude_e_per_s']
    elif row['suite'] == 'physical_pointing':
        pattern = pointing_delta(reference, row['shift_yx'])
        scale = row['pattern_multiplier']
        assert scale == 1.
        np.testing.assert_allclose(pattern[aperture].sum(), row['aperture_projection_e_per_s'], rtol=1e-12, atol=1e-10)
    else:
        raise ValueError('unknown LS7E suite')
    return pattern, float(scale), residual, None if parent is None else parent['trial_id']


def reconstruct(native, seconds, recipe, pattern):
    p, centers = pulse_shape(seconds, recipe['phase_seconds'], recipe['shape'], 20.)
    injected = native+(recipe['pattern_scale']*p)[:, None, None]*np.asarray(pattern)
    if recipe['residual'] is not None:
        d = recipe['residual']; y, x = d['pixel_yx']
        injected[d['start']:d['stop'], y, x] += d['amplitude_e_per_s']
    return injected, centers


def validate_links(recipes, counts):
    if len({r['case_id'] for r in recipes}) != len(recipes):
        raise ValueError('duplicate globally qualified case')
    for sector, total in counts.items():
        selected = [r for r in recipes if r['sector'] == int(sector)]
        if [r['source_row'] for r in selected] != list(range(total)):
            raise ValueError('missing, reordered or duplicated source row')
        if any(r['case_id'] != f's{int(sector):03d}/{r["source_trial_id"]}' for r in selected):
            raise ValueError('wrong global identity')
