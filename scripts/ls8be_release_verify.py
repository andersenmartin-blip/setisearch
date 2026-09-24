#!/usr/bin/env python3
"""Offline LS8BD/LS8BE release identities and scope bookkeeping; no scientific refit."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess

import numpy as np
from ls8k_l2_audit import parse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification_ls8be'
SOURCE = '8f376712060244153b92ee462d7f54115ac8d58f'


def read(path):
    return json.loads((ROOT / path).read_text())


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def main():
    inventory = read('verification_ls8be/public_file_inventory.json')
    assert inventory['head'] == SOURCE and inventory['total_commits'] == 8
    assert len(inventory['files']) == 157
    local = subprocess.check_output(['git', 'diff', '--name-only', inventory['base'], SOURCE],
                                    cwd=ROOT, text=True).splitlines()
    assert sorted(local) == sorted(f['path'] for f in inventory['files'])
    unavailable = {f['path']: f for f in inventory['unavailable_locally']}
    assert set(unavailable) == {
        'results_ls8be_images/TG007401_P0/SCI_CAL_SubArray.bin.gz',
        'results_ls8be_images/TG007401_P0/SCI_COR_SubArray.bin.gz'}
    files = []
    for f in inventory['files']:
        assert f['status'] == 'added'
        if f['path'] in unavailable and not (ROOT / f['path']).exists():
            assert unavailable[f['path']]['sha'] == f['sha']
            receipt = read(f['path'] + '.json')
            files.append({'path': f['path'], 'git_blob': f['sha'],
                'sha256': receipt['gzip_sha256'], 'raw_sha256': receipt['raw_sha256'],
                'raw_bytes': receipt['count'], 'verification': 'published independent CI audit; unavailable locally'})
            continue
        raw = (ROOT / f['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == f['sha'], f['path']
        files.append({'path': f['path'], 'git_blob': blob,
                      'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'verification': 'local bytes'})
    manifests = []
    for folder in ['results_ls8bd_l2_metadata', 'results_ls8bd_l2_screen', 'results_ls8be_metadata', 'results_ls8be_images']:
        entries = (ROOT / folder / 'SHA256SUMS').read_text().splitlines()
        local_entries = 0; ci_entries = 0
        for line in entries:
            expected, name = line.split('  ', 1)
            relative = folder + '/' + name
            if relative in unavailable and not (ROOT / relative).exists():
                assert read(relative + '.json')['gzip_sha256'] == expected
                ci_entries += 1
            else:
                assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
                local_entries += 1
        manifests.append({'path': folder + '/SHA256SUMS', 'entries': len(entries),
            'verified_locally': local_entries, 'verified_in_published_independent_CI_audit': ci_entries})
    pins = []
    for name in ['config/ls8bd_selected_pair.json', 'config/ls8bd_l2_scope.json', 'config/ls8be_representatives.json', 'config/ls8be_payload_scope.json']:
        cfg = read(name)
        for relative, expected in cfg['input_pins'].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
        pins.append({'config': name, 'verified_pins': len(cfg['input_pins'])})
    runs = read('verification_ls8be/workflow_runs.json')
    assert {r['head_sha'] for r in runs} == {
        'c536c25eea1cc0609fd3158ffb5c80e71392da4c',
        '905b30a6800a804eef5862e8924636141444306f',
        '5fcf8e4e89cc06b68493203fb25eba03e2dc6fad',
        'a2b1b19a49b37b5e1b2bac5e64e62105c23e6352'}
    assert all(r['status'] == 'completed' and r['conclusion'] == 'success' for r in runs)
    audit = read('results_ls8bd_l2_screen/audit.json')
    assert audit['status'] == 'PASS' and not audit['numeric_disagreements']
    assert audit['numeric_and_discrete_comparisons'] == 1980
    assert read('verification_ls8bd/header_audit.json')['status'] == 'PASS'
    summary = read('results_ls8bd_l2_screen/summary.json')
    assert summary['status'] == 'COMPLETE_AUDITED'
    assert summary['totals']['positive_clusters'] == 1 and summary['totals']['negative_clusters'] == 0
    image_audit = read('results_ls8be_images/audit.json')
    assert image_audit['status'] == 'PASS' and not image_audit['disagreements']
    assert image_audit['comparisons'] == {'numeric': 94537, 'exact': 160581}
    meta_audit = read('results_ls8be_metadata/audit.json')
    assert meta_audit == {'status': 'PASS', 'joined_rows': 58, 'exact_checks': 269, 'image_bytes_read': 0}
    image_summary = read('results_ls8be_images/summary.json')
    assert image_summary['status'] == 'COMPLETE_AUDITED' and image_summary['outcomes'] == {'CORRECTION_LINKED': 1}
    image_cfg = read('config/ls8be_images.json')
    receipts = []
    context = image_cfg['contexts'][0]
    for kind in ['SCI_CAL_SubArray', 'SCI_COR_SubArray', 'SMEAR']:
        name = 'results_ls8be_images/TG007401_P0/' + kind + '.bin.gz'
        rec = read(name + '.json')
        product = 'SCI_COR_SubArray' if kind == 'SMEAR' else kind
        spec = image_cfg['sources'][context['file_key']][product]
        assert rec['status'] == 206 and rec['attempts'] == 1 and not rec['prior_transport_failures']
        assert rec['start'] == context['ranges'][kind]['start'] and rec['count'] == context['ranges'][kind]['count']
        assert (rec['etag'], rec['total'], rec['content_disposition']) == (spec['etag'], spec['total'], spec['content_disposition'])
        if (ROOT / name).exists():
            compressed = (ROOT / name).read_bytes(); raw = gzip.decompress(compressed)
            assert hashlib.sha256(compressed).hexdigest() == rec['gzip_sha256']
            assert len(raw) == rec['count'] and hashlib.sha256(raw).hexdigest() == rec['raw_sha256']
        receipts.append({'path': name, 'raw_bytes': rec['count'], 'raw_sha256': rec['raw_sha256'],
                         'gzip_sha256': rec['gzip_sha256'], 'available_locally': (ROOT / name).exists()})
    metadata_bytes = sum(row['count'] for p in (ROOT / 'results_ls8be_metadata').rglob('*_ranges.json')
                         for row in json.loads(p.read_text())['ranges'])
    visits = []
    for v in summary['visits']:
        folder = ROOT / 'results_ls8bd_l2_screen' / v['file_key']
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
    save('release_verification.json', {'status': 'PASS_LOCAL_FILES_AND_PUBLISHED_CI_EVIDENCE', 'scientific_source_commit': SOURCE,
        'public_compare_base': inventory['base'], 'scientific_files_published': len(files),
        'scientific_files_verified_locally': sum(f['verification'] == 'local bytes' for f in files),
        'large_files_verified_in_published_CI': len(unavailable),
        'files': files, 'manifests': manifests, 'input_pins': pins,
        'image_audit': image_audit, 'metadata_audit': meta_audit, 'image_receipts': receipts,
        'image_metadata_bytes_acquired': metadata_bytes,
        'workflows': runs, 'independent_l2_comparisons': 1980, 'numeric_disagreements': 0,
        'archive_bytes_acquired_by_this_verification': 0,
        'scope_bookkeeping': 'eligible_scope.json', 'next_cohort_rank': 24, 'next_target': '2MASS J11474440+0048164'})
    print(json.dumps({'status': 'PASS_LOCAL_FILES_AND_PUBLISHED_CI_EVIDENCE', 'public_files': len(files),
                      'large_files_unavailable_locally': len(unavailable),
                      'manifest_entries_verified_locally': sum(m['verified_locally'] for m in manifests),
                      'input_pins': sum(p['verified_pins'] for p in pins),
                      'new_archive_bytes': 0}, indent=2))


if __name__ == '__main__':
    main()
