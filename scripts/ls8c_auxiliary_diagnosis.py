#!/usr/bin/env python3
"""Offline, fixed-window LS8C auxiliary diagnosis. Refuses output overwrite."""
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
from astropy.io import fits
from ls8a_l2_evaluate import dtype
from seti_repeater.cheops_auxiliary import diagnose_context

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8c_auxiliary'
CONFIG = ROOT / 'config/ls8c_auxiliary.json'


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    assert not OUT.exists(), 'refuse completed diagnosis overwrite'
    cfg = json.loads(CONFIG.read_text())
    tables, hashes = {}, {}
    for key, expected in cfg['input_table_sha256'].items():
        raw = (ROOT / 'results_ls8b_l2_suite' / key / 'lightcurve_table.bin').read_bytes()
        hashes[key] = hashlib.sha256(raw).hexdigest()
        assert hashes[key] == expected
        header = fits.Header.fromstring((ROOT / 'results_ls8b_l2_metadata' / key /
                                        'lightcurve_header.bin').read_bytes().decode('ascii'), sep='')
        assert header['EXT_VER'] == '13.1'
        assert len(raw) == header['NAXIS1'] * header['NAXIS2']
        tables[key] = np.frombuffer(raw, dtype=dtype(header))
    representatives = list(csv.DictReader((ROOT / 'results_ls8b_l2_suite' /
                                          'cluster_representatives.csv').open()))
    selected = [(r['file_key'], r['sign'], int(r['cluster_id']), int(r['start_row']),
                 int(r['duration_rows'])) for r in representatives]
    assert selected == [tuple(r) for r in cfg['representatives']]
    records = []
    for key, sign, cluster, start, duration in selected:
        result = diagnose_context(tables[key], start, duration)
        ctx = tables[key][result['context_start']:result['context_stop']]
        assert (ctx['STATUS'] == 0).all() and (ctx['EVENT'] == 0).all()
        records.append({'file_key': key, 'sign': sign, 'cluster_id': cluster,
                        'start': start, 'duration': duration, **result})
    OUT.mkdir()
    save(OUT / 'diagnostics.json', records)
    save(OUT / 'summary.json', {
        'stage': 'LS8C_RETROSPECTIVE_AUXILIARY_DIAGNOSIS', 'status': 'COMPLETE_UNAUDITED',
        'representatives': len(records), 'positive': 7, 'negative': 1,
        'series_diagnostics': sum(len(r['series']) for r in records),
        'available_series': sum(s['status'] == 'AVAILABLE' for r in records for s in r['series'].values()),
        'available_couplings': sum(c['status'] == 'AVAILABLE' for r in records for c in r['couplings'].values()),
        'new_archive_science_bytes': 0, 'new_windows_selected': 0,
        'event_selection_or_veto_changed': False, 'original_ls8b_audit': 'FAIL',
        'input_table_sha256': hashes, 'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        'python': platform.python_version(), 'numpy': np.__version__,
        'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
            'src/seti_repeater/cheops_auxiliary.py', 'scripts/ls8c_auxiliary_diagnosis.py',
            'scripts/ls8c_auxiliary_audit.py')},
    })
    with (OUT / 'measurements.csv').open('w') as f:
        fields = ['file_key', 'sign', 'cluster_id', 'start', 'duration', 'field', 'unit',
                  'status', 'event_mean', 'predicted_event_mean', 'mean_residual',
                  'sum_residual', 'side_mad', 'side_rms', 'mad_displacement', 'slope_per_second']
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        for r in records:
            for name, s in r['series'].items():
                writer.writerow({**{k: r[k] for k in fields[:5]}, 'field': name,
                                 **{k: s.get(k) for k in fields[6:]}})
    print((OUT / 'summary.json').read_text())


if __name__ == '__main__':
    main()
