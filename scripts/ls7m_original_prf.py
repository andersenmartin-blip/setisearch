#!/usr/bin/env python3
"""Restore bounded mission MATLAB PRFs and compare their export geometry."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits
from scipy.io import loadmat, whosmat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7m_prf_inputs'
SIZES = {3: 5200793, 4: 5198689}


def describe(value):
    array = np.asarray(value)
    result = {'shape': list(array.shape), 'dtype': str(array.dtype)}
    if array.dtype.kind in 'fiu':
        result['finite'] = int(np.isfinite(array).sum())
        result['minimum'] = float(array.min()) if array.size else None
        result['maximum'] = float(array.max()) if array.size else None
        if array.size <= 250:
            result['values'] = array.tolist()
    return result


def main():
    assert not OUT.exists(), 'refuse to overwrite a completed acquisition'
    assert sum(SIZES.values()) < 32_000_000
    (OUT / 'originals').mkdir(parents=True)
    inv = json.loads((ROOT / 'results_ls7k_inputs/inventory.json').read_text())
    sources, models = [], []
    for ccd, expected in SIZES.items():
        name = f'tess2019107181902-00195_045-4-{ccd}-characterized-prf.mat'
        url = f'https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/cam4_ccd{ccd}/{name}'
        with urlopen(Request(url, method='HEAD'), timeout=30) as response:
            assert response.status == 200
            assert int(response.headers['Content-Length']) == expected < 16_000_000
            validators = {key: response.headers.get(key) for key in ('ETag', 'Last-Modified')}
        with urlopen(Request(url), timeout=30) as response:
            assert response.status == 200
            assert int(response.headers['Content-Length']) == expected
            assert all(response.headers.get(k) == v for k, v in validators.items())
            raw = response.read(expected + 1)
        assert len(raw) == expected
        path = OUT / 'originals' / name
        path.write_bytes(raw)
        source = {'name': name, 'url': url, 'bytes': expected,
                  'sha256': hashlib.sha256(raw).hexdigest(), 'validators': validators,
                  'variables': whosmat(path)}
        data = loadmat(path, struct_as_record=False, squeeze_me=True)
        entries = np.atleast_1d(data['prfStruct'])
        assert entries.size == 25
        for entry in entries:
            col, row = int(entry.ccdColumn), int(entry.ccdRow)
            match = next(x for x in inv['prf_models'] if x['ccd'] == ccd and x['grid_col'] == col and x['grid_row'] == row)
            fpath = ROOT / 'results_ls7k_inputs' / match['path']
            assert hashlib.sha256(fpath.read_bytes()).hexdigest() == match['sha256']
            record = {'ccd': ccd, 'grid_col': col, 'grid_row': row,
                      'fits_file': match['name'], 'mat_fields': entry._fieldnames,
                      'field_descriptions': {f: describe(getattr(entry, f)) for f in entry._fieldnames},
                      'comparisons': {}}
            with fits.open(fpath) as hdus:
                for field, index in [('values', 0), ('uncertainties', 1)]:
                    array = np.asarray(getattr(entry, field))
                    reference = hdus[index].data
                    record['comparisons'][field] = {
                        'identity_equal': bool(np.array_equal(array, reference)),
                        'transpose_equal': bool(np.array_equal(array.T, reference)),
                        'identity_max_abs': float(np.max(np.abs(array-reference))),
                        'transpose_max_abs': float(np.max(np.abs(array.T-reference)))}
            models.append(record)
        sources.append(source)
        print(json.dumps({'ccd': ccd, 'bytes': expected, 'sha256': source['sha256'], 'models': int(entries.size)}), flush=True)
    result = {'study': 'LS7M original PRF coordinate inputs', 'sources': sources, 'models': models,
              'native_response_comparisons': 0, 'new_detector_decisions': 0}
    (OUT / 'inventory.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
