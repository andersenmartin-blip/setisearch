#!/usr/bin/env python3
"""Offline LS8BC release identities and scope bookkeeping; no scientific refit."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess

import numpy as np
from ls8k_l2_audit import parse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification_ls8bc'
SOURCE = '0f1cc15422d5d0d70721269e43b2cae68c484bf8'


def read(path):
    return json.loads((ROOT / path).read_text())


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def main():
    inventory = read('verification_ls8bc/public_file_inventory.json')
    assert inventory['head'] == SOURCE and inventory['total_commits'] == 4
    assert len(inventory['files']) == 64
    local = subprocess.check_output(['git', 'diff', '--name-only', inventory['base'], SOURCE],
                                    cwd=ROOT, text=True).splitlines()
    assert sorted(local) == sorted(f['path'] for f in inventory['files'])
    files = []
    for f in inventory['files']:
        assert f['status'] == 'added'
        raw = (ROOT / f['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == f['sha'], f['path']
        files.append({'path': f['path'], 'git_blob': blob,
                      'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    manifests = []
    for folder in ['results_ls8bc_l2_metadata', 'results_ls8bc_l2_screen']:
        entries = (ROOT / folder / 'SHA256SUMS').read_text().splitlines()
        for line in entries:
            expected, name = line.split('  ', 1)
            assert hashlib.sha256((ROOT / folder / name).read_bytes()).hexdigest() == expected
        manifests.append({'path': folder + '/SHA256SUMS', 'verified_entries': len(entries)})
    pins = []
    for name in ['config/ls8bc_selected_pair.json', 'config/ls8bc_l2_scope.json']:
        cfg = read(name)
        for relative, expected in cfg['input_pins'].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
        pins.append({'config': name, 'verified_pins': len(cfg['input_pins'])})
    runs = read('verification_ls8bc/workflow_runs.json')
    assert {r['head_sha'] for r in runs} == {
        'e49ae422eaeadef9dada30c1700d25dfcf3f1ba3',
        '9a38e512f5b08e4117068786dad4afb85508e9bf'}
    assert all(r['status'] == 'completed' and r['conclusion'] == 'success' for r in runs)
    audit = read('results_ls8bc_l2_screen/audit.json')
    assert audit['status'] == 'PASS' and not audit['numeric_disagreements']
    assert audit['numeric_and_discrete_comparisons'] == 900
    assert read('verification_ls8bc/header_audit.json')['status'] == 'PASS'
    summary = read('results_ls8bc_l2_screen/summary.json')
    assert summary['status'] == 'COMPLETE_AUDITED'
    assert summary['totals']['positive_clusters'] == summary['totals']['negative_clusters'] == 0
    visits = []
    for v in summary['visits']:
        folder = ROOT / 'results_ls8bc_l2_screen' / v['file_key']
        data = parse((folder / 'lightcurve_table.bin').read_bytes())
        windows = [json.loads(line) for line in gzip.decompress((folder / 'ledger.jsonl.gz').read_bytes()).splitlines()]
        assert len(windows) == v['eligible_windows']
        valid = np.isfinite(data['flux']) & np.isfinite(data['bjd'])
        ok = valid & (data['status'] == 0)
        median = float(np.median(data['flux'][ok]))
        union = sorted({i for w in windows for i in range(w['start'], w['start'] + w['duration'])})
        assert len(union) == v['unique_event_rows']
        extrema = []
        for kind, fn in [('maximum', np.argmax), ('minimum', np.argmin)]:
            index = int(np.flatnonzero(valid)[fn(data['flux'][valid])])
            extrema.append({'kind': kind, 'row_zero_based': index, 'status': int(data['status'][index]),
                'flux_over_status_zero_visit_median': float(data['flux'][index] / median),
                'eligible_window_count_including_row': sum(w['start'] <= index < w['start'] + w['duration'] for w in windows)})
        gaps = np.diff(data['bjd']) * 86400
        cadence = v['cadence_seconds']
        visits.append({'file_key': v['file_key'], 'rows': v['rows'], 'eligible_windows': len(windows),
            'eligible_event_row_union_zero_based': union,
            'flagged_rows_zero_based': np.flatnonzero(data['status'] != 0).tolist(),
            'cadence_gap_after_rows_zero_based': np.flatnonzero((gaps < .5 * cadence) | (gaps > 1.5 * cadence)).tolist(),
            'finite_extrema_display_only': extrema})
    save('eligible_scope.json', {'source_commit': SOURCE,
        'purpose': 'Retained-data scope bookkeeping; no reselection, new scoring, fits, masks, archive access or qualified observing coverage',
        'visits': visits})
    save('release_verification.json', {'status': 'PASS', 'scientific_source_commit': SOURCE,
        'public_compare_base': inventory['base'], 'scientific_files_verified_locally': len(files),
        'files': files, 'manifests': manifests, 'input_pins': pins,
        'workflows': runs, 'independent_l2_comparisons': 900, 'numeric_disagreements': 0,
        'archive_bytes_acquired_by_this_verification': 0,
        'scope_bookkeeping': 'eligible_scope.json', 'next_cohort_rank': 23, 'next_target': 'GJ 494'})
    print(json.dumps({'status': 'PASS', 'public_files': len(files),
                      'manifest_entries': sum(m['verified_entries'] for m in manifests),
                      'input_pins': sum(p['verified_pins'] for p in pins),
                      'new_archive_bytes': 0}, indent=2))


if __name__ == '__main__':
    main()
