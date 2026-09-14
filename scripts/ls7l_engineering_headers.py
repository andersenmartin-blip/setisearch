#!/usr/bin/env python3
"""Bounded HTTP-range FITS header inventory; no science-value selection."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits
from astropy.io.fits.card import Undefined

ROOT = Path(__file__).resolve().parents[1]


class RangeReader:
    def __init__(self, url, out, cap=16_000_000):
        self.url, self.out, self.cap = url, Path(out), cap
        self.used, self.records = 0, []
        self.out.mkdir(parents=True, exist_ok=True)
        with urlopen(Request(url, method='HEAD'), timeout=30) as r:
            self.size = int(r.headers['Content-Length'])
            self.etag = r.headers.get('ETag')
            self.modified = r.headers.get('Last-Modified')

    def get(self, start, size, label):
        assert 0 <= start < self.size and 0 < size <= 8_000_000
        size = min(size, self.size-start)
        assert self.used + size <= self.cap, 'fixed byte budget exhausted'
        headers = {'Range': f'bytes={start}-{start+size-1}'}
        if self.etag and not self.etag.startswith('W/'):
            headers['If-Range'] = self.etag
        elif self.modified:
            headers['If-Range'] = self.modified
        with urlopen(Request(self.url, headers=headers), timeout=30) as r:
            assert r.status == 206, 'range access not honored; no full download permitted'
            assert r.headers['Content-Range'] == f'bytes {start}-{start+size-1}/{self.size}'
            assert r.headers.get('ETag') == self.etag
            assert r.headers.get('Last-Modified') == self.modified
            data = r.read(size+1)
            assert len(data) == size
        self.used += size
        path = self.out / label
        path.write_bytes(data)
        self.records.append({'start': start, 'bytes': size, 'path': label,
                             'sha256': hashlib.sha256(data).hexdigest()})
        return data


def inspect(url, out):
    reader = RangeReader(url, out)
    offset, hdus = 0, []
    while offset < reader.size:
        assert len(hdus) < 128
        blocks = []
        for block in range(90):
            data = reader.get(offset+block*2880, 2880, f'hdu{len(hdus):03d}_block{block:03d}.bin')
            blocks.append(data)
            if any(data[i:i+8] == b'END     ' for i in range(0, len(data), 80)):
                break
        else:
            raise ValueError('header exceeds fixed cap')
        raw = b''.join(blocks)
        h = fits.Header.fromstring(raw.decode('ascii'), sep='')
        axes = [h[f'NAXIS{i}'] for i in range(1, h['NAXIS']+1)]
        count = math.prod(axes) if axes else 0
        data_size = (abs(h['BITPIX'])//8 * count + h.get('PCOUNT', 0)) * h.get('GCOUNT', 1)
        hdus.append({'index': len(hdus), 'header_offset': offset, 'header_bytes': len(raw),
                     'data_offset': offset+len(raw), 'data_bytes': data_size,
                     'cards': [{'key': c.keyword, 'value': None if isinstance(c.value, Undefined) else c.value,
                                'comment': c.comment} for c in h.cards]})
        offset += len(raw) + (data_size+2879)//2880*2880
    assert offset == reader.size
    result = {'url': url, 'source_bytes': reader.size, 'etag': reader.etag,
              'last_modified': reader.modified, 'downloaded_bytes': reader.used,
              'ranges': reader.records, 'hdus': hdus, 'full_file_sha256': None,
              'identity_scope': 'HTTP validators, complete header chain and individual range hashes; not a complete-file hash'}
    (Path(out)/'headers.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='results_ls7l_engineering')
    args = p.parse_args()
    out = Path(args.output)
    assert not out.exists(), 'refuse to overwrite input evidence'
    products = json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())['engineering']['selected_links']
    for product in products:
        result = inspect(product['url'], out/product['name'])
        summaries = []
        for item in result['hdus']:
            h = {c['key']: c['value'] for c in item['cards']}
            summaries.append({'hdu': item['index'], 'name': h.get('EXTNAME'), 'rows': h.get('NAXIS2'),
                              'row_bytes': h.get('NAXIS1'), 'time_system': h.get('TIMESYS'),
                              'time_reference': h.get('TIMEREF'),
                              'fields': [h.get(f'TTYPE{i}') for i in range(1, h.get('TFIELDS', 0)+1)]})
        print(json.dumps({'product': product['name'], 'bytes_read': result['downloaded_bytes'], 'hdus': summaries}), flush=True)


if __name__ == '__main__':
    main()
