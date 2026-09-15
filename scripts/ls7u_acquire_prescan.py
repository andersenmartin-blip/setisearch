#!/usr/bin/env python3
"""Acquire only the fixed virtual prescan extension; never target-image data."""
import argparse
import gzip
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits
from ls7r_acquire import BASE, KEY, SAFE_HEADERS, get_url, sha, save_json

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'results_ls7r_metadata'
OUT = ROOT / 'results_ls7u_prescan'
KIND = 'SCI_RAW_SubArray'
EXTENSION = 'SCI_RAW_OverscanLeft'
HEADER_FILE = f'{KIND}_hdu07_header.txt'
NCOLUMNS = 4
RANGES = [(86803200, 8640), (86811840, 1382400)]
LIMIT = sum(count for _, count in RANGES)


def header_check(body):
    expected = ''.join((OLD/HEADER_FILE).read_text().splitlines()).encode('ascii')
    if body != expected:
        raise ValueError('Native prescan header changed from LS7R')
    h = fits.Header.fromstring(body.decode('ascii'), sep='')
    expected_cards = {'EXTNAME': EXTENSION, 'XTENSION': 'IMAGE', 'BITPIX': -32,
        'NAXIS': 3, 'NAXIS1': NCOLUMNS, 'NAXIS2': 200, 'NAXIS3': 432,
        'PCOUNT': 0, 'GCOUNT': 1, 'BUNIT': 'ADU', 'NEXP': 14,
        'MRG_PROC': 'image', 'STACKING': 'coadd', 'ROUNDING': 0, 'NLIN_COR': False}
    for key, value in expected_cards.items():
        if h.get(key) != value:
            raise ValueError(f'Invalid prescan card: {key}')
    if h.get('BSCALE', 1) != 1 or h.get('BZERO', 0) != 0:
        raise ValueError('Unexpected scaled floating-point margin')
    return h


def read_saved(root, entry):
    blob = (root/entry['file']).read_bytes()
    if sha(blob) != entry['compressed_sha256']:
        raise ValueError('Compressed range identity mismatch')
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        body = stream.read(entry['count']+1)
    if len(body) != entry['count'] or sha(body) != entry['sha256']:
        raise ValueError('Original range identity mismatch')
    return body


def image_hdu(header, body):
    primary = fits.PrimaryHDU().header.tostring().encode('ascii')
    return fits.open(io.BytesIO(primary+header+body), memmap=False)


def acquire(offline=False):
    OUT.mkdir(exist_ok=True)
    original = json.loads((OLD/f'{KIND}_ranges.json').read_text())
    expected_etag = original['etag']
    expected_total = original['total_file_bytes']
    dispositions = {e['headers']['Content-Disposition'] for e in original['ranges']}
    if not expected_etag or len(dispositions) != 1:
        raise ValueError('Original object provenance is incomplete')
    expected_disposition = dispositions.pop()
    manifest_path = OUT/'acquisition.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if old and (old['etag'] != expected_etag or old['total_object_bytes'] != expected_total):
        raise ValueError('Cached prescan belongs to a different object')
    entries, bodies, transferred, url = [], [], 0, None
    for start, count in RANGES:
        cached = next((e for e in old['ranges'] if (e['start'],e['count']) == (start,count)), None) if old else None
        if cached:
            body = read_saved(OUT, cached)
            entry = cached
        else:
            if offline:
                raise ValueError('Offline prescan range unavailable')
            if transferred+count > LIMIT:
                raise ValueError('Fixed prescan transfer bound exceeded')
            if url is None:
                url = get_url(KIND)
            with urlopen(Request(url, headers={'Range': f'bytes={start}-{start+count-1}',
                    'Accept-Encoding': 'identity'}), timeout=45) as r:
                if (r.status != 206 or r.headers.get('Content-Range') !=
                        f'bytes {start}-{start+count-1}/{expected_total}' or
                        r.headers.get('ETag') != expected_etag or
                        r.headers.get('Content-Disposition') != expected_disposition or
                        r.headers.get('Content-Length') != str(count)):
                    raise ValueError('Prescan range or object identity refused')
                body = r.read(count+1)
                if len(body) != count:
                    raise ValueError('Prescan length mismatch')
                headers = {k:v for k,v in r.headers.items() if k.lower() in SAFE_HEADERS}
            transferred += count
            compressed = gzip.compress(body, mtime=0)
            name = f'prescan_bytes_{start}_{count}.bin.gz'
            (OUT/name).write_bytes(compressed)
            entry = {'file': name, 'start': start, 'count': count,
                'sha256': sha(body), 'compressed_sha256': sha(compressed),
                'compressed_bytes': len(compressed), 'http_status': 206,
                'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'headers': headers}
        entries.append(entry)
        bodies.append(body)
        if len(bodies) == 1:
            header_check(body)  # must pass before requesting array bytes
        save_json(manifest_path, {'file_key': KEY, 'extension': EXTENSION,
            'download_api': BASE+'download', 'etag': expected_etag,
            'total_object_bytes': expected_total, 'transfer_bound': LIMIT,
            'target_image_bytes': 0, 'virtual_reference_array_bytes':
            sum(e['count'] for e in entries if e['start'] == RANGES[1][0]),
            'ranges': entries})
    with image_hdu(*bodies) as hd:
        if hd[1].verify_checksum() != 1 or hd[1].verify_datasum() != 1:
            raise ValueError('Original prescan extension checksum mismatch')
    print(json.dumps({'verified': True, 'retained_range_bytes': LIMIT,
        'new_transfer_bytes': transferred, 'virtual_reference_array_bytes': RANGES[1][1],
        'target_image_bytes': 0}, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()
    acquire(args.offline)
