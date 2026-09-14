#!/usr/bin/env python3
"""Retrospective bookkeeping of sealed LS7J corrections; no refit or selection."""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7j_auxiliary'


def read(name):
    return json.loads((OUT/name).read_text())


def rows(name):
    return [json.loads(r) for r in gzip.decompress((OUT/name).read_bytes()).splitlines()]


def main():
    for line in (OUT/'SHA256SUMS').read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        assert hashlib.sha256((OUT/path.strip()).read_bytes()).hexdigest() == digest
    summary = read('summary.json'); assert read('AUDIT.json')['passed']
    frames = {r['frame_id']: r for r in rows('frames.jsonl.gz')}
    baselines = {r['fold_id']: r for r in read('baselines.json')}
    native = rows('native_windows.jsonl.gz'); entries = []
    maximum_identity_error = 0.
    for row in native:
        frame, b = frames[row['frame_id']], baselines[row['fold_id']]
        chol = np.linalg.cholesky(b['covariance'])
        one = solve_triangular(chol, np.ones(len(b['mean'])), lower=True)

        def whiten(vector):
            w = solve_triangular(chol, vector, lower=True)
            return w-one*(w@one)/(one@one)

        residual = whiten(np.array(row['normalized_response'])-b['mean'])
        e0 = float(residual@residual)
        np.testing.assert_allclose(e0, row['energies']['static'], rtol=1e-10, atol=1e-9)
        for method in ['motion', 'plane', 'combined']:
            correction = row['corrections_aperture'][method]
            if correction is None:
                entries.append({'window_id': row['window_id'], 'sector': row['sector'], 'anchor': row['anchor'],
                                'method': method, 'available': False})
                continue
            correction = whiten(np.array(correction)/frame['sigma'])
            alignment, power = float(residual@correction), float(correction@correction)
            predicted_energy = e0-2*alignment+power
            error = abs(predicted_energy-row['energies'][method]); maximum_identity_error = max(error, maximum_identity_error)
            np.testing.assert_allclose(predicted_energy, row['energies'][method], rtol=1e-10, atol=1e-9)
            entries.append({'window_id': row['window_id'], 'sector': row['sector'], 'anchor': row['anchor'],
                            'method': method, 'available': True, 'static_energy': e0,
                            'alignment': alignment, 'correction_power': power, 'corrected_energy': predicted_energy})
    sectors = {}
    for sector in [29, 32]:
        methods = {}
        for method in ['motion', 'plane', 'combined']:
            selected = [r for r in entries if r['sector'] == sector and r['method'] == method and r['available']]
            e0 = sum(r['static_energy'] for r in selected)
            alignment = sum(r['alignment'] for r in selected); power = sum(r['correction_power'] for r in selected)
            value = {'available_windows': len(selected), 'static_energy': e0, 'alignment': alignment,
                     'correction_power': power, 'alignment_term_over_static': -2*alignment/e0,
                     'correction_power_over_static': power/e0, 'net_energy_change_over_static': (power-2*alignment)/e0,
                     'aggregate_alignment_cosine': alignment/np.sqrt(e0*power) if power > 0 else None,
                     'per_background': []}
            np.testing.assert_allclose(1+value['net_energy_change_over_static'], summary['sectors'][str(sector)]['methods'][method]['ratio'], rtol=1e-10, atol=1e-9)
            for anchor in range(10):
                rr = [r for r in selected if r['anchor'] == anchor]
                baseline = sum(r['static_energy'] for r in rr)
                aa = sum(r['alignment'] for r in rr); pp = sum(r['correction_power'] for r in rr)
                value['per_background'].append({'anchor': anchor, 'alignment_term_over_static': -2*aa/baseline,
                                                'correction_power_over_static': pp/baseline,
                                                'net_energy_change_over_static': (pp-2*aa)/baseline})
            methods[method] = value
        sectors[str(sector)] = methods
    result = {'scope': 'Retrospective energy identity for existing sealed corrections; no new predictor, sign, gain or delay evaluated',
              'source_result_commit': '52ef2780a374e1314252f8fe9f37d8fcae4d985f',
              'source_manifest_sha256': hashlib.sha256((OUT/'SHA256SUMS').read_bytes()).hexdigest(),
              'source_summary_sha256': hashlib.sha256((OUT/'summary.json').read_bytes()).hexdigest(),
              'maximum_energy_identity_error': maximum_identity_error, 'sectors': sectors, 'window_method_rows': entries}
    (ROOT/'LS7J_LIMITATIONS.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'maximum_energy_identity_error': maximum_identity_error,
                     'sectors': {s: {m: {k: v for k, v in value.items() if k != 'per_background'} for m, value in methods.items()}
                                 for s, methods in sectors.items()}}, indent=2))


if __name__ == '__main__':
    main()
