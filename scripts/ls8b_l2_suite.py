#!/usr/bin/env python3
"""Bounded LS8B acquisition and unchanged LS7X/LS8A transfer. No images."""
import argparse
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits
from seti_repeater.cheops_l2 import DURATIONS, GUARD, SCREEN, SIDE, cluster_positive, score_window
from ls8a_l2_evaluate import dtype

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'results_ls8b_l2_metadata'
OUT = ROOT / 'results_ls8b_l2_suite'
BASE = 'https://cheops-webapp-pg.obsuksprd2.unige.ch/'
VISITS = (
    ('100006000302', 1310135, 'CH_PR100006_TG000302_V0300'),
    ('100006000303', 1310137, 'CH_PR100006_TG000303_V0300'),
    ('100006000304', 1319869, 'CH_PR100006_TG000304_V0300'),
    ('100006000305', 1319870, 'CH_PR100006_TG000305_V0300'),
)
PINS = {
    'src/seti_repeater/cheops_l2.py': '33e6b2dc5ea704e1f867bc397c580564b3543f3f47f00d2e847dd7cfbe46d546',
    'scripts/ls8a_l2_evaluate.py': '0258061b00e1591e0dd728bc37f4b4ccbeb5eb6ea0d8a23f723c738aab5be976',
    'scripts/ls8a_l2_audit.py': 'd98ab8c538b1287d8bae45ba8d4f011bc37b82901197a5346c8c871babb6c736',
    'tests/test_ls7x_l2.py': '141eca01b0b32ff8856b30d44ad894abf8912fb90c36ebfcdaf6089c6d344ef9',
    'LS8B_FOUR_VISIT_SCOPE.md': 'e2f3041677217071538560c08ee143462f95fa7eccdabbeb83f1fdf0fb71f928',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def manifest(directory):
    paths = sorted(p for p in directory.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (directory / 'SHA256SUMS').write_text(''.join(
        f'{sha(p.read_bytes())}  {p.relative_to(directory)}\n' for p in paths))


def verify_manifest(directory):
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha((directory / name).read_bytes()) == expected, name


def verify_inputs():
    for name, expected in PINS.items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    assert (SIDE, GUARD, DURATIONS, SCREEN) == (12, 2, (1, 2, 3), 8.5)
    inventory = json.loads((ROOT / 'results_ls7r_metadata/archive_visits.json').read_text())
    rows = [dict(zip(inventory['columns'], row)) for row in inventory['rows']]
    chosen = sorted((r for r in rows if r['proprietary'] == 'PUBLIC' and
                     r['obs_start'] > '2020-12-01T14:06:00'), key=lambda r: (r['obs_start'], r['visit_id']))[:4]
    assert [(r['visit_id'], int(r['obsid'])) for r in chosen] == [(v, o) for v, o, _ in VISITS]


def get_url(key):
    payload = {'fileType': 'lightcurves', 'filters': {'file_key': {'equal': [key]}}, 'aperture': 'default'}
    request = Request(BASE + 'download', data=json.dumps(payload).encode(),
                      headers={'Accept': 'application/json', 'User-Agent': 'dace-query/3.0.1'})
    with urlopen(request, timeout=45) as response:
        info = json.load(response)
    if not isinstance(info.get('key'), str) or not info['key']:
        raise RuntimeError('exact DEFAULT lightcurve unavailable: ' + key)
    return BASE + 'download/photometry/' + info['key'] + '?compressed=false'


def read_range(url, start, count, identity=None):
    headers = {'Range': f'bytes={start}-{start+count-1}', 'Accept': 'application/octet-stream',
               'Accept-Encoding': 'identity'}
    if identity:
        headers['If-Match'] = identity['etag']
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        assert response.status == 206
        prefix, total = response.headers['Content-Range'].split('/')
        assert prefix == f'bytes {start}-{start+count-1}'
        assert int(response.headers['Content-Length']) == count
        now = {'total': int(total), 'etag': response.headers.get('ETag'),
               'content_disposition': response.headers.get('Content-Disposition')}
        assert now['etag'] and now['content_disposition']
        if identity:
            assert now == identity, (now, identity)
        raw = response.read(count + 1)
        assert len(raw) == count
        return raw, now, {'start': start, 'count': count, 'sha256': sha(raw),
                         'status': response.status, 'content_range': response.headers['Content-Range'],
                         **now, 'retrieved_utc': datetime.now(timezone.utc).isoformat()}


def header(url, start, identity, receipts):
    raw = b''
    for _ in range(16):
        assert (len(receipts) + 1) * 2880 <= 65536
        block, identity, receipt = read_range(url, start + len(raw), 2880, identity)
        receipts.append(receipt)
        raw += block
        if any(block[i:i+8] == b'END     ' for i in range(0, 2880, 80)):
            return raw, start + len(raw), identity
    raise RuntimeError('header exceeds bound')


def metadata():
    verify_inputs()
    assert not META.exists(), 'refuse metadata overwrite'
    META.mkdir()
    summaries = []
    for visit, obsid, key in VISITS:
        directory = META / key
        directory.mkdir()
        receipts = []
        try:
            url = get_url(key)
            primary, offset, identity = header(url, 0, None, receipts)
            h0 = fits.Header.fromstring(primary.decode('ascii'), sep='')
            assert h0['SIMPLE'] is True and h0['NAXIS'] == 0
            table, start, identity = header(url, offset, identity, receipts)
            h1 = fits.Header.fromstring(table.decode('ascii'), sep='')
            assert h1['XTENSION'] == 'BINTABLE' and h1['EXTNAME'] == 'SCI_COR_Lightcurve'
            assert h1.get('PCOUNT', 0) == 0
            assert key.replace('_V0300', '_TU') in identity['content_disposition']
            assert 'SCI_COR_Lightcurve-DEFAULT_V0300.fits' in identity['content_disposition']
            count = h1['NAXIS1'] * h1['NAXIS2']
            assert start == sum(r['count'] for r in receipts)
            assert start + count <= identity['total']
            dt = dtype(h1)
            assert {'BJD_TIME', 'FLUX', 'FLUXERR', 'STATUS', 'EVENT'} <= set(dt.names)
            columns = [{'name': h1[f'TTYPE{i}'], 'format': h1[f'TFORM{i}'], 'unit': h1.get(f'TUNIT{i}')}
                       for i in range(1, h1['TFIELDS'] + 1)]
            units = {c['name']: c['unit'] for c in columns}
            assert units['FLUX'] == units['FLUXERR'] == 'electrons'
            keys = ['EXT_VER', 'PIPE_VER', 'AP_RADI', 'NEXP', 'EXPTIME', 'TEXPTIME',
                    'TIMESYS', 'T_STRT_U', 'T_STOP_U', 'CHECKSUM', 'DATASUM']
            keywords = {k: h1.get(k, h0.get(k)) for k in keys}
            assert np.isfinite(keywords['TEXPTIME']) and keywords['TEXPTIME'] > 0
            (directory / 'primary_header.bin').write_bytes(primary)
            (directory / 'lightcurve_header.bin').write_bytes(table)
            summary = {'status': 'METADATA_ONLY', 'visit_id': visit, 'obsid': obsid, 'file_key': key,
                       'aperture': 'DEFAULT', **identity, 'table_data_start': start,
                       'table_bytes_declared': count, 'rows': h1['NAXIS2'], 'row_bytes': h1['NAXIS1'],
                       'header_bytes_acquired': start, 'table_data_bytes_acquired': 0,
                       'keywords': keywords, 'columns': columns}
            save(directory / 'summary.json', summary)
        except Exception as exc:
            summary = {'status': 'BLOCKED', 'visit_id': visit, 'obsid': obsid, 'file_key': key,
                       'error_type': type(exc).__name__, 'reason': str(exc), 'table_data_bytes_acquired': 0}
            save(directory / 'obstruction.json', summary)
        save(directory / 'ranges.json', receipts)
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    save(META / 'summary.json', {'stage': 'LS8B_METADATA', 'status': 'PASS' if all(
        s['status'] == 'METADATA_ONLY' for s in summaries) else 'BLOCKED', 'visits': summaries,
        'selection_freeze': '45bf61fb8fd2883124bd481ddeadc6e8e37f86ea',
        'table_data_bytes_acquired': 0, 'substituted_visits': 0})
    manifest(META)


def signed_clusters(rows, sign):
    groups = cluster_positive([{**r, 'score': sign * r['score']} for r in rows], SCREEN)
    result = []
    for number, group in enumerate(groups):
        representative = dict(group['representative'])
        representative['score'] *= sign
        result.append({'cluster_id': number, 'min_start': group['min_start'], 'max_end': group['max_end'],
                       'representative': representative, 'members': [
                           {'start': r['start'], 'duration': r['duration'], 'score': sign * r['score']}
                           for r in group['members']]})
    return result


def evaluate(freeze):
    verify_inputs()
    verify_manifest(META)
    metadata_summary = json.loads((META / 'summary.json').read_text())
    assert metadata_summary['status'] == 'PASS'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == freeze
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT)
    assert not OUT.exists(), 'refuse evaluated suite overwrite'
    OUT.mkdir()
    summaries = []
    for _, _, key in VISITS:
        m = json.loads((META / key / 'summary.json').read_text())
        assert m['status'] == 'METADATA_ONLY' and m['table_data_bytes_acquired'] == 0
        h = fits.Header.fromstring((META / key / 'lightcurve_header.bin').read_bytes().decode('ascii'), sep='')
        raw, _, receipt = read_range(get_url(key), m['table_data_start'], m['table_bytes_declared'],
                                    {k: m[k] for k in ['total', 'etag', 'content_disposition']})
        directory = OUT / key
        directory.mkdir()
        (directory / 'lightcurve_table.bin').write_bytes(raw)
        save(directory / 'source.json', receipt)
        table = np.frombuffer(raw, dtype=dtype(h), count=m['rows'])
        cadence = float(m['keywords']['TEXPTIME'])
        rows = []
        for duration in DURATIONS:
            for start in range(len(table) - duration + 1):
                row = score_window(table['BJD_TIME'], table['FLUX'], table['FLUXERR'], table['STATUS'],
                                   table['EVENT'], start, duration, cadence)
                if row is not None:
                    rows.append(row)
        (directory / 'ledger.jsonl.gz').write_bytes(gzip.compress(''.join(
            json.dumps(r, sort_keys=True, allow_nan=False) + '\n' for r in rows).encode(), mtime=0))
        positive, negative = signed_clusters(rows, 1), signed_clusters(rows, -1)
        save(directory / 'clusters.json', {'positive': positive, 'negative': negative})
        per_duration = []
        for duration in DURATIONS:
            selected = [r for r in rows if r['duration'] == duration]
            per_duration.append({'duration_rows': duration, 'duration_seconds': duration * cadence,
                                 'eligible_windows': len(selected),
                                 'positive_windows': sum(r['score'] >= SCREEN for r in selected),
                                 'negative_windows': sum(r['score'] <= -SCREEN for r in selected)})
        union = {i for r in rows for i in r['event_indices']}
        summary = {'file_key': key, 'rows': len(table), 'cadence_seconds': cadence,
                   'eligible_windows': len(rows), 'duration_results': per_duration,
                   'positive_windows': sum(r['score'] >= SCREEN for r in rows),
                   'negative_windows': sum(r['score'] <= -SCREEN for r in rows),
                   'positive_clusters': len(positive), 'negative_clusters': len(negative),
                   'maximum_score': max((r['score'] for r in rows), default=None),
                   'minimum_score': min((r['score'] for r in rows), default=None),
                   'unique_event_rows': len(union), 'eligible_event_row_union_seconds': len(union) * cadence}
        save(directory / 'summary.json', summary)
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    save(OUT / 'summary.json', {'stage': 'LS8B_FOUR_VISIT_TRANSFER', 'status': 'COMPLETE_UNAUDITED',
         'evaluation_freeze_commit': freeze, 'method_pins': PINS, 'visits': summaries,
         'screen_threshold': SCREEN, 'other_apertures_opened': False, 'image_bytes_acquired': 0,
         'detector_qualified': False, 'candidate_claims': 0,
         'interpretation': 'Descriptive transfer and tail behavior; overlapping windows are not independent.'})
    manifest(OUT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['metadata', 'evaluate'])
    parser.add_argument('--freeze')
    args = parser.parse_args()
    if args.stage == 'metadata':
        metadata()
    else:
        assert args.freeze and len(args.freeze) == 40
        evaluate(args.freeze)
