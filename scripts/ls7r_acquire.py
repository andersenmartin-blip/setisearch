#!/usr/bin/env python3
"""Acquire bounded CHEOPS FITS headers/metadata, never science array bytes.

Public DACE download contract: dace-query 3.0.1 CheopsClass.download().
Range support and object identity are checked on every read. Requires astropy.
"""
import argparse
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7r_metadata'
BASE = 'https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEY = 'CH_PR300024_TG000301_V0300'
TYPES = ['SCI_RAW_Imagette', 'SCI_RAW_SubArray', 'SCI_CAL_SubArray',
         'SCI_COR_SubArray', 'PIP_COR_PixelFlagMapSubArray']
ALLOWED_TABLES = {'SCI_RAW_ImagetteMetadata', 'SCI_RAW_ImageMetadata',
                  'SCI_RAW_UnstackedImageMetadata',
                  'SCI_CAL_ImageMetadata', 'SCI_COR_ImageMetadata'}
SAFE_HEADERS = {'content-length', 'content-type', 'content-range',
                'accept-ranges', 'content-disposition', 'etag', 'last-modified'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def get_url(kind):
    payload = {'fileType': kind, 'filters': {'file_key': {'equal': [KEY]}},
               'aperture': None}
    with urlopen(Request(BASE + 'download', data=json.dumps(payload).encode(),
                         headers={'Accept': 'application/json',
                                  'User-Agent': 'dace-query/3.0.1'}), timeout=45) as r:
        info = json.load(r)
    return BASE + 'download/photometry/' + info['key'] + '?compressed=false'


class Reader:
    def __init__(self, kind, url):
        self.kind, self.url = kind, url
        self.total, self.etag = None, None
        self.entries = []
        self.bytes_read = 0
        manifest = OUT / f'{kind}_ranges.json'
        self.previous = json.loads(manifest.read_text()) if manifest.exists() else None

    def read(self, start, count):
        assert 0 < count <= 20_000_000
        path = OUT / f'{self.kind}_bytes_{start}_{count}.bin'
        # Existing bytes are only reused with their exact prior provenance.
        if path.exists() and self.previous:
            previous = self.previous
            entry = next((e for e in previous['ranges'] if e['file'] == path.name), None)
            if entry and sha(path.read_bytes()) == entry['sha256']:
                self.total, self.etag = previous['total_file_bytes'], previous['etag']
                self.entries.append(entry)
                self.bytes_read += count
                return path.read_bytes()
        if self.url is None:
            raise ValueError(f'Missing verified offline range: {path.name}')
        with urlopen(Request(self.url, headers={
            'Range': f'bytes={start}-{start+count-1}',
            'Accept': 'application/octet-stream', 'Accept-Encoding': 'identity'
        }), timeout=45) as r:
            # Never fall back to a whole-file transfer if Range is ignored.
            if r.status != 206:
                raise ValueError(f'Range refused: HTTP {r.status}')
            cr = r.headers['Content-Range']
            prefix, total = cr.split('/')
            total = int(total)
            assert prefix == f'bytes {start}-{start+count-1}'
            assert int(r.headers['Content-Length']) == count
            assert start + count <= total
            etag = r.headers.get('ETag')
            if self.total is not None:
                assert total == self.total and etag == self.etag
            self.total, self.etag = total, etag
            body = r.read(count + 1)
            assert len(body) == count
            self.bytes_read += len(body)
            assert self.bytes_read <= 20_000_000
            entry = {'start': start, 'count': count, 'file': path.name,
                     'sha256': sha(body), 'status': r.status,
                     'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                     'headers': {k: v for k, v in r.headers.items()
                                 if k.lower() in SAFE_HEADERS}}
        path.write_bytes(body)
        self.entries.append(entry)
        self.checkpoint()
        return body

    def checkpoint(self):
        save_json(OUT / f'{self.kind}_ranges.json', {
            'file_key': KEY, 'file_type': self.kind,
            'download_api': BASE + 'download',
            'total_file_bytes': self.total, 'etag': self.etag,
            'ranges': self.entries})


def acquire(kind, offline=False):
    r = Reader(kind, None if offline else get_url(kind))
    offset = 0
    hdus = []
    while r.total is None or offset < r.total:
        start = offset
        header = b''
        for _ in range(64):
            block = r.read(offset, 2880)
            header += block
            offset += 2880
            if any(block[j:j+8] == b'END     ' for j in range(0, 2880, 80)):
                break
        else:
            raise ValueError('Header exceeds fixed block limit')
        h = fits.Header.fromstring(header.decode('ascii'), sep='')
        assert not h.get('GROUPS', False)
        dims = [h[f'NAXIS{i}'] for i in range(1, h['NAXIS']+1)]
        size = (abs(h['BITPIX']) // 8) * h.get('GCOUNT', 1) * (
            h.get('PCOUNT', 0) + (math.prod(dims) if dims else 0))
        name = h.get('EXTNAME', 'PRIMARY')
        hpath = OUT / f'{kind}_hdu{len(hdus):02d}_header.txt'
        hpath.write_text('\n'.join(header[i:i+80].decode('ascii')
                                   for i in range(0, len(header), 80)) + '\n')
        item = {'hdu': len(hdus), 'name': name, 'header_start': start,
                'header_bytes': len(header), 'data_start': offset,
                'data_bytes': size, 'header_file': hpath.name,
                'science_array_acquired': False}
        # Metadata is read only after EXTNAME and BINTABLE are established.
        if name in ALLOWED_TABLES:
            assert h['XTENSION'] == 'BINTABLE'
            table_bytes = r.read(offset, size)
            p = OUT / f'{kind}_hdu{len(hdus):02d}_metadata.fits'
            primary = fits.PrimaryHDU().header.tostring().encode('ascii')
            p.write_bytes(primary + header + table_bytes + b'\0' * ((-size) % 2880))
            item['metadata_file'] = p.name
            item['metadata_rows'] = h['NAXIS2']
        hdus.append(item)
        offset += size + ((-size) % 2880)
        assert offset <= r.total
    assert offset == r.total
    r.checkpoint()
    save_json(OUT / f'{kind}_hdus.json', hdus)
    print(kind, 'file bytes', r.total, 'metadata/header bytes', r.bytes_read,
          'HDUs', [(h['name'], h['data_bytes']) for h in hdus], flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true', help='Use verified saved ranges only')
    ap.add_argument('types', nargs='*', choices=TYPES)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    # Independent product reads can overlap; each product retains ordered
    # header/data dependencies. At most five products x 20 MB = 100 MB.
    kinds = list(dict.fromkeys(args.types or TYPES))
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda kind: acquire(kind, args.offline), kinds))
