#!/usr/bin/env python3
"""LS8AH offline use of the one already published, pinned LS8AG contexts."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from astropy.io import fits
from ls8k_l2_screen import dtype
from seti_repeater.cheops_duration_noise import (
    layout, training_rows, prepare, describe, boundary_account,
    correction_account, injections)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8ah_residuals'


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    assert os.environ.get('GITHUB_SHA') == subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    cfg = json.loads((ROOT / 'config/ls8ah_residuals.json').read_text())
    original = json.loads((ROOT / 'config/ls8ag_images.json').read_text())
    for name, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    old = ROOT / 'results_ls8ag_images'
    for line in (old / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((old / name).read_bytes()).hexdigest() == digest, name
    assert json.loads((old / 'audit.json').read_text())['status'] == 'PASS'
    assert cfg['context_ids'] == [c['id'] for c in original['contexts']]
    assert not OUT.exists(), 'refuse to overwrite an earlier outcome'
    OUT.mkdir(); summaries = []; controls = []; payload_bytes = 0
    previous = {r['id']: r for r in json.loads((old / 'diagnostics.json').read_text())}
    for context in original['contexts']:
        scope = cfg['contexts'][context['id']]; duration = context['duration']
        SIDE, EVENT, BLOCKS = layout(duration); cadence = scope['cadence_seconds']
        assert scope['duration_rows'] == duration
        assert scope['side_rows'] == SIDE.tolist() and scope['event_rows'] == EVENT.tolist()
        assert scope['held_blocks'] == [b.tolist() for b in BLOCKS]
        key = context['file_key']; folder = OUT / context['id']; folder.mkdir()
        header = fits.Header.fromstring((ROOT / 'results_ls8af_l2_metadata' / key / 'lightcurve_header.bin').read_bytes().decode(), sep='')
        rows = np.frombuffer((ROOT / 'results_ls8af_l2_screen' / key / 'lightcurve_table.bin').read_bytes(), dtype=dtype(header))[context['lo']:context['hi']]
        assert len(rows) == 28 + duration
        assert header['NEXP'] == 1 and header['EXPTIME'] == header['TEXPTIME'] == cadence
        times = (rows['BJD_TIME'].astype(float) - float(rows['BJD_TIME'][14])) * 86400
        cubes = {}
        for kind in ('CAL', 'COR'):
            path = old / context['id'] / f'SCI_{kind}_SubArray.bin.gz'
            raw = gzip.decompress(path.read_bytes()); receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            assert hashlib.sha256(raw).hexdigest() == receipt['raw_sha256']
            assert len(raw) == context['ranges'][f'SCI_{kind}_SubArray']['count'] == (28 + duration) * 320000
            cubes[kind] = np.frombuffer(raw, dtype='>f8').astype(float).reshape(28 + duration, 200, 200)
            payload_bytes += len(raw)
        common = np.isfinite(cubes['CAL'][np.r_[SIDE, EVENT]]).all(axis=0) & np.isfinite(cubes['COR'][np.r_[SIDE, EVENT]]).all(axis=0)
        spec = original['sources'][key]['SCI_COR_SubArray']
        center = np.array([rows['CENTROID_X'][SIDE].astype(float).mean() - spec['xoff'], rows['CENTROID_Y'][SIDE].astype(float).mean() - spec['yoff']])
        item = {'id': context['id'], 'sign': context['sign'],
            'original_ls8ag_classification': previous[context['id']]['classification'],
            'duration_rows': duration, 'cadence_seconds': cadence, 'event_rows': EVENT.tolist(), 'conventions': {}}
        masks = []
        with np.load(old / context['id'] / 'event_maps.npz') as previous_maps:
            assert np.array_equal(common, previous_maps['COMMON'])
            maps = {kind: previous_maps[kind].copy() for kind in ('CAL', 'COR', 'DELTA')}
        for number in (0, 1):
            conv = f'C{number}'; cc = center - number; states = {}; info = {}; arrays = {'COMMON': common}
            for kind in ('CAL', 'COR'):
                state = prepare(times, cubes[kind], SIDE, EVENT, common, cc, cadence)
                np.testing.assert_allclose(state['y'], maps[kind][state['mask']], rtol=2e-8, atol=1e-6)
                states[kind] = state; detail, residual = describe(state); detail['held_blocks'] = []
                for block in BLOCKS:
                    training = training_rows(SIDE, block)
                    pseudo = prepare(times, cubes[kind], training, block, common, cc, cadence)
                    result, _ = describe(pseudo)
                    detail['held_blocks'].append({'held_local_rows': block.tolist(), **result})
                metric = detail['models']['combined']['weighted_residual_to_sideband_ratio']
                detail['held_blocks_at_least_event'] = sum(p['models']['combined']['weighted_residual_to_sideband_ratio'] >= metric for p in detail['held_blocks'])
                detail['held_block_count'] = len(BLOCKS)
                detail['original_ls8ag_unweighted_fits'] = previous[context['id']]['conventions'][conv]['fits'][kind]
                info[kind] = detail
                controls.extend({'id': context['id'], 'convention': conv, 'product': kind, **r} for r in injections(state))
                for name in ('y', 'side', 'x', 'variance', 's2', 'mask', 'xy', 'row_weights', 'correlation'):
                    arrays[f'{kind}_{name}'] = state[name]
                arrays[f'{kind}_residual'] = residual
            masks.append(states['COR']['mask'])
            info['correction_residual_account'] = correction_account(states['CAL'], states['COR'])
            info['center'] = cc.tolist(); item['conventions'][conv] = info
            np.savez_compressed(folder / f'{conv}_arrays.npz', **arrays)
        item['boundary_account'] = boundary_account(maps, masks)
        save(folder / 'diagnostics.json', item); summaries.append(item)
        print(context['id'], '4 native fits and', 4 * len(BLOCKS), 'duration-matched held cases complete', flush=True)
    assert payload_bytes == 18560000 and len(controls) == 64
    save(OUT / 'diagnostics.json', summaries); save(OUT / 'injection_controls.json', controls)
    save(OUT / 'summary.json', {'status': 'COMPLETE_UNAUDITED', 'contexts': len(summaries),
        'actual_product_conventions': 4, 'held_duration_matched_cases': 96,
        'signed_injection_cases': len(controls), 'retained_cal_cor_bytes_read': payload_bytes,
        'new_native_source_bytes': 0, 'new_classifier': False, 'qualified_candidates_added': 0,
        'qualified_coverage_added': False, 'original_ls8ag_classifications_unchanged': True})


if __name__ == '__main__':
    main()
