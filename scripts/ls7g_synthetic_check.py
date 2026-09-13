#!/usr/bin/env python3
"""Exercise every LS7G suite on artificial backgrounds before the source freeze."""
from collections import Counter
import json
from pathlib import Path
import numpy as np

from ls7f_review import direct_fit
from seti_repeater.light_sail_tess import robust_sigma
from seti_repeater.tess_transfer import evaluate_contexts, expected_suites, summarize

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT/'config/ls7g_transfer.json').read_text())
    basecfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    rng = np.random.default_rng(73029)
    aperture = np.zeros((11, 11), bool); aperture[3:8, 3:8] = True
    for y, x in [(3, 3), (3, 7), (7, 3), (7, 7)]:
        aperture[y, x] = False
    yy, xx = np.indices((11, 11))
    mean = 20+800*np.exp(-((yy-5)**2+(xx-5)**2)/2)
    native = mean+2*rng.normal(size=(10, 401, 11, 11))+rng.normal(size=(10, 401, 1, 1))
    seconds = np.tile(np.arange(-200, 201)*20., (10, 1))
    sigmas = np.array([robust_sigma(x[:, aperture].sum(axis=1)) for x in native])
    rows, training, models, patterns = evaluate_contexts(native, seconds, aperture, sigmas, cfg, basecfg)
    assert dict(Counter(r['suite'] for r in rows)) == expected_suites()
    assert len({r['trial_id'] for r in rows}) == 3540
    result = summarize(rows, cfg)
    assert len(result['core_cells']) == 36 and len(result['per_background']) == 360
    model_map = {m['model_id']: m for m in models}
    checked, worst, seen = 0, 0., set()
    for r in rows:
        key = (r['anchor'], r['suite'])
        if key in seen:
            continue
        seen.add(key)
        model = model_map[r['model_id']]; chol = np.linalg.cholesky(model['covariance'])
        for method, data in r['methods'].items():
            for field, templates in [('star', model['star_templates']), ('original_nuisance', model['original_templates']), ('broad_nuisance', model['broad_templates'])]:
                fit = data[field]
                check = direct_fit(np.array(r['event_vector']), templates[fit['template_index']], chol, fit['sparse_pixel'], 9.)
                worst = max(worst, abs(check['objective']-fit['objective']))
                np.testing.assert_allclose(check['objective'], fit['objective'], rtol=1e-7, atol=2e-7)
                checked += 1
    print(json.dumps({'scope': 'artificial smoke fixture only; no telescope input', 'passed': True,
                      'rows': len(rows), 'core_cells': 36, 'background_cells': 360,
                      'independent_fit_checks': checked, 'max_objective_error': worst}))


if __name__ == '__main__':
    main()
