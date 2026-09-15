#!/usr/bin/env python3
"""Bounded, product-specific instrument telemetry acquisition; no image HDUs."""
import argparse
import json
from pathlib import Path

import ls7r_acquire as base
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7t_contract'
KIND = 'SCI_RAW_HkExtended'
EXPECTED = 'CH_PR300024_TG000301_TU2020-03-09T04-54-45_SCI_RAW_HkExtended_V0300.fits'
LIMIT = 5_000_000


class BoundedReader(base.Reader):
    def read(self, start, count):
        if count <= 0 or self.bytes_read + count > LIMIT:
            raise ValueError('LS7T five-megabyte acquisition limit exceeded')
        data = super().read(start, count)
        if self.total > LIMIT:
            raise ValueError('Unexpected oversized housekeeping product')
        disposition = self.entries[-1]['headers'].get('Content-Disposition', '')
        if EXPECTED not in disposition:
            raise ValueError('Unexpected visit/product identity')
        return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    base.OUT = OUT
    reader = BoundedReader(KIND, None if args.offline else base.get_url(KIND))
    offset, hdus = 0, []
    for index in range(2):
        start, header = offset, b''
        for _ in range(64):
            block = reader.read(offset, 2880)
            header += block
            offset += 2880
            if any(block[k:k+8] == b'END     ' for k in range(0, 2880, 80)):
                break
        else:
            raise ValueError('Header block limit exceeded')
        h = fits.Header.fromstring(header.decode('ascii'), sep='')
        if index == 0:
            if not h.get('SIMPLE') or h['NAXIS'] != 0:
                raise ValueError('Unexpected primary HDU')
            size = 0
        else:
            if h.get('XTENSION') != 'BINTABLE' or h.get('EXTNAME') != KIND:
                raise ValueError('Unexpected instrument table')
            if h.get('PCOUNT', 0) != 0 or h.get('GCOUNT', 1) != 1:
                raise ValueError('Variable-length heap not allowed')
            if h['BITPIX'] != 8 or h['NAXIS'] != 2:
                raise ValueError('Unexpected table geometry')
            for col in range(1, h['TFIELDS'] + 1):
                if 'P' in h[f'TFORM{col}'] or 'Q' in h[f'TFORM{col}']:
                    raise ValueError('Variable-length column not allowed')
            size = h['NAXIS1'] * h['NAXIS2']
            if offset + size + (-size) % 2880 != reader.total:
                raise ValueError('Unexpected trailing HDU or geometry')
        hpath = OUT / f'{KIND}_hdu{index:02d}_header.txt'
        hpath.write_text('\n'.join(header[k:k+80].decode('ascii')
                                    for k in range(0, len(header), 80)) + '\n')
        item = {'hdu': index, 'name': h.get('EXTNAME', 'PRIMARY'),
                'header_start': start, 'header_bytes': len(header),
                'data_start': offset, 'data_bytes': size,
                'header_file': hpath.name, 'science_array_acquired': False}
        if size:
            body = reader.read(offset, size)
            path = OUT / f'{KIND}_hdu{index:02d}_metadata.fits'
            path.write_bytes(fits.PrimaryHDU().header.tostring().encode('ascii')
                             + header + body + b'\0' * ((-size) % 2880))
            item.update(metadata_file=path.name, metadata_rows=h['NAXIS2'])
        hdus.append(item)
        offset += size + (-size) % 2880
    if offset != reader.total:
        raise ValueError('Unexpected trailing product bytes')
    reader.checkpoint()
    base.save_json(OUT / f'{KIND}_hdus.json', hdus)
    print(json.dumps({'file_bytes': reader.total, 'retained_bytes': reader.bytes_read,
                      'hdus': hdus}, indent=2))


if __name__ == '__main__':
    main()
