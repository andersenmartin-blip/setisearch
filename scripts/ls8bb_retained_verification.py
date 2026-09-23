#!/usr/bin/env python3
"""Offline receipt/overlap verification and a readable retained-map overview.

No acquisition, event fitting, classification or threshold change.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results_ls8bb_images'
OUT = ROOT / 'verification_ls8bb_retained'
MANIFEST_PIN = 'de0e33fcd3ee90556097cbbc62223026000ef6a7a3b23a01d085c11762d3a4a6'
SCOPE_PIN = '4de10b41be1da7aaea49c96d02dc9f12c1df34a67b95f77b50c0d9771bbabb85'


def main():
    assert os.environ.get('GITHUB_SHA') == subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    assert not OUT.exists(), 'preserve any earlier verification outcome'
    OUT.mkdir()
    # The exact audited result and public manifest are pinned by the protocol.
    assert hashlib.sha256((SOURCE / 'SHA256SUMS').read_bytes()).hexdigest() == MANIFEST_PIN
    entries = 0
    for line in (SOURCE / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
        entries += 1
    assert json.loads((SOURCE / 'audit.json').read_text())['status'] == 'PASS'
    cfg = json.loads((ROOT / 'config/ls8bb_images.json').read_text())
    assert hashlib.sha256((ROOT / 'config/ls8bb_images.json').read_bytes()).hexdigest() == SCOPE_PIN
    assert [c['id'] for c in cfg['contexts']] == ['TG010801_P0', 'TG010801_N0']
    positive, negative = cfg['contexts']
    assert (positive['lo'], positive['hi'], negative['lo'], negative['hi']) == (11, 40, 10, 39)
    receipts = []; overlaps = []
    for kind, frame in [('SCI_CAL_SubArray', 320000), ('SCI_COR_SubArray', 320000), ('SMEAR', 1600)]:
        cubes = []
        for context in (positive, negative):
            path = SOURCE / context['id'] / (kind + '.bin.gz')
            packed = path.read_bytes(); raw = gzip.decompress(packed)
            record = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            assert hashlib.sha256(packed).hexdigest() == record['gzip_sha256']
            assert hashlib.sha256(raw).hexdigest() == record['raw_sha256']
            assert len(raw) == record['count'] == context['ranges'][kind]['count'] == 29 * frame
            assert record['start'] == context['ranges'][kind]['start'] and record['status'] == 206
            receipts.append({'path': str(path.relative_to(ROOT)), 'packed_sha256': record['gzip_sha256'],
                             'raw_sha256': record['raw_sha256'], 'raw_bytes': len(raw), 'status': 'PASS'})
            cubes.append(raw)
        assert positive['ranges'][kind]['start'] - negative['ranges'][kind]['start'] == frame
        assert cubes[0][:-frame] == cubes[1][frame:]
        overlaps.append({'kind': kind, 'shared_rows': 28, 'shared_bytes': 28 * frame,
                         'shared_sha256': hashlib.sha256(cubes[0][:-frame]).hexdigest(),
                         'distinct_union_rows': 30, 'distinct_union_bytes': 30 * frame, 'byte_exact': True})
    diagnostics = json.loads((SOURCE / 'diagnostics.json').read_text())
    assert [d['id'] for d in diagnostics] == [c['id'] for c in cfg['contexts']]
    fig = plt.figure(figsize=(14, 8))
    grid = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, .045], left=.055, right=.94,
                           bottom=.075, top=.92, wspace=.29, hspace=.32)
    for row, event in enumerate(diagnostics):
        with np.load(SOURCE / event['id'] / 'event_maps.npz') as arrays:
            maps = {k: arrays[k].copy() for k in ('CAL', 'COR', 'DELTA')}
        limit = max(float(np.max(np.abs(a[np.isfinite(a)]))) for a in maps.values())
        assert np.isfinite(limit) and limit > 0
        for column, (kind, values) in enumerate(maps.items()):
            ax = fig.add_subplot(grid[row, column])
            im = ax.imshow(values, origin='lower', cmap='RdBu_r', vmin=-limit, vmax=limit)
            for name, style in [('C0', '-'), ('C1', '--')]:
                ax.add_patch(Circle(event['conventions'][name]['center'], 25, fill=False,
                                    color='#222222', linestyle=style, linewidth=.9))
            ax.set_title(event['id'] + ' · ' + kind, fontsize=11)
            ax.set_xlabel('Native x pixel', fontsize=9); ax.set_ylabel('Native y pixel', fontsize=9)
            ax.tick_params(labelsize=8)
        bar = fig.colorbar(im, cax=fig.add_subplot(grid[row, 3]))
        bar.set_label('Event residual sum [native ADU]', fontsize=9); bar.ax.tick_params(labelsize=8)
    fig.suptitle('LS8BB · both original signed events · CORRECTION_LINKED', fontsize=14)
    fig.text(.5, .018, 'Common signed scale within each row; solid/dashed circles: original C0/C1 apertures.',
             ha='center', fontsize=9)
    fig.savefig(OUT / 'paired_image_review.png', dpi=130); plt.close(fig)
    result = {'status': 'PASS', 'source_result_commit': '0031edaebfcb221bd9b381fb524ace39d3f91342',
              'source_manifest_entries_verified': entries, 'payload_receipts': receipts,
              'exact_overlap_checks': overlaps, 'new_archive_bytes': 0, 'native_fits_repeated': False,
              'original_labels_unchanged': {e['id']: e['classification'] for e in diagnostics},
              'overview': 'Same retained maps, signs, scales per event, centers and apertures; layout only.'}
    (OUT / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
