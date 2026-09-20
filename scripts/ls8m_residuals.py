#!/usr/bin/env python3
"""Offline LS8M analysis of the three immutable LS8L contexts."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from astropy.io import fits
from ls8k_l2_screen import dtype
from seti_repeater.cheops_residual_noise import prepare, describe, correction_account, injections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8m_residuals'


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    cfg = json.loads((ROOT / 'config/ls8m_residuals.json').read_text())
    oldcfg = json.loads((ROOT / 'config/ls8l_images.json').read_text())
    for relative, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    old = ROOT / 'results_ls8l_images'
    for line in (old / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        assert hashlib.sha256((old / relative).read_bytes()).hexdigest() == digest, relative
    assert json.loads((old / 'audit.json').read_text())['status'] == 'PASS'
    assert cfg['context_ids'] == [c['id'] for c in oldcfg['contexts']]
    assert not OUT.exists(), 'refuse to overwrite any previous outcome'
    OUT.mkdir()
    oldresults = {r['id']: r for r in json.loads((old / 'diagnostics.json').read_text())}
    summaries = []; controls = []; payload_bytes = 0
    for c in oldcfg['contexts']:
        key = c['file_key']; folder = OUT / c['id']; folder.mkdir()
        header = fits.Header.fromstring((ROOT / 'results_ls8k_l2_metadata' / key / 'lightcurve_header.bin').read_bytes().decode(), sep='')
        rows = np.frombuffer((ROOT / 'results_ls8k_l2_screen' / key / 'lightcurve_table.bin').read_bytes(), dtype=dtype(header))[c['lo']:c['hi']]
        times = (rows['BJD_TIME'].astype(float) - float(rows['BJD_TIME'][14])) * 86400
        side = np.asarray(cfg['side_rows']); target = cfg['event_row']
        assert len(rows) == 29 and c['duration'] == 1
        cubes = {}
        for kind in ('CAL', 'COR'):
            path = old / c['id'] / f'SCI_{kind}_SubArray.bin.gz'
            raw = gzip.decompress(path.read_bytes())
            receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            assert hashlib.sha256(raw).hexdigest() == receipt['raw_sha256']
            assert len(raw) == c['ranges'][f'SCI_{kind}_SubArray']['count'] == 9280000
            cubes[kind] = np.frombuffer(raw, dtype='>f8').astype(float).reshape(29, 200, 200)
            payload_bytes += len(raw)
        common = np.isfinite(cubes['CAL'][np.r_[side, target]]).all(axis=0) & np.isfinite(cubes['COR'][np.r_[side, target]]).all(axis=0)
        spec = oldcfg['sources'][key]['SCI_COR_SubArray']
        center = [rows['CENTROID_X'][side].astype(float).mean() - spec['xoff'], rows['CENTROID_Y'][side].astype(float).mean() - spec['yoff']]
        item = {'id': c['id'], 'sign': c['sign'], 'original_ls8l_classification': oldresults[c['id']]['classification'], 'conventions': {}}
        for number in cfg['center_conventions']:
            conv = f'C{number}'; current_center = np.asarray(center) - number
            states = {}; data = {}; arrays = {'COMMON': common}
            for kind, cube in cubes.items():
                state = prepare(times, cube, side, target, common, current_center)
                states[kind] = state; description, residual = describe(state)
                description['loso'] = []
                for held in side:
                    pseudo = prepare(times, cube, side[side != held], int(held), common, current_center)
                    result, _ = describe(pseudo)
                    description['loso'].append({'held_local_row': int(held), **result})
                metric = description['models']['combined']['weighted_residual_to_sideband_ratio']
                description['loso_at_least_event'] = sum(p['models']['combined']['weighted_residual_to_sideband_ratio'] >= metric for p in description['loso'])
                description['loso_count'] = len(side)
                # Exact original fit is a retained comparison, never overwritten.
                description['original_ls8l_unweighted_fits'] = oldresults[c['id']]['conventions'][conv]['fits'][kind]
                data[kind] = description
                controls.extend({'id': c['id'], 'convention': conv, 'product': kind, **r} for r in injections(state))
                for name in ('y', 'side', 'x', 'variance', 's2', 'mask', 'xy'):
                    arrays[f'{kind}_{name}'] = state[name]
                arrays[f'{kind}_residual'] = residual
            data['correction_residual_account'] = correction_account(states['CAL'], states['COR'])
            data['center'] = current_center.tolist()
            item['conventions'][conv] = data
            np.savez_compressed(folder / f'{conv}_arrays.npz', **arrays)
        save(folder / 'diagnostics.json', item); summaries.append(item)
        print(c['id'], '12 actual model fits; 288 leave-one-sideband model fits', flush=True)
    save(OUT / 'diagnostics.json', summaries)
    save(OUT / 'injection_controls.json', controls)
    save(OUT / 'summary.json', {'status': 'COMPLETE_UNAUDITED', 'contexts': len(summaries),
        'actual_product_conventions': 12, 'leave_one_sideband_cases': 288,
        'signed_injection_cases': len(controls), 'retained_cal_cor_bytes_read': payload_bytes,
        'new_native_source_bytes': 0, 'new_classifier': False, 'qualified_candidates_added': 0,
        'qualified_coverage_added': False, 'original_ls8l_classifications_unchanged': True})


if __name__ == '__main__':
    main()
