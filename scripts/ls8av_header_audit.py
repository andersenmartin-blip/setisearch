#!/usr/bin/env python3
"""Independent scalar FITS-card audit of retained LS8AV headers; no network."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'results_ls8av_l2_metadata'
OUT = ROOT / 'verification_ls8av'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def cards(raw):
    assert len(raw) % 2880 == 0
    result = {}
    for offset in range(0, len(raw), 80):
        card = raw[offset:offset + 80].decode('ascii')
        key = card[:8].strip()
        if key == 'END':
            assert raw[offset + 80:].strip(b' ') == b''
            return result
        if card[8:10] != '= ':
            continue
        value = card[10:].lstrip()
        if value.startswith("'"):
            chars = []; i = 1
            while i < len(value):
                if value[i] == "'":
                    if i + 1 < len(value) and value[i + 1] == "'":
                        chars.append("'"); i += 2; continue
                    break
                chars.append(value[i]); i += 1
            else:
                raise ValueError('unterminated FITS string')
            value = ''.join(chars).rstrip()
        else:
            value = value.split('/', 1)[0].strip()
            if value in ('T', 'F'):
                value = value == 'T'
            elif value:
                value = float(value.replace('D', 'E')) if any(x in value for x in '.ED') else int(value)
            else:
                value = None
        assert key not in result, key
        result[key] = value
    raise ValueError('missing END')


def main():
    cfg = json.loads((ROOT / 'config/ls8av_selected_pair.json').read_text())
    suite = json.loads((META / 'summary.json').read_text())
    assert suite['status'] == 'PASS_COMPATIBLE'
    assert suite['table_data_bytes_acquired'] == suite['lightcurve_values_read'] == suite['image_pixels_read'] == 0
    keys = [v['file_key'] for v in cfg['cohort']['selected_visits']]
    assert suite['selected_keys'] == keys
    manifest_count = 0
    for line in (META / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert digest((META / name).read_bytes()) == expected, name
        manifest_count += 1
    reference = json.loads((ROOT / 'results_ls8k_l2_metadata/summary.json').read_text())['products'][0]['columns']
    products = []
    for visit, p in zip(cfg['cohort']['selected_visits'], suite['products'], strict=True):
        key = visit['file_key']; folder = META / key
        assert p == json.loads((folder / 'summary.json').read_text())
        primary_raw = (folder / 'primary_header.bin').read_bytes()
        table_raw = (folder / 'lightcurve_header.bin').read_bytes()
        primary, table = cards(primary_raw), cards(table_raw)
        assert primary['SIMPLE'] is True and primary['NAXIS'] == 0
        assert table['XTENSION'] == 'BINTABLE' and table['EXTNAME'] == 'SCI_COR_Lightcurve'
        assert table['NAXIS'] == 2 and table['PCOUNT'] == 0 and table['GCOUNT'] == 1
        assert table['NAXIS1'] == p['row_bytes'] == 138
        assert table['NAXIS2'] == p['rows'] and p['rows'] > 0
        assert table['TFIELDS'] == p['fields'] == 18
        columns = [{'index': i, 'name': table[f'TTYPE{i}'], 'format': table[f'TFORM{i}'],
                    'unit': table.get(f'TUNIT{i}')} for i in range(1, 19)]
        assert columns == p['columns'] == reference
        for name, value in p['keywords'].items():
            assert table.get(name, primary.get(name)) == value, (key, name)
        assert p['keywords']['PIPE_VER'] == visit['data_pipe_version'] == '14.1.2'
        assert p['keywords']['NEXP'] == visit['obs_nexp'] == 1
        assert float(p['keywords']['EXPTIME']) == float(visit['obs_exptime']) == 60.0
        assert float(p['keywords']['TEXPTIME']) == float(visit['obs_total_exptime']) == 60.0
        start = len(primary_raw) + len(table_raw)
        count = table['NAXIS1'] * table['NAXIS2']
        assert start == p['table_data_start'] == p['header_bytes_acquired']
        assert count == p['table_bytes_declared'] and start + count <= p['total_file_bytes']
        assert p['table_data_bytes_acquired'] == p['lightcurve_values_read'] == p['image_pixels_read'] == 0
        assert p['content_disposition'].startswith('attachment; filename=' + key.rsplit('_', 1)[0] + '_TU')
        assert p['content_disposition'].endswith('_SCI_COR_Lightcurve-DEFAULT_V0300.fits')
        rr = json.loads((folder / 'ranges.json').read_text())
        assert rr['budget_bytes'] == 65536 and rr['total_bytes_read'] == start <= 65536
        assert [x['start'] for x in rr['ranges']] == list(range(0, start, 2880))
        blocks = []
        for row in rr['ranges']:
            raw = (folder / f"header_block_{row['start']:06d}.bin").read_bytes()
            h = {k.lower(): v for k, v in row['headers'].items()}
            assert len(raw) == row['count'] == 2880 and digest(raw) == row['sha256']
            assert int(h['content-length']) == 2880
            assert h['content-range'] == f"bytes {row['start']}-{row['start']+2879}/{p['total_file_bytes']}"
            assert h['etag'] == p['etag'] and h['content-disposition'] == p['content_disposition']
            blocks.append(raw)
        assert b''.join(blocks) == primary_raw + table_raw
        products.append({'file_key': key, 'rows': p['rows'], 'row_bytes': 138,
                         'table_start': start, 'table_bytes': count,
                         'header_bytes_verified': start, 'schema_columns_verified': 18,
                         'exposure_tuple': [1, 60.0, 60.0], 'identity_and_receipts_verified': True})
    result = {'status': 'PASS', 'method': 'independent 80-byte scalar FITS-card parser; no astropy or producer imports',
              'manifest_entries_verified': manifest_count, 'products': products,
              'science_values_read': 0, 'image_pixels_read': 0}
    OUT.mkdir(exist_ok=True)
    (OUT / 'header_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
